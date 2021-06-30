import json
import yagmail
import datetime as dt
from alphabot.config import TRADE_TYPES, DEFAULT_STRAT_CONFIG


def get_readable_time():
    return dt.datetime.now().isoformat()[5:16].replace("T", " ")


def get_current_trade_direction(_trade_status, user, strat, logger):
    # logger.debug(f"{user} {strat} get_current_trade_direction, type is {_trade_status['status']['type']}")
    if not _trade_status:
        return None
    #logger.debug(f"get_current_trade_direction, trade status: {_trade_status}")
    _open = is_trade_open(_trade_status=_trade_status) or is_trade_opening(_trade_status=_trade_status)
    long = _trade_status["position"]["type"] == "buy"
    if _open and long:
        return "long"
    elif _open and not long:
        return "short"
    else:
        return None


def get_trade_entry(_trade_status):
    return float(_trade_status["position"]["price"]["value_without_commission"])


def is_trade_open(_trade_status):
    return _trade_status["status"]["type"] in TRADE_TYPES["open"]


def is_trade_opening(_trade_status):
    return _trade_status["status"]["type"] in TRADE_TYPES["opening"]


def is_trade_closed(_trade_status):
    try:
        _trade_status["data"]["closed_at"]
    except KeyError:
        return False
    return True


def get_profit_and_roe(_trade_status):
    try:
        profit = float(_trade_status["profit"]["percent"])
        roe = float(_trade_status["profit"]["roe"])
    except KeyError:
        return None, None
    return profit, roe


def get_last_tp_price(_trade_status):
    last_step = len(_trade_status["take_profit"]["steps"]) - 1
    return float(_trade_status["take_profit"]["steps"][last_step]["price"]["value"])


def in_order(_dict):
    return json.dumps(_dict, sort_keys=True)


def screen_for_str_bools(value):
    if isinstance(value, str):
        if value == "true":
            return True
        if value == "false":
            return False
    return value


def send_email(to, subject, body=None):
    yagmail.SMTP("lathamfell@gmail.com", "lrhnapmiegubspht").send(to, subject, body)


def get_default_open_trade_mongo_set_command(strat, trade_id, direction, tsl):
    entry_time = dt.datetime.now().isoformat()[5:16].replace("T", " ")
    return {
        f"{strat}.status.trade_id": trade_id,
        f"{strat}.status.tsl_reset_points_hit": [],
        f"{strat}.status.profit_logged": False,
        f"{strat}.status.last_entry_direction": direction,
        f"{strat}.status.max_profit_this_entry": -100000,
        f"{strat}.status.max_drawdown_this_entry": 0,
        f"{strat}.status.last_tsl_set": tsl,
        f"{strat}.status.entry_time": entry_time,
        f"{strat}.status.most_recent_profit": 0,
        f"{strat}.status.took_partial_profit": False
    }


def set_up_default_strat_config(coll, user, strat):
    coll.update_one(
        {"_id": user},
        {
            "$set": {
                f"{strat}.config.tp_pct": DEFAULT_STRAT_CONFIG["tp_pct"],
                f"{strat}.config.tp_trail": DEFAULT_STRAT_CONFIG["tp_trail"],
                f"{strat}.config.sl_pct": DEFAULT_STRAT_CONFIG["sl_pct"],
                f"{strat}.config.leverage": DEFAULT_STRAT_CONFIG["leverage"],
                f"{strat}.config.units": DEFAULT_STRAT_CONFIG["units"],
            }
        },
        upsert=True,
    )