import pymongo
from alphabot.config import USER_ATTR
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
            potential_assets = status.get("potential_paper_assets", 0)
            leverage = config.get("leverage", 1)
            median_potential_profit = status.get("median_potential_profit", 0)
            mean_potential_profit = status.get("mean_potential_profit", 0)
            profit_std_dev = status.get("profit_std_dev", 0)
            median_drawdown = status.get("median_drawdown", 0)
            drawdown_std_dev = status.get("drawdown_std_dev", 0)
            description = config.get("description")
            config_change_time = str(status.get("config_change_time"))
            entry = {
                "assets": assets,
                "potential_assets": potential_assets,
                "designation": f"{description}. Median potential profit: {median_potential_profit}%, "
                               f"mean potential profit: {mean_potential_profit}%, std dev "
                               f"{profit_std_dev}. Median drawdown: {median_drawdown}%, std dev: {drawdown_std_dev}. "
                               f"Leverage: {leverage}. Trades: {len(full_profit_history)} since {config_change_time}",
            }
            output.append(entry)
    sorted_entries = sorted(output, key=lambda k: k["assets"])
    for entry in sorted_entries:
        assets_no = entry["assets"]
        assets_po = entry["potential_assets"]
        assets_str = f"${assets_no:,} out of potential ${assets_po:,}"
        print(f"Report: {assets_str}: {entry['designation']}")

    print("** REPORT COMPLETE **")

    return "report ack"
