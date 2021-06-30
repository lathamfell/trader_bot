import pymongo
import datetime as dt

from alphabot.helpers import in_order, screen_for_str_bools, set_up_default_strat_config
from alphabot.config import STARTING_PAPER, USER_ATTR


def config_update(request, logger):
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
        tls=True,
        tlsAllowInvalidCertificates=True,
    )
    db = client.indicators_db
    coll = db.indicators_coll

    _update = request.json
    user = _update["user"]

    if _update.get("reset"):
        # this is just a reset update. Reset all paper profits and return
        for strat in USER_ATTR[user]["strats"]:
            if strat in _update.get("to_reset", []):
                set_command, reset_str = get_reset_set_command(strat=strat)
                coll.update_one({"_id": user}, {"$set": set_command}, upsert=True)
                logger.info(f"Reset paper assets for {strat}")
        return "strats reset"

    strat = _update["strat"]
    # make sure the strat exists
    user_strats = []
    for user_strat in USER_ATTR[user]["strats"]:
        user_strats.append(user_strat)
    if strat not in user_strats:
        logger.error(f"Strat {strat} not in the AlphaBot internal config. Strats for user {user} are: {user_strats}")
        raise Exception

    state = coll.find_one({"_id": user}).get(strat)
    if not state:
        set_up_default_strat_config(coll=coll, user=user, strat=strat)
        state = coll.find_one({"_id": user})[strat]
    current_config = state.get("config", {})
    logger.debug(f"current config is {current_config}")
    current_description = current_config.get("description")

    logger.info(
        f"{current_description} received direct config update request: {in_order(_update)}"
    )
    new_config = _update["config"]

    reset_profits = False  # only reset profits if we change something related to TP/SL

    new_tp_pct = new_config.get("tp_pct")
    old_tp_pct = current_config.get("tp_pct")
    if new_tp_pct:
        new_tp_pct = float(new_tp_pct)
    if new_tp_pct != old_tp_pct:
        reset_profits = True
        logger.info(f"Changing tp_pct from {old_tp_pct} to {new_tp_pct}")

    new_tp_pct_2 = new_config.get("tp_pct_2")
    old_tp_pct_2 = current_config.get("tp_pct_2")
    if new_tp_pct_2:
        new_tp_pct_2 = float(new_tp_pct_2)
    if new_tp_pct_2 != old_tp_pct_2:
        reset_profits = True
        logger.info(f"Changing tp_pct_2 from {old_tp_pct_2} to {new_tp_pct_2}")

    new_tp_trail = new_config.get("tp_trail")
    old_tp_trail = current_config.get("tp_trail")
    if new_tp_trail:
        new_tp_trail = float(new_tp_trail)
    if new_tp_trail != old_tp_trail:
        reset_profits = True
        logger.info(f"Changing tp_trail from {old_tp_trail} to {new_tp_trail}")

    new_sl_pct = new_config.get("sl_pct")
    old_sl_pct = current_config.get("sl_pct")
    if new_sl_pct:
        new_sl_pct = float(new_sl_pct)
    if new_sl_pct != old_sl_pct:
        reset_profits = True
        logger.info(f"Changing sl_pct from {old_sl_pct} to {new_sl_pct}")

    new_reset_tsl = screen_for_str_bools(new_config.get("reset_tsl"))
    old_reset_tsl = current_config.get("reset_tsl")
    if new_reset_tsl != old_reset_tsl:
        reset_profits = True
        logger.info(f"Changing reset_tsl from {old_reset_tsl} to {new_reset_tsl}")

    new_tsl_reset_points = new_config.get("tsl_reset_points")
    old_tsl_reset_points = current_config.get("tsl_reset_points")
    if new_tsl_reset_points:
        for tsl_reset_point in new_tsl_reset_points:
            tsl_reset_point[0] = float(tsl_reset_point[0])
            tsl_reset_point[1] = float(tsl_reset_point[1])
    if new_tsl_reset_points != old_tsl_reset_points:
        reset_profits = True
        logger.info(f"Changing tsl_reset_points from {old_tsl_reset_points} to {new_tsl_reset_points}")

    new_leverage = new_config.get("leverage")
    old_leverage = current_config.get("leverage")
    if new_leverage:
        new_leverage = int(new_leverage)
    if new_leverage != old_leverage:
        reset_profits = True
        logger.info(f"Changing leverage from {old_leverage} to {new_leverage}")

    new_units = new_config.get("units")
    old_units = current_config.get("units")
    if new_units:
        new_units = int(new_units)
    if new_units != old_units:
        logger.info(f"Changing units from {old_units} to {new_units}")

    new_description = new_config.get('description', '')
    full_new_description = f"{user} {strat} <{new_description}>"
    if full_new_description != current_description:
        logger.info(f"Changing description from {current_description} to {new_description}")

    # check to make sure tp_pct_2 and units are aligned
    if new_tp_pct_2 is not None and new_units < 2:
        logger.error(f"Config update failed, need more than one unit in trade if using multiple TP points")
        raise Exception

    if reset_profits:
        set_command, reset_str = get_reset_set_command(strat=strat)
    else:
        set_command = {}
        reset_str = ""
        logger.info(
            f"Not resetting paper assets because no config changes were made to TP, SL or leverage."
        )

    if new_tp_pct or new_tp_pct == 0:
        set_command[f"{strat}.config.tp_pct"] = new_tp_pct
    if new_tp_pct_2 or new_tp_pct_2 == 0:
        set_command[f"{strat}.config.tp_pct_2"] = new_tp_pct_2
    if new_tp_trail or (
        not new_tp_trail and "tp_trail" in new_config
    ):  # cover tp_trail = null scenario
        set_command[f"{strat}.config.tp_trail"] = new_tp_trail
    if new_sl_pct or new_sl_pct == 0:
        set_command[f"{strat}.config.sl_pct"] = new_sl_pct
    if new_leverage:
        set_command[f"{strat}.config.leverage"] = new_leverage
    if new_units:
        set_command[f"{strat}.config.units"] = new_units
    if (new_reset_tsl is True) or (new_reset_tsl is False):
        set_command[f"{strat}.config.reset_tsl"] = new_reset_tsl
    if new_tsl_reset_points:
        set_command[f"{strat}.config.tsl_reset_points"] = new_tsl_reset_points
    if full_new_description:
        set_command[f"{strat}.config.description"] = full_new_description

    coll.update_one({"_id": user}, {"$set": set_command}, upsert=True)

    logger.info(f"{full_new_description} completed direct config update request.{reset_str}")
    return "config updated"


def get_reset_set_command(strat):
    now = dt.datetime.now().isoformat()[5:16].replace("T", " ")
    set_command = {
        f"{strat}.status.paper_assets": STARTING_PAPER,
        f"{strat}.status.potential_paper_assets": STARTING_PAPER,
        f"{strat}.status.full_profit_history": {},
        f"{strat}.status.potential_profits": [],
        f"{strat}.status.drawdowns": [],
        f"{strat}.status.median_potential_profit": 0,
        f"{strat}.status.median_drawdown": 0,
        f"{strat}.status.config_change_time": now,
        f"{strat}.status.profit_std_dev": 0,
        f"{strat}.status.drawdown_std_dev": 0,
    }
    reset_str = f" Reset paper assets to ${STARTING_PAPER:,} because a change was made to TP, SL or leverage"

    return set_command, reset_str
