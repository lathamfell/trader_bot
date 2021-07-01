import logging

DEFAULT_STRAT_CONFIG = {
    "tp_pct": 0.2,
    "tp_trail": None,
    "sl_pct": 0.2,
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
TP_ORDER_TYPE = "market"

USER_ATTR = {
    "malcolm": {
        "c3_api_key": "b122f74e630541109a11b9cb61540e151fe44e5887d943a78d2a5dc0d7f8055a",
        "c3_secret": "f57e76a3095e03d9701c0880a442b23e950cdbee8190e521de4ce0b01f2462e8b49779862a5046346c094d5a531c99f829726698036af968ce50f746d7876fe6e9d23de6a71682b8537867d591709e992f4b1eb6d7aaf22d092e29f6a818d431b7d62217",
        "email": "malcerlee@gmail.com",
        "email_enabled": False,
        "strats": {
            "BTC_M1": {
                "logic": "gamma",
                "coin": "btc",
                "account_id": 29896590,  # Binance Futures
                "pair": "BTC_BTCUSD_PERP",
                "description": "",
                "simulate_leverage": True
            },
            "ETH_M1": {
                "logic": "gamma",
                "coin": "eth",
                "account_id": 29896590,  # Binance Futures
                "pair": "ETH_ETHUSD_PERP",
                "description": "",
                "simulate_leverage": True
            },
            "BTC_M2": {
                "logic": "gamma",
                "coin": "btc",
                "account_id": 30571928,  # Binance lathcolm
                "pair": "BTC_BTCUSD_PERP",
                "description": "",
                "simulate_leverage": True
            }
        },
    },
    "latham": {
        "c3_api_key": "418a3c2e87f447219ca6ed9ebf35b4706e1c7610fbd24850b312ca504cf8bfa6",
        "c3_secret": "602bcc216123d14028e8eaff528636aab3e0622a3985d694a1e8cf47b389e7bc89bc81254f5f541ef02ad4661162e339d264091d22a7f30281268081bfb61b78acdc9be6b56a1d5c7c8e6a8e628af4f7ced2f4d9b3b33d72ca46523cb4040c432d25a783",
        "email": "lathamfell@gmail.com",
        "email_enabled": False,
        "strats": {
            "BTC_L1": {  # 1m - Chrome
                "logic": "gamma",
                "coin": "btc",
                "account_id": 30034871,  # lec   2 BTC limit
                "pair": "BTC_BTCUSD_PERP",
                # configured leverage will be used to calculate paper profits, but trades will be made on the
                # exchange at 1x
                "simulate_leverage": True
            },
            "BTC_L2": {  # 1m = Firefox
                "logic": "gamma",
                "coin": "btc",
                "account_id": 30391847,  # tk  2 BTC limit
                "pair": "BTC_BTCUSD_PERP",
                "simulate_leverage": True
            },
            "BTC_M3": {
                "logic": "gamma",
                "coin": "btc",
                "account_id": 30549010,  # slackerbot  2 BTC limit.  Malcolm's $300 of BTC
                "pair": "BTC_BTCUSD_PERP",
                "simulate_leverage": True
            },
            "BTC_M4": {
                "logic": "gamma",
                "coin": "btc",
                "account_id": 30572521,  # lf2  2 BTC limit.  Malcolm's $300 of BTC
                "pair": "BTC_BTCUSD_PERP",
                "simulate_leverage": True
            },
            "BTC_L3": {
                "logic": "gamma",
                "coin": "btc",
                "account_id": 30398341,  # lf  2 BTC limit
                "pair": "BTC_BTCUSD_PERP",
                "simulate_leverage": True
            },
            "BTC_L4": {
                "logic": "gamma",
                "coin": "btc",
                "account_id": 30491505,  # Eth8  2 BTC limit
                "pair": "BTC_BTCUSD_PERP",
                "simulate_leverage": True
            },
            "BTC_M5": {
                "logic": "gamma",
                "coin": "btc",
                "account_id": 30572479,  # PsychoBot  2 BTC limit  # Malcolm's $300 of BTC
                "pair": "BTC_BTCUSD_PERP",
                "simulate_leverage": True
            },
            "BTC_L5": {  # 1m - Brave
                "logic": "gamma",
                "coin": "btc",
                "account_id": 29799999,  # lef35   0.05 BTC limit
                "pair": "BTC_BTCUSD_PERP",
                "simulate_leverage": True
            },
            "BTC_L6": {
                "logic": "gamma",
                "coin": "btc",
                "account_id": 30577995,  # Binance swethbot
                "pair": "BTC_BTCUSD_PERP",
                "simulate_leverage": True
            }
        },
    },
}
