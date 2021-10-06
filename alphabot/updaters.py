import alphabot.helpers as h
from alphabot.config import STARTING_PAPER, USER_ATTR


def config_update(request, logger):
    coll = h.get_mongo_coll()

    _update = request.json
    user = _update["user"]

    if _update.get("reset"):
        # this is just a reset update. Reset all paper profits and return
        for strat in USER_ATTR[user]["strats"]:
            if strat in _update.get("to_reset", []):
                set_command, reset_str = get_reset_set_command(strat=strat)
                coll.update_one({"_id": user}, {"$set": set_command}, upsert=True)
                print(f"Reset paper assets for {strat}")
        return "strats reset"

    strat = _update["strat"]
    # make sure the strat exists
    user_strats = USER_ATTR[user]["strats"].keys()
    if strat not in user_strats:
        print(
            f"Strat {strat} not in the AlphaBot internal config. Strats for user {user} are: {user_strats}"
        )
        raise Exception

    state = coll.find_one({"_id": user}).get(strat)
    if not state:
        h.set_up_default_strat_config(coll=coll, user=user, strat=strat)
        state = coll.find_one({"_id": user})[strat]
    current_config = state.get("config", {})
    print(f"current config is {current_config}")
    current_description = current_config.get("description")

    print(
        f"{current_description} received direct config update request: {h.in_order(_update)}"
    )
    new_config = _update["config"]

    reset_profits = False  # only reset profits if we change something related to TP/SL

    new_tp_pct = new_config.get("tp_pct")
    old_tp_pct = current_config.get("tp_pct")
    if new_tp_pct:
        new_tp_pct = float(new_tp_pct)
    if new_tp_pct != old_tp_pct:
        reset_profits = True
        print(f"Changing tp_pct from {old_tp_pct} to {new_tp_pct}")

    new_tp_pct_2 = new_config.get("tp_pct_2")
    old_tp_pct_2 = current_config.get("tp_pct_2")
    if new_tp_pct_2:
        new_tp_pct_2 = float(new_tp_pct_2)
    if new_tp_pct_2 != old_tp_pct_2:
        reset_profits = True
        print(f"Changing tp_pct_2 from {old_tp_pct_2} to {new_tp_pct_2}")

    new_sl_pct = new_config.get("sl_pct")
    old_sl_pct = current_config.get("sl_pct")
    if new_sl_pct:
        new_sl_pct = float(new_sl_pct)
    if new_sl_pct != old_sl_pct:
        reset_profits = True
        print(f"Changing sl_pct from {old_sl_pct} to {new_sl_pct}")

    new_sl_trail = h.screen_for_str_bools(new_config.get("sl_trail"))
    old_sl_trail = current_config.get("sl_trail")
    if new_sl_trail != old_sl_trail:
        reset_profits = True
        print(f"Changing sl_trail from {old_sl_trail} to {new_sl_trail}")

    new_reset_sl = h.screen_for_str_bools(new_config.get("reset_sl"))
    old_reset_sl = current_config.get("reset_sl")
    if new_reset_sl != old_reset_sl:
        reset_profits = True
        print(f"Changing reset_sl from {old_reset_sl} to {new_reset_sl}")

    new_sl_reset_points = new_config.get("sl_reset_points")
    old_sl_reset_points = current_config.get("sl_reset_points")
    if new_sl_reset_points:
        for sl_reset_point in new_sl_reset_points:
            sl_reset_point[0] = float(sl_reset_point[0])
            sl_reset_point[1] = float(sl_reset_point[1])
    if new_sl_reset_points != old_sl_reset_points:
        reset_profits = True
        print(
            f"Changing sl_reset_points from {old_sl_reset_points} to {new_sl_reset_points}"
        )

    new_leverage = new_config.get("leverage")
    old_leverage = current_config.get("leverage")
    if new_leverage:
        new_leverage = int(new_leverage)
    if new_leverage != old_leverage:
        reset_profits = True
        print(f"Changing leverage from {old_leverage} to {new_leverage}")

    new_loss_limit_fraction = new_config.get("loss_limit_fraction")
    old_loss_limit_fraction = current_config.get("loss_limit_fraction")
    if new_loss_limit_fraction:
        new_loss_limit_fraction = float(new_loss_limit_fraction)
    if new_loss_limit_fraction != old_loss_limit_fraction:
        reset_profits = True
        print(f"Changing loss_limit_fraction from {old_loss_limit_fraction} to {new_loss_limit_fraction}")

    new_pct_of_starting_assets = new_config.get("pct_of_starting_assets")
    old_pct_of_starting_assets = current_config.get("pct_of_starting_assets")
    if new_pct_of_starting_assets:
        new_pct_of_starting_assets = int(new_pct_of_starting_assets)
    if new_pct_of_starting_assets != old_pct_of_starting_assets:
        print(f"Changing pct_of_starting_assets from {old_pct_of_starting_assets} to {new_pct_of_starting_assets}")

    new_units = new_config.get("units")
    old_units = current_config.get("units")
    if new_units:
        new_units = int(new_units)
    if new_units != old_units:
        print(f"Changing units from {old_units} to {new_units}")

    new_description = new_config.get("description", "")
    full_new_description = f"{user} {strat} <{new_description}>"
    if full_new_description != current_description:
        print(f"Changing description from {current_description} to {new_description}")

    # check to make sure tp_pct_2 and units are aligned
    if new_tp_pct_2 is not None and new_units < 2:
        print(
            f"Config update failed, need more than one unit in trade if using multiple TP points"
        )
        raise Exception

    if reset_profits:
        set_command, reset_str = get_reset_set_command(strat=strat)
    else:
        set_command = {}
        reset_str = ""
        print(
            f"Not resetting paper assets because no config changes were made to TP, SL, leverage or loss limiter."
        )

    if new_tp_pct or new_tp_pct == 0:
        set_command[f"{strat}.config.tp_pct"] = new_tp_pct
    if new_tp_pct_2 or new_tp_pct_2 == 0 or new_tp_pct_2 is None:
        set_command[f"{strat}.config.tp_pct_2"] = new_tp_pct_2
    if new_sl_pct or new_sl_pct == 0:
        set_command[f"{strat}.config.sl_pct"] = new_sl_pct
    if (new_sl_trail is True) or (new_sl_trail is False):
        set_command[f"{strat}.config.sl_trail"] = new_sl_trail
    if new_leverage:
        set_command[f"{strat}.config.leverage"] = new_leverage
    if new_loss_limit_fraction:
        set_command[f"{strat}.config.loss_limit_fraction"] = new_loss_limit_fraction
    if new_pct_of_starting_assets:
        set_command[f"{strat}.config.pct_of_starting_assets"] = new_pct_of_starting_assets
    if new_units:
        set_command[f"{strat}.config.units"] = new_units
    if (new_reset_sl is True) or (new_reset_sl is False):
        set_command[f"{strat}.config.reset_sl"] = new_reset_sl
    if new_sl_reset_points:
        set_command[f"{strat}.config.sl_reset_points"] = new_sl_reset_points
    if full_new_description:
        set_command[f"{strat}.config.description"] = full_new_description

    coll.update_one({"_id": user}, {"$set": set_command}, upsert=True)

    print(f"{full_new_description} completed direct config update request.{reset_str}")
    return "config updated"


def get_reset_set_command(strat):
    now = h.get_readable_time()
    set_command = {
        f"{strat}.status.paper_assets": STARTING_PAPER,
        f"{strat}.status.potential_paper_assets": STARTING_PAPER,
        f"{strat}.status.full_profit_history": {},
        f"{strat}.status.potential_profits": [],
        f"{strat}.status.drawdowns": [],
        f"{strat}.status.median_potential_profit": 0,
        f"{strat}.status.mean_potential_profit": 0,
        f"{strat}.status.median_drawdown": 0,
        f"{strat}.status.config_change_time": now,
        f"{strat}.status.profit_std_dev": 0,
        f"{strat}.status.drawdown_std_dev": 0,
    }
    reset_str = f" Reset paper assets to ${STARTING_PAPER:,} because a change was made to TP, SL or leverage"

    return set_command, reset_str
