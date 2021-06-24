import json
import yagmail
import datetime as dt
from time import sleep

from alphabot.config import TRADE_TYPES, DEFAULT_STRAT_CONFIG
import alphabot.trade_checkup as tc


def trade_status(py3c, trade_id, user, strat, logger):
    error, data = py3c.request(
        entity="smart_trades_v2", action="get_by_id", action_id=str(trade_id)
    )
    if error.get("error"):
        logger.error(
            f"{user} {strat} Error getting trade info for trade {trade_id}, {error['msg']}"
        )
        raise Exception

    # logger.debug(f"{user} {strat} trade_status returning {data}")
    return data


def get_current_trade_direction(_trade_status, user, strat, logger):
    # logger.debug(f"{user} {strat} get_current_trade_direction, type is {_trade_status['status']['type']}")
    if not _trade_status:
        return None
    _open = _trade_status["status"]["type"] in TRADE_TYPES["open"]
    long = _trade_status["position"]["type"] == "buy"
    if _open and long:
        return "long"
    elif _open and not long:
        return "short"
    else:
        return None


def is_trade_open(_trade_status):
    return _trade_status["status"]["type"] in TRADE_TYPES["open"]


def is_trade_closed(_trade_status):
    try:
        _trade_status["data"]["closed_at"]
    except KeyError:
        return False
    return True


def current_trade_profit_pct(_trade_status):
    profit_pct = _trade_status["data"]["profit"]["percent"]
    return profit_pct


def in_order(_dict):
    return json.dumps(_dict, sort_keys=True)


def close_trade(py3c, trade_id, user, strat, logger):
    error, data = py3c.request(
        entity="smart_trades_v2", action="close_by_market", action_id=trade_id
    )
    if error.get("error"):
        logger.error(f"{user} {strat} Error closing trade {trade_id}, {error['msg']}")
        raise Exception

    while True:
        _trade_status = trade_status(
            py3c=py3c, trade_id=trade_id, user=user, strat=strat, logger=logger
        )
        if is_trade_closed(_trade_status):
            break
        logger.debug(
            f"{user} {strat} trade {trade_id} waiting for close. Status: {_trade_status['status']['type']}. "
            f"Full status: {_trade_status}"
        )
        sleep(1)

    logger.info(
        f"{user} {strat} trade {trade_id} successfully closed, status: {_trade_status['status']['type']}. "
        f"Full response: {data}"
    )
    # Do a one off profit log, because we can, because we closed this one ourselves
    # This prevents the daemon profit checker from missing this profit when we open another trade within 15s
    tc.log_profits(
        _trade_status=_trade_status,
        trade_id=trade_id,
        user=user,
        strat=strat,
        logger=logger,
    )
    return data


def open_trade(
    py3c,
    account_id,
    pair,
    _type,
    leverage,
    units,
    tp_pct,
    tp_trail,
    sl_pct,
    user,
    strat,
    note,
    logger,
):
    # logger.debug(
    #    f"{user} {strat} open_trade called with account_id {account_id}, pair {pair}, _type {_type}, leverage "
    #    f"{leverage}, units {units}, tp_pct {tp_pct}, tp_trail {tp_trail}, sl_pct {sl_pct}, note {note}"
    # )
    base_trade = get_base_trade(
        account_id=account_id,
        pair=pair,
        _type=_type,
        leverage=leverage,
        units=units,
        user=user,
        strat=strat,
        note=note,
        logger=logger,
    )
    # logger.debug(f"{user} {strat} Sending base trade: {base_trade}")
    base_trade_error, base_trade_data = py3c.request(
        entity="smart_trades_v2", action="new", payload=base_trade
    )
    if base_trade_error.get("error"):
        logger.error(
            f"{user} {strat} Error opening trade of type {_type} for account {account_id}, {base_trade_error['msg']}"
        )
        raise Exception

    trade_id = str(base_trade_data["id"])

    while True:
        _trade_status = trade_status(
            py3c=py3c, trade_id=trade_id, user=user, strat=strat, logger=logger
        )
        if is_trade_open(_trade_status):
            break
        logger.debug(
            f"{user} {strat} trade {trade_id} waiting for base open. Status: {_trade_status['status']['type']}. "
            f"Full status: {_trade_status}"
        )
        sleep(1)

    logger.debug(
        f"{user} {strat} trade {trade_id} successfully opened base, status: {_trade_status['status']['type']}. "
        f"Full response: {base_trade_data}"
    )

    trade_entry = float(base_trade_data["position"]["price"]["value"])
    logger.info(
        f"{user} {strat} Entered base trade {trade_id} {_type} at {trade_entry}"
    )
    if _type == "buy":
        tp_price = trade_entry * (1 + tp_pct / 100)
        sl_price = trade_entry * (1 - sl_pct / 100)
    else:  # sell
        tp_price = trade_entry * (1 - tp_pct / 100)
        sl_price = trade_entry * (1 + sl_pct / 100)
    update_trade = get_update_trade(
        trade_id=trade_id,
        _type=_type,
        units=units,
        tp_price=tp_price,
        tp_trail=tp_trail,
        sl_price=sl_price,
        sl_pct=sl_pct,
        user=user,
        strat=strat,
        logger=logger,
    )
    # logger.debug(
    #    f"{user} {strat} Sending update trade while opening trade: {update_trade}"
    # )

    update_trade_error, update_trade_data = py3c.request(
        entity="smart_trades_v2",
        action="update",
        action_id=trade_id,
        payload=update_trade,
    )
    if update_trade_error.get("error"):
        logger.error(
            f"{user} {strat} Error updating trade while opening, {update_trade_error['msg']}"
        )
        logger.info(
            f"{user} {strat} Closing trade {trade_id} since we couldn't apply TP/SL"
        )
        close_trade(py3c=py3c, trade_id=trade_id, user=user, strat=strat, logger=logger)
        raise Exception

    logger.debug(
        f"{user} {strat} trade {trade_id} successfully updated with TP/SL, response: {update_trade_data}"
    )
    return trade_id


def get_base_trade(account_id, pair, _type, leverage, units, user, strat, note, logger):
    # logger.debug(
    #    f"{user} {strat} get_base_trade called with account_id {account_id}, pair {pair}, _type {_type}, leverage "
    #    f"{leverage}, units {units}, note {note}"
    # )
    return {
        "account_id": account_id,
        "note": note,
        "pair": pair,
        "leverage": {"enabled": True, "type": "isolated", "value": leverage},
        "position": {
            "type": _type,  # 'buy' / 'sell'
            "units": {"value": units},
            "order_type": "market",
        },
        "take_profit": {"enabled": False},
        "stop_loss": {"enabled": False},
    }


def get_update_trade(
    trade_id, _type, units, tp_price, sl_price, sl_pct, tp_trail, user, strat, logger
):
    # logger.debug(
    #    f"{user} {strat} get_update_trade called with trade_id {trade_id}, units {units}, tp_price {tp_price}, "
    #    f"sl_price {sl_price}, sl_pct {sl_pct}, tp_trail {tp_trail}"
    # )
    update_trade = {
        "id": trade_id,
        "position": {"type": _type, "units": {"value": units}, "order_type": "market"},
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
                "trailing": {"enabled": True, "percent": sl_pct},
            },
        },
    }
    if tp_trail:
        update_trade["take_profit"]["steps"][0]["trailing"] = {
            "enabled": True,
            "percent": tp_trail,
        }
    return update_trade


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
        f"{strat}.status.max_profit_this_entry": -100,
        f"{strat}.status.max_drawdown_this_entry": 0,
        f"{strat}.status.last_tsl_set": tsl,
        f"{strat}.status.entry_time": entry_time,
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
