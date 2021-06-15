import json
from py3cw.request import Py3CW

from config import USER_ATTR


def main():
    # change this to whatever you need
    user = 'latham'

    api_key = USER_ATTR[user]['c3_api_key']
    secret = USER_ATTR[user]['c3_secret']
    py3c = Py3CW(key=api_key, secret=secret)

    base_trade = get_base_trade()
    base_trade_error, base_trade_data = py3c.request(entity="smart_trades_v2", action="new", payload=base_trade)
    if base_trade_error.get("error"):
        raise Exception(f"Error opening base trade, {base_trade_error['msg']}")
    trade_id = str(base_trade_data['id'])
    price = round(float(base_trade_data['position']['price']['value']), 2)
    print(f"purchase price was {price}")
    tp = 0.2
    tp_trailing = 0.02
    sl = 0.2
    tp_price = round(price * (1 + tp/100), 2)
    sl_price = round(price * (1 - sl/100), 2)
    print(f"calculated tp of {tp_price}, sl of {sl_price}")
    trade_update = get_trade_update(trade_id=trade_id, tp=tp_price, sl_price=sl_price, sl_pct=sl, tp_trailing=tp_trailing)
    update_trade_error, update_trade_data = py3c.request(
        entity="smart_trades_v2", action="update", action_id=trade_id, payload=trade_update)
    if update_trade_error.get("error"):
        raise Exception(f"Error opening tp trade, {update_trade_error['msg']}")
    print(update_trade_data)


def get_base_trade():
    return {
        "account_id": 30391847,
        "pair": "ETH_ETHUSD_PERP",
        "position": {
            "type": "buy",
            "units": {
                "value": "1.0"
            },
            "order_type": "market"
        },
        "leverage": {
            "enabled": True,
            "type": "isolated",
            "value": "1"
        },
        "take_profit": {
            "enabled": False
        },
        "stop_loss": {
            "enabled": False
        }
    }


def get_trade_update(trade_id, tp, sl_price, sl_pct, tp_trailing):
    return {
        "id": trade_id,
        "position": {
            "type": "buy",
            "units": {
                "value": "3.0"
            },
            "order_type": "market"
        },
        "take_profit": {
            "enabled": True,
            "steps": [
                {
                    "order_type": "market",
                    "price": {
                        "value": tp,
                        "type": "last"
                    },
                    "volume": 100,
                    "trailing": {
                        "enabled": True,
                        "percent": tp_trailing
                    }
                }
            ]
        },
        "stop_loss": {
            "enabled": True,
            "order_type": "market",
            "conditional": {
                "price": {
                    "value": sl_price,
                    "type": "last"
                },
                "trailing": {
                    "enabled": True,
                    "percent": sl_pct
                }
            }
        }
    }


if __name__ == '__main__':
    main()
