from alphabot.config import USER_ATTR, STARTING_PAPER
import alphabot.helpers as h


def report(logger):
    coll = h.get_mongo_coll()

    print("** REPORT **")
    output = []
    for user in USER_ATTR:
        for strat in USER_ATTR[user]["strats"]:
            state = coll.find_one({"_id": user}).get(strat, {})
            status = state.get("status")
            if not status:
                # strat doesn't have a status yet, let's add it
                coll.update_one(
                    {"_id": user}, {"$set": {f"{strat}.status": {}}}, upsert=True
                )
                # re-pull
                state = coll.find_one({"_id": user}).get(strat)
            status = state.get("status")
            config = state.get("config", {})
            assets = status.get("paper_assets", 0)
            full_profit_history = status.get("full_profit_history", {})
            leverage = config.get("leverage", 1)
            description = config.get("description")

            # calculate APY
            current_time = h.get_readable_time()
            assets_earned = assets - STARTING_PAPER
            config_change_time = status.get("config_change_time")
            days = h.get_days_elapsed(start=config_change_time, end=current_time)
            apy = h.get_apy(assets_earned=assets_earned, days=days)

            entry = {
                "assets": assets,
                "designation": f"{description}. Leverage: {leverage}. Trades: {len(full_profit_history)}",
                "config_change_time": str(config_change_time),
                "apy": apy
            }
            output.append(entry)
    sorted_entries = sorted(output, key=lambda k: k["assets"])
    for entry in sorted_entries:
        assets_no = entry["assets"]
        assets_str = f"${assets_no:,} since {entry['config_change_time']}, {entry['apy']}% APY."
        print(f"Report: {assets_str} {entry['designation']}")

    print("** REPORT COMPLETE **")

    return "report ack"
