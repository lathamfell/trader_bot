from alphabot.py3cw.request import Py3CW
from time import sleep
import logging

from alphabot.config import USER_ATTR
import alphabot.helpers as h
import alphabot.trading as trading

USER = "latham"

logger = logging.getLogger()


def main():
    api_key = USER_ATTR[USER]["c3_api_key"]
    secret = USER_ATTR[USER]["c3_secret"]
    py3c = Py3CW(key=api_key, secret=secret)
    account_id = 30577995
    pair = "BTC_BTCUSD_PERP"
    leverage = 1
    _type = "buy"
    units = 2
    tp_pct = 10
    tp_trail = None
    sl_pct = 10


    error, data = py3c.request(entity="accounts", action="", action_id="29834950")
    print(error)
    print(data)
    for account in data:
        if account['id'] == 29834950:
            print(account['btc_amount'])






    # partial signal sell starts here
    """
    base_trade = {
        "account_id": account_id,
        "note": "",
        "pair": pair,
        "leverage": {"enabled": True, "type": "isolated", "value": leverage},
        "position": {
            "type": _type,  # 'buy' / 'sell'
            "units": {"value": units},
            "order_type": "market",
        },
        "take_profit": {
            "enabled": True,
            "steps": [
                {
                    "order_type": "market",
                    "price": {"value": 45000, "type": "last"},
                    "volume": 100
                }
            ],
        },
        "stop_loss": {
            "enabled": True,
            "order_type": "market",
            "conditional": {
                "price": {"value": 20000, "type": "last"},
                "trailing": {"enabled": True, "percent": sl_pct},
            },
        },
    }
    base_trade_error, base_trade_data = py3c.request(
        entity="smart_trades_v2", action="new", payload=base_trade
    )

    trade_id = str(base_trade_data["id"])
    while True:
        _trade_status = trading.trade_status(
            py3c=py3c, trade_id=trade_id, description="", logger=logger
        )
        if h.is_trade_open(_trade_status):
            break
        logger.debug(
            f"trade {trade_id} waiting for base open. Status: {_trade_status['status']['type']}. "
            f"Full status: {_trade_status}"
        )
        sleep(1)
    
    # pull stop loss from trade status (see waiting_targets.py), put that SL in the next request
    
    # now try updating with a split TP
    print("original trade is opened with 1 TP at 45000.  Confirm on 3Commas")
    sleep(10)
    print("now sending update trade with a split TP, the first TP is well below current price")
    update_trade = {
        "id": trade_id,
        "position": {"type": _type, "units": {"value": units}, "order_type": "market"},
        "take_profit": {
            "enabled": True,
            "steps": [
            {
                "order_type": "market",
                "price": {"value": 25000, "type": "last"},
                "volume": 50
            },
            {
                "order_type": "market",
                "price": {"value": 45000, "type": "last"},
                "volume": 50
            }
        ],
        },
        "stop_loss": {
            "enabled": True,
            "order_type": "market",
            "conditional": {
                "price": {"value": 20000, "type": "last"},
                "trailing": {"enabled": True, "percent": sl_pct},
            },
        },
    }

    error, data = py3c.request(
        entity="smart_trades_v2",
        action="update",
        action_id=trade_id,
        payload=update_trade
    )
    print(error)
    print(data)
    """

    # end of signal based partial sell

"""
    # now try updating to 1 unit
    add_funds = {
        "id": 7675088,
        "order_type": "market",
        "units": {"value": -1},
    }

    update_trade_error, update_trade_data = py3c.request(
        entity="smart_trades_v2",
        action="add_funds",
        action_id="7675088",
        payload=add_funds,
    )
    print(update_trade_data)
    print(update_trade_error)

    # trade_id = "7508801"
    # _trade_status = trade_status(py3c, trade_id)

    # base_trade = get_base_trade(account_id, pair, _type, leverage, units)
    # error, data = py3c.request(entity="smart_trades_v2", action="new", payload=base_trade)
    # trade_id = str(data['id'])
    # sleep(1)
    # trade_id = "7490766"
    # trade_info = py3c.request(entity="smart_trades_v2", action="get_by_id", action_id=trade_id)

    # data = close_trade(py3c=py3c, trade_id=trade_id)
    # print(data)

    working_base_trade = {
        "account_id": 30391847,
        "pair": "ETH_ETHUSD_PERP",
        "leverage": {"enabled": True, "type": "isolated", "value": 1},
        "position": {"type": "buy", "units": {"value": 1}, "order_type": "market"},
        "take_profit": {"enabled": False},
        "stop_loss": {"enabled": False},
    }
    print("making base trade")
    error1, data1 = py3c.request(
        entity="smart_trades_v2", action="new", payload=working_base_trade
    )
    trade_id = data1["id"]
    trade_entry = round(float(data1["position"]["price"]["value"]), 2)

    tp_price = round(trade_entry * (1 + 1.0 / 100))
    sl_price = round(trade_entry * (1 - 1.0 / 100))

    working_update_trade = {
        "id": trade_id,
        "position": {"type": "buy", "units": {"value": 1}, "order_type": "market"},
        "take_profit": {
            "enabled": True,
            "steps": [
                {
                    "order_type": "market",
                    "price": {"value": tp_price, "type": "last"},
                    "volume": 100,
                }
            ],
        },
        "stop_loss": {
            "enabled": True,
            "order_type": "market",
            "conditional": {
                "price": {"value": sl_price, "type": "last"},
                "trailing": {"enabled": True, "percent": 1.0},
            },
        },
    }

    # check status like we do in breakeven
    _trade_status = trade_status(py3c, trade_id)

    error2, data2 = py3c.request(
        entity="smart_trades_v2",
        action="update",
        action_id=str(data1["id"]),
        payload=working_update_trade,
    )

    failing_update_trade = {
        "id": trade_id,
        "position": {"type": "buy", "units": {"value": "1"}, "order_type": "market"},
        "take_profit": {
            "enabled": True,
            "steps": [
                {
                    "order_type": "market",
                    "price": {"value": tp_price, "type": "last"},
                    "volume": 100,
                }
            ],
        },
        "stop_loss": {
            "enabled": True,
            "order_type": "market",
            "conditional": {
                "price": {"value": 37735, "type": "last"},
                "trailing": {"enabled": True, "percent": 0.3},
            },
        },
    }
    error3, data3 = py3c.request(
        entity="smart_trades_v2",
        action="update",
        action_id=str(data1["id"]),
        payload=failing_update_trade,
    )
    print(error3)

    sleep(1)
    data = close_trade(py3c=py3c, trade_id=str(data1["id"]))
"""


if __name__ == "__main__":
    main()
