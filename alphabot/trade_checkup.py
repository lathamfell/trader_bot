from time import sleep
from statistics import median, mean
from numpy import std

from alphabot.py3cw.request import Py3CW
import alphabot.helpers as h
import alphabot.trading as trading

from alphabot.config import USER_ATTR, STARTING_PAPER


def trade_checkup(logger):
    coll = h.get_mongo_coll()

    # print("--")

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
                # print(
                #    f"{description} skipping trade checkup because it's not in a trade"
                # )
                continue
            _trade_status = trading.trade_status(
                py3c=py3c, trade_id=trade_id, description=description, logger=logger
            )  # only one API call per checkup
            # logger.debug(f"Trade checkup on {description} got trade status {_trade_status}")
            # if a TP is triggered, this function will pass back an updated trade status
            #   otherwise it returns the original
            # _trade_status = check_take_profits(
            #    _trade_status=_trade_status, strat_states=strat_states, strat=strat, py3c=py3c,
            #    description=description, logger=logger, trade_id=trade_id, user=user
            # )

            entry_order_type = USER_ATTR[user]["strats"][strat]["entry_order_type"]
            tp_order_type = USER_ATTR[user]["strats"][strat]["tp_order_type"]
            sl_order_type = USER_ATTR[user]["strats"][strat]["sl_order_type"]
            #new_sl = check_sl_reset_due_to_reset_trigger_hit(
            #    _trade_status=_trade_status,
            #    strat_states=strat_states,
            #    strat=strat,
            #    user=user,
            #    entry_order_type=entry_order_type,
            #    tp_order_type=tp_order_type,
            #    sl_order_type=sl_order_type,
            #    trade_id=trade_id,
            #    py3c=py3c,
            #    coll=coll,
            #    description=description,
            #    logger=logger,
            #)
            check_tp_and_sl_reset_due_to_dca_hit(
                _trade_status=_trade_status,
                strat_states=strat_states,
                strat=strat,
                user=user,
                entry_order_type=entry_order_type,
                tp_order_type=tp_order_type,
                sl_order_type=sl_order_type,
                trade_id=trade_id,
                py3c=py3c,
                coll=coll,
                description=description,
                logger=logger
            )
            log_profit_and_roe(
                _trade_status=_trade_status,
                trade_id=trade_id,
                description=description,
                user=user,
                strat=strat,
                logger=logger,
                coll=coll,
                new_sl=None
            )

    return "Trade checkup complete"


def check_take_profits(
    _trade_status, strat_states, user, strat, trade_id, py3c, description, logger
):
    print("Check take profits should not be getting called")
    if not h.is_trade_open(_trade_status=_trade_status):
        return
    tp_pct = strat_states[strat]["config"]["tp_pct"]
    tp_pct_2 = strat_states[strat]["config"].get("tp_pct_2")

    profit, roe = h.get_profit_and_roe(_trade_status)
    if (tp_pct_2 and tp_pct_2 >= profit) or (not tp_pct_2 and tp_pct >= profit):
        # close trade completely
        _trade_status = trading.close_trade(
            py3c=py3c,
            trade_id=trade_id,
            user=user,
            strat=strat,
            description=description,
            logger=logger,
        )
    elif tp_pct_2 and tp_pct >= profit:
        # partial close
        _trade_status = trading.take_partial_profit(
            py3c=py3c,
            trade_id=trade_id,
            description=description,
            user=user,
            strat=strat,
            logger=logger,
        )
        return _trade_status

    return _trade_status


"""
def check_sl_reset_due_to_reset_trigger_hit(
    _trade_status, description, strat_states, strat, user, entry_order_type, tp_order_type, sl_order_type, trade_id, py3c, coll, logger
):
    if not h.is_trade_open(_trade_status=_trade_status):
        # logger.debug(f"{description} not in a trade, not checking SL resets")
        return
    sl_price, sl_trigger, new_sl = get_sl_reset(
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
    sl_pct = strat_states[strat]["config"]["sl_pct"]
    sl_trail = strat_states[strat]["config"]["sl_trail"]
    description = strat_states[strat]["config"].get("description")

    update_trade = trading.get_update_trade_payload(
        trade_id=trade_id,
        _type=_type,
        units=units,
        tp_price_1=tp_price_1,
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
    print(f"{description} sending update trade while resetting SL: {update_trade}")
    update_trade_error, update_trade_data = py3c.request(
        entity="smart_trades_v2",
        action="update",
        action_id=trade_id,
        payload=update_trade,
    )
    if update_trade_error.get("error"):
        print(f"{description} error resetting SL, {update_trade_error['msg']}")
        print(f"{description} closing trade {trade_id} by market since we couldn't reset SL")
        sleep(1)
        trading.close_trade(
            py3c=py3c,
            trade_id=trade_id,
            user=user,
            strat=strat,
            description=description,
            logger=logger,
        )
        raise Exception
    # update strat status so we don't do these triggers again
    set_command = {}
    direction = strat_states[strat]["status"].get("last_entry_direction")
    if sl_trigger:
        sl_reset_points_hit = strat_states[strat]["status"]["sl_reset_points_hit"]
        sl_reset_points_hit.append(sl_trigger)
        set_command[f"{strat}.status.sl_reset_points_hit"] = sl_reset_points_hit
        # save the most recent sl set, for convenience
        set_command[f"{strat}.status.last_sl_set"] = new_sl
        print(f"{description} {direction} {trade_id} set SL to {new_sl}")

    coll.update_one(
        {"_id": user},
        {"$set": set_command},
        upsert=True,
    )

    if new_sl:
        return new_sl



def get_sl_reset(
    _trade_status, description, strat_states, strat, user, trade_id, logger
):
    tf_idx = h.get_tf_idx(strat_states[strat]["status"]["entry_signal"])
    try:
        reset_sl = strat_states[strat]["config"]["reset_sl"][tf_idx]
        sl_reset_points = strat_states[strat]["config"]["sl_reset_points"]
        if not reset_sl or sl_reset_points == [[[]]]:
            # logger.debug(f"{user} {strat} has SL reset disabled or has no reset points, skipping")
            return None, None, None
    except KeyError:
        print(
            f"{description} skipping SL reset check because missing a SL reset config item. "
            f"Strat state is {strat_states[strat]}"
        )
        return None, None, None

    # get the reset points for this TF
    sl_reset_points = sl_reset_points[tf_idx]

    profit, roe = h.get_profit_and_roe(_trade_status)
    direction = strat_states[strat]["status"].get("last_entry_direction")
    sl_reset_points_hit = strat_states[strat]["status"]["sl_reset_points_hit"]
    for sl_reset_point in sl_reset_points:
        sl_trigger = sl_reset_point[0]
        new_sl = sl_reset_point[1]
        if sl_trigger not in sl_reset_points_hit:
            if profit < sl_trigger:
                print(
                    f"{description} {direction} {trade_id} waiting for next SL trigger {sl_reset_point[0]}"
                )
                return None, None, None
            # all right, get new SL!

            _type = _trade_status["position"]["type"]
            trade_entry = h.get_trade_entry(_trade_status=_trade_status)
            if _type == "buy":
                sl_price = trade_entry * (1 - new_sl / 100)
            else:  # sell
                sl_price = trade_entry * (1 + new_sl / 100)

            print(
                f"{description} {direction} {trade_id} resetting SL to {new_sl}% (price {round(sl_price, 2)}) because "
                f"profit {profit}% >= {sl_trigger}%"
            )

            return sl_price, sl_trigger, new_sl

    return None, None, None
"""


def check_tp_and_sl_reset_due_to_dca_hit(
        _trade_status, description, strat_states, strat, user, entry_order_type, tp_order_type, sl_order_type, trade_id,
        py3c, coll, logger
):
    if not h.is_trade_open(_trade_status=_trade_status):
        print(f"{description} not in a trade, not checking for DCA")
        return

    current_tp_price = _trade_status["take_profit"]["steps"][0]["price"]["value"]
    current_sl_price = _trade_status["stop_loss"]["conditional"]["price"]["value"]
    new_dca_stage, new_tp_price, new_sl_price = get_tp_sl_reset_due_to_dca(
        _trade_status=_trade_status, strat_states=strat_states, strat=strat
    )

    if not new_dca_stage:
        return

    print(f"{description} DCA stage {new_dca_stage} hit")

    # most things are the same
    _type = _trade_status["position"]["type"]
    units = _trade_status["position"]["units"]["value"]
    sl_pct = _trade_status["stop_loss"]["conditional"]["trailing"]["percent"]
    sl_trail = _trade_status["stop_loss"]["conditional"]["trailing"]["enabled"]
    description = strat_states[strat]["config"].get("description")

    update_trade = trading.get_update_trade_payload(
        trade_id=trade_id,
        _type=_type,
        units=units,
        tp_price_1=new_tp_price,
        tp_price_2=None,
        sl_price=new_sl_price,
        sl_pct=sl_pct,  # this is only used if trailing is enabled; not relevant for now
        sl_trail=sl_trail,
        entry_order_type=entry_order_type,
        tp_order_type=tp_order_type,
        sl_order_type=sl_order_type,
        description=description,
        logger=logger
    )
    print(
        f"{description} sending update trade to reset TP from {current_tp_price} to {new_tp_price} and SL "
        f"from {current_sl_price} to {new_sl_price} due to DCA hit: {update_trade}"
    )
    update_trade_error, update_trade_data = py3c.request(
        entity="smart_trades_v2",
        action="update",
        action_id=trade_id,
        payload=update_trade
    )
    if update_trade_error.get("error"):
        print(f"{description} error resetting TP/SL, {update_trade_error['msg']}")
        print(f"{description} ** WARNING ** could not reset TP/SL on trade {trade_id}")
        raise Exception

    # update trade status with new dca stage
    set_command = {
        f"{strat}.status.dca_stage": new_dca_stage
    }
    coll.update_one(
        {"_id": user},
        {"$set": set_command},
        upsert=True
    )
    print(f"{description} updated trade status DCA stage to {new_dca_stage}")


def get_tp_sl_reset_due_to_dca(_trade_status, strat_states, strat):
    state = strat_states[strat]
    current_units = float(_trade_status["position"]["units"]["value"])
    expected_cumulative_units = state["config"]["expected_cumulative_units"]
    dca_stage = state["status"]["dca_stage"]

    if dca_stage >= len(expected_cumulative_units):
        # reached all dca stages
        # nothing else to do
        return None, None, None
    
    if current_units == expected_cumulative_units[dca_stage]:
        # nothing to do because next DCA stage hasn't been reached yet
        # print(f"current_units {current_units} matches expected {expected_cumulative_units[dca_stage]} for stage {dca_stage}")
        return None, None, None

    # we reached the next dca stage
    print(
        f"current_units {current_units} does not match expected {expected_cumulative_units[dca_stage]} for "
        f"stage {dca_stage}")
    tf_idx = h.get_tf_idx(state["status"]["entry_signal"])
    new_dca_stage = dca_stage + 1
    new_tp_pct = state["config"]["tp_pct_after_dca"][tf_idx]
    sl_pct = state["config"]["sl_pct"][tf_idx]
    new_entry = h.get_trade_entry(_trade_status=_trade_status)
    new_tp_price = h.get_tp_price_from_pct(
        tp_pct=new_tp_pct,
        entry=new_entry,
        direction=state["status"]["last_entry_direction"])
    new_sl_price = h.get_sl_or_dca_price_from_pct(
        sl_or_dca_pct=sl_pct,
        entry=new_entry,
        direction=state["status"]["last_entry_direction"]
    )
    print(
        f"New TP pct is {new_tp_pct}, SL pct is still {sl_pct}. Starting from new average entry of {new_entry}, "
        f"new TP price is {new_tp_price} and new SL price is {new_sl_price}")
    return new_dca_stage, new_tp_price, new_sl_price


def log_profit_and_roe(
    _trade_status, trade_id, description, user, strat, logger, coll=None, new_sl=None
):
    if not coll:
        coll = h.get_mongo_coll()

    strat_states = coll.find_one({"_id": user})
    tf_idx = h.get_tf_idx(strat_states[strat]["status"]["entry_signal"])
    profit_logged = strat_states[strat]["status"].get("profit_logged")
    if profit_logged:
        print(f"{description} already logged profit for trade {trade_id}")
        return

    paper_assets = strat_states[strat]["status"].get("paper_assets", STARTING_PAPER)
    leverage = strat_states[strat]["config"].get("leverage", [1])[tf_idx]
    #tp = strat_states[strat]["config"]["tp_pct"][tf_idx]
    tp = h.get_current_tp_from_trade_status(ts=_trade_status)

    profit_pct, roe = h.get_profit_and_roe(_trade_status=_trade_status)
    if new_sl:
        last_sl_set = new_sl
    else:
        last_sl_set = strat_states[strat]["status"].get("last_sl_set")
    direction = strat_states[strat]["status"].get("last_entry_direction")
    description = strat_states[strat]["config"].get("description")
    entry_signal = strat_states[strat]["status"].get("entry_signal")

    set_command = {}

    # check for new max profit
    cur_max_profit = strat_states[strat]["status"].get("max_profit_this_entry", -100000)
    max_profit_this_entry = max(profit_pct, cur_max_profit)
    if max_profit_this_entry > cur_max_profit:
        set_command[f"{strat}.status.max_profit_this_entry"] = max_profit_this_entry

    # check for new max drawdown
    cur_max_drawdown = strat_states[strat]["status"].get("max_drawdown_this_entry", 0)
    max_drawdown_this_entry = min(profit_pct, cur_max_drawdown)
    if max_drawdown_this_entry < cur_max_drawdown:
        set_command[f"{strat}.status.max_drawdown_this_entry"] = max_drawdown_this_entry

    if not h.is_trade_closed(_trade_status=_trade_status, logger=logger):
        # save listed profit for comparison to profit on close later
        set_command[f"{strat}.status.most_recent_profit"] = profit_pct
        if set_command:
            coll.update_one({"_id": user}, {"$set": set_command}, upsert=True)
            # print(f"{description} set most recent profit to {profit}")

    if not h.is_trade_closed(_trade_status=_trade_status, logger=logger):
        # logger.debug(f"{description} detected that trade {trade_id} is not closed, doing profit update and returning")
        # update the user
        entry_time = strat_states[strat]["status"].get("entry_time")
        units = int(float(_trade_status["position"]["units"]["value"]))
        print(
            f"{description} {entry_signal} {direction} profit: {profit_pct}/{tp}% (ROE {round(profit_pct*leverage, 2)}/{round(tp*leverage, 2)}%) on {units} units, "
            f"max {max_profit_this_entry}% (ROE {round(max_profit_this_entry*leverage, 2)}%), dd "
            f"{max_drawdown_this_entry}/{last_sl_set}% (ROE {round(max_drawdown_this_entry * leverage, 2)}/{round(last_sl_set*leverage)}%). "
            f"Entry {entry_time}. Full trade status: {_trade_status}"
        )
        return

    # trade is closed!
    print(f"{description} Detected a closed trade, full status: {_trade_status}")
    # calculate profit on total assets, considering DCA

    state = strat_states[strat]
    current_units = float(_trade_status["position"]["units"]["value"])
    expected_cumulative_units = state["config"]["expected_cumulative_units"]
    asset_allocation = state["config"]["units"][tf_idx] / 100
    share_of_assets_committed = current_units / expected_cumulative_units[-1] * asset_allocation
    print(
        f"{description} share of assets committed was {share_of_assets_committed}, calculated from current_units "
        f"{current_units}, max units {expected_cumulative_units[-1]} and asset allocation {asset_allocation}")
    profit_on_assets = roe * share_of_assets_committed
    print(f"{description} adjusted profit on assets is {profit_on_assets}, calculated from roe {roe}")
    new_paper_assets = int(paper_assets * (1 + profit_on_assets / 100))
    print(
        f"{description} roe was {roe}, updating paper assets from {paper_assets} to {new_paper_assets}"
    )
    most_recent_profit = strat_states[strat]["status"].get("most_recent_profit", 0)
    print(
        f"{description} got most recent profit {most_recent_profit} from strat status. Final trade profit was {profit_pct}"
    )
    close_dump = profit_pct - most_recent_profit
    print(f"{description} close dump (slippage + fees) is {round(close_dump, 2)}%")
    # add to profits record and history

    drawdowns = strat_states[strat]["status"].get("drawdowns", [])
    drawdowns.append(max_drawdown_this_entry)
    median_drawdown = round(median(drawdowns), 2)
    drawdown_std_dev = round(std(drawdowns), 2)

    full_profit_history = strat_states[strat]["status"].get("full_profit_history", {})
    entry_time = h.get_readable_time(t=_trade_status["data"]["created_at"])
    exit_time = h.get_readable_time(t=_trade_status["data"]["closed_at"])
    new_history_entry = {
        "direction": direction,
        "profit": profit_pct,
        "roe": roe,
        "max_drawdown": max_drawdown_this_entry,
        "assets": new_paper_assets,
        "exit_time": exit_time,
        "close_dump": close_dump,
        "trade_id": trade_id,
        "entry_signal": entry_signal
    }
    full_profit_history[entry_time] = new_history_entry
    print(f"{description} added entry to full profit history: {new_history_entry}")

    # update performance
    asset_ratio_to_original = new_paper_assets / 10000
    config_change_time = strat_states[strat]["status"]["config_change_time"]
    days = h.get_days_elapsed(start=config_change_time, end=exit_time)
    apy = h.get_apy(asset_ratio=asset_ratio_to_original, days=days)
    coll.update_one(
        {"_id": user},
        {
            "$set": {
                f"{strat}.status.paper_assets": new_paper_assets,
                f"{strat}.status.profit_logged": True,
                f"{strat}.status.full_profit_history": full_profit_history,
                f"{strat}.status.drawdowns": drawdowns,
                f"{strat}.status.drawdown_std_dev": drawdown_std_dev,
                f"{strat}.status.median_drawdown": median_drawdown,
                f"{strat}.status.trade_id": None,
                f"{strat}.status.apy": apy
            }
        },
        upsert=True,
    )
    print(
        f"{description} {direction} {trade_id} **CLOSED**  Profit: {profit_pct}% ({round(profit_pct * leverage, 2)}% ROE), "
        f"paper assets are now ${new_paper_assets:,}"
    )
