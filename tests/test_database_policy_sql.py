"""SQL保护离线用例：仅解析字符串，绝不执行SQL。"""
import unittest

from database_tools.policy_errors import OperationNotAllowed
from database_tools.policy_sql import validate_sql


class SqlPolicyTests(unittest.TestCase):
    def test_supported_queries(self):
        queries = [
            "SELECT 1", "select version(), current_user", "SELECT count(*) FROM users",
            "SELECT id, name FROM users WHERE id IN (1, 2) LIMIT 10;",
            "SELECT 'DROP TABLE users; -- not a command' AS sample",
            "SELECT 'it''s a test'", 'SELECT "delete" FROM "my;table"',
            "/* normal comment */ SELECT 1 -- comment\n;",
            "WITH candidates AS (SELECT id FROM records) SELECT * FROM candidates",
            "SHOW TABLES", "SHOW DATABASES", "SHOW GRANTS", "SHOW CREATE TABLE records",
            "SHOW COLUMNS FROM records", "DESCRIBE records", "DESC records",
            "EXPLAIN SELECT id FROM records", "SELECT current_database()",
            "SELECT COUNT(*) FROM (SELECT id FROM records) AS sample",
            "SELECT lower(name) FROM records WHERE name LIKE 'drop%'",
            "INSERT INTO sample (id, value) VALUES (1, 'ok')",
            'INSERT INTO "db"."sample" ("id", "value") VALUES (1, \'ok\')',
            "INSERT INTO sample VALUES (1), (2)",
            "INSERT INTO sample SELECT id FROM input_data",
            "INSERT INTO sample (id) VALUES (1) ON DUPLICATE KEY UPDATE id=2",
            "INSERT INTO sample (id) VALUES (1) ON CONFLICT (id) DO UPDATE SET id=2",
            "UPDATE sample SET value='new', amount=amount+1 WHERE id=1",
            "UPDATE public.sample AS s SET value='new' WHERE s.id=1",
        ]
        for engine in ("mysql_query", "postgresql_query", "clickhouse_query"):
            for query in queries:
                with self.subTest(engine=engine, query=query):
                    validate_sql(engine, query)

    def test_mutations_and_indirect_execution_rejected(self):
        queries = [
            "DROP DATABASE app", "drop table records", "ALTER TABLE t DROP COLUMN c",
            "TRUNCATE records", "DELETE FROM records", "REPLACE INTO t VALUES (1)",
            "INSERT INTO FUNCTION remote('host','db','t') VALUES (1)",
            "INSERT INTO t VALUES (1); DROP TABLE t",
            "UPDATE t SET x=dangerous_udf()", "UPDATE t SET x=1; DELETE FROM t",
            "UPDATE t JOIN mysql.user u ON 1=1 SET u.password='x'",
            "UPDATE t, other SET t.x=1", "UPDATE mysql.user SET password='x'",
            'INSERT INTO "system"."settings" VALUES (1)',
            'INSERT INTO TABLE "system"."settings" VALUES (1)',
            'INSERT INTO TABLE "mysql"."user" VALUES (1)',
            "INSERT INTO t bogus VALUES (1)", "INSERT INTO t(id) bogus VALUES (1)",
            "INSERT INTO a.b.c VALUES (1)",
            "SELECT 1; DROP TABLE records", "SELECT 1;;", ";SELECT 1",
            "WITH x AS (DELETE FROM t RETURNING *) SELECT * FROM x",
            "WITH x AS (SELECT 1) INSERT INTO t SELECT * FROM x",
            "SELECT 1 -- comment\r; SET transaction_read_only=off; DROP TABLE t",
            "SELECT * INTO backup FROM t", "SELECT 1 INTO OUTFILE '/tmp/a'",
            "SELECT 1 SETTINGS readonly=0", "EXPLAIN ANALYZE SELECT 1",
            "EXPLAIN DELETE FROM t", "CALL erase()", "EXECUTE prepared",
            "PREPARE stmt FROM 'DROP TABLE t'", "DO $$ BEGIN END $$",
            "SELECT dangerous_udf()", "SELECT public.lower('x')",
            'SELECT "dangerous_udf"()', "SELECT pg_terminate_backend(1)",
            "SELECT set_config('transaction_read_only','off',false)",
            "SELECT dblink_exec('db','DROP TABLE t')", "SELECT nextval('seq')",
            "SELECT * FROM remote('host', 'db', 'table')", "SELECT sleep(10)",
            "SELECT value::custom_type FROM t", "SELECT CAST(value AS custom_type) FROM t",
            "SELECT 1 FOR UPDATE", "SELECT 1 LOCK IN SHARE MODE", "SYSTEM DROP DNS CACHE",
            "SHOW TABLES; DELETE FROM t", "SHOW CREATE PROCEDURE erase",
            "SHOW made_up_command", "DESCRIBE remote('host', 'db', 't')",
        ]
        for engine in ("mysql_query", "postgresql_query", "clickhouse_query"):
            for query in queries:
                with self.subTest(engine=engine, query=query), self.assertRaises(OperationNotAllowed):
                    validate_sql(engine, query)

    def test_ambiguous_lexing_rejected(self):
        queries = [
            "/*!50000 DROP TABLE t */ SELECT 1", "/*M! DROP TABLE t */ SELECT 1",
            "SELECT /*+ SET_VAR(readonly=0) */ 1", "SELECT /* nested /* x */ 1 */",
            "SELECT 1 /* unfinished", "SELECT 'unfinished", "SELECT $$ text $$",
            "SELECT E'back\\slash'", "SELECT 1\\gexec", "SELECT 1 --x\nDROP TABLE t",
            "SELECT 1 # comment", "SELECT 1\x00", "SELECT 1\u2028DROP TABLE t",
            "SELECT 1 @var", "SELECT (1", "SELECT 1)", "SELECT 1:foo",
        ]
        for query in queries:
            with self.subTest(query=query), self.assertRaises(OperationNotAllowed):
                validate_sql("mysql_query", query)

    def test_resource_boundaries(self):
        for query in ("SELECT " + "(" * 65 + "1" + ")" * 65,
                      "SELECT " + "x," * 17000):
            with self.assertRaises(OperationNotAllowed):
                validate_sql("postgresql_query", query)

    def test_system_targets_rejected(self):
        for engine, query, database in (
                ("mysql_query", "UPDATE user SET password='x'", "mysql"),
                ("postgresql_query", "UPDATE pg_proc SET prosrc='x'", "postgres"),
                ("clickhouse_query", "INSERT INTO settings VALUES (1)", "system")):
            with self.assertRaises(OperationNotAllowed):
                validate_sql(engine, query, database)


if __name__ == "__main__":
    unittest.main()
