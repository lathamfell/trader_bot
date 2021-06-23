import pymongo
import datetime as dt


def handle_hull_indicator(_update, indicator, logger):
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
        tls=True,
        tlsAllowInvalidCertificates=True,
    )
    db = client.indicators_db
    coll = db.indicators_coll

    coin = _update["coin"]
    interval = _update["interval"]
    mhull = round(_update["MHULL"], 2)
    shull = round(_update["SHULL"], 2)

    indicatorz = coll.find_one({"_id": "indicators"})
    if not indicatorz:
        # really starting from scratch
        cur_hull = None
    else:
        cur_hull = indicatorz.get(indicator)
    if not cur_hull:
        # starting from scratch
        history = {}
        cur_color = None
    else:
        # make sure we have coin and interval first
        try:
            indicatorz[indicator][coin]
        except KeyError:
            indicatorz[indicator][coin] = {}
        try:
            indicatorz[indicator][coin][interval]
        except KeyError:
            indicatorz[indicator][coin][interval] = {}

        history = indicatorz[indicator][coin][interval].get("history", {})
        cur_color = indicatorz[indicator][coin][interval].get("color", {})

    # calculate green vs red
    if mhull >= shull:
        new_color = "green"
    else:
        new_color = "red"
    # add to history
    now = dt.datetime.now().isoformat()[5:16].replace("T", " ")
    history[now] = new_color

    coll.update_one(
        {"_id": "indicators"},
        {
            "$set": {
                f"{indicator}.{coin}.{interval}.color": new_color,
                f"{indicator}.{coin}.{interval}.history": history,
            }
        },
        upsert=True,
    )
    if cur_color != new_color:
        #logger.debug(f"Indicator {indicator} {coin} {interval} switched to {new_color}")
        pass
    else:
        #logger.debug(f"Indicator {indicator} {coin} {interval} is still {new_color}")
        pass
