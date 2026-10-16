"""构造固定数据库客户端命令；用户值不进入 shell 或本地 JS 源码。"""
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Invocation:
    """子进程参数及私有输入；不得记录 repr 或环境内容。"""
    argv: list = field(repr=False)
    stdin: bytes = field(default=b"", repr=False)
    environment: dict = field(default_factory=dict, repr=False)


MONGO_SCRIPT = """
try {
  const p = JSON.parse(process.env.HEXSTRIKE_MONGO_REQUEST);
  const enc = encodeURIComponent;
  const host = p.host.includes(':') ? '[' + p.host + ']' : p.host;
  const auth = p.username ? enc(p.username) + ':' + enc(p.password) + '@' : '';
  const uri = 'mongodb://' + auth + host + ':' + p.port + '/' + enc(p.database)
    + '?authSource=' + enc(p.auth_database) + '&directConnection=true'
    + '&retryReads=false&retryWrites=false&serverSelectionTimeoutMS=' + (p.timeout * 1000);
  const connection = new Mongo(uri);
  const result = connection.getDB(p.database).runCommand(p.command);
  print(EJSON.stringify(result));
  const bulkWrite = Object.keys(p.command)[0].toLowerCase() === 'bulkwrite';
  const batch = result.cursor && result.cursor.firstBatch;
  const failed = result.ok !== 1
    || (Array.isArray(result.writeErrors) && result.writeErrors.length > 0)
    || Boolean(result.writeConcernError) || result.nErrors > 0
    || (bulkWrite && Array.isArray(batch) && batch.some(item => item.ok === 0));
  quit(failed ? 1 : 0);
} catch (error) {
  print('MongoDB 连接或命令失败；未输出可能包含凭据的异常详情');
  quit(1);
}
""".strip()


def build_invocation(name, args, workdir):
    """在私有目录构造无连接密码的 argv；PostgreSQL SQL 使用单次 --command。"""
    builders = {"mysql_query": _mysql, "clickhouse_query": _clickhouse,
                "postgresql_query": _postgresql, "redis_command": _redis,
                "mongodb_command": _mongodb}
    return builders[name](args, Path(workdir))


def _mysql(a, directory):
    argv = ["mysql", "--no-defaults", "--batch", "--raw", "--quick",
            "--binary-mode", "--sandbox", "--local-infile=0", "--skip-reconnect",
            "--protocol=TCP", f"--host={a['host']}", f"--port={a['port']}",
            f"--user={a['username']}", f"--connect-timeout={a['timeout']}"]
    if a["database"]:
        argv.append(f"--database={a['database']}")
    return Invocation(argv, a["query"].encode("utf-8"), {"MYSQL_PWD": a["password"]})


def _clickhouse(a, directory):
    config = directory / "clickhouse.xml"
    config.write_text("<config></config>\n", encoding="utf-8")
    argv = ["clickhouse-client", f"--config-file={config}", f"--host={a['host']}",
            f"--port={a['port']}", f"--user={a['username']}",
            f"--database={a['database']}", "--format=JSONEachRow"]
    return Invocation(argv, a["query"].encode("utf-8"), {"CLICKHOUSE_PASSWORD": a["password"]})


def _postgresql(a, directory):
    argv = ["psql", "--no-psqlrc", "--no-password", "--quiet", "--no-align",
            "--set=ON_ERROR_STOP=1", "--pset=pager=off",
            f"--host={a['host']}", f"--port={a['port']}",
            f"--username={a['username']}", f"--dbname={a['database']}",
            "--command=" + a["query"]]
    env = {"PGPASSWORD": a["password"], "PGCONNECT_TIMEOUT": str(a["timeout"]),
           "PGPASSFILE": str(directory / "absent.pgpass")}
    return Invocation(argv, environment=env)


def _redis(a, directory):
    argv = ["redis-cli", "--raw", "-e", "-h", a["host"], "-p", str(a["port"]),
            "-n", str(a["database"])]
    if a["username"]:
        argv.extend(["--user", a["username"]])
    command = a["command"]
    # stdin 命令行会进入 REPL，使 -e 失效。保持非交互，仅将末尾值交给 -x。
    if len(command) > 1:
        argv.extend(["-x", *command[:-1]])
        stdin = command[-1].encode("utf-8")
    else:
        argv.extend(command)
        stdin = b""
    env = {"REDISCLI_AUTH": a["password"]} if a["password"] or a["username"] else {}
    return Invocation(argv, stdin, env)


def _mongodb(a, directory):
    argv = ["mongosh", "--nodb", "--norc", "--quiet", "--eval", MONGO_SCRIPT]
    return Invocation(argv, environment={
        "HEXSTRIKE_MONGO_REQUEST": json.dumps(a, ensure_ascii=True, allow_nan=False)})
