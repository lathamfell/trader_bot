import logging

DEFAULT_STRAT_CONFIG = {
    "tp_pct": 0.2,
    "sl_pct": 0.2,
    "sl_trail": False,
    "leverage": 1,
    "units": 1,
}

TRADE_TYPES = {
    "opening": ["waiting_position", "created"],
    "open": ["waiting_targets"],
    "closing": [
        "stop_loss_in_progress",
        "panic_sell_pending",
        "panic_sell_in_progress",
        "cancellation_in_progress",
    ],
    "closed": ["finished", "panic_sold", "stop_loss_finished", "cancelled"],
}

LOG_LEVEL = logging.DEBUG
STARTING_PAPER = 10000

USER_ATTR = {
    "malcolm": {
        "c3_api_key": "a9fbc731bfcb41b590534b8b938ec06a66c7438cc2b242b0b02991f858f5cc12",
        "c3_secret": "13fac45a153dbe6948ee225b863243decd79060eb146029f6d01f8150b0561ab7f5fa7fb238c3a74f1bb6ec34359be2f22e8a9f38d6e48f73444dce17876096b18899f01558a4628981e526858155793dda952019937fb9f0629c356f18c2f9014fc4ea6",
        "email": "malcerlee@gmail.com",
        "email_enabled": False,
        "strats": {
            "BTC_M1": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 30841543,
                "pair": "BTC_BTCUSD",
                "entry_order_type": "market",
                "tp_order_type": "limit",
                "sl_order_type": "market",
            },
            "BTC_M2": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 31485337,
                "pair": "BTC_BTCUSD",
                "entry_order_type": "market",
                "tp_order_type": "limit",
                "sl_order_type": "market"
            },
            "BTC_M3": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 31538061,
                "pair": "BTC_BTCUSD",
                "entry_order_type": "market",
                "tp_order_type": "limit",
                "sl_order_type": "market"
            },
            "BTC_M4": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 31538077,
                "pair": "BTC_BTCUSD",
                "entry_order_type": "market",
                "tp_order_type": "limit",
                "sl_order_type": "market"
            }
        },
    },
    "latham": {
        "c3_api_key": "418a3c2e87f447219ca6ed9ebf35b4706e1c7610fbd24850b312ca504cf8bfa6",
        "c3_secret": "602bcc216123d14028e8eaff528636aab3e0622a3985d694a1e8cf47b389e7bc89bc81254f5f541ef02ad4661162e339d264091d22a7f30281268081bfb61b78acdc9be6b56a1d5c7c8e6a8e628af4f7ced2f4d9b3b33d72ca46523cb4040c432d25a783",
        "email": "lathamfell@gmail.com",
        "email_enabled": False,
        "strats": {
            "BTC_L1": {  # DubA Scalper 1D1m
                "logic": "alpha",
                "coin": "btc",
                "account_id": 30823191,  # lathamfell@gmail.com
                "pair": "BTC_BTCUSD",
                "entry_order_type": "market",
                "tp_order_type": "limit",
                "sl_order_type": "market",
            },
            "BTC_L2": {  # test
                "logic": "alpha",
                "coin": "btc",
                "account_id": 30823322,  # psychobot2021@gmail.com
                "pair": "BTC_BTCUSD",
                "entry_order_type": "market",
                "tp_order_type": "limit",
                "sl_order_type": "market",
            },
            "BTC_L3": {  # Nerd Lama 1D45m5m
                "logic": "alpha",
                "coin": "btc",
                "account_id": 31212864,  # trendking2021@gmail.com
                "pair": "BTC_BTCUSD",
                "entry_order_type": "market",
                "tp_order_type": "limit",
                "sl_order_type": "market"
            },
            "BTC_L4": {  # Scared Lama 1D45m1m
                "logic": "alpha",
                "coin": "btc",
                "account_id": 31462134,  # slackerbot2021@gmail.com
                "pair": "BTC_BTCUSD",
                "entry_order_type": "market",
                "tp_order_type": "limit",
                "sl_order_type": "market"
            },
            "BTC_L5": {  # Nerd Lama 1D45m1m
                "logic": "alpha",
                "coin": "btc",
                "account_id": 31466503,  # swethbot@gmail.com
                "pair": "BTC_BTCUSD",
                "entry_order_type": "market",
                "tp_order_type": "limit",
                "sl_order_type": "market"
            },
            "BTC_L6": {  # Scared Lama 1D45m5m
                "logic": "alpha",
                "coin": "btc",
                "account_id": 31467510,  # shorterbot2021@hotmail.com
                "pair": "BTC_BTCUSD",
                "entry_order_type": "market",
                "tp_order_type": "limit",
                "sl_order_type": "market"
            }
        },
    },
}
