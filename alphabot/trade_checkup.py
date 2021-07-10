from time import sleep
from statistics import median, mean
from numpy import std

from alphabot.py3cw.request import Py3CW
import alphabot.helpers as h
import alphabot.trading as trading

from alphabot.config import USER_ATTR, STARTING_PAPER


def trade_checkup(logger):
    coll = h.get_mongo_coll()

    print("--")

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

            description = strat_states[strat]["config"].get("description", "")
            if not trade_id:
                #print(
                #    f"{description} skipping trade checkup because it's not in a trade"
                #)
                continue
            _trade_status = trading.trade_status(
                py3c=py3c, trade_id=trade_id, description=description, logger=logger
            )  # only one API call per checkup
            print(f"{_trade_status} for trade {trade_id}")
            #logger.debug(f"Trade checkup on {description} got trade status {_trade_status}")
            # if a TP is triggered, this function will pass back an updated trade status
            #   otherwise it returns the original
            #_trade_status = check_take_profits(
            #    _trade_status=_trade_status, strat_states=strat_states, strat=strat, py3c=py3c,
            #    description=description, logger=logger, trade_id=trade_id, user=user
            #)

            new_tsl = check_tsl(
                _trade_status=_trade_status,
                strat_states=strat_states,
                strat=strat,
                user=user,
                trade_id=trade_id,
                py3c=py3c,
                coll=coll,
                description=description,
                logger=logger,
            )
            log_profit_and_roe(
                _trade_status=_trade_status,
                trade_id=trade_id,
                description=description,
                user=user,
                strat=strat,
                logger=logger,
                coll=coll,
                new_tsl=new_tsl
            )

    return "Trade checkup complete"


def check_take_profits(_trade_status, strat_states, user, strat, trade_id, py3c, description, logger):
    print("Check take profits should not be getting called")
    if not h.is_trade_open(_trade_status=_trade_status):
        return
    tp_pct = strat_states[strat]["config"]["tp_pct"]
    tp_pct_2 = strat_states[strat]["config"].get("tp_pct_2")

    profit, roe = h.get_profit_and_roe(_trade_status)
    if (tp_pct_2 and tp_pct_2 >= profit) or (not tp_pct_2 and tp_pct >= profit):
        # close trade completely
        _trade_status = trading.close_trade(
            py3c=py3c, trade_id=trade_id, user=user, strat=strat, description=description, logger=logger)
    elif tp_pct_2 and tp_pct >= profit:
        # partial close
        _trade_status = trading.take_partial_profit(
            py3c=py3c, trade_id=trade_id, description=description, user=user, strat=strat, logger=logger,
        )
        return _trade_status

    return _trade_status


def check_tsl(_trade_status, description, strat_states, strat, user, trade_id, py3c, coll, logger):
    if not h.is_trade_open(_trade_status=_trade_status):
        #logger.debug(f"{description} not in a trade, not checking TSL resets")
        return
    sl_price, sl_trigger, new_tsl = get_tsl_reset(
        _trade_status=_trade_status,
        strat_states=strat_states,
        description=description,
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
    tp_price_1 = _trade_status["take_profit"]["steps"][0]["price"]["value"]
    tp_price_2 = None
    try:
        tp_price_2 = _trade_status["take_profit"]["steps"][1]["price"]["value"]
    except IndexError:
        # only one TP
        pass
    tp_trail = _trade_status["take_profit"]["steps"][0]["trailing"]["percent"]
    sl_pct = strat_states[strat]["config"]["sl_pct"]
    description = strat_states[strat]["config"].get("description")

    update_trade = trading.get_update_trade(
        trade_id=trade_id,
        _type=_type,
        units=units,
        tp_price_1=tp_price_1,
        tp_price_2=tp_price_2,
        tp_trail=tp_trail,
        sl_price=sl_price,
        sl_pct=sl_pct,
        description=description,
        logger=logger,
    )
    print(
        f"{description} sending update trade while resetting TSL: {update_trade}"
    )
    update_trade_error, update_trade_data = py3c.request(
        entity="smart_trades_v2",
        action="update",
        action_id=trade_id,
        payload=update_trade,
    )
    if update_trade_error.get("error"):
        print(f"{description} error resetting TSL, {update_trade_error['msg']}")
        print(
            f"{description} closing trade {trade_id} since we couldn't reset TSL"
        )
        sleep(1)
        trading.close_trade(
            py3c=py3c, trade_id=trade_id, user=user, strat=strat, description=description, logger=logger
        )
        raise Exception
    # update strat status so we don't do these triggers again
    set_command = {}
    direction = strat_states[strat]["status"].get("last_entry_direction")
    if sl_trigger:
        tsl_reset_points_hit = strat_states[strat]["status"]["tsl_reset_points_hit"]
        tsl_reset_points_hit.append(sl_trigger)
        set_command[f"{strat}.status.tsl_reset_points_hit"] = tsl_reset_points_hit
        # save the most recent tsl set, for convenience
        set_command[f"{strat}.status.last_tsl_set"] = new_tsl
        print(f"{description} {direction} {trade_id} set TSL to {new_tsl}")

    coll.update_one(
        {"_id": user},
        {"$set": set_command},
        upsert=True,
    )

    if new_tsl:
        return new_tsl


def get_tsl_reset(_trade_status, description, strat_states, strat, user, trade_id, logger):
    try:
        reset_tsl = strat_states[strat]["config"]["reset_tsl"]
        tsl_reset_points = strat_states[strat]["config"]["tsl_reset_points"]
    except KeyError:
        print(
            f"{description} skipping TSL reset check because missing a TSL reset config item. "
            f"Strat state is {strat_states[strat]}"
        )
        return None, None, None
    if not reset_tsl:
        # logger.debug(f"{user} {strat} has TSL reset disabled, skipping")
        return None, None, None
    profit, roe = h.get_profit_and_roe(_trade_status)
    direction = strat_states[strat]["status"].get("last_entry_direction")
    tsl_reset_points_hit = strat_states[strat]["status"]["tsl_reset_points_hit"]
    for tsl_reset_point in tsl_reset_points:
        sl_trigger = tsl_reset_point[0]
        new_tsl = tsl_reset_point[1]
        if sl_trigger not in tsl_reset_points_hit:
            if profit < sl_trigger:
                print(
                    f"{description} {direction} {trade_id} waiting for next TSL trigger {tsl_reset_point[0]}"
                )
                return None, None, None
            # all right, get new TSL!

            _type = _trade_status["position"]["type"]
            trade_entry = h.get_trade_entry(_trade_status=_trade_status)
            if _type == "buy":
                sl_price = trade_entry * (1 - new_tsl / 100)
            else:  # sell
                sl_price = trade_entry * (1 + new_tsl / 100)

            print(
                f"{description} {direction} {trade_id} resetting TSL to {new_tsl}% (price {round(sl_price, 2)}) because "
                f"profit {profit}% >= {sl_trigger}%"
            )

            return sl_price, sl_trigger, new_tsl

    return None, None, None


def log_profit_and_roe(
    _trade_status, trade_id, description, user, strat, logger, coll=None, new_tsl=None
):
    if not coll:
        coll = h.get_mongo_coll()

    strat_states = coll.find_one({"_id": user})
    profit_logged = strat_states[strat]["status"].get("profit_logged")
    if profit_logged:
        print(
           f"{description} already logged profit for trade {trade_id}")
        return

    paper_assets = strat_states[strat]["status"].get("paper_assets", STARTING_PAPER)
    potential_paper_assets = strat_states[strat]["status"].get(
        "potential_paper_assets", STARTING_PAPER
    )
    leverage = strat_states[strat]["config"].get("leverage", 1)
    profit, roe = h.get_profit_and_roe(_trade_status=_trade_status)
    if new_tsl:
        last_tsl_set = new_tsl
    else:
        last_tsl_set = strat_states[strat]["status"].get("last_tsl_set")
    direction = strat_states[strat]["status"].get("last_entry_direction")
    description = strat_states[strat]["config"].get("description")

    set_command = {}

    # check for new max profit
    cur_max_profit = strat_states[strat]["status"].get("max_profit_this_entry", -100000)
    max_profit_this_entry = max(profit, cur_max_profit)
    if max_profit_this_entry > cur_max_profit:
        set_command[f"{strat}.status.max_profit_this_entry"] = max_profit_this_entry

    # check for new max drawdown
    cur_max_drawdown = strat_states[strat]["status"].get("max_drawdown_this_entry", 0)
    max_drawdown_this_entry = min(profit, cur_max_drawdown)
    if max_drawdown_this_entry < cur_max_drawdown:
        set_command[f"{strat}.status.max_drawdown_this_entry"] = max_drawdown_this_entry

    if not h.is_trade_closed(_trade_status=_trade_status, logger=logger):
        # save listed profit for comparison to profit on close later
        set_command[f"{strat}.status.most_recent_profit"] = profit
        if set_command:
            coll.update_one({"_id": user}, {"$set": set_command}, upsert=True)
            #print(f"{description} set most recent profit to {profit}")

    if not h.is_trade_closed(_trade_status=_trade_status, logger=logger):
        # logger.debug(f"{description} detected that trade {trade_id} is not closed, doing profit update and returning")
        # update the user
        if last_tsl_set is not None:
            tsl_str = f" TSL was set at {1 * last_tsl_set}% ({round(1 * last_tsl_set * leverage, 2)}% ROE)."
        else:
            tsl_str = ""
        entry_time = strat_states[strat]["status"].get("entry_time")
        print(
            f"{description} {direction} {trade_id} current profit: {profit}% ({round(profit * leverage, 2)}% ROE), "
            f"max profit: {max_profit_this_entry}% ({round(max_profit_this_entry * leverage, 2)}% ROE), max drawdown: "
            f"{max_drawdown_this_entry}% ({round(max_drawdown_this_entry * leverage, 2)}% ROE).{tsl_str} "
            f"Entry time: {entry_time}"
        )
        return

    # trade is closed!
    print(f"{description} Detected a closed trade, full status: {_trade_status}")
    new_paper_assets = int(paper_assets * (1 + roe / 100))
    print(f"{description} roe was {roe}, old paper assets was {paper_assets} new paper assets are {new_paper_assets}")
    # calculate potential profit for this trade. Take the max recorded profit, and subtract the observed close dump
    most_recent_profit = strat_states[strat]["status"].get("most_recent_profit", 0)
    print(f"{description} got most recent profit {most_recent_profit} from strat status. Final trade profit was {profit}")
    close_dump = profit - most_recent_profit
    print(f"{description} close dump (slippage + fees) is {round(close_dump, 2)}%")
    new_potential_paper_assets = int(
        potential_paper_assets * (1 + ((max_profit_this_entry + close_dump) * leverage) / 100)
    )
    print(
        f"{description} max profit this entry was {max_profit_this_entry}. Potential paper assets were "
        f"{potential_paper_assets}, now is {new_potential_paper_assets}")

    # add to profits record and history
    potential_profits = strat_states[strat]["status"].get("potential_profits", [])
    potential_profits.append(max_profit_this_entry)
    median_potential_profit = round(median(potential_profits), 2)
    mean_potential_profit = round(mean(potential_profits), 2)
    profit_std_dev = round(std(potential_profits), 2)

    drawdowns = strat_states[strat]["status"].get("drawdowns", [])
    drawdowns.append(max_drawdown_this_entry)
    median_drawdown = round(median(drawdowns), 2)
    drawdown_std_dev = round(std(drawdowns), 2)

    full_profit_history = strat_states[strat]["status"].get("full_profit_history", {})
    entry_time = h.get_readable_time(t=_trade_status["data"]["created_at"])
    exit_time = h.get_readable_time(t=_trade_status["data"]["closed_at"])
    new_history_entry = {
        "profit": profit,
        "roe": roe,
        "potential_profit": max_profit_this_entry,
        "max_drawdown": max_drawdown_this_entry,
        "assets": new_paper_assets,
        "potential_assets": new_potential_paper_assets,
        "exit_time": exit_time,
        "close_dump": close_dump,
        "trade_id": trade_id
    }
    full_profit_history[entry_time] = new_history_entry
    print(f"Added entry to full profit history: {new_history_entry}")

    coll.update_one(
        {"_id": user},
        {
            "$set": {
                f"{strat}.status.paper_assets": new_paper_assets,
                f"{strat}.status.potential_paper_assets": new_potential_paper_assets,
                f"{strat}.status.profit_logged": True,
                f"{strat}.status.full_profit_history": full_profit_history,
                f"{strat}.status.potential_profits": potential_profits,
                f"{strat}.status.drawdowns": drawdowns,
                f"{strat}.status.median_potential_profit": median_potential_profit,
                f"{strat}.status.mean_potential_profit": mean_potential_profit,
                f"{strat}.status.profit_std_dev": profit_std_dev,
                f"{strat}.status.drawdown_std_dev": drawdown_std_dev,
                f"{strat}.status.median_drawdown": median_drawdown,
                f"{strat}.status.trade_id": None
            }
        },
        upsert=True,
    )
    print(
        f"{description} {direction} {trade_id} **CLOSED**  Profit: {profit}% ({round(profit * leverage, 2)}% ROE) out "
        f"of "
        f"a potential "
        f"{max_profit_this_entry}% ({round(max_profit_this_entry * leverage, 2)}% ROE), paper assets are now "
        f"${new_paper_assets:,} out of a potential ${new_potential_paper_assets:,}"
    )
