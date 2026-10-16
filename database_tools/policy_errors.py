"""数据库命令策略错误；不包含用户查询、目标或凭据。"""


class OperationNotAllowed(ValueError):
    """请求不属于数据库检查接口允许的命令子集。"""

    def __init__(self, reason="命令不在允许的查询、新增或更新范围内"):
        super().__init__(f"数据库保护策略拒绝执行：{reason}")
