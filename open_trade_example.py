data = {
    "id": 7508801,
    "version": 2,
    "account": {
        "id": 30391847,
        "type": "binance_futures_coin",
        "name": "COIN-M tk",
        "market": "Binance Futures COIN-M",
        "link": "/accounts/30391847"
    },
    "pair": "ETH_ETHUSD_PERP",
    "instant": False,
    "status": {
        "type": "waiting_targets",
        "title": "Waiting Targets"
    },
    "leverage": {
        "enabled": True,
        "type": "isolated",
        "value": "1.0"
    },
    "position": {
        "type": "buy",
        "editable": False,
        "units": {
            "value": "1.0",
            "editable": False
        },
        "price": {
            "value": "2455.35",
            "value_without_commission": "2454.37",
            "editable": False
        },
        "total": {
            "value": "0.00407273"
        },
        "order_type": "market",
        "status": {
            "type": "finished",
            "title": "Finished"
        }
    },
    "take_profit": {
        "enabled": True,
        "steps": [{
            "id": 26320269,
            "order_type": "market",
            "editable": True,
            "units": {
                "value": "1.0"
            },
            "price": {
                "value": "2459.0",
                "type": "last",
                "percent": None
            },
            "volume": "100.0",
            "total": "0.00406669",
            "trailing": {
                "enabled": False,
                "percent": None
            },
            "status": {
                "type": "to_process",
                "title": "Pending"
            },
            "data": {
                "cancelable": True,
                "panic_sell_available": True
            },
            "position": 1
        }]
    },
    "stop_loss": {
        "enabled": True,
        "order_type": "market",
        "editable": True,
        "price": {
            "value": None
        },
        "conditional": {
            "price": {
                "value": "2448.99",
                "type": "last",
                "percent": None
            },
            "trailing": {
                "enabled": True,
                "percent": None
            }
        },
        "timeout": {
            "enabled": False,
            "value": None
        },
        "status": {
            "type": "trailing_activated",
            "title": "Trailing Activated"
        }
    },
    "note": "",
    "skip_enter_step": False,
    "data": {
        "editable": True,
        "current_price": {
            "bid": "2451.45",
            "ask": "2451.46",
            "last": "2451.45",
            "day_change_percent": "-3.585",
            "quote_volume": "924589.1908461"
        },
        "target_price_type": "price",
        "base_order_finished": True,
        "missing_funds_to_close": 0,
        "liquidation_price": None,
        "average_enter_price": "2455.35",
        "average_close_price": None,
        "average_enter_price_without_commission": "2454.37",
        "average_close_price_without_commission": None,
        "panic_sell_available": True,
        "add_funds_available": True,
        "force_start_available": False,
        "force_process_available": True,
        "cancel_available": True,
        "finished": False,
        "base_position_step_finished": True,
        "created_at": "2021-06-17T07:12:35.545Z",
        "updated_at": "2021-06-17T07:12:35.545Z",
        "type": "smart_trade"
    },
    "profit": {
        "volume": "-0.00000484806",
        "usd": "-0.0118847766870000000000000310501675724562",
        "percent": "-0.12",
        "roe": "-0.12"
    },
    "margin": {
        "amount": "1.0",
        "total": "0.004072730256"
    },
    "is_position_not_filled": False
}
