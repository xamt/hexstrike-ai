"""查询及新增/更新SQL的保守允许列表；拒绝删除、DDL与动态执行。"""
from .policy_errors import OperationNotAllowed
from .sql_tokens import tokenize_sql

FORBIDDEN_WORDS = frozenset("""
INSERT UPDATE DELETE DROP TRUNCATE ALTER CREATE REPLACE MERGE UPSERT
GRANT REVOKE CALL EXEC EXECUTE PREPARE DEALLOCATE DO SET RESET USE
COPY LOAD IMPORT EXPORT INTO OUTFILE DUMPFILE INFILE LOCK UNLOCK
COMMIT ROLLBACK BEGIN START SAVEPOINT RELEASE DISCARD VACUUM ANALYZE
OPTIMIZE REPAIR KILL SYSTEM ATTACH DETACH RENAME EXCHANGE MOVE
RESTORE BACKUP INSTALL UNINSTALL PLUGIN EXTENSION SETTINGS FORMAT
DELIMITER SOURCE HANDLER FLUSH PURGE CHECKPOINT REASSIGN SECURITY
OPERATOR PROCEDURE FUNCTION CAST CONVERT
""".split())

# 刻意只保留常见标量/聚合与身份函数；任意UDF和远端表函数不开放。
FUNCTIONS = frozenset("""
COUNT SUM AVG MIN MAX ABS ROUND CEIL CEILING FLOOR LOWER UPPER LENGTH
CHAR_LENGTH CHARACTER_LENGTH OCTET_LENGTH CONCAT CONCAT_WS SUBSTRING
SUBSTR LEFT RIGHT TRIM LTRIM RTRIM COALESCE NULLIF IFNULL IF
VERSION DATABASE CURRENT_DATABASE CURRENT_SCHEMA CURRENT_SCHEMAS
CURRENT_USER SESSION_USER USER SYSTEM_USER CONNECTION_ID PG_BACKEND_PID
NOW CURRENT_DATE CURRENT_TIME CURRENT_TIMESTAMP DATE YEAR MONTH DAY
HAS_TABLE_PRIVILEGE HAS_SCHEMA_PRIVILEGE HAS_DATABASE_PRIVILEGE PG_HAS_ROLE
""".split())
GROUP_KEYWORDS = frozenset("IN EXISTS NOT AND OR AS FROM WHERE HAVING ON OVER SELECT DISTINCT WHEN THEN ELSE VALUES".split())
SHOW_PREFIXES = (
    ("TABLES",), ("DATABASES",), ("SCHEMAS",), ("COLUMNS",), ("FIELDS",),
    ("INDEX",), ("INDEXES",), ("KEYS",), ("GRANTS",), ("STATUS",),
    ("VARIABLES",), ("PROCESSLIST",), ("ALL",), ("FULL", "TABLES"),
    ("FULL", "COLUMNS"), ("FULL", "PROCESSLIST"), ("CREATE", "TABLE"),
    ("CREATE", "VIEW"), ("CREATE", "DATABASE"), ("CREATE", "SCHEMA"),
    ("GLOBAL", "STATUS"), ("GLOBAL", "VARIABLES"),
    ("SESSION", "STATUS"), ("SESSION", "VARIABLES"),
)
SYSTEM_NAMESPACES = frozenset({"MYSQL", "INFORMATION_SCHEMA", "PERFORMANCE_SCHEMA",
                               "SYS", "PG_CATALOG", "PG_TOAST", "SYSTEM"})


def validate_sql(name, query, database=""):
    """允许单条查询、新增和更新；不开放删除、DDL和间接执行语法。"""
    tokens = tokenize_sql(query)
    if tokens and tokens[-1] == ("symbol", ";"):
        tokens.pop()
    if not tokens or any(token == ("symbol", ";") for token in tokens):
        raise OperationNotAllowed("仅支持一条非空SQL语句")
    if tokens[0][0] != "word":
        raise OperationNotAllowed()
    first = tokens[0][1]
    if first not in {"SELECT", "WITH", "SHOW", "DESCRIBE", "DESC", "EXPLAIN", "INSERT", "UPDATE"}:
        raise OperationNotAllowed()
    exempt_create = _validate_statement(first, tokens)
    allowed_write_words = {"INSERT", "UPDATE", "INTO", "SET", "DO"} if first == "INSERT" else (
        {"UPDATE", "SET"} if first == "UPDATE" else set())
    for index, (kind, value) in enumerate(tokens):
        if kind == "word" and value in FORBIDDEN_WORDS - allowed_write_words and index != exempt_create:
            raise OperationNotAllowed("不允许删除、结构变更、管理或间接执行语法")
    column_group = _validate_write_target(name, tokens, database) if first in {"INSERT", "UPDATE"} else None
    _validate_parentheses(tokens, column_group)


def _validate_statement(first, tokens):
    if first == "SHOW":
        words = tuple(value if kind == "word" else "" for kind, value in tokens[1:])
        if not any(words[:len(prefix)] == prefix for prefix in SHOW_PREFIXES):
            raise OperationNotAllowed("不支持该SHOW元数据语法")
        return 1 if words[0] == "CREATE" else None
    if first == "EXPLAIN" and tokens[1:2] != [("word", "SELECT")]:
        raise OperationNotAllowed("仅支持不执行语句的EXPLAIN SELECT")
    if first in {"DESC", "DESCRIBE"}:
        if len(tokens) < 2 or any(kind not in {"word", "identifier"} and value != "."
                                  for kind, value in tokens[1:]):
            raise OperationNotAllowed("仅支持普通对象的字段描述")
    return None


def _validate_write_target(name, tokens, database):
    insert = tokens[0][1] == "INSERT"
    if insert and tokens[1:2] != [("word", "INTO")]:
        raise OperationNotAllowed("新增语句仅支持INSERT INTO普通对象")
    position, names = _target_name(tokens, 2 if insert else 1)
    if (database.upper() in SYSTEM_NAMESPACES or any(part in SYSTEM_NAMESPACES for part in names[:-1])
            or (name == "postgresql_query" and names[-1].startswith("PG_"))):
        raise OperationNotAllowed("不允许修改系统元数据对象")
    if not insert:
        if tokens[position:position + 1] == [("word", "AS")]:
            position += 1
        if position < len(tokens) and tokens[position] != ("word", "SET"):
            if tokens[position][0] not in {"word", "identifier"}:
                raise OperationNotAllowed("更新仅支持单个普通对象")
            position += 1
        if tokens[position:position + 1] != [("word", "SET")]:
            raise OperationNotAllowed("更新仅支持单个普通对象及SET赋值")
        return None
    return _insert_columns(tokens, position)


def _target_name(tokens, position):
    names = []
    while True:
        if position >= len(tokens) or tokens[position][0] not in {"word", "identifier"}:
            raise OperationNotAllowed("写入语句缺少普通对象名称")
        names.append(tokens[position][1].upper())
        if len(names) > 2:
            raise OperationNotAllowed("写入对象名称层级不受支持")
        position += 1
        if tokens[position:position + 1] != [("symbol", ".")]:
            break
        position += 1
    return position, names


def _insert_columns(tokens, position):
    if tokens[position:position + 1] != [("symbol", "(")]:
        _validate_insert_source(tokens, position)
        return None
    opening = position
    expect_column = True
    for index in range(position + 1, len(tokens)):
        kind, value = tokens[index]
        if kind == "symbol" and value == ")" and not expect_column:
            _validate_insert_source(tokens, index + 1)
            return opening
        if expect_column and kind in {"word", "identifier"}:
            expect_column = False
        elif not expect_column and kind == "symbol" and value == ",":
            expect_column = True
        else:
            break
    raise OperationNotAllowed("新增语句仅支持普通字段列表")


def _validate_insert_source(tokens, position):
    if (position >= len(tokens) or tokens[position][0] != "word"
            or tokens[position][1] not in {"VALUES", "SELECT", "SET"}):
        raise OperationNotAllowed("新增对象后仅支持字段列表及VALUES/SELECT/SET")


def _validate_parentheses(tokens, column_group):
    depth = 0
    for index, (kind, value) in enumerate(tokens):
        if kind != "symbol":
            continue
        if value == "(":
            depth += 1
            if depth > 64:
                raise OperationNotAllowed("SQL嵌套超过策略上限")
            if index and index != column_group:
                _validate_call(tokens, index)
        elif value == ")":
            depth -= 1
            if depth < 0:
                raise OperationNotAllowed("SQL括号不匹配")
    if depth:
        raise OperationNotAllowed("SQL括号不匹配")


def _validate_call(tokens, index):
    kind, value = tokens[index - 1]
    if kind not in {"word", "identifier"}:
        return
    qualified = index >= 2 and tokens[index - 2] == ("symbol", ".")
    if value == "CONFLICT" and tokens[index - 2:index - 1] == [("word", "ON")]:
        return
    if kind == "identifier" or qualified or value not in FUNCTIONS | GROUP_KEYWORDS:
        raise OperationNotAllowed("不支持自定义、限定名称或未列入允许列表的函数")
