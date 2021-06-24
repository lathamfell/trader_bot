import pymongo

from alphabot.helpers import in_order, screen_for_str_bools, set_up_default_strat_config
from alphabot.config import STARTING_PAPER


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
    strat = _update["strat"]

    state = coll.find_one({"_id": user}).get(strat)
    if not state:
        set_up_default_strat_config(coll=coll, user=user, strat=strat)
        current_config = coll.find_one({"_id": user})[strat]["config"]
    current_config = state["config"]
    logger.debug(f"current config is {current_config}")

    logger.info(
        f"{user} {strat} Received direct config update request: {in_order(_update)}"
    )
    new_config = _update["config"]

    reset_profits = False  # only reset profits if we change something related to TP/SL

    new_tp_pct = new_config.get("tp_pct")
    old_tp_pct = current_config.get("tp_pct")
    if new_tp_pct:
        new_tp_pct = float(new_tp_pct)
    if new_tp_pct != old_tp_pct:
        reset_profits = True
        logger.debug(
            f"setting reset_profits True because new_tp_pct {new_tp_pct} != {old_tp_pct}"
        )

    new_tp_trail = new_config.get("tp_trail")
    old_tp_trail = current_config.get("tp_trail")
    if new_tp_trail:
        new_tp_trail = float(new_tp_trail)
    if new_tp_trail != old_tp_trail:
        reset_profits = True
        logger.debug(
            f"setting reset profits True because new_tp_trail {new_tp_trail} != {old_tp_trail}"
        )

    new_sl_pct = new_config.get("sl_pct")
    old_sl_pct = current_config.get("sl_pct")
    if new_sl_pct:
        new_sl_pct = float(new_sl_pct)
    if new_sl_pct != old_sl_pct:
        reset_profits = True
        logger.debug(
            f"setting reset profits True because new_sl_pct {new_sl_pct} != {old_sl_pct}"
        )

    new_reset_tsl = screen_for_str_bools(new_config.get("reset_tsl"))
    old_reset_tsl = current_config.get("reset_tsl")
    if new_reset_tsl != old_reset_tsl:
        reset_profits = True
        logger.debug(
            f"setting reset profits True because new_reset_tsl {new_reset_tsl} != {old_reset_tsl}"
        )

    new_tsl_reset_points = new_config.get("tsl_reset_points")
    old_tsl_reset_points = current_config.get("tsl_reset_points")
    if new_tsl_reset_points:
        for tsl_reset_point in new_tsl_reset_points:
            tsl_reset_point[0] = float(tsl_reset_point[0])
            tsl_reset_point[1] = float(tsl_reset_point[1])
    if new_tsl_reset_points != old_tsl_reset_points:
        reset_profits = True
        logger.debug(
            f"setting reset profits True because new_tsl_reset_points {new_tsl_reset_points} != {old_tsl_reset_points}"
        )

    leverage = new_config.get("leverage")
    if leverage:
        leverage = int(leverage)

    units = new_config.get("units")
    if units:
        units = int(units)

    if reset_profits:
        set_command = {
            f"{strat}.status.paper_assets": STARTING_PAPER,
            f"{strat}.status.potential_paper_assets": STARTING_PAPER,
            f"{strat}.status.profit_history": {},
        }
        reset_str = f" Reset paper assets to ${STARTING_PAPER:,}"
        logger.debug(
            f"because reset profits is {reset_profits}, set_command is now {set_command} and reset-str is {reset_str}"
        )
    else:
        set_command = {}
        reset_str = ""
        logger.debug(
            f"because reset profits is {reset_profits}, set_command is now {set_command} and reset_str is {reset_str}"
        )

    if new_tp_pct or new_tp_pct == 0:
        set_command[f"{strat}.config.tp_pct"] = new_tp_pct
    if new_tp_trail or (
        not new_tp_trail and "tp_trail" in new_config
    ):  # cover tp_trail = null scenario
        set_command[f"{strat}.config.tp_trail"] = new_tp_trail
    if new_sl_pct or new_sl_pct == 0:
        set_command[f"{strat}.config.sl_pct"] = new_sl_pct
    if leverage:
        set_command[f"{strat}.config.leverage"] = leverage
    if units:
        set_command[f"{strat}.config.units"] = units
    if (new_reset_tsl is True) or (new_reset_tsl is False):
        set_command[f"{strat}.config.reset_tsl"] = new_reset_tsl
    if new_tsl_reset_points:
        set_command[f"{strat}.config.tsl_reset_points"] = new_tsl_reset_points

    logger.debug(f"loaded up set command: {set_command}")

    coll.update_one({"_id": user}, {"$set": set_command}, upsert=True)

    logger.info(f"{user} {strat} Completed direct config update request.{reset_str}")
    return "config updated"
