import pymongo

from alphabot.helpers import in_order, screen_for_str_bools
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
    strat = _update.get("strat")
    logger.info(
        f"{user} {strat} Received direct config update request: {in_order(_update)}"
    )
    config = _update["config"]

    tp_pct = config.get("tp_pct")
    if tp_pct:
        tp_pct = float(tp_pct)
    tp_trail = config.get("tp_trail")
    if tp_trail:
        tp_trail = float(tp_trail)
    sl_pct = config.get("sl_pct")
    if sl_pct:
        sl_pct = float(sl_pct)
    leverage = config.get("leverage")
    if leverage:
        leverage = int(leverage)
    units = config.get("units")
    if units:
        units = int(units)
    one_entry_per_trend = screen_for_str_bools(config.get("one_entry_per_trend"))
    cooldown = config.get("cooldown")
    if cooldown:
        cooldown = int(cooldown)
    reset_tsl = screen_for_str_bools(config.get("reset_tsl"))
    tsl_reset_points = config.get("tsl_reset_points")
    if tsl_reset_points:
        for tsl_reset_point in tsl_reset_points:
            tsl_reset_point[0] = float(tsl_reset_point[0])
            tsl_reset_point[1] = float(tsl_reset_point[1])
    reset_tp = screen_for_str_bools(config.get("reset_tp"))
    tp_reset_points = config.get("tp_reset_points")
    if tp_reset_points:
        for tp_reset_point in tp_reset_points:
            tp_reset_point[0] = float(tp_reset_point[0])
            tp_reset_point[1] = float(tp_reset_point[1])

    set_command = {
        f"{strat}.status.paper_assets": STARTING_PAPER,
        f"{strat}.status.profit_history": {}
    }

    if tp_pct or tp_pct == 0:
        set_command[f"{strat}.config.tp_pct"] = tp_pct
    if tp_trail or (
        not tp_trail and "tp_trail" in config
    ):  # cover tp_trail = null scenario
        set_command[f"{strat}.config.tp_trail"] = tp_trail
    if sl_pct or sl_pct == 0:
        set_command[f"{strat}.config.sl_pct"] = sl_pct
    if leverage:
        set_command[f"{strat}.config.leverage"] = leverage
    if units:
        set_command[f"{strat}.config.units"] = units
    if (one_entry_per_trend is True) or (one_entry_per_trend is False):
        set_command[f"{strat}.config.one_entry_per_trend"] = one_entry_per_trend
    if cooldown or cooldown == 0:
        set_command[f"{strat}.config.cooldown"] = cooldown
    if (reset_tsl is True) or (reset_tsl is False):
        set_command[f"{strat}.config.reset_tsl"] = reset_tsl
    if tsl_reset_points:
        set_command[f"{strat}.config.tsl_reset_points"] = tsl_reset_points
    if (reset_tp is True) or (reset_tp is False):
        set_command[f"{strat}.config.reset_tp"] = reset_tp
    if tp_reset_points:
        set_command[f"{strat}.config.tp_reset_points"] = tp_reset_points

    coll.update_one({"_id": user}, {"$set": set_command}, upsert=True)

    logger.info(
        f"{user} {strat} Completed direct config update request, and reset strat paper assets to ${STARTING_PAPER:,}"
    )
    return "config updated"
