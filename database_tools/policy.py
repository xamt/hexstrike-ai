"""五类数据库工具共享命令保护入口。"""
from .policy_errors import OperationNotAllowed
from .policy_nosql import validate_mongodb, validate_redis
from .policy_sql import validate_sql


def enforce_policy(name, args):
    """在执行前拒绝删除和高风险操作；没有请求级绕过开关。"""
    if name in {"mysql_query", "postgresql_query", "clickhouse_query"}:
        validate_sql(name, args["query"], args.get("database", ""))
    elif name == "redis_command":
        validate_redis(args["command"])
    elif name == "mongodb_command":
        command = args["command"]
        operation = next(iter(command), None)
        if operation in {"insert", "update"}:
            target = command[operation]
            if (args.get("database", "").lower() in {"admin", "config", "local"}
                    or isinstance(target, str) and target.lower().startswith("system.")):
                raise OperationNotAllowed("不允许修改系统元数据对象")
        validate_mongodb(args["command"])
    else:
        raise OperationNotAllowed()
