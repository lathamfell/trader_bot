from time import sleep

import alphabot.trade_checkup as tc
import alphabot.helpers as h


def trade_status(py3c, trade_id, description, logger):
    error, _trade_status = py3c.request(
        entity="smart_trades_v2", action="get_by_id", action_id=str(trade_id)
    )
    if error.get("error"):
        print(
            f"{description} error getting trade info for trade {trade_id}, {error['msg']}"
        )
        raise Exception
    # logger.debug(f"Trade {trade_id} current status: {_trade_status}")
    return _trade_status


def close_trade(py3c, trade_id, user, strat, description, logger):
    coll = h.get_mongo_coll()

    error, data = py3c.request(
        entity="smart_trades_v2", action="close_by_market", action_id=trade_id
    )
    print(f"{description} direct response to close trade req: {data}")
    if error.get("error"):
        print(f"{description} Error closing trade {trade_id}, {error['msg']}")
        raise Exception

    while True:
        _trade_status = trade_status(
            py3c=py3c, trade_id=trade_id, description=description, logger=logger
        )
        if h.is_trade_closed(_trade_status=_trade_status, logger=logger):
            break
        print(
            f"{description} trade {trade_id} waiting for close. Status: {_trade_status['status']['type']}. "
            f"Full status: {_trade_status}"
        )
        sleep(1)

    print(
        f"{description} trade {trade_id} successfully closed, status: {_trade_status['status']['type']}. "
        f"Full response: {_trade_status}"
    )
    # Do a one off profit log, because we can, because we closed this one ourselves
    # This prevents the daemon profit checker from missing this profit when we open another trade within 15s
    tc.log_profit_and_roe(
        _trade_status=_trade_status,
        trade_id=trade_id,
        description=description,
        user=user,
        strat=strat,
        logger=logger,
    )
    coll.update_one(
        {"_id": user}, {"$set": {f"{strat}.status.trade_id": None}}, upsert=True
    )
    return _trade_status


def open_trade(
    py3c,
    account_id,
    pair,
    _type,
    leverage,
    units,
    tp_pct,
    sl_pct,
    sl_trail,
    logger,
    description,
    alert_price,
    entry_order_type,
    tp_order_type,
    sl_order_type,
    dca_pct=None,
    user=None,
    strat=None,
    tp_pct_2=None,
    coll=None,
    entry_signal=None
):
    # logger.debug(
    #    f"{user} {strat} open_trade called with account_id {account_id}, pair {pair}, _type {_type}, leverage "
    #    f"{leverage}, units {units}, tp_pct {tp_pct}, tp_trail {tp_trail}, sl_pct {sl_pct}, note {note}"
    # )
    if not coll:
        h.get_mongo_coll()

    if tp_pct_2 is not None and units < 2:
        print(f"Partial TP configured, but units are only 1. Rejecting trade")
        raise Exception

    if _type == "buy":
        direction = "long"
    else:
        direction = "short"

    dca_prices = []
    if dca_pct:
        units = units // (len(dca_pct) + 1)

    base_trade = get_base_trade(
        account_id=account_id,
        pair=pair,
        _type=_type,
        leverage=leverage,
        alert_price=alert_price,
        units=units,
        entry_order_type=entry_order_type,
        user=user,
        strat=strat,
        note=f"{description} {entry_signal} {direction}",
        logger=logger,
    )
    # logger.debug(f"{user} {strat} Sending base trade: {base_trade}")
    base_trade_error, base_trade_data = py3c.request(
        entity="smart_trades_v2", action="new", payload=base_trade
    )
    print(f"base_trade_data: {base_trade_data}")
    print(f"base_trade_error: {base_trade_error}")

    if base_trade_error.get("error"):
        error_msg = f"{description} error opening trade of type {_type} for account {account_id}, {base_trade_error['msg']}"
        print(error_msg)
        raise Exception(error_msg)

    trade_id = str(base_trade_data["id"])

    while True:
        _trade_status = trade_status(
            py3c=py3c, trade_id=trade_id, description=description, logger=logger
        )
        if h.is_trade_open(_trade_status):
            break
        print(
            f"{description} {entry_signal} trade {trade_id} waiting for base open. Status: {_trade_status['status']['type']}. "
            f"Full status: {_trade_status}"
        )
        sleep(1)

    print(
        f"{description} {entry_signal} {direction} {trade_id} base order in, status: {_trade_status['status']['type']}. "
        f"Full response: {_trade_status}"
    )

    trade_entry = h.get_trade_entry(_trade_status=_trade_status)

    if alert_price:
        if _type == "buy":
            slippage = (alert_price - trade_entry) / trade_entry
        else:
            slippage = (trade_entry - alert_price) / alert_price
        print(
            f"{description} {entry_signal} entered base trade {trade_id} {_type} at {trade_entry}"
        )

    if _type == "buy":
        tp_price = trade_entry * (1 + tp_pct / 100)
        if tp_pct_2 is not None:
            tp_price_2 = trade_entry * (1 + tp_pct_2 / 100)
        else:
            tp_price_2 = None
        sl_price = trade_entry * (1 - sl_pct / 100)
        if dca_pct:
            for dca in dca_pct:
                dca_prices.append(trade_entry * (1 - dca / 100))
        direction = "long"
    else:  # sell
        tp_price = trade_entry * (1 - tp_pct / 100)
        if tp_pct_2 is not None:
            tp_price_2 = trade_entry * (1 - tp_pct_2 / 100)
        else:
            tp_price_2 = None
        sl_price = trade_entry * (1 + sl_pct / 100)
        if dca_pct:
            for dca in dca_pct:
                dca_prices.append(trade_entry * (1 + dca / 100))
        direction = "short"
    update_trade_payload = get_update_trade_payload(
        trade_id=trade_id,
        _type=_type,
        units=units,
        tp_price_1=tp_price,
        tp_price_2=tp_price_2,
        sl_price=sl_price,
        sl_pct=sl_pct,
        sl_trail=sl_trail,
        entry_order_type=entry_order_type,
        tp_order_type=tp_order_type,
        sl_order_type=sl_order_type,
        description=description,
        logger=logger,
    )
    # logger.debug(
    #    f"{user} {strat} Sending update trade while opening trade: {update_trade}"
    # )

    # separate API call to add TP and SL. This is because we needed the exact entry price from the base trade call in
    #   order to calculate them.
    print(f"Updating trade {trade_id} with payload: {update_trade_payload}")
    update_trade_error, update_trade_data = py3c.request(
        entity="smart_trades_v2",
        action="update",
        action_id=trade_id,
        payload=update_trade_payload,
    )
    if update_trade_error.get("error"):
        print(
            f"{description} Error updating trade while opening, {update_trade_error['msg']}"
        )
        print(
            f"full update trade config: {update_trade_payload}"
        )
        print(f"{description} Closing trade {trade_id} by market since we couldn't apply TP/SL")
        close_trade(
            py3c=py3c,
            trade_id=trade_id,
            user=user,
            strat=strat,
            description=description,
            logger=logger,
        )
        raise Exception
    print(f"Trade {trade_id} updated with TP/SL")

    if dca_pct:
        for i, dca in enumerate(dca_pct):
            # per 3C API docs, separate API call required to add the DCA limit order
            add_funds_payload = get_add_funds_payload(
                units=units,
                price=dca_prices[i],
                trade_id=trade_id
            )
            print(f"Adding funds to trade {trade_id} with payload {add_funds_payload}")
            add_funds_error, add_funds_data = py3c.request(
                entity="smart_trades_v2",
                action="add_funds",
                action_id=trade_id,
                payload=add_funds_payload
            )
            if add_funds_error.get("error"):
                print(
                    f"{description} Error adding DCA limit order while opening, {add_funds_error['msg']}"
                )
                print(
                    f"full DCA (add_funds) config: {add_funds_payload}"
                )
                print(f"{description} Closing trade {trade_id} by market since we couldn't apply DCA {dca}%")
                close_trade(
                    py3c=py3c,
                    trade_id=trade_id,
                    user=user,
                    strat=strat,
                    description=description,
                    logger=logger,
                )
                raise Exception
            print(f"{description} trade {trade_id} updated with DCA order at {dca}%")

    coll.update_one(
        {"_id": user},
        {
            "$set": h.get_default_open_trade_mongo_set_command(
                strat=strat,
                trade_id=trade_id,
                direction=direction,
                sl=sl_pct,
                dca=dca_pct,
                entry_signal=entry_signal
            )
        },
        upsert=True,
    )

    print(
        f"{description} {entry_signal} {direction} {trade_id} **OPENED**  Full trade status: {update_trade_data}"
    )

    return trade_id


def get_base_trade(account_id, pair, _type, leverage, alert_price, units, user, strat, entry_order_type, note, logger):
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
            "order_type": entry_order_type,
        },
        "take_profit": {"enabled": False},
        "stop_loss": {"enabled": False},
    }
    if entry_order_type == "limit":
        base_trade["position"]["price"] = {"value": alert_price}
    return base_trade


def get_update_trade_payload(
    trade_id,
    _type,
    units,
    tp_price_1,
    sl_price,
    sl_pct,
    sl_trail,
    entry_order_type,
    tp_order_type,
    sl_order_type,
    description,
    logger,
    tp_price_2=None
):
    # logger.debug(
    #    f"{user} {strat} get_update_trade called with trade_id {trade_id}, units {units}, tp_price {tp_price}, "
    #    f"sl_price {sl_price}, sl_pct {sl_pct}"
    # )
    update_trade_payload = {
        "id": trade_id,
        "position": {"type": _type, "units": {"value": units}, "order_type": entry_order_type},
        "take_profit": {
            "enabled": True,
            "steps": [
                {
                    "order_type": tp_order_type,
                    "price": {"value": tp_price_1, "type": "last"},
                    "volume": 100,
                }
            ],
        },
        "stop_loss": {
            "enabled": True,
            "order_type": sl_order_type,
            "conditional": {
                "price": {"value": sl_price, "type": "last"},
                "trailing": {"enabled": sl_trail, "percent": sl_pct},
            },
        },
    }

    if tp_price_2 is not None:
        update_trade_payload["take_profit"]["steps"] = [
            {
                "order_type": tp_order_type,
                "price": {"value": tp_price_1, "type": "last"},
                "volume": 50,
            },
            {
                "order_type": tp_order_type,
                "price": {"value": tp_price_2, "type": "last"},
                "volume": 50,
            },
        ]

    return update_trade_payload


def get_add_funds_payload(units, price, trade_id):
    add_funds_payload = {
        "order_type": "limit",
        "units": {
            "value": units
        },
        "price": {
            "value": price
        },
        "id": trade_id,
    }
    return add_funds_payload


"""
def take_partial_profit(
    py3c,
    trade_id,
    description,
    user,
    entry_order_type,
    tp_order_type,
    sl_order_type,
    strat,
    logger,
    strat_states=None,
    _trade_status=None,
):
    # get current trade attributes
    if strat_states:
        # check for ourselves whether partial profit has been taken
        if strat_states[user]["strats"][strat].get("took_partial_profit"):
            print(f"{description} already took partial profit, exiting")
            return _trade_status
    if not _trade_status:
        _trade_status = trade_status(
            py3c=py3c, trade_id=trade_id, description=description, logger=logger
        )
    current_sl = _trade_status["stop_loss"]["conditional"]["price"]["value"]
    current_sl_trail = _trade_status["stop_loss"]["conditional"]["trailing"]["enabled"]
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
        trade_id=trade_id,
        _type=_type,
        units=units,
        tp_price_1=tp_price_1,
        tp_price_2=tp_price_2,
        sl_price=current_sl,
        sl_pct=None,
        sl_trail=current_sl_trail,
        entry_order_type=entry_order_type,
        tp_order_type=tp_order_type,
        sl_order_type=sl_order_type,
        description=description,
        logger=logger,
    )

    update_trade_error, update_trade_data = py3c.request(
        entity="smart_trades_v2",
        action="update",
        action_id=trade_id,
        payload=update_trade,
    )
    if update_trade_error.get("error"):
        print(
            f"{description} Error updating trade while taking partial profit, {update_trade_error['msg']}"
        )
        print(
            f"full update trade config: {update_trade}"
        )
        print(
            f"{description} Closing trade {trade_id} by market since we couldn't take partial profit"
        )
        close_trade(
            py3c=py3c,
            trade_id=trade_id,
            user=user,
            strat=strat,
            description=description,
            logger=logger,
        )
        raise Exception

    if _type == "buy":
        direction = "long"
    else:
        direction = "short"

    print(
        f"{description} {direction} {trade_id} **PARTIAL CLOSE** Took partial profit.  Full trade status: "
        f"{update_trade_data}"
    )
    return _trade_status
"""
