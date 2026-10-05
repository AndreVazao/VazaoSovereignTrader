from types import SimpleNamespace

from PC_ENGINE.core.venue_capability_verifier import verify_adapter_contract


class MinimalAdapter:
    name = "TEST"

    def fetch_ohlcv(self, symbol, timeframe, limit):
        return []

    def fetch_ticker(self, symbol):
        return {}

    def fetch_balance(self):
        return {}

    def free_quote_balance(self, quote="USDT"):
        return 0.0

    def market_buy(self, symbol, qty):
        return {}

    def market_sell(self, symbol, qty):
        return {}

    def fetch_open_orders(self, symbol=None):
        return []

    def market_buy_with_client_order_id(self, symbol, qty, client_order_id):
        return {}

    def market_sell_with_client_order_id(self, symbol, qty, client_order_id):
        return {}


def test_contract_verification_is_positive_for_supported_paper_capabilities():
    rows = verify_adapter_contract(MinimalAdapter(), "PAPER")
    by_name = {row.capability: row for row in rows}
    assert by_name["market_data_historical"].verified
    assert by_name["account_balances"].verified
    assert by_name["paper_order_submit"].verified
    assert not by_name["market_data_websocket"].verified


def test_real_order_capability_never_becomes_verified_from_static_contract_alone():
    rows = verify_adapter_contract(MinimalAdapter(), "REAL")
    by_name = {row.capability: row for row in rows}
    assert by_name["real_order_submit"].declared
    assert not by_name["real_order_submit"].verified
    assert by_name["real_order_submit"].risk_level == "critical"


def test_missing_real_cancel_and_positions_are_explicitly_blocked():
    rows = verify_adapter_contract(MinimalAdapter(), "PAPER")
    by_name = {row.capability: row for row in rows}
    assert not by_name["real_order_cancel"].declared
    assert not by_name["account_positions"].declared
