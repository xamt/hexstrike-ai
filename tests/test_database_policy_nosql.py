"""NoSQL 查询及受限新增更新策略测试；不启动客户端或连接数据库。"""
import unittest

from database_tools.policy_errors import OperationNotAllowed
from database_tools.policy_nosql import validate_mongodb, validate_redis


class RedisPolicyTests(unittest.TestCase):
    def test_explicit_read_commands_and_data_are_allowed(self):
        cases = [["GET", "DROP"], ["MGET", "SET", "DEL"], ["HGETALL", "a"],
                 ["LRANGE", "items", "0", "10"], ["SCAN", "0", "MATCH", "*"],
                 ["XREAD", "STREAMS", "events", "0"], ["SORT_RO", "items"],
                 ["INFO"], ["PING"], ["CONFIG", "GET", "appendonly"],
                 ["ACL", "GETUSER", "RESET"], ["CLIENT", "LIST"],
                 ["MEMORY", "USAGE", "PURGE"], ["OBJECT", "ENCODING", "a"],
                 ["XINFO", "STREAM", "a"], ["CLUSTER", "INFO"]]
        for command in cases:
            with self.subTest(command=command):
                self.assertIsNone(validate_redis(command))

    def test_deletes_scripts_and_unknown_commands_are_denied(self):
        cases = [["DEL", "x"], ["UNLINK", "x"],
                 ["FLUSHALL"], ["FLUSHDB"], ["GETDEL", "x"], ["GETEX", "x"],
                 ["SORT", "items", "STORE", "result"], ["SORT", "items"],
                 ["XREADGROUP", "GROUP", "g", "c", "STREAMS", "a", ">"],
                 ["EVAL", "return 1", "0"], ["EVAL_RO", "return 1", "0"],
                 ["FCALL", "f", "0"], ["FCALL_RO", "f", "0"],
                 ["MODULE", "LIST"], ["JSON.GET", "a"], ["ANY_NEW_COMMAND"],
                 ["ACL", "LOG", "RESET"], ["ACL", "SETUSER", "x"],
                 ["CONFIG", "SET", "dir", "/tmp"], ["CLIENT", "KILL", "x"],
                 ["MEMORY", "PURGE"], ["CLUSTER", "RESET"], ["AUTH", "secret"]]
        for command in cases:
            with self.subTest(command=command), self.assertRaises(OperationNotAllowed):
                validate_redis(command)

    def test_explicit_nondelete_writes_are_allowed(self):
        cases = [["SET", "x", "EX", "NX", "GET"], ["SET", "x", "1", "KEEPTTL"],
                 ["MSET", "x", "1", "y", "DEL"], ["MSETNX", "x", "1"],
                 ["HSET", "h", "a", "1", "b", "2"], ["HMSET", "h", "a", "1"],
                 ["HSETNX", "h", "a", "1"], ["SADD", "s", "DEL", "DROP"],
                 ["LPUSH", "l", "1"], ["RPUSH", "l", "1"],
                 ["LPUSHX", "l", "1"], ["RPUSHX", "l", "1"], ["LSET", "l", "0", "x"],
                 ["INCR", "n"], ["DECR", "n"], ["INCRBY", "n", "2"],
                 ["DECRBY", "n", "2"], ["INCRBYFLOAT", "n", "0.5"],
                 ["HINCRBY", "h", "n", "2"], ["HINCRBYFLOAT", "h", "n", "0.5"],
                 ["ZADD", "z", "1", "NX", "2", "GT"]]
        for command in cases:
            with self.subTest(command=command):
                self.assertIsNone(validate_redis(command))

    def test_write_modifiers_and_malformed_writes_are_denied(self):
        cases = [["SET", "x", "1", opt, "1"] for opt in ("EX", "PX", "EXAT", "PXAT")]
        cases += [["SET", "x", "1", "NX", "XX"], ["SET", "x", "1", "GET", "GET"],
                  ["SET", "x", "1", "UNKNOWN"], ["SET", "x"], ["MSET", "x"],
                  ["HSET", "h", "field"], ["HSETNX", "h", "f", "v", "extra"],
                  ["INCR", "n", "extra"], ["INCRBY", "n", "bad"],
                  ["ZADD", "z", "NX", "1", "member"], ["ZADD", "z", "NaN", "member"],
                  ["EXPIRE", "x", "1"], ["LTRIM", "l", "0", "1"], ["LPOP", "l"],
                  ["SPOP", "s"], ["ZPOPMIN", "z"], ["MOVE", "k", "1"],
                  ["HDEL", "h", "field"], ["LREM", "l", "0", "value"],
                  ["SREM", "s", "member"], ["ZREM", "z", "member"],
                  ["RENAME", "k", "other"], ["RESTORE", "k", "0", "data"],
                  ["XADD", "s", "MAXLEN", "1", "*", "f", "v"]]
        for command in cases:
            with self.subTest(command=command), self.assertRaises(OperationNotAllowed):
                validate_redis(command)

    def test_malformed_inputs_fail_closed(self):
        for command in (None, "GET x", [], ["GET", 1], [""], ["GET\0"], ["ACL"]):
            with self.subTest(command=command), self.assertRaises(OperationNotAllowed):
                validate_redis(command)


class MongoPolicyTests(unittest.TestCase):
    def test_inserts_and_operator_updates_are_allowed_with_literal_data(self):
        self.assertIsNone(validate_mongodb({"insert": "records", "documents": [
            {"action": "DROP", "delete": "ordinary", "nested": {"$where": "literal"}}
        ], "ordered": True}))
        for operator in ("$set", "$setOnInsert", "$inc", "$mul", "$min", "$max", "$currentDate"):
            value = {"nested": {"$function": "literal-data"}} if operator == "$set" else 1
            self.assertIsNone(validate_mongodb({"update": "records", "updates": [{
                "q": {"name": "DROP"}, "u": {operator: {"value": value}},
                "upsert": True, "multi": False}]}))

    def test_delete_update_operators_replacements_and_bypass_are_denied(self):
        cases = []
        for operator in ("$unset", "$rename", "$pull", "$pop", "$push", "$addToSet", "$unknown"):
            cases.append({"update": "records", "updates": [{"q": {}, "u": {operator: {"x": 1}}}]})
        cases += [{"update": "records", "updates": [{"q": {}, "u": {"x": 1}}]},
                  {"update": "records", "updates": [{"q": {}, "u": [{"$set": {"x": 1}}]}]},
                  {"update": "records", "updates": [{"q": {"$where": "return true"},
                    "u": {"$set": {"x": 1}}}]},
                  {"update": "records", "updates": [{"q": {}, "u": {"$set": {"x": 1}},
                    "unknown": True}]},
                  {"insert": "records", "documents": [{}], "bypassDocumentValidation": False},
                  {"insert": "records", "documents": "not-list"},
                  {"insert": "records", "documents": [1]},
                  {"update": "records", "updates": [
                    {"q": {}, "u": {"$set": {"x": 1}}},
                    {"q": {}, "u": {"$unset": {"y": ""}}}]},
                  {"update": "records", "updates": [{"q": {}, "u": {"$set": {"x": 1}},
                    "arrayFilters": [{"x": {"$where": "return true"}}]}]}]
        for command in cases:
            with self.subTest(command=command), self.assertRaises(OperationNotAllowed):
                validate_mongodb(command)

    def test_read_command_allowlist_and_plain_data_are_allowed(self):
        cases = [{"find": "records", "filter": {"action": "DROP", "delete": "ordinary"}},
                 {"count": "records", "query": {"name": "SET"}},
                 {"distinct": "records", "key": "category"},
                 {"listCollections": 1, "nameOnly": True}, {"listIndexes": "records"},
                 {"listDatabases": 1}, {"ping": 1}, {"hello": 1}, {"buildInfo": 1},
                 {"connectionStatus": 1}, {"dbStats": 1}, {"collStats": "records"},
                 {"serverStatus": 1}, {"usersInfo": 1}, {"rolesInfo": 1}]
        for command in cases:
            with self.subTest(command=command):
                self.assertIsNone(validate_mongodb(command))

    def test_read_aggregation_stages_and_nested_pipelines(self):
        command = {"aggregate": "records", "pipeline": [
            {"$match": {"score": {"$gt": 1}}},
            {"$project": {"name": 1}}, {"$unset": "privateField"},
            {"$facet": {"summary": [{"$count": "total"}]}},
            {"$lookup": {"from": "other", "pipeline": [{"$limit": 1}], "as": "other"}},
            {"$unionWith": {"coll": "more", "pipeline": [{"$sort": {"id": 1}}]}},
        ], "cursor": {"batchSize": 10}}
        self.assertIsNone(validate_mongodb(command))

    def test_write_commands_unknown_top_fields_and_case_are_denied(self):
        cases = [{"delete": "records", "deletes": []}, {"drop": "records"},
                 {"dropDatabase": 1}, {"dropIndexes": "records", "index": "*"},
                 {"renameCollection": "db.a", "to": "db.b"},
                 {"collMod": "records"}, {"createIndexes": "records", "indexes": []},
                 {"createUser": "new-user"},
                 {"getMore": 123, "collection": "records", "batchSize": 10},
                 {"insert": "records", "documents": []}, {"update": "records", "updates": []},
                 {"findAndModify": "records"}, {"bulkWrite": 1}, {"mapReduce": "records"},
                 {"eval": "function() {}"}, {"explain": {"find": "records"}},
                 {"FIND": "records"}, {"find": "records", "unknownOption": 1},
                 {"find": "records", "delete": "other"},
                 {"find": "records", "writeConcern": {"w": 1}},
                 {"filter": {}, "find": "records"}]
        for command in cases:
            with self.subTest(command=command), self.assertRaises(OperationNotAllowed):
                validate_mongodb(command)

    def test_nested_executable_expressions_and_write_stages_are_denied(self):
        cases = [{"find": "records", "filter": {"$or": [{"$where": "return true"}]}},
                 {"aggregate": "records", "pipeline": [{"$out": "copy"}], "cursor": {}},
                 {"aggregate": "records", "pipeline": [{"$merge": {"into": "copy"}}]},
                 {"aggregate": "records", "pipeline": [{"$project": {
                     "value": {"$function": {"body": "return 1", "args": [], "lang": "js"}}}}]},
                 {"aggregate": "records", "pipeline": [{"$group": {
                     "_id": None, "value": {"$accumulator": {"init": "return 1"}}}}]},
                 {"aggregate": "records", "pipeline": [{"$facet": {
                     "hidden": [{"$out": "copy"}]}}]},
                 {"aggregate": "records", "pipeline": [{"$lookup": {
                     "from": "other", "pipeline": [{"$merge": "copy"}], "as": "x"}}]},
                 {"aggregate": "records", "pipeline": [{"$unionWith": {
                     "coll": "other", "pipeline": [{"$newStage": {}}]}}]},
                 {"aggregate": "records", "pipeline": [{"$unknownStage": {}}]}]
        for command in cases:
            with self.subTest(command=command), self.assertRaises(OperationNotAllowed):
                validate_mongodb(command)

    def test_malformed_and_deep_inputs_fail_closed(self):
        cases = [None, [], {}, {"aggregate": "records"},
                 {"aggregate": "records", "pipeline": {}},
                 {"aggregate": "records", "pipeline": [{"$match": {}, "$limit": 1}]},
                 {"aggregate": "records", "pipeline": [{"$facet": {"bad": "not-list"}}]},
                 {"aggregate": "records", "pipeline": [{"$lookup": {"pipeline": {}}}]},
                 {"find": "records", "filter": {1: "invalid-key"}}]
        nested = {}
        for _ in range(80):
            nested = {"next": nested}
        cases.append({"find": "records", "filter": nested})
        for command in cases:
            with self.assertRaises(OperationNotAllowed):
                validate_mongodb(command)


if __name__ == "__main__":
    unittest.main()
