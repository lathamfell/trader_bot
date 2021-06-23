import pymongo
from time import sleep

from alphabot.py3cw.request import Py3CW
from alphabot.helpers import (
    trade_status,
    get_current_trade_direction,
    get_update_trade,
    close_trade,
    is_trade_closed,
)

from alphabot.config import USER_ATTR, STARTING_PAPER


def trade_checkup(logger):
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
        tls=True,
        tlsAllowInvalidCertificates=True,
    )
    db = client.indicators_db
    coll = db.indicators_coll

    logger.info("Checking profits")

    for user in USER_ATTR:
        api_key = USER_ATTR[user]["c3_api_key"]
        secret = USER_ATTR[user]["c3_secret"]
        py3c = Py3CW(key=api_key, secret=secret)
        strat_states = coll.find_one({"_id": user})
        for strat in USER_ATTR[user]["strats"]:
            try:
                trade_id = strat_states[strat]["status"].get("trade_id")
            except KeyError:
                #logger.debug(
                #    f"{user} {strat} skipping trade checkup because strat is missing the status field"
                #)
                continue
            if not trade_id:
                logger.debug(f"{user} {strat} skipping trade checkup because it's never opened a trade")
                continue
            _trade_status = trade_status(
                py3c, trade_id, user, strat, logger
            )  # only one API call per checkup
            check_tsl_tp(
                _trade_status, strat_states, strat, user, trade_id, py3c, coll, logger
            )
            log_profits(
                _trade_status, trade_id, user, strat, logger, coll, strat_states
            )

    return "Trade checkup complete"


def log_profits(_trade_status, trade_id, user, strat, logger, coll=None, strat_states=None):
    if not coll:
        client = pymongo.MongoClient(
            "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
            tls=True,
            tlsAllowInvalidCertificates=True,
        )
        db = client.indicators_db
        coll = db.indicators_coll

    if not strat_states:
        strat_states = coll.find_one({"_id": user})

    paper_assets = strat_states[strat]["status"].get("paper_assets")
    if not paper_assets and paper_assets != 0:
        # first paper outlay
        paper_assets = STARTING_PAPER
    profit_pct = float(_trade_status["profit"]["percent"])

    if not is_trade_closed(_trade_status):
        direction = get_current_trade_direction(_trade_status, user, strat, logger)
        logger.info(
            f"{user} {strat} {direction} {trade_id} current profit: {profit_pct}%"
        )
        return

    profit_logged = strat_states[strat]["status"].get("profit_logged")
    if profit_logged:
        #logger.debug(
        #    f"{user} {strat} already logged profit for trade {trade_id}, current paper assets: ${paper_assets}")
        return

    new_paper_assets = int(paper_assets * (1 + profit_pct/100))

    # add to history
    profit_history = strat_states[strat]["status"].get("profit_history", {})
    entry_time = _trade_status["data"]["created_at"][5:16].replace("T", " ")
    exit_time = _trade_status["data"]["closed_at"][5:16].replace("T", " ")
    profit_history[entry_time] = {
        "profit": round(profit_pct, 2),
        "assets": new_paper_assets,
        "exit_time": exit_time
    }

    coll.update_one(
        {"_id": user},
        {
            "$set": {
                f"{strat}.status.paper_assets": new_paper_assets,
                f"{strat}.status.profit_logged": True,
                f"{strat}.status.profit_history": profit_history
            }
        },
    )
    direction = strat_states[strat]["status"].get("last_entry_direction")
    logger.info(
        f"{user} {strat} profit on last trade ({direction}) was {profit_pct}%, paper assets are "
        f"now ${new_paper_assets:,}"
    )


def check_tsl_tp(
    _trade_status, strat_states, strat, user, trade_id, py3c, coll, logger
):
    trade_direction = get_current_trade_direction(_trade_status, user, strat, logger)
    if not trade_direction:
        #logger.debug(f"{user} {strat} not in a trade, not checking TSL/TP resets")
        return

    sl_price, sl_trigger = get_tsl_reset(
        _trade_status, strat_states, strat, user, trade_id, logger
    )
    tp_price, tp_trigger = get_tp_reset(
        _trade_status, strat_states, strat, user, trade_id, logger
    )

    if not sl_price and not tp_price:
        return

    if not sl_price:
        # get the old one
        sl_price = _trade_status["stop_loss"]["conditional"]["price"]["value"]
    if not tp_price:
        tp_price = _trade_status["take_profit"]["steps"][0]["price"]["value"]

    # most things are the same
    _type = _trade_status["position"]["type"]
    units = _trade_status["position"]["units"]["value"]
    tp_trail = _trade_status["take_profit"]["steps"][0]["trailing"]["percent"]
    sl_pct = strat_states[strat]["config"]["sl_pct"]

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
    logger.debug(
        f"{user} {strat} Sending update trade while resetting TP/TSL: {update_trade}"
    )
    update_trade_error, update_trade_data = py3c.request(
        entity="smart_trades_v2",
        action="update",
        action_id=trade_id,
        payload=update_trade,
    )
    if update_trade_error.get("error"):
        logger.error(
            f"{user} {strat} Error resetting TP/TSL, {update_trade_error['msg']}"
        )
        logger.info(
            f"{user} {strat} Closing trade {trade_id} since we couldn't reset TP/TSL"
        )
        sleep(1)
        close_trade(py3c, trade_id, user, strat, logger)
        raise Exception
    # update strat status so we don't do these triggers again
    set_command = {}
    if sl_trigger:
        tsl_reset_points_hit = strat_states[strat]["status"]["tsl_reset_points_hit"]
        tsl_reset_points_hit.append(sl_trigger)
        set_command[f"{strat}.status.tsl_reset_points_hit"] = tsl_reset_points_hit
    if tp_trigger:
        tp_reset_points_hit = strat_states[strat]["status"]["tp_reset_points_hit"]
        tp_reset_points_hit.append(tp_trigger)
        set_command[f"{strat}.status.tp_reset_points_hit"] = tp_reset_points_hit

    coll.update_one(
        {"_id": user},
        {"$set": set_command},
        upsert=True,
    )
    logger.info(
        f"{user} {strat} {trade_id} {trade_direction} successfully reset TP/TSL, response: "
        f"{update_trade_data}"
    )


def get_tsl_reset(_trade_status, strat_states, strat, user, trade_id, logger):
    try:
        reset_tsl = strat_states[strat]["config"]["reset_tsl"]
        tsl_reset_points = strat_states[strat]["config"]["tsl_reset_points"]
    except KeyError:
        logger.warn(
            f"{user} {strat} skipping TSL reset check because {user} {strat} is missing a TSL reset config item. "
            f"Strat state is {strat_states[strat]}"
        )
        return None, None
    if not reset_tsl:
        #logger.debug(f"{user} {strat} has TSL reset disabled, skipping")
        return None, None
    profit_pct = float(_trade_status["profit"]["percent"])
    direction = strat_states[strat]["status"].get("last_entry_direction")
    tsl_reset_points_hit = strat_states[strat]["status"]["tsl_reset_points_hit"]
    for tsl_reset_point in tsl_reset_points:
        sl_trigger = tsl_reset_point[0]
        new_tsl = tsl_reset_point[1]
        if sl_trigger not in tsl_reset_points_hit:
            if profit_pct < sl_trigger:
                logger.debug(
                    f"{user} {strat} {direction} {trade_id} not resetting TSL, not enough in profit: "
                    f"{profit_pct} < {tsl_reset_point[0]}"
                )
                return None, None
            # all right, get new TSL!
            logger.info(
                f"{user} {strat} {direction} {trade_id} resetting TSL to {new_tsl} because profit "
                f"{profit_pct} >= {sl_trigger}")
            _type = _trade_status["position"]["type"]
            trade_entry = round(float(_trade_status["position"]["price"]["value"]))
            if _type == "buy":
                sl_price = round(trade_entry * (1 - new_tsl / 100))
            else:  # sell
                sl_price = round(trade_entry * (1 + new_tsl / 100))
            return sl_price, sl_trigger


def get_tp_reset(_trade_status, strat_states, strat, user, trade_id, logger):
    try:
        reset_tp = strat_states[strat]["config"]["reset_tp"]
        tp_reset_points = strat_states[strat]["config"]["tp_reset_points"]
    except KeyError:
        #logger.debug(
        #    f"{user} {strat} skipping TP reset check because {user} {strat} is missing a TP reset config item. "
        #    f"Strat state is {strat_states[strat]}"
        #)
        return None, None
    if not reset_tp:
        #logger.debug(f"{user} {strat} has TP reset disabled, skipping")
        return None, None
    profit_pct = float(_trade_status["profit"]["percent"])
    direction = strat_states[strat]["status"].get("last_entry_direction")
    tp_reset_points_hit = strat_states[strat]["status"]["tp_reset_points_hit"]
    for tp_reset_point in tp_reset_points:
        tp_trigger = tp_reset_point[0]
        new_tp = tp_reset_point[1]
        if tp_trigger not in tp_reset_points_hit:
            if profit_pct < tp_trigger:
                #logger.debug(
                #    f"trade {user} {strat} {trade_id} not resetting TP, not enough in profit: "
                #    f"{profit_pct} < {tp_reset_point[0]}"
                #)
                return None, None
            # all right, get new TP!
            logger.info(
                f"{user} {strat} {direction} {trade_id} resetting TP to {new_tp} because profit "
                f"{profit_pct} >= {tp_trigger}")
            _type = _trade_status["position"]["type"]
            trade_entry = round(float(_trade_status["position"]["price"]["value"]))
            if _type == "buy":
                tp_price = round(trade_entry * (1 + new_tp / 100))
            else:  # sell
                tp_price = round(trade_entry * (1 - new_tp / 100))

            return tp_price, tp_trigger
