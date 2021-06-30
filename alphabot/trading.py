from time import sleep

import alphabot.trade_checkup as tc
import alphabot.helpers as h


def trade_status(py3c, trade_id, description, logger):
    error, _trade_status = py3c.request(
        entity="smart_trades_v2", action="get_by_id", action_id=str(trade_id)
    )
    if error.get("error"):
        logger.error(
            f"{description} error getting trade info for trade {trade_id}, {error['msg']}"
        )
        raise Exception

    return _trade_status


def close_trade(py3c, trade_id, user, strat, description, logger):
    error, data = py3c.request(
        entity="smart_trades_v2", action="close_by_market", action_id=trade_id
    )
    if error.get("error"):
        logger.error(f"{description} Error closing trade {trade_id}, {error['msg']}")
        raise Exception

    while True:
        _trade_status = trade_status(
            py3c=py3c, trade_id=trade_id, description=description, logger=logger
        )
        if h.is_trade_closed(_trade_status):
            break
        logger.debug(
            f"{description} trade {trade_id} waiting for close. Status: {_trade_status['status']['type']}. "
            f"Full status: {_trade_status}"
        )
        sleep(1)

    logger.info(
        f"{description} trade {trade_id} successfully closed, status: {_trade_status['status']['type']}. "
        f"Full response: {data}"
    )
    # Do a one off profit log, because we can, because we closed this one ourselves
    # This prevents the daemon profit checker from missing this profit when we open another trade within 15s
    tc.log_profit_and_roe(
        _trade_status=_trade_status,
        trade_id=trade_id,
        user=user,
        strat=strat,
        logger=logger,
        py3c=py3c
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
    logger,
    description,
    price,
    user=None,
    strat=None,
    simulate_leverage=False,
    tp_pct_2=None
):
    # logger.debug(
    #    f"{user} {strat} open_trade called with account_id {account_id}, pair {pair}, _type {_type}, leverage "
    #    f"{leverage}, units {units}, tp_pct {tp_pct}, tp_trail {tp_trail}, sl_pct {sl_pct}, note {note}"
    # )
    if tp_pct_2 is not None and units < 2:
        logger.warning(f"Partial TP configured, but units are only 1. Rejecting trade")
        raise Exception
    if simulate_leverage:
        # use 1x for the actual trade. Configured leverage will still be used to calculate paper profits
        leverage = 1

    if _type == "buy":
        direction = "long"
    else:
        direction = "short"

    base_trade = get_base_trade(
        account_id=account_id,
        pair=pair,
        _type=_type,
        leverage=leverage,
        units=units,
        user=user,
        strat=strat,
        note=f"{description} {direction}",
        logger=logger,
    )
    # logger.debug(f"{user} {strat} Sending base trade: {base_trade}")
    base_trade_error, base_trade_data = py3c.request(
        entity="smart_trades_v2", action="new", payload=base_trade
    )
    if base_trade_error.get("error"):
        error_msg = f"{description} error opening trade of type {_type} for account {account_id}, {base_trade_error['msg']}"
        logger.error(error_msg)
        raise Exception(error_msg)

    trade_id = str(base_trade_data["id"])

    while True:
        _trade_status = trade_status(
            py3c=py3c, trade_id=trade_id, description=description, logger=logger
        )
        if h.is_trade_open(_trade_status):
            break
        logger.debug(
            f"{description} trade {trade_id} waiting for base open. Status: {_trade_status['status']['type']}. "
            f"Full status: {_trade_status}"
        )
        sleep(1)

    logger.debug(
        f"{description} {direction} {trade_id} base order in, status: {_trade_status['status']['type']}. "
        f"Full response: {_trade_status}"
    )

    trade_entry = h.get_trade_entry(_trade_status=_trade_status)

    if price:
        if _type == "buy":
            slippage = ((price - trade_entry) / trade_entry)
        else:
            slippage = ((trade_entry - price) / price)
        logger.info(
            f"{description} entered base trade {trade_id} {_type} at {trade_entry}, alert price was {price}. "
            f"Slippage: {round(slippage * 100, 2)}%"
        )

    if _type == "buy":
        tp_price = trade_entry * (1 + tp_pct / 100)
        if tp_pct_2 is not None:
            tp_price_2 = trade_entry * (1 + tp_pct_2 / 100)
        else:
            tp_price_2 = None
        sl_price = trade_entry * (1 - sl_pct / 100)
    else:  # sell
        tp_price = trade_entry * (1 - tp_pct / 100)
        if tp_pct_2 is not None:
            tp_price_2 = trade_entry * (1 - tp_pct_2 / 100)
        else:
            tp_price_2 = None
        sl_price = trade_entry * (1 + sl_pct / 100)
    update_trade = get_update_trade(
        trade_id=trade_id,
        _type=_type,
        units=units,
        tp_price_1=tp_price,
        tp_price_2=tp_price_2,
        tp_trail=tp_trail,
        sl_price=sl_price,
        sl_pct=sl_pct,
        description=description,
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
            f"{description} Error updating trade while opening, {update_trade_error['msg']}"
        )
        logger.info(
            f"{description} Closing trade {trade_id} since we couldn't apply TP/SL"
        )
        close_trade(py3c=py3c, trade_id=trade_id, user=user, strat=strat, description=description, logger=logger)
        raise Exception

    logger.debug(
        f"{description} {direction} {trade_id} **OPENED**  Full trade status: {update_trade_data}"
    )
    return trade_id


def get_base_trade(account_id, pair, _type, leverage, units, user, strat, note, logger):
    # logger.debug(
    #    f"{user} {strat} get_base_trade called with account_id {account_id}, pair {pair}, _type {_type}, leverage "
    #    f"{leverage}, units {units}, note {note}"
    # )
    base_trade = {
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
    return base_trade


def get_update_trade(
    trade_id, _type, units, tp_price_1, sl_price, sl_pct, description, logger, tp_price_2=None, tp_trail=None
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
                    "price": {"value": tp_price_1, "type": "last"},
                    "volume": 100
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
    #if tp_trail:
    #    update_trade["take_profit"]["steps"][0]["trailing"] = {
    #        "enabled": True,
    #        "percent": tp_trail,
    #    }
    if tp_price_2 is not None:
        update_trade["take_profit"]["steps"] = [
            {
                "order_type": "market",
                "price": {"value": tp_price_1, "type": "last"},
                "volume": 50
            },
            {
                "order_type": "market",
                "price": {"value": tp_price_2, "type": "last"},
                "volume": 50
            }
        ]

    return update_trade


def take_partial_profit(py3c, trade_id, description, user, strat, logger):
    # get current trade attributes
    _trade_status = trade_status(py3c=py3c, trade_id=trade_id, description=description, logger=logger)
    current_sl = _trade_status["stop_loss"]["conditional"]["price"]["value"]
    current_tp = h.get_last_tp_price(_trade_status=_trade_status)
    _type = _trade_status["position"]["type"]
    units = _trade_status["position"]["units"]["value"]
    # get an update trade where TP1 is well within current profit and TP2 is old single TP
    if _type == "buy":
        tp_price_1 = current_tp / 2
    else:
        tp_price_1 = current_tp * 2

    tp_price_2 = current_tp
    update_trade = get_update_trade(
        trade_id=trade_id, _type=_type, units=units, tp_price_1=tp_price_1, tp_price_2=tp_price_2, sl_price=current_sl,
        sl_pct=None, description=description, logger=logger)

    update_trade_error, update_trade_data = py3c.request(
        entity="smart_trades_v2",
        action="update",
        action_id=trade_id,
        payload=update_trade,
    )
    if update_trade_error.get("error"):
        logger.error(
            f"{description} Error updating trade while taking partial profit, {update_trade_error['msg']}"
        )
        logger.info(
            f"{description} Closing trade {trade_id} since we couldn't take partial profit"
        )
        close_trade(py3c=py3c, trade_id=trade_id, user=user, strat=strat, description=description, logger=logger)
        raise Exception

    if _type == "buy":
        direction = "long"
    else:
        direction = "short"

    logger.debug(
        f"{description} {direction} {trade_id} **PARTIAL CLOSE** Took partial profit.  Full trade status: "
        f"{update_trade_data}"
    )
    return
