import logging

USER_ATTR = {
    "malcolm": {
        "c3_api_key": "b122f74e630541109a11b9cb61540e151fe44e5887d943a78d2a5dc0d7f8055a",
        "c3_secret": "f57e76a3095e03d9701c0880a442b23e950cdbee8190e521de4ce0b01f2462e8b49779862a5046346c094d5a531c99f829726698036af968ce50f746d7876fe6e9d23de6a71682b8537867d591709e992f4b1eb6d7aaf22d092e29f6a818d431b7d62217",
        "email": "malcerlee@gmail.com",
        "email_enabled": False,
        "strats": {
            "btc": {
                "logic": "gamma",
                "coin": "btc",
                "account_id": 29896590,  # Binance COIN-M
                "pair": "BTC_BTCUSD_PERP",
                "description": ""
            },
            "eth": {
                "logic": "gamma",
                "coin": "eth",
                "account_id": 29896590,  # Binance COIN-M
                "pair": "ETH_ETHUSD_PERP",
                "description": ""
            },
        },
    },
    "latham": {
        "c3_api_key": "418a3c2e87f447219ca6ed9ebf35b4706e1c7610fbd24850b312ca504cf8bfa6",
        "c3_secret": "602bcc216123d14028e8eaff528636aab3e0622a3985d694a1e8cf47b389e7bc89bc81254f5f541ef02ad4661162e339d264091d22a7f30281268081bfb61b78acdc9be6b56a1d5c7c8e6a8e628af4f7ced2f4d9b3b33d72ca46523cb4040c432d25a783",
        "email": "lathamfell@gmail.com",
        "email_enabled": False,
        "strats": {
            "eth1": {  # 1m Crayons/Heuristic with minimum TP/SL
                "logic": "alpha",
                "coin": "eth",
                "account_id": 29799999,  # COIN-M lef35
                "pair": "ETH_ETHUSD_PERP",
                "interval": "1m",
                "description": "1m Crayons + Heuristic entry with minimal TP/SL"
            },
            "eth2": {  # 1m Heuristic trend follower
                "logic": "gamma",
                "coin": "eth",
                "account_id": 30548884,  # COIN-M lf2 (lathamfell2)
                "pair": "ETH_ETHUSD_PERP",
                "interval": "1m",
                "description": "1m Heuristic trend follower"
            },
            "eth3": {  # 1m Crayons/Heuristic
                "logic": "alpha",
                "coin": "eth",
                "account_id": 30391847,  # COIN-M tk (trendking2021)
                "pair": "ETH_ETHUSD_PERP",
                "interval": "1m",
                "description": "1m Crayons + Heuristic entry with TSL"
            },
            "eth4": {  # 1m Crayons/Heuristic with Hull alignment
                "logic": "beta",
                "coin": "eth",
                "account_id": 30398341,  # Binance lf Futures COIN-M (lathamfell)
                "pair": "ETH_ETHUSD_PERP",
                "interval": "1m",
                "description": "1m Crayons + Heuristic entry with Hull alignment and TSL"
            },
            "eth5": {  # 15m Crayons/Heuristic
                "logic": "alpha",
                "coin": "eth",
                "account_id": 30491505,  # Binance Eth8 Futures COIN-M (eth8eth8eth8)
                "pair": "ETH_ETHUSD_PERP",
                "interval": "15m",
                "description": "15m Crayons + Heuristic entry with TSL"
            },
            "eth6": {  # 15m Crayons/Heuristic with Hull alignment
                "logic": "beta",
                "coin": "eth",
                "account_id": "30034871",  # Binance COIN-M lec
                "pair": "ETH_ETHUSD_PERP",
                "interval": "15m",
                "description": "15m Crayons + Heuristic entry with Hull alignment and TSL"
            },
            "eth7": {  # 15m Heuristic trend follower
                "logic": "gamma",
                "coin": "eth",
                "account_id": "30549010",
                "pair": "ETH_ETHUSD_PERP",
                "interval": "15m",
                "description": "15m Heuristic trend follower"
            }
        },
    },
}

DEFAULT_STRAT_CONFIG = {
    "tp_pct": 0.2,
    "tp_trail": None,
    "sl_pct": 0.2,
    "leverage": 1,
    "units": 1,
}

TRADE_TYPES = {
    "open": ["waiting_targets"],
    "closing": ["stop_loss_in_progress", "panic_sell_pending", "panic_sell_in_progress"],
    "closed": ["finished", "panic_sold", "stop_loss_finished"]
}

LOG_LEVEL = logging.DEBUG
STARTING_PAPER = 10000
