import pymongo
from time import sleep

from alphabot.py3cw.request import Py3CW
import alphabot.helpers as h

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
                # logger.debug(
                #    f"{user} {strat} skipping trade checkup because strat is missing the status field"
                # )
                continue
            if not trade_id:
                logger.debug(
                    f"{user} {strat} skipping trade checkup because it's never opened a trade"
                )
                continue
            _trade_status = h.trade_status(
                py3c=py3c, trade_id=trade_id, user=user, strat=strat, logger=logger
            )  # only one API call per checkup
            # logger.debug(f"{user} {strat} got trade status {_trade_status}")
            check_tsl(
                _trade_status=_trade_status,
                strat_states=strat_states,
                strat=strat,
                user=user,
                trade_id=trade_id,
                py3c=py3c,
                coll=coll,
                logger=logger,
            )
            log_profits(
                _trade_status=_trade_status,
                trade_id=trade_id,
                user=user,
                strat=strat,
                logger=logger,
                coll=coll,
                strat_states=strat_states,
            )

    return "Trade checkup complete"


def log_profits(
    _trade_status, trade_id, user, strat, logger, coll=None, strat_states=None
):
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

    paper_assets = strat_states[strat]["status"].get("paper_assets", STARTING_PAPER)
    potential_paper_assets = strat_states[strat]["status"].get(
        "potential_paper_assets", STARTING_PAPER
    )
    profit_pct = float(_trade_status["profit"]["percent"])
    last_tsl_set = strat_states[strat]["status"].get("last_tsl_set")

    # check for new max profit
    cur_max_profit = strat_states[strat]["status"].get("max_profit_this_entry", -100)
    max_profit_this_entry = max(profit_pct, cur_max_profit)
    if max_profit_this_entry > cur_max_profit:
        # update the db
        coll.update_one(
            {"_id": user},
            {"$set": {f"{strat}.status.max_profit_this_entry": max_profit_this_entry}},
            upsert=True,
        )

    # check for new max drawdown
    cur_max_drawdown = strat_states[strat]["status"].get("max_drawdown_this_entry", 0)
    max_drawdown_this_entry = min(profit_pct, cur_max_drawdown)
    if max_drawdown_this_entry < cur_max_drawdown:
        # update the db
        coll.update_one(
            {"_id": user},
            {
                "$set": {
                    f"{strat}.status.max_drawdown_this_entry": max_drawdown_this_entry
                }
            },
            upsert=True,
        )

    if not h.is_trade_closed(_trade_status):
        direction = h.get_current_trade_direction(
            _trade_status=_trade_status, user=user, strat=strat, logger=logger
        )
        if last_tsl_set is not None:
            tsl_str = f" TSL was set at {-1 * last_tsl_set}% profit."
        else:
            tsl_str = ""
        entry_time = strat_states[strat]["status"].get("entry_time")
        # logger.warning(f"{user} {strat} about to print profit update, direction is {direction}")
        logger.info(
            f"{user} {strat} {direction} {trade_id} current profit: {profit_pct}%, "
            f"max profit: {max_profit_this_entry}%, max drawdown: {max_drawdown_this_entry}%.{tsl_str} "
            f"Entry time: {entry_time} UTC"
        )
        return

    profit_logged = strat_states[strat]["status"].get("profit_logged")
    if profit_logged:
        # logger.debug(
        #    f"{user} {strat} already logged profit for trade {trade_id}, current paper assets: ${paper_assets}")
        return

    new_paper_assets = int(paper_assets * (1 + profit_pct / 100))
    new_potential_paper_assets = int(
        potential_paper_assets * (1 + max_profit_this_entry / 100)
    )

    # add to history
    profit_history = strat_states[strat]["status"].get("profit_history", {})
    entry_time = _trade_status["data"]["created_at"][5:16].replace("T", " ")
    exit_time = _trade_status["data"]["closed_at"][5:16].replace("T", " ")
    profit_history[entry_time] = {
        "profit": round(profit_pct, 2),
        "potential_profit": round(max_profit_this_entry, 2),
        "max_drawdown": round(max_drawdown_this_entry, 2),
        "assets": new_paper_assets,
        "potential_assets": new_potential_paper_assets,
        "exit_time": exit_time,
    }

    coll.update_one(
        {"_id": user},
        {
            "$set": {
                f"{strat}.status.paper_assets": new_paper_assets,
                f"{strat}.status.potential_paper_assets": new_potential_paper_assets,
                f"{strat}.status.profit_logged": True,
                f"{strat}.status.profit_history": profit_history,
            }
        },
        upsert=True,
    )
    direction = strat_states[strat]["status"].get("last_entry_direction")
    logger.info(
        f"{user} {strat} profit on last trade ({direction}) was {profit_pct}% out of a potential "
        f"{max_profit_this_entry}%, paper assets are now ${new_paper_assets:,} out of a potential "
        f"${new_potential_paper_assets:,}"
    )


def check_tsl(_trade_status, strat_states, strat, user, trade_id, py3c, coll, logger):
    trade_direction = h.get_current_trade_direction(
        _trade_status=_trade_status, user=user, strat=strat, logger=logger
    )
    if not trade_direction:
        # logger.debug(f"{user} {strat} not in a trade, not checking TSL resets")
        return

    sl_price, sl_trigger, new_tsl = get_tsl_reset(
        _trade_status=_trade_status,
        strat_states=strat_states,
        strat=strat,
        user=user,
        trade_id=trade_id,
        logger=logger,
    )

    if not sl_price:
        return

    if not sl_price:
        # get the old one
        sl_price = _trade_status["stop_loss"]["conditional"]["price"]["value"]

    # most things are the same
    _type = _trade_status["position"]["type"]
    units = _trade_status["position"]["units"]["value"]
    tp_price = _trade_status["take_profit"]["steps"][0]["price"]["value"]
    tp_trail = _trade_status["take_profit"]["steps"][0]["trailing"]["percent"]
    sl_pct = strat_states[strat]["config"]["sl_pct"]

    update_trade = h.get_update_trade(
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
        f"{user} {strat} Sending update trade while resetting TSL: {update_trade}"
    )
    update_trade_error, update_trade_data = py3c.request(
        entity="smart_trades_v2",
        action="update",
        action_id=trade_id,
        payload=update_trade,
    )
    if update_trade_error.get("error"):
        logger.error(f"{user} {strat} Error resetting TSL, {update_trade_error['msg']}")
        logger.info(
            f"{user} {strat} Closing trade {trade_id} since we couldn't reset TSL"
        )
        sleep(1)
        h.close_trade(
            py3c=py3c, trade_id=trade_id, user=user, strat=strat, logger=logger
        )
        raise Exception
    # update strat status so we don't do these triggers again
    set_command = {}
    if sl_trigger:
        tsl_reset_points_hit = strat_states[strat]["status"]["tsl_reset_points_hit"]
        tsl_reset_points_hit.append(sl_trigger)
        set_command[f"{strat}.status.tsl_reset_points_hit"] = tsl_reset_points_hit
        # save the most recent tsl set, for convenience
        set_command[f"{strat}.status.last_tsl_set"] = new_tsl
        logger.info(f"{user} {strat} {trade_direction} {trade_id} set TSL to {new_tsl}")

    coll.update_one(
        {"_id": user},
        {"$set": set_command},
        upsert=True,
    )


def get_tsl_reset(_trade_status, strat_states, strat, user, trade_id, logger):
    try:
        reset_tsl = strat_states[strat]["config"]["reset_tsl"]
        tsl_reset_points = strat_states[strat]["config"]["tsl_reset_points"]
    except KeyError:
        logger.warning(
            f"{user} {strat} skipping TSL reset check because {user} {strat} is missing a TSL reset config item. "
            f"Strat state is {strat_states[strat]}"
        )
        return None, None, None
    if not reset_tsl:
        # logger.debug(f"{user} {strat} has TSL reset disabled, skipping")
        return None, None, None
    profit_pct = float(_trade_status["profit"]["percent"])
    direction = strat_states[strat]["status"].get("last_entry_direction")
    tsl_reset_points_hit = strat_states[strat]["status"]["tsl_reset_points_hit"]
    for tsl_reset_point in tsl_reset_points:
        sl_trigger = tsl_reset_point[0]
        new_tsl = tsl_reset_point[1]
        if sl_trigger not in tsl_reset_points_hit:
            if profit_pct < sl_trigger:
                # logger.debug(
                #    f"{user} {strat} {direction} {trade_id} not resetting TSL, not enough in profit: "
                #    f"{profit_pct} < {tsl_reset_point[0]}"
                # )
                return None, None, None
            # all right, get new TSL!
            logger.info(
                f"{user} {strat} {direction} {trade_id} resetting TSL to {new_tsl} because profit "
                f"{profit_pct} >= {sl_trigger}"
            )
            _type = _trade_status["position"]["type"]
            trade_entry = float(_trade_status["position"]["price"]["value"])
            if _type == "buy":
                sl_price = trade_entry * (1 - new_tsl / 100)
            else:  # sell
                sl_price = trade_entry * (1 + new_tsl / 100)
            return sl_price, sl_trigger, new_tsl
