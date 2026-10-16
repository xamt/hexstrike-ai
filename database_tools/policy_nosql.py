"""Redis 与 MongoDB 的查询及受限新增更新策略；删除和未知能力不执行。"""
import math

from .policy_errors import OperationNotAllowed


REDIS_READ_COMMANDS = frozenset("""
PING ECHO GET MGET GETRANGE STRLEN SUBSTR EXISTS TYPE TTL PTTL EXPIRETIME
PEXPIRETIME DBSIZE KEYS SCAN RANDOMKEY DUMP HGET HGETALL HMGET HEXISTS HKEYS
HLEN HSTRLEN HVALS HSCAN HRANDFIELD LLEN LINDEX LRANGE LPOS SCARD SISMEMBER
SMISMEMBER SMEMBERS SRANDMEMBER SSCAN SDIFF SINTER SUNION SINTERCARD ZCARD
ZCOUNT ZLEXCOUNT ZRANGE ZRANGEBYSCORE ZRANGEBYLEX ZREVRANGE ZREVRANGEBYSCORE
ZREVRANGEBYLEX ZRANK ZREVRANK ZSCORE ZMSCORE ZSCAN ZRANDMEMBER ZDIFF ZINTER
ZUNION ZINTERCARD GEODIST GEOHASH GEOPOS GEOSEARCH SORT_RO XLEN XRANGE
XREVRANGE XREAD XPENDING INFO ROLE LASTSAVE TIME
""".split())

REDIS_READ_SUBCOMMANDS = {
    "ACL": {"CAT", "GETUSER", "LIST", "USERS", "WHOAMI"},
    "CONFIG": {"GET"},
    "CLIENT": {"LIST", "INFO", "ID", "GETNAME", "TRACKINGINFO"},
    "MEMORY": {"USAGE", "STATS", "DOCTOR", "MALLOC-STATS"},
    "OBJECT": {"ENCODING", "IDLETIME", "FREQ", "REFCOUNT"},
    "XINFO": {"CONSUMERS", "GROUPS", "STREAM"},
    "PUBSUB": {"CHANNELS", "NUMSUB", "NUMPAT", "SHARDCHANNELS", "SHARDNUMSUB"},
    "COMMAND": {"INFO", "DOCS", "COUNT", "GETKEYS", "GETKEYSANDFLAGS", "LIST"},
    "CLUSTER": {"INFO", "NODES", "SLOTS", "SHARDS", "MYID", "MYSHARDID", "KEYSLOT",
                "COUNTKEYSINSLOT", "GETKEYSINSLOT", "LINKS", "REPLICAS", "SLAVES"},
}

MONGO_FIELDS = {
    "find": "filter sort projection hint skip limit batchSize singleBatch maxTimeMS max min "
            "returnKey showRecordId tailable awaitData noCursorTimeout allowPartialResults "
            "collation readConcern comment let allowDiskUse",
    "count": "query limit skip hint maxTimeMS readConcern collation comment",
    "distinct": "key query readConcern collation maxTimeMS comment",
    "listCollections": "filter nameOnly authorizedCollections cursor comment",
    "listIndexes": "cursor maxTimeMS comment",
    "listDatabases": "filter nameOnly authorizedDatabases comment",
    "ping": "",
    "hello": "helloOk maxAwaitTimeMS topologyVersion",
    "buildInfo": "",
    "connectionStatus": "showPrivileges",
    "dbStats": "scale freeStorage",
    "collStats": "scale",
    "serverStatus": "",
    "usersInfo": "showCredentials showPrivileges showAuthenticationRestrictions filter comment",
    "rolesInfo": "showPrivileges showBuiltinRoles showAuthenticationRestrictions comment",
    "aggregate": "pipeline cursor allowDiskUse maxTimeMS hint readConcern collation let comment",
    "insert": "documents ordered comment maxTimeMS",
    "update": "updates ordered comment maxTimeMS",
}
MONGO_COLLECTION_COMMANDS = {"find", "count", "distinct", "listIndexes", "collStats", "insert", "update"}
MONGO_READ_STAGES = frozenset("""
$match $project $unset $addFields $set $replaceRoot $replaceWith $group $sort
$limit $skip $count $unwind $sample $sortByCount $bucket $bucketAuto $facet
$lookup $unionWith
""".split())
MONGO_FORBIDDEN_KEYS = {"$out", "$merge", "$where", "$function", "$accumulator"}
MONGO_UPDATE_OPERATORS = {"$set", "$setOnInsert", "$inc", "$mul", "$min", "$max", "$currentDate"}


def validate_redis(command):
    """接受明确查询和受限新增更新，拒绝删除、过期、脚本及未知命令。"""
    if not isinstance(command, list) or not command:
        raise OperationNotAllowed()
    if any(type(item) is not str or "\0" in item for item in command):
        raise OperationNotAllowed()
    name = command[0].upper()
    if name in REDIS_READ_COMMANDS:
        return
    if name in REDIS_READ_SUBCOMMANDS and len(command) > 1:
        if command[1].upper() in REDIS_READ_SUBCOMMANDS[name]:
            return
    if _redis_write_allowed(name, command):
        return
    raise OperationNotAllowed()


def _redis_write_allowed(name, command):
    size = len(command)
    if name == "SET":
        options = [value.upper() for value in command[3:]]
        return (size >= 3 and len(options) == len(set(options))
                and set(options) <= {"NX", "XX", "GET", "KEEPTTL"}
                and not {"NX", "XX"} <= set(options))
    if name in {"MSET", "MSETNX"}:
        return size >= 3 and size % 2 == 1
    if name in {"HSET", "HMSET"}:
        return size >= 4 and size % 2 == 0
    if name == "HSETNX":
        return size == 4
    if name in {"SADD", "LPUSH", "RPUSH", "LPUSHX", "RPUSHX"}:
        return size >= 3
    if name == "LSET":
        return size == 4 and _redis_number(command[2], integer=True)
    if name in {"INCR", "DECR"}:
        return size == 2
    if name in {"INCRBY", "DECRBY", "INCRBYFLOAT"}:
        return size == 3 and _redis_number(command[2], integer=name != "INCRBYFLOAT")
    if name in {"HINCRBY", "HINCRBYFLOAT"}:
        return size == 4 and _redis_number(command[3], integer=name == "HINCRBY")
    if name == "ZADD":
        return (size >= 4 and size % 2 == 0
                and all(_redis_number(value) for value in command[2::2]))
    return False


def _redis_number(value, integer=False):
    try:
        parsed = int(value) if integer else float(value)
        return math.isfinite(parsed)
    except (ValueError, OverflowError):
        return False


def validate_mongodb(command):
    """校验 MongoDB 查询和受限插入更新；不承诺消除数据库内部副作用。"""
    if type(command) is not dict or not command:
        raise OperationNotAllowed()
    name = next(iter(command))
    if type(name) is not str or name not in MONGO_FIELDS:
        raise OperationNotAllowed()
    allowed = {name, *MONGO_FIELDS[name].split()}
    if any(type(key) is not str or key not in allowed for key in command):
        raise OperationNotAllowed()
    _validate_mongo_target(name, command)
    _validate_json_tree(command, reject_execution=name not in {"insert", "update"})
    if name in {"insert", "update"}:
        _validate_mongo_write(name, command)
    if name == "aggregate":
        _validate_pipeline(command.get("pipeline"))


def _validate_mongo_write(name, command):
    for flag in ("ordered",):
        if flag in command and type(command[flag]) is not bool:
            raise OperationNotAllowed()
    if "maxTimeMS" in command:
        if type(command["maxTimeMS"]) is not int or command["maxTimeMS"] < 0:
            raise OperationNotAllowed()
    entries = command.get("documents" if name == "insert" else "updates")
    if type(entries) is not list or not entries or any(type(item) is not dict for item in entries):
        raise OperationNotAllowed()
    if name == "update":
        for item in entries:
            _validate_update_item(item)


def _validate_update_item(item):
    allowed = {"q", "u", "upsert", "multi", "collation", "arrayFilters", "hint"}
    if set(item) - allowed or type(item.get("q")) is not dict:
        raise OperationNotAllowed()
    update = item.get("u")
    if type(update) is not dict or not update or set(update) - MONGO_UPDATE_OPERATORS:
        raise OperationNotAllowed()
    for fields in update.values():
        if type(fields) is not dict or not fields or any(not field for field in fields):
            raise OperationNotAllowed()
    for flag in ("upsert", "multi"):
        if flag in item and type(item[flag]) is not bool:
            raise OperationNotAllowed()
    _validate_json_tree(item["q"])
    if "collation" in item and type(item["collation"]) is not dict:
        raise OperationNotAllowed()
    if "hint" in item and type(item["hint"]) not in {str, dict}:
        raise OperationNotAllowed()
    if "arrayFilters" in item:
        filters = item["arrayFilters"]
        if type(filters) is not list or any(type(value) is not dict for value in filters):
            raise OperationNotAllowed()
        _validate_json_tree(filters)


def _validate_mongo_target(name, command):
    target = command[name]
    if name in MONGO_COLLECTION_COMMANDS:
        if type(target) is not str or not target or "\0" in target:
            raise OperationNotAllowed()
    elif name == "aggregate":
        if not ((type(target) is str and target and "\0" not in target)
                or (type(target) is int and target == 1)):
            raise OperationNotAllowed()
    elif name in {"usersInfo", "rolesInfo"}:
        if not ((type(target) is int and target == 1)
                or (type(target) in {str, dict, list} and bool(target))):
            raise OperationNotAllowed()
    elif type(target) is not int or target != 1:
        raise OperationNotAllowed()


def _validate_json_tree(root, reject_execution=True):
    pending = [(root, 0)]
    count = 0
    while pending:
        value, depth = pending.pop()
        count += 1
        if depth > 40 or count > 10000:
            raise OperationNotAllowed()
        if type(value) is dict:
            for key, child in value.items():
                if (type(key) is not str or "\0" in key
                        or (reject_execution and key in MONGO_FORBIDDEN_KEYS)):
                    raise OperationNotAllowed()
                pending.append((child, depth + 1))
        elif type(value) is list:
            pending.extend((child, depth + 1) for child in value)
        elif type(value) not in {str, int, float, bool, type(None)}:
            raise OperationNotAllowed()
        elif type(value) is float and not math.isfinite(value):
            raise OperationNotAllowed()


def _validate_pipeline(pipeline, depth=0):
    if type(pipeline) is not list or depth > 20:
        raise OperationNotAllowed()
    for stage in pipeline:
        if type(stage) is not dict or len(stage) != 1:
            raise OperationNotAllowed()
        name, value = next(iter(stage.items()))
        if name not in MONGO_READ_STAGES:
            raise OperationNotAllowed()
        if name == "$facet":
            if type(value) is not dict:
                raise OperationNotAllowed()
            for nested in value.values():
                _validate_pipeline(nested, depth + 1)
        elif name in {"$lookup", "$unionWith"}:
            _validate_join_pipeline(name, value, depth)


def _validate_join_pipeline(name, value, depth):
    if name == "$unionWith" and type(value) is str and value:
        return
    fields = {"from", "localField", "foreignField", "let", "pipeline", "as"}
    if name == "$unionWith":
        fields = {"coll", "pipeline"}
    if type(value) is not dict or set(value) - fields:
        raise OperationNotAllowed()
    if "pipeline" in value:
        _validate_pipeline(value["pipeline"], depth + 1)
