import pymongo
import datetime as dt


def handle_trend_indicator(_update, indicator, logger):
    # for example Hull and Heuristic
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
        tls=True,
        tlsAllowInvalidCertificates=True,
    )
    db = client.indicators_db
    coll = db.indicators_coll

    coin = _update["coin"]
    interval = _update["interval"]
    new_value = _update["value"]

    indicatorz = coll.find_one({"_id": "indicators"})
    if not indicatorz:
        # really starting from scratch
        cur_indicator = None
    else:
        cur_indicator = indicatorz.get(indicator)
    if not cur_indicator:
        # starting from scratch
        history = {}
        cur_value = None
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
        cur_value = indicatorz[indicator][coin][interval].get("value", {})

    # add to history
    now = dt.datetime.now().isoformat()[5:16].replace("T", " ")
    history[now] = new_value

    coll.update_one(
        {"_id": "indicators"},
        {
            "$set": {
                f"{indicator}.{coin}.{interval}.value": new_value,
                f"{indicator}.{coin}.{interval}.history": history,
            }
        },
        upsert=True,
    )
    if cur_value != new_value:
        logger.debug(f"Indicator {indicator} {coin} {interval} switched to {new_value}")
        pass
    else:
        # logger.debug(f"Indicator {indicator} {coin} {interval} is still {new_value}")
        pass
