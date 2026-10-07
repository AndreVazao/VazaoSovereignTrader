import pytest

from PC_ENGINE.exchanges.adapter_contract import AdapterContractError, normalize_order_response


def test_normalizes_closed_order_and_quote_fee():
    order = normalize_order_response(
        {
            "id": "v-1",
            "status": "closed",
            "filled": 0.1,
            "average": 100.0,
            "fee": {"cost": 0.10, "currency": "USDT"},
            "clientOrderId": "c-1",
        },
        symbol="BTC/USDT",
        side="buy",
        requested_qty=0.1,
        fallback_price=99.0,
    )
    assert order.venue_order_id == "v-1"
    assert order.client_order_id == "c-1"
    assert order.status == "FILLED"
    assert order.filled_qty == pytest.approx(0.1)
    assert order.fee == pytest.approx(0.10)


def test_base_currency_fee_is_converted_to_quote_not_dropped():
    order = normalize_order_response(
        {
            "id": "v-2",
            "status": "closed",
            "filled": 0.1,
            "average": 100.0,
            "fee": {"cost": 0.001, "currency": "BTC"},
        },
        symbol="BTC/USDT",
        side="sell",
        requested_qty=0.1,
        fallback_price=100.0,
    )
    assert order.fee == pytest.approx(0.1)


def test_unknown_status_is_fail_closed():
    with pytest.raises(AdapterContractError):
        normalize_order_response(
            {"id": "v-3", "status": "mystery", "filled": 0.1, "average": 100.0},
            symbol="BTC/USDT",
            side="buy",
            requested_qty=0.1,
            fallback_price=100.0,
        )


def test_missing_order_identity_is_fail_closed():
    with pytest.raises(AdapterContractError):
        normalize_order_response(
            {"status": "closed", "filled": 0.1, "average": 100.0},
            symbol="BTC/USDT",
            side="buy",
            requested_qty=0.1,
            fallback_price=100.0,
        )


def test_overfill_is_fail_closed():
    with pytest.raises(AdapterContractError):
        normalize_order_response(
            {"id": "v-5", "status": "closed", "filled": 0.11, "average": 100.0},
            symbol="BTC/USDT",
            side="buy",
            requested_qty=0.1,
            fallback_price=100.0,
        )


def test_client_order_identity_mismatch_is_fail_closed():
    with pytest.raises(AdapterContractError):
        normalize_order_response(
            {
                "id": "v-6", "status": "closed", "filled": 0.1, "average": 100.0,
                "clientOrderId": "different-client",
            },
            symbol="BTC/USDT",
            side="buy",
            requested_qty=0.1,
            fallback_price=100.0,
            expected_client_order_id="expected-client",
        )
