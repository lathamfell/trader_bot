from unittest.mock import call
import json
import alphabot.helpers as h


MOCK_USER_ATTR = {
    "malcolm": {
        "c3_api_key": "b122f74e630541109a11b9cb61540e151fe44e5887d943a78d2a5dc0d7f8055a",
        "c3_secret": "f57e76a3095e03d9701c0880a442b23e950cdbee8190e521de4ce0b01f2462e8b49779862a5046346c094d5a531c99f829726698036af968ce50f746d7876fe6e9d23de6a71682b8537867d591709e992f4b1eb6d7aaf22d092e29f6a818d431b7d62217",
        "email": "malcerlee@gmail.com",
        "email_enabled": False,
        "strats": {
            "BTC_M1": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 29896590,
                "pair": "BTC_BTCUSD_PERP",
                "description": "",
                "entry_order_type": "market",
                "tp_order_type": "market",
                "sl_order_type": "market",
            },
            "ETH_M1": {
                "logic": "alpha",
                "coin": "eth",
                "account_id": 29896590,
                "pair": "ETH_ETHUSD_PERP",
                "description": "",
                "entry_order_type": "market",
                "tp_order_type": "market",
                "sl_order_type": "market",
            },
            "BTC_M2": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 30571928,
                "pair": "BTC_BTCUSD_PERP",
                "description": "",
                "entry_order_type": "market",
                "tp_order_type": "market",
                "sl_order_type": "market",
            }
        },
    },
    "latham": {
        "c3_api_key": "418a3c2e87f447219ca6ed9ebf35b4706e1c7610fbd24850b312ca504cf8bfa6",
        "c3_secret": "602bcc216123d14028e8eaff528636aab3e0622a3985d694a1e8cf47b389e7bc89bc81254f5f541ef02ad4661162e339d264091d22a7f30281268081bfb61b78acdc9be6b56a1d5c7c8e6a8e628af4f7ced2f4d9b3b33d72ca46523cb4040c432d25a783",
        "email": "lathamfell@gmail.com",
        "email_enabled": False,
        "strats": {
            "BTC_L1": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 30034871,
                "pair": "BTC_BTCUSD_PERP",
                "entry_order_type": "market",
                "tp_order_type": "market",
                "sl_order_type": "market",
            },
            "BTC_L2": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 30391847,
                "pair": "BTC_BTCUSD_PERP",
                "entry_order_type": "market",
                "tp_order_type": "market",
                "sl_order_type": "market",
            },
            "BTC_M3": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 30549010,
                "pair": "BTC_BTCUSD_PERP",
                "entry_order_type": "market",
                "tp_order_type": "market",
                "sl_order_type": "market",
            },
            "BTC_M4": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 30572521,
                "pair": "BTC_BTCUSD_PERP",
                "entry_order_type": "market",
                "tp_order_type": "market",
                "sl_order_type": "market",
            },
            "BTC_L3": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 30398341,
                "pair": "BTC_BTCUSD_PERP",
                "entry_order_type": "market",
                "tp_order_type": "market",
                "sl_order_type": "market",
            },
            "BTC_L4": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 30491505,
                "pair": "BTC_BTCUSD_PERP",
                "entry_order_type": "market",
                "tp_order_type": "market",
                "sl_order_type": "market",
            },
            "BTC_M5": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 30572479,
                "pair": "BTC_BTCUSD_PERP",
                "entry_order_type": "market",
                "tp_order_type": "market",
                "sl_order_type": "market",
            },
            "BTC_L5": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 29799999,
                "pair": "BTC_BTCUSD_PERP",
                "entry_order_type": "market",
                "tp_order_type": "market",
                "sl_order_type": "market",
            },
            "BTC_L6": {
                "logic": "alpha",
                "coin": "btc",
                "account_id": 30577995,
                "pair": "BTC_BTCUSD_PERP",
                "entry_order_type": "market",
                "tp_order_type": "market",
                "sl_order_type": "market",
            }
        },
    },
}

EXPECTED_REPORT_CALL_STRS = ['** REPORT **',
                             'Report: $9,844 out of potential $9,905: latham BTC_L5 <15m TP and SL>. Median potential profit: 0.12%, mean potential profit: 0.02%, std dev 0.28. Median drawdown: -0.21%, std dev: 0.25. Leverage: [1]. Trades: 6 since 07-06 05:23 UTC',
                             'Report: $9,856 out of potential $10,046: latham BTC_L3 <15m Tiny TP>. Median potential profit: 0.15%, mean potential profit: 0.11%, std dev 0.31. Median drawdown: -0.31%, std dev: 0.3. Leverage: [1]. Trades: 7 since 07-06 05:23 UTC',
                             'Report: $9,911 out of potential $10,064: latham BTC_L4 <15m Split TPs>. Median potential profit: 0.27%, mean potential profit: 0.15%, std dev 0.29. Median drawdown: -0.3%, std dev: 0.29. Leverage: [1]. Trades: 7 since 07-06 05:23 UTC',
                             'Report: $9,977 out of potential $10,019: malcolm BTC_M1 <A2A 15m>. Median potential profit: 0.32%, mean potential profit: 0.32%, std dev 0. Median drawdown: -0.23%, std dev: 0. Leverage: [1]. Trades: 1 since 07-08 03:51 UTC',
                             'Report: $9,987 out of potential $10,025: latham BTC_L6 <15m SL>. Median potential profit: 0.23%, mean potential profit: 0.12%, std dev 0.3. Median drawdown: -0.15%, std dev: 0.18. Leverage: [1]. Trades: 5 since 07-06 05:23 UTC',
                             'Report: $10,000 out of potential $10,000: malcolm ETH_M1 <15m ETH Fo Shizzle on da A2A>. Median potential profit: 0%, mean potential profit: 0%, std dev 0. Median drawdown: 0%, std dev: 0. Leverage: [1]. Trades: 0 since 07-08 18:23 UTC',
                             'Report: $10,000 out of potential $10,000: malcolm BTC_M2 <30m A2A HSL>. Median potential profit: 0%, mean potential profit: 0%, std dev 0. Median drawdown: 0%, std dev: 0. Leverage: [1]. Trades: 0 since 07-08 17:09 UTC',
                             'Report: $10,000 out of potential $10,000: latham BTC_L1 <1m Benchmark>. Median potential profit: 0%, mean potential profit: 0%, std dev 0. Median drawdown: 0%, std dev: 0. Leverage: [1]. Trades: 0 since 07-06 05:23 UTC',
                             'Report: $10,000 out of potential $10,000: latham BTC_L2 <1m Split TP>. Median potential profit: 0%, mean potential profit: 0%, std dev 0. Median drawdown: 0%, std dev: 0. Leverage: [5]. Trades: 0 since 07-06 05:23 UTC',
                             'Report: $10,000 out of potential $10,000: latham BTC_M3 <1h SL/TP>. Median potential profit: 0%, mean potential profit: 0%, std dev 0. Median drawdown: 0%, std dev: 0. Leverage: [1]. Trades: 0 since 07-08 18:27 UTC',
                             'Report: $10,000 out of potential $10,000: latham BTC_M4 < 5/15 A2A HSL>. Median potential profit: 0%, mean potential profit: 0%, std dev 0. Median drawdown: 0%, std dev: 0. Leverage: [1]. Trades: 0 since 07-08 18:27 UTC',
                             'Report: $10,000 out of potential $10,000: latham BTC_M5 <15m A2A HSL>. Median potential profit: 0%, mean potential profit: 0%, std dev 0. Median drawdown: 0%, std dev: 0. Leverage: [1]. Trades: 0 since 07-08 18:27 UTC',
                             ]


def get_expected_calls(_expected_str_set):
    expected_calls = []
    for _str in _expected_str_set:
        expected_calls.append(call(_str))
    return expected_calls


def reset_test_coll(reset_file):
    coll = h.get_mongo_coll()
    coll.drop()
    with open(f"test/test_files/{reset_file}") as _f:
        file_data = json.load(_f)
    coll.insert_many(file_data)
    return coll
