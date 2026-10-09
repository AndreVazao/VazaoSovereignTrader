from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PC_ENGINE = ROOT / "PC_ENGINE"
APPROVED_ORDER_ADAPTER = Path("PC_ENGINE/exchanges/ccxt_client.py")
ORDER_SUBMISSION_METHODS = {
    "create_order",
    "create_market_buy_order",
    "create_market_sell_order",
}
APPROVED_WRAPPER_METHODS = {
    "market_buy_with_client_order_id",
    "market_sell_with_client_order_id",
    "market_buy",
    "market_sell",
}


class ExternalOrderCallVisitor(ast.NodeVisitor):
    def __init__(self, relative_path: Path) -> None:
        self.relative_path = relative_path
        self.function_stack: list[str] = []
        self.calls: list[tuple[Path, int, str, str | None, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in ORDER_SUBMISSION_METHODS:
            receiver = ast.unparse(func.value)
            method = self.function_stack[-1] if self.function_stack else None
            self.calls.append((self.relative_path, node.lineno, func.attr, method, receiver))
        self.generic_visit(node)


def _order_submission_calls() -> list[tuple[Path, int, str, str | None, str]]:
    calls = []
    for source in PC_ENGINE.rglob("*.py"):
        # Never scan the project's local virtual environment or generated caches.
        if ".venv" in source.parts or "__pycache__" in source.parts:
            continue
        relative = Path(source.relative_to(ROOT).as_posix())
        tree = ast.parse(source.read_text(encoding="utf-8-sig"), filename=str(source))
        visitor = ExternalOrderCallVisitor(relative)
        visitor.visit(tree)
        calls.extend(visitor.calls)
    return calls


def test_direct_exchange_order_submission_is_confined_to_approved_adapter():
    calls = _order_submission_calls()

    assert calls, "expected to find the exchange order-submission boundary"
    unexpected = [call for call in calls if call[0] != APPROVED_ORDER_ADAPTER]
    assert not unexpected, f"direct order submission bypasses the approved adapter: {unexpected}"


def test_ccxt_order_submission_uses_only_reviewed_adapter_wrappers():
    calls = _order_submission_calls()

    unexpected = [
        call for call in calls
        if call[0] == APPROVED_ORDER_ADAPTER
        and (call[3] not in APPROVED_WRAPPER_METHODS or call[4] != "self.client")
    ]
    assert not unexpected, f"unreviewed CCXT order-submission call site: {unexpected}"
    assert {call[2] for call in calls} == ORDER_SUBMISSION_METHODS
