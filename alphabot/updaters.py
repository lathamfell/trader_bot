import alphabot.helpers as h
from alphabot.config import STARTING_PAPER, USER_ATTR


def config_update(request, logger):
    coll = h.get_mongo_coll()

    _update = request.json
    user = _update["user"]

    if _update.get("reset"):
        # this is just a reset update. Reset all paper profits and return
        for strat in _update.get("to_reset", []):
            if strat in USER_ATTR[user]["strats"]:
                set_command, reset_str = get_reset_set_command(strat=strat)
                coll.update_one({"_id": user}, {"$set": set_command}, upsert=True)
                print(f"Reset paper assets for {strat}")
            else:
                print(f"Did not find strat {strat} for user {user}")
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

    new_tp_pct = normalized(new_config.get("tp_pct"))
    old_tp_pct = current_config.get("tp_pct")
    if new_tp_pct != old_tp_pct:
        print(f"Changing tp_pct from {old_tp_pct} to {new_tp_pct}")

    new_tp_pct_after_dca = normalized(new_config.get("tp_pct_after_dca"))
    old_tp_pct_after_dca = current_config.get("tp_pct_after_dca")
    if new_tp_pct_after_dca != old_tp_pct_after_dca:
        print(f"Changing tp_pct_after_dca from {old_tp_pct_after_dca} to {new_tp_pct_after_dca}")

    new_tp_pct_2 = normalized(new_config.get("tp_pct_2"))
    old_tp_pct_2 = current_config.get("tp_pct_2")
    if new_tp_pct_2 != old_tp_pct_2:
        print(f"Changing tp_pct_2 from {old_tp_pct_2} to {new_tp_pct_2}")

    new_sl_pct = normalized(new_config.get("sl_pct"))
    old_sl_pct = current_config.get("sl_pct")
    if new_sl_pct != old_sl_pct:
        print(f"Changing sl_pct from {old_sl_pct} to {new_sl_pct}")

    new_dca_pct = normalized(new_config.get("dca_pct"))
    old_dca_pct = current_config.get("dca_pct")
    if new_dca_pct != old_dca_pct:
        screen_dca_pct(new_dca_pct)
        print(f"Changing dca_pct from {old_dca_pct} to {new_dca_pct}")

    new_dca_weights = normalized(new_config.get("dca_weights"))
    old_dca_weights = current_config.get("dca_weights")
    if new_dca_weights != old_dca_weights:
        screen_dca_weights(
            dca_weights=new_dca_weights,
            dca_pct=new_dca_pct if new_dca_pct else old_dca_pct
        )
        print(f"Changing dca_weights from {old_dca_weights} to {new_dca_weights}")

    new_sl_trail = normalized(new_config.get("sl_trail"))
    old_sl_trail = current_config.get("sl_trail")
    if new_sl_trail != old_sl_trail:
        print(f"Changing sl_trail from {old_sl_trail} to {new_sl_trail}")

    new_trail_delay = normalized(new_config.get("trail_delay"))
    old_trail_delay = current_config.get("trail_delay")
    if new_trail_delay != old_trail_delay:
        print(f"Changing trail_delay from {old_trail_delay} to {new_trail_delay}")

    new_reset_sl = normalized(new_config.get("reset_sl"))
    old_reset_sl = current_config.get("reset_sl")
    if new_reset_sl != old_reset_sl:
        print(f"Changing reset_sl from {old_reset_sl} to {new_reset_sl}")

    new_sl_reset_points = normalized(new_config.get("sl_reset_points"))
    old_sl_reset_points = current_config.get("sl_reset_points")
    if new_sl_reset_points != old_sl_reset_points:
        print(
            f"Changing sl_reset_points from {old_sl_reset_points} to {new_sl_reset_points}"
        )

    new_leverage = normalized(new_config.get("leverage"))
    old_leverage = current_config.get("leverage")
    if new_leverage != old_leverage:
        print(f"Changing leverage from {old_leverage} to {new_leverage}")

    new_units = normalized(new_config.get("units"))
    old_units = current_config.get("units")
    if new_units != old_units:
        screen_units(new_units)
        print(f"Changing units from {old_units} to {new_units}")

    new_description = new_config.get("description", "")
    full_new_description = f"{user} {strat} {new_description}"
    if full_new_description != current_description:
        print(f"Changing description from {current_description} to {new_description}")

    # check to make sure tp_pct_2 and units are aligned
    if new_tp_pct_2:
        for i in range(len(new_tp_pct_2)):
            if new_tp_pct_2[i] is not None and new_units[i] < 2:
                print(
                    f"Config update failed, need more than one unit in trade if using multiple TP points"
                )
                raise Exception

    set_command = {}

    if new_tp_pct:
        set_command[f"{strat}.config.tp_pct"] = new_tp_pct
    if new_tp_pct_after_dca:
        set_command[f"{strat}.config.tp_pct_after_dca"] = new_tp_pct_after_dca
    if new_tp_pct_2:
        set_command[f"{strat}.config.tp_pct_2"] = new_tp_pct_2
    if new_sl_pct:
        set_command[f"{strat}.config.sl_pct"] = new_sl_pct
    if new_dca_pct:
        set_command[f"{strat}.config.dca_pct"] = new_dca_pct
    if new_dca_weights:
        set_command[f"{strat}.config.dca_weights"] = new_dca_weights
    if new_sl_trail:
        set_command[f"{strat}.config.sl_trail"] = new_sl_trail
    if new_trail_delay:
        set_command[f"{strat}.config.trail_delay"] = new_trail_delay
    if new_leverage:
        set_command[f"{strat}.config.leverage"] = new_leverage
    if new_units:
        set_command[f"{strat}.config.units"] = new_units
    if new_reset_sl:
        set_command[f"{strat}.config.reset_sl"] = new_reset_sl
    if new_sl_reset_points:
        set_command[f"{strat}.config.sl_reset_points"] = new_sl_reset_points
    if full_new_description:
        set_command[f"{strat}.config.description"] = full_new_description

    coll.update_one({"_id": user}, {"$set": set_command}, upsert=True)

    print(f"{full_new_description} completed direct config update request.")
    return "config updated"


def get_reset_set_command(strat):
    now = h.get_readable_time()
    set_command = {
        f"{strat}.status.paper_assets": STARTING_PAPER,
        f"{strat}.status.full_profit_history": {},
        f"{strat}.status.drawdowns": [],
        f"{strat}.status.median_drawdown": 0,
        f"{strat}.status.config_change_time": now,
        f"{strat}.status.profit_std_dev": 0,
        f"{strat}.status.drawdown_std_dev": 0,
    }
    reset_str = f" Reset paper assets to ${STARTING_PAPER:,} because a change was made to TP, SL, DCA or leverage"

    return set_command, reset_str


def normalized(config_list):
    # edit list in place
    if not config_list:
        return config_list
    for i, element in enumerate(config_list):
        if isinstance(element, list):  # must be sl reset points or dca
            normalize_list_of_lists(config_list)
            return config_list
        elif isinstance(element, str):  # must be str
            try:
                config_list[i] = float(element)
            except ValueError:
                config_list[i] = h.screen_for_str_bools(element)
    return config_list


def normalize_list_of_lists(ll):
    for i, element in enumerate(ll):
        if isinstance(element, list):
            for j, sub_element in enumerate(element):
                if isinstance(sub_element, list):
                    for k, sub_sub_element in enumerate(sub_element):
                        sub_element[k] = float(sub_element[k])
                else:
                    element[j] = float(element[j])
        else:
            ll[i] = float(ll[i])


def screen_dca_pct(dca_pct):
    for tf in dca_pct:
        for i in range(1, len(tf)):
            assert tf[i] >= tf[i - 1], f"tf {tf} in dca_pct {dca_pct} has pcts in wrong order"


def screen_dca_weights(dca_weights, dca_pct):
    for i, tf in enumerate(dca_weights):
        # make sure they add up to 100
        total_weight = 0
        for weight in tf:
            total_weight += weight
        assert total_weight == 100, f"DCA weights {tf} do not add up to 100"
        # make sure there is more one weight than pct for each timeframe
        assert len(tf) == len(dca_pct[i]) + 1, f"DCA pct {dca_pct[i]} does not match DCA weight {tf}"


def screen_units(units):
    for tf_units_pct in units:
        if tf_units_pct < 0 or tf_units_pct > 100:
            raise Exception(f"Invalid units % setting: {tf_units_pct} in {units}")
