from py3cw.request import Py3CW
from time import sleep

from config import USER_ATTR
from helpers import open_trade, close_trade, get_base_trade, trade_status

USER = "latham"

FUNCTION = 1


def main():
    if FUNCTION == 1:
        main1()


def main1():
    api_key = USER_ATTR[USER]["c3_api_key"]
    secret = USER_ATTR[USER]["c3_secret"]
    py3c = Py3CW(key=api_key, secret=secret)
    account_id = 30391847
    pair = "ETH_ETHUSD_PERP"
    leverage = 1
    _type = "buy"
    units = 1
    tp_pct = 0.2
    tp_trail = None
    sl_pct = 0.2

    """
    trade_id = open_trade(
        py3c=py3c,
        account_id=account_id,
        pair=pair,
        _type=_type,
        leverage=leverage,
        units=units,
        tp_pct=tp_pct,
        tp_trail=tp_trail,
        sl_pct=sl_pct,
    )
    """
    trade_id = "7508801"
    _trade_status = trade_status(py3c, trade_id)


    #base_trade = get_base_trade(account_id, pair, _type, leverage, units)
    #error, data = py3c.request(entity="smart_trades_v2", action="new", payload=base_trade)
    #trade_id = str(data['id'])
    sleep(1)
    #trade_id = "7490766"
    #trade_info = py3c.request(entity="smart_trades_v2", action="get_by_id", action_id=trade_id)

    data = close_trade(py3c=py3c, trade_id=trade_id)
    print(data)




if __name__ == "__main__":
    main()
