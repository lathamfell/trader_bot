import json
import yagmail
import datetime as dt
import pymongo
from time import sleep

from config import DEBUG, DEBUG2


def trade_status(py3c, trade_id):
    error, data = py3c.request(
        entity="smart_trades_v2", action="get_by_id", action_id=str(trade_id)
    )
    if error.get("error"):
        print(
            f"\n!!!! ERROR !!!! Error getting trade info for trade {trade_id}, {error['msg']}\n"
        )
        raise Exception

    return data


def get_current_trade_direction(_trade_status):
    _open = (_trade_status["status"]["type"] == "waiting_targets")
    long = (_trade_status["position"]["type"] == "buy")
    if _open and long:
        return "long"
    elif _open and not long:
        return "short"
    else:
        return None


def is_trade_closed(_trade_status):
    try:
        _trade_status["data"]["closed_at"]
    except KeyError:
        return False
    return True


def current_trade_profit_pct(_trade_status):
    profit_pct = _trade_status["data"]["profit"]["percent"]
    return profit_pct


def in_order(_dict):
    return json.dumps(_dict, sort_keys=True)


def close_trade(py3c, trade_id):
    error, data = py3c.request(
        entity="smart_trades_v2", action="close_by_market", action_id=trade_id
    )
    if error.get("error"):
        print(
            f"\n!!!!  ERROR !!! Error closing trade {trade_id}, {error['msg']}\n"
        )
        raise Exception
    print(f"trade {trade_id} successfully closed, response: {data}")
    return data


def open_trade(
    py3c, account_id, pair, _type, leverage, units, tp_pct, tp_trail, sl_pct
):
    if DEBUG:
        print(
            f"DEBUG open_trade called with account_id {account_id}, pair {pair}, _type {_type}, leverage {leverage}, units {units}, tp_pct {tp_pct}, tp_trail {tp_trail}, sl_pct {sl_pct}"
        )
    base_trade = get_base_trade(
        account_id=account_id, pair=pair, _type=_type, leverage=leverage, units=units
    )
    if DEBUG:
        print(f"DEBUG Sending base trade: {base_trade}")
    base_trade_error, base_trade_data = py3c.request(
        entity="smart_trades_v2", action="new", payload=base_trade
    )
    if base_trade_error.get("error"):
        print(f"\n !!!! ERROR !!!! Error opening trade of type {_type} for account {account_id}, {base_trade_error['msg']}\n")
        raise Exception

    trade_id = str(base_trade_data["id"])
    trade_entry = round(float(base_trade_data["position"]["price"]["value"]), 2)
    if DEBUG:
        print(f"DEBUG Entered trade at {trade_entry}")
    if _type == 'buy':
        tp_price = round(trade_entry * (1 + tp_pct / 100))
        sl_price = round(trade_entry * (1 - sl_pct / 100))
    else:  # sell
        tp_price = round(trade_entry * (1 - tp_pct / 100))
        sl_price = round(trade_entry * (1 + sl_pct / 100))
    update_trade = get_update_trade(
        trade_id=trade_id,
        _type=_type,
        units=units,
        tp_price=tp_price,
        tp_trail=tp_trail,
        sl_price=sl_price,
        sl_pct=sl_pct,
    )
    if DEBUG:
        print(f"DEBUG Sending update trade while opening trade: {update_trade}")
    update_trade_error, update_trade_data = py3c.request(
        entity="smart_trades_v2", action="update", action_id=trade_id, payload=update_trade
    )
    if update_trade_error.get("error"):
        print(f"\n !!!! ERROR !!!! Error updating trade while opening, {update_trade_error['msg']}\n")
        print(f"Closing trade {trade_id} since we couldn't apply TP/SL")
        sleep(1)
        close_trade(py3c, trade_id)
        raise Exception
    if DEBUG:
        print(f"DEBUG trade {trade_id} successfully updated with TP/SL, response: {update_trade_data}")
    return trade_id


def get_base_trade(account_id, pair, _type, leverage, units):
    if DEBUG:
        print(f"DEBUG get_base_trade called with account_id {account_id}, pair {pair}, _type {_type}, leverage {leverage}, units {units}")
    return {
        "account_id": account_id,
        "pair": pair,
        "leverage": {"enabled": True, "type": "isolated", "value": leverage},
        "position": {
            "type": _type,  # 'buy' / 'sell'
            "units": {"value": units},
            "order_type": "market",
        },
        "take_profit": {"enabled": False},
        "stop_loss": {"enabled": False},
    }


def get_update_trade(trade_id, _type, units, tp_price, sl_price, sl_pct, tp_trail):
    if DEBUG:
        print(f"DEBUG get_update_trade called with trade_id {trade_id}, units {units}, tp_price {tp_price}, sl_price {sl_price}, sl_pct {sl_pct}, tp_trail {tp_trail}")
    update_trade = {
        "id": trade_id,
        "position": {"type": _type, "units": {"value": units}, "order_type": "market"},
        "take_profit": {
            "enabled": True,
            "steps": [
                {
                    "order_type": "market",
                    "price": {"value": tp_price, "type": "last"},
                    "volume": 100,
                }
            ],
        },
        "stop_loss": {
            "enabled": True,
            "order_type": "market",
            "conditional": {
                "price": {"value": sl_price, "type": "last"},
                "trailing": {"enabled": True, "percent": sl_pct},
            },
        },
    }
    if tp_trail:
        update_trade["take_profit"]["steps"][0]["trailing"] = {
            "enabled": True,
            "percent": tp_trail,
        }
    return update_trade


def screen_for_str_bools(value):
    if isinstance(value, str):
        if value == "true":
            return True
        if value == "false":
            return False
    return value


def send_email(to, subject, body=None):
    yagmail.SMTP("lathamfell@gmail.com", "lrhnapmiegubspht").send(to, subject, body)


def get_oldest_value(value_history):
    oldest_dt = get_oldest_dt(value_history)
    return value_history[oldest_dt]


def get_oldest_dt(value_history):
    oldest_dt = dt.datetime.now().isoformat()
    for historical_dt in value_history:
        if historical_dt < oldest_dt:
            oldest_dt = historical_dt
    return oldest_dt


def handle_kst_indicator(_update, indicator):
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
        tls=True,
        tlsAllowInvalidCertificates=True,
    )
    db = client.indicators_db
    coll = db.indicators_coll

    coin = _update["coin"]
    interval = _update["interval"]
    cur_value = round(_update["value"], 2)
    number_of_minutes_to_count_back = 16
    indicatorz = coll.find_one({"_id": "indicators"})
    cur_kst = indicatorz.get(indicator)
    if not cur_kst:
        # starting from scratch
        change_history = {}
        recent_value_history = {}
    else:
        change_history = cur_kst[coin][interval].get("change_history", {})
        recent_value_history = cur_kst[coin][interval].get("recent_value_history", {})
        # dump the oldest one if the recent history is full
        if len(recent_value_history) >= number_of_minutes_to_count_back:
            oldest_dt = get_oldest_dt(recent_value_history)
            del recent_value_history[oldest_dt]

    # add the new one
    now = dt.datetime.now().isoformat()[5:16].replace("T", " ")
    recent_value_history[now] = cur_value
    # calculate the pct change from oldest recent value to current value
    oldest_value = recent_value_history[get_oldest_dt(recent_value_history)]
    change = round(cur_value - oldest_value, 2)
    # add to change history
    change_history[now] = change

    coll.update_one(
        {"_id": "indicators"},
        {
            "$set": {
                f"{indicator}.{coin}.{interval}.change": change,
                f"{indicator}.{coin}.{interval}.change_history": change_history,
                f"{indicator}.{coin}.{interval}.recent_value_history": recent_value_history,
            }
        },
        upsert=True,
    )
    if DEBUG:
        print(
            f"DEBUG Indicator {indicator} change from {oldest_value} to {cur_value} over {number_of_minutes_to_count_back} minutes is {change}"
        )


def handle_ma_indicator(_update, indicator):
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
        tls=True,
        tlsAllowInvalidCertificates=True,
    )
    db = client.indicators_db
    coll = db.indicators_coll

    coin = _update["coin"]
    interval = _update["interval"]
    value = _update["value"]
    update_pct = _update["update_pct"]

    # pull current state of indicators
    cur = coll.find_one({"_id": "indicators"})

    if update_pct:
        # print an update for easy traceability of calculation in the logs
        MA_cur_to_print = "{:.2f}".format(cur[indicator][coin][interval]["current"])
        MA_1_bar_to_print = "{:.2f}".format(
            cur[indicator][coin][interval]["MA_1_bar_ago"]
        )
        MA_2_bars_to_print = "{:.2f}".format(
            cur[indicator][coin][interval]["MA_2_bars_ago"]
        )
        state_to_print = f"cur: {MA_cur_to_print}, 1 bar ago: {MA_1_bar_to_print}, 2 bars ago: {MA_2_bars_to_print}"

        MA_2_bars_ago = cur[indicator][coin][interval]["MA_2_bars_ago"]
        MA_pct_per_2_bars = ((value - MA_2_bars_ago) / MA_2_bars_ago) * 100
        coll.update_one(
            {"_id": "indicators"},
            {
                "$set": {
                    f"{indicator}.{coin}.{interval}.current": value,
                    f"{indicator}.{coin}.{interval}.MA_pct_per_2_bars": MA_pct_per_2_bars,
                }
            },
            upsert=True,
        )
        if DEBUG:
            print(
                f"Indicator {indicator} pct for {coin} {interval} updated to {'{:.2f}'.format(MA_pct_per_2_bars)}, based on {state_to_print}"
            )
    else:
        MA_3_bars_ago = cur[indicator][coin][interval]["MA_2_bars_ago"]
        MA_2_bars_ago = cur[indicator][coin][interval]["MA_1_bar_ago"]
        MA_1_bar_ago = value
        # update db
        coll.update_one(
            {"_id": "indicators"},
            {
                "$set": {
                    f"{indicator}.{coin}.{interval}.MA_3_bars_ago": MA_3_bars_ago,
                    f"{indicator}.{coin}.{interval}.MA_2_bars_ago": MA_2_bars_ago,
                    f"{indicator}.{coin}.{interval}.MA_1_bar_ago": MA_1_bar_ago,
                }
            },
        )
        if DEBUG:
            print(
                f"Indicator {indicator} for {coin} {interval} updated to {'{:.2f}'.format(MA_1_bar_ago)}"
            )


def handle_supertrend_indicator(_update, indicator):
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
        tls=True,
        tlsAllowInvalidCertificates=True,
    )
    db = client.indicators_db
    coll = db.indicators_coll
    coin = _update["coin"]
    interval = _update["interval"]
    value = _update["value"]
    coll.update_one(
        {"_id": "indicators"}, {"$set": {f"{indicator}.{coin}.{interval}": value}}
    )
    print(f"Indicator {indicator} for {coin} {interval} updated to {value}")
