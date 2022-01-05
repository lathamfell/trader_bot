from alphabot.config import USER_ATTR, STARTING_PAPER
import alphabot.helpers as h
from alphabot.py3cw.request import Py3CW
import alphabot.trading as trading


def report(logger):
    coll = h.get_mongo_coll()

    print("** REPORT **")
    output = []
    for user in USER_ATTR:
        api_key = USER_ATTR[user]["c3_api_key"]
        secret = USER_ATTR[user]["c3_secret"]
        py3c = Py3CW(key=api_key, secret=secret)
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

            # START APR calculations
            trade_id = status.get("trade_id")
            _trade_status = trading.trade_status(
                py3c=py3c, trade_id=trade_id, description=description, logger=logger
            )

            profit, roe = h.get_profit_and_roe(_trade_status=_trade_status)
            paper_assets = status.get("paper_assets", STARTING_PAPER)
            new_paper_assets = int(paper_assets * (1 + roe / 100))

            exit_time = h.get_readable_time()
            asset_ratio_to_original = new_paper_assets / 10000
            config_change_time = status.get("config_change_time")
            days = h.get_days_elapsed(start=config_change_time, end=exit_time)
            daily_profit_pct_avg = round((asset_ratio_to_original ** (1 / float(days)) - 1) * 100, 2)
            apr = int((((1 + daily_profit_pct_avg / 100) ** 365) - 1) * 100)
            # END APR calculations

            entry = {
                "assets": assets,
                "designation": f"{description}. Leverage: {leverage}. Trades: {len(full_profit_history)}",
                "config_change_time": str(config_change_time)
            }
            output.append(entry)
    sorted_entries = sorted(output, key=lambda k: k["assets"])
    for entry in sorted_entries:
        assets_no = entry["assets"]
        assets_str = f"${assets_no:,} since {entry['config_change_time']}"
        print(f"Report: {assets_str}: {entry['designation']}")

    print("** REPORT COMPLETE **")

    return "report ack"
