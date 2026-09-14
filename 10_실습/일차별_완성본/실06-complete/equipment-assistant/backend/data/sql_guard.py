"""Validate model SQL before executing its unchanged text with a read-only cursor."""
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope

ALLOWED_FUNCTIONS = {"COUNT", "SUM", "AVG", "MIN", "MAX", "ROUND", "ABS", "COALESCE",
                     "CAST", "NULLIF", "STDDEV", "STDDEV_POP", "STDDEV_SAMP"}


def validate_select(text: str, tables: set[str]) -> str:
    statements = sqlglot.parse(text, read="postgres")
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise ValueError("하나의 SELECT만 허용합니다")
    tree = statements[0]
    if tree.args.get("into") or tree.args.get("locks"):
        raise ValueError("저장과 행 잠금은 허용하지 않습니다")
    forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Command, exp.Union)
    if any(tree.find_all(*forbidden)):
        raise ValueError("허용하지 않은 SQL 구조입니다")
    if sum(1 for _ in tree.find_all(exp.Select)) > 4:
        raise ValueError("질의 중첩 상한을 넘었습니다")
    for function in tree.find_all(exp.Func):
        name = function.name.upper() if isinstance(function, exp.Anonymous) else function.sql_name()
        if name not in ALLOWED_FUNCTIONS:
            raise ValueError(f"허용하지 않은 함수: {name}")
    real_tables = 0
    for scope in traverse_scope(tree):
        for _, selected in scope.selected_sources.values():
            if isinstance(selected, exp.Table):
                if selected.catalog or selected.db not in ("", "lab") or selected.name not in tables:
                    raise ValueError("선택한 원천의 조회용 표만 허용합니다")
                real_tables += 1
    if not real_tables:
        raise ValueError("등록된 표를 조회해야 합니다")
    return text

