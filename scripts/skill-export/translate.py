"""受限、失败即停止的 Python AST → JavaScript 导出器，仅供开发维护。"""
import ast
import json


def literal(value):
    return json.dumps(value, ensure_ascii=False)


class Translator:
    """只支持现有工具使用的语法；新增未覆盖语法必须显式实现并验证。"""

    def __init__(self, names):
        self.names = set(names)

    def expr(self, n):
        if isinstance(n, ast.Constant):
            return literal(n.value)
        if isinstance(n, ast.Name):
            return "v_" + n.id
        if isinstance(n, (ast.List, ast.Tuple)):
            return "[" + ", ".join(map(self.expr, n.elts)) + "]"
        if isinstance(n, ast.Dict):
            return "({" + ", ".join(f"[{self.expr(k)}]: {self.expr(v)}" for k, v in zip(n.keys, n.values)) + "})"
        if isinstance(n, ast.Subscript):
            if isinstance(n.slice, ast.Slice):
                lo = self.expr(n.slice.lower) if n.slice.lower else "0"
                hi = self.expr(n.slice.upper) if n.slice.upper else "undefined"
                if n.slice.step:
                    raise ValueError("不支持切片步长")
                return f"{self.expr(n.value)}.slice({lo}, {hi})"
            return f"{self.expr(n.value)}[{self.expr(n.slice)}]"
        if isinstance(n, ast.IfExp):
            return f"(py.truth({self.expr(n.test)}) ? {self.expr(n.body)} : {self.expr(n.orelse)})"
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            return f"!py.truth({self.expr(n.operand)})"
        if isinstance(n, ast.BoolOp):
            if isinstance(n.op, ast.And):
                return "(" + " && ".join(f"py.truth({self.expr(x)})" for x in n.values) + ")"
            return "py.or(" + ", ".join(self.expr(x) for x in n.values) + ")"
        if isinstance(n, ast.Compare):
            return self.compare(n)
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult):
            return f"py.repeat({self.expr(n.left)}, {self.expr(n.right)})"
        if isinstance(n, (ast.ListComp, ast.GeneratorExp)):
            return self.comprehension(n)
        if isinstance(n, ast.JoinedStr):
            return self.formatted(n)
        if isinstance(n, ast.Call):
            return self.call(n)
        raise ValueError(f"不支持表达式: {ast.dump(n)}")

    def compare(self, n):
        if len(n.ops) != 1:
            raise ValueError("不支持链式比较")
        left, right = self.expr(n.left), self.expr(n.comparators[0])
        op = n.ops[0]
        if isinstance(op, (ast.In, ast.NotIn)):
            prefix = "!" if isinstance(op, ast.NotIn) else ""
            return f"{prefix}py.contains({right}, {left})"
        symbol = {ast.Eq: "===", ast.NotEq: "!==", ast.Gt: ">", ast.GtE: ">=", ast.Lt: "<"}[type(op)]
        return f"({left} {symbol} {right})"

    def comprehension(self, n):
        if len(n.generators) != 1 or n.generators[0].is_async:
            raise ValueError("不支持复杂推导式")
        g = n.generators[0]
        target = self.expr(g.target)
        value = self.expr(g.iter)
        for cond in g.ifs:
            value += f".filter(({target}) => py.truth({self.expr(cond)}))"
        return f"{value}.map(({target}) => {self.expr(n.elt)})"

    def formatted(self, n):
        parts = []
        for v in n.values:
            if isinstance(v, ast.Constant):
                parts.append(literal(v.value))
            elif v.format_spec:
                spec = ast.literal_eval(v.format_spec.values[0])
                parts.append(f"Number({self.expr(v.value)}).toFixed({int(spec[1:-1])})")
            else:
                parts.append(f"String({self.expr(v.value)})")
        return "(" + " + ".join(parts) + ")"

    def call(self, n):
        args = [self.expr(a) for a in n.args]
        if n.keywords:
            raise ValueError("未支持关键字参数")
        name = ast.unparse(n.func)
        if name == "time.time":
            return "clock.seconds()"
        if name == "datetime.now().isoformat":
            return "clock.iso()"
        if name == "json.loads":
            return f"JSON.parse({args[0]})"
        if name == "isinstance":
            return f"(typeof {args[0]} === 'string')"
        if name == "len":
            return f"py.len({args[0]})"
        if name == "str":
            return f"String({args[0]})"
        if name in ("min", "max"):
            return f"Math.{name}({', '.join(args)})"
        if name.startswith("hexstrike_client."):
            return f"(await client.{n.func.attr}({', '.join(args)}))"
        if name.startswith("self.") or name in self.names:
            tool = name.removeprefix("self.")
            return f"(await tools[{literal(tool)}]({', '.join(args)}))"
        if isinstance(n.func, ast.Attribute):
            value, method = self.expr(n.func.value), n.func.attr
            if method == "get":
                return f"py.get({value}, {', '.join(args)})"
            if method in ("strip", "lower", "append", "split"):
                method = {"strip": "trim", "lower": "toLowerCase", "append": "push"}.get(method, method)
                return f"{value}.{method}({', '.join(args)})"
            if method == "join":
                return f"{args[0]}.join({value})"
        raise ValueError(f"不支持调用: {name}")

    def block(self, statements, level=2):
        return "\n".join(self.statement(n, level) for n in statements)

    def statement(self, n, level):
        indent = "  " * level
        if isinstance(n, ast.Assign):
            return indent + " = ".join([*(self.expr(t) for t in n.targets), self.expr(n.value)]) + ";"
        if isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add):
            return indent + f"{self.expr(n.target)} += {self.expr(n.value)};"
        if isinstance(n, ast.Return):
            return indent + f"return {self.expr(n.value)};"
        if isinstance(n, ast.Expr):
            return indent + self.expr(n.value) + ";"
        if isinstance(n, (ast.Import, ast.Pass)):
            return ""
        if isinstance(n, ast.If):
            text = indent + f"if (py.truth({self.expr(n.test)})) {{\n{self.block(n.body, level+1)}\n{indent}}}"
            if n.orelse:
                text += f" else {{\n{self.block(n.orelse, level+1)}\n{indent}}}"
            return text
        if isinstance(n, ast.For):
            return indent + f"for ({self.expr(n.target)} of {self.expr(n.iter)}) {{\n{self.block(n.body, level+1)}\n{indent}}}"
        if isinstance(n, ast.Try) and len(n.handlers) == 1 and not n.orelse and not n.finalbody:
            handler = n.handlers[0]
            return indent + f"try {{\n{self.block(n.body, level+1)}\n{indent}}} catch (v_{handler.name or 'error'}) {{\n{self.block(handler.body, level+1)}\n{indent}}}"
        raise ValueError(f"不支持语句: {ast.dump(n)}")

    def function(self, node):
        args = [a.arg for a in node.args.args]
        stores = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        local = sorted(stores - set(args))
        optional = len(args) - len(node.args.defaults)
        signature = [f"v_{a}" if i < optional else f"v_{a} = {self.expr(node.args.defaults[i-optional])}" for i, a in enumerate(args)]
        header = f"  tools[{literal(node.name)}] = async ({', '.join(signature)}) => {{"
        variables = f"    let {', '.join('v_' + a for a in local)};\n" if local else ""
        return header + "\n" + variables + self.block(node.body) + "\n  };"
