import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler

import logging
from flask import Flask, request
import pymongo
import datetime as dt
from py3cw.request import Py3CW
import traceback
from dateutil import parser
import pytz
from time import sleep

from helpers import (
    in_order,
    close_trade,
    open_trade,
    screen_for_str_bools,
    handle_ma_indicator,
    handle_supertrend_indicator,
    handle_kst_indicator,
    send_email,
    trade_status,
    get_current_trade_direction,
    get_update_trade,
    is_trade_closed
)
from config import USER_ATTR, DEFAULT_STRAT_CONFIG


app = Flask(__name__)

logging_client = google.cloud.logging.Client()
handler = CloudLoggingHandler(logging_client)
cloud_logger = logging.getLogger('cloudLogger')
cloud_logger.setLevel(logging.DEBUG)  # defaults to WARN
cloud_logger.addHandler(handler)


@app.route("/", methods=["GET", "POST"])
def main():
    try:
        if request.method == "GET":
            return "Crypto Bros reporting for duty! None yet died of natural causes!"

        route = request.json.get("route")
        cloud_logger.info(f"Google logger: got route: {route}")
        cloud_logger.debug(f"Google logger: got route: {route}")
        cloud_logger.error(f"Google logger: got route: {route}")

        if route == "indicators":
            return indicators()
        if route == "report":
            return report()
        if route == "condition_update":
            return condition_update()
        if route == "config_update":
            return config_update()
        if route == "breakeven_check":
            return breakeven_check()
        else:
            AlertHandler()
            return "ok"
    except Exception as err:
        print(
            f"\n !!!!  ERROR !!!! Caught exception while handling request {request} with {request.data}\n"
        )
        traceback.print_exc()
        send_email(
            to="lathamfell@gmail.com", subject="AlphaBot Error", body=f"{request.data}"
        )
        return "request not processed due to server error"


def breakeven_check():
    print("running breakeven check")
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
        tls=True,
        tlsAllowInvalidCertificates=True,
    )
    db = client.indicators_db
    coll = db.indicators_coll

    for user in USER_ATTR:
        print(f"DEBUG checking breakeven for user {user}")
        api_key = USER_ATTR[user]["c3_api_key"]
        secret = USER_ATTR[user]["c3_secret"]
        py3c = Py3CW(key=api_key, secret=secret)
        strat_states = coll.find_one({"_id": user})
        for strat in USER_ATTR[user]["strats"]:
            print(f"DEBUG checking breakeven for {user} {strat}")
            if strat_states[strat]["status"].get("breakeven_set"):
                print(
                    f"DEBUG skipping breakeven check because {user} {strat} was already set to breakeven"
                )
                continue
            trade_id = strat_states[strat]["status"].get("trade_id")
            print(f"DEBUG {user} {strat} has trade_id {trade_id}")
            try:
                set_breakeven = strat_states[strat]["config"]["set_breakeven"]
                breakeven_trigger_pct = strat_states[strat]["config"][
                    "breakeven_trigger_pct"
                ]
                breakeven_sl_pct = strat_states[strat]["config"]["breakeven_sl_pct"]
            except KeyError:
                print(
                    f"DEBUG skipping breakeven check because {user} {strat} is missing a breakeven config item. "
                    f"Strat state is {strat_states[strat]}"
                )
                continue
            if not set_breakeven:
                print(f"DEBUG {user} {strat} has breakeven disabled, skipping")
                continue
            if trade_id:
                _trade_status = trade_status(py3c, trade_id, user, strat)
                trade_direction = get_current_trade_direction(_trade_status, user, strat)
                if not trade_direction:
                    print(f"DEBUG {user} {strat} not in a trade, not setting breakeven")
                    continue
                profit_pct = float(_trade_status["profit"]["percent"])
                if profit_pct < breakeven_trigger_pct:
                    print(
                        f"DEBUG trade {user} {strat} {trade_id} not setting breakeven, not enough in "
                        f"profit: {profit_pct} < {breakeven_trigger_pct}"
                    )
                    continue
                # all right, set it to breakeven!
                # most things are the same
                _type = _trade_status["position"]["type"]
                units = _trade_status["position"]["units"]["value"]
                tp_price = _trade_status["take_profit"]["steps"][0]["price"]["value"]
                tp_trail = _trade_status["take_profit"]["steps"][0]["trailing"][
                    "percent"
                ]
                sl_pct = strat_states[strat]["config"][
                    "sl_pct"
                ]  # not sure how to get this out of trade status
                # recalculate sl price
                trade_entry = round(float(_trade_status["position"]["price"]["value"]))
                if _type == "buy":
                    sl_price = round(trade_entry * (1 - breakeven_sl_pct / 100))
                else:  # sell
                    sl_price = round(trade_entry * (1 + breakeven_sl_pct / 100))

                update_trade = get_update_trade(
                    trade_id=trade_id,
                    _type=_type,
                    units=units,
                    tp_price=tp_price,
                    tp_trail=tp_trail,
                    sl_price=sl_price,
                    sl_pct=sl_pct,
                    user=user,
                    strat=strat
                )
                print(
                    f"DEBUG {user} {strat} Sending update trade while setting trade to breakeven: {update_trade}"
                )
                update_trade_error, update_trade_data = py3c.request(
                    entity="smart_trades_v2",
                    action="update",
                    action_id=trade_id,
                    payload=update_trade,
                )
                if update_trade_error.get("error"):
                    print(
                        f"\n !!!! ERROR !!!! {user} {strat} Error updating trade to breakeven, {update_trade_error['msg']}\n"
                    )
                    print(f"{user} {strat} Closing trade {trade_id} since we couldn't apply breakeven")
                    sleep(1)
                    close_trade(py3c, trade_id, user, strat)
                    raise Exception
                # update strat status so we don't set it to breakeven again
                coll.update_one(
                    {"_id": user},
                    {"$set": {f"{strat}.status.breakeven_set": True}},
                    upsert=True,
                )
                print(
                    f"DEBUG trade {user} {strat} {trade_id} successfully updated to breakeven, response: {update_trade_data}"
                )

    return "breakeven check complete"


def indicators():
    _update = request.json
    indicator = _update["indicator"]
    if indicator == "MA":
        handle_ma_indicator(_update, indicator)
    elif indicator == "SuperTrend":
        handle_supertrend_indicator(_update, indicator)
    elif indicator == "KST":
        handle_kst_indicator(_update, indicator)
    else:
        print(f"\n !!!! ERROR ERROR ERROR !!!! Unknown indicator {indicator} received")
        raise Exception
    return "indicator updated"


def report():
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
        tls=True,
        tlsAllowInvalidCertificates=True,
    )
    db = client.indicators_db
    coll = db.indicators_coll
    print("** STRAT REPORT **")
    # user specific updates
    for user in USER_ATTR:
        for strat in USER_ATTR[user]["strats"]:
            logic = USER_ATTR[user]["strats"][strat]["logic"]
            state = coll.find_one({"_id": user}).get(strat)

            status = state.get("status")
            if not status:
                # strat doesn't have a status yet, let's add it
                coll.update_one(
                    {"_id": user}, {"$set": {f"{strat}.status": {}}}, upsert=True
                )
                # re-pull
                state = coll.find_one({"_id": user}).get(strat)

            trade_status = "idle"
            if state["status"].get("in_long"):
                trade_status = "long"
            if state["status"].get("in_short"):
                trade_status = "short"

            state_str = ""
            if state:
                state_str = f"State: {state}.  "

            print(f"{user} {strat} is {trade_status}.  {state_str}Logic: {logic}")
    # indicator updates
    indicatorz = coll.find_one({"_id": "indicators"})
    del indicatorz["_id"]
    for indicator in indicatorz:
        for coin in indicatorz[indicator]:
            for interval in indicatorz[indicator][coin]:
                if indicator == "MA":
                    MA_pct_per_2_bars = round(
                        indicatorz[indicator][coin][interval]["MA_pct_per_2_bars"], 2
                    )
                    current = round(indicatorz[indicator][coin][interval]["current"], 2)
                    MA_1_bar_ago = round(
                        indicatorz[indicator][coin][interval]["MA_1_bar_ago"], 2
                    )
                    MA_2_bars_ago = round(
                        indicatorz[indicator][coin][interval]["MA_2_bars_ago"], 2
                    )
                    status_str = f"MA_pct_per_2_bars: {MA_pct_per_2_bars}, current: {current}, MA_1_bar_ago: {MA_1_bar_ago}, MA_2_bars_ago: {MA_2_bars_ago}"
                else:
                    continue
                    # status_str = f"{indicatorz[indicator][coin][interval]}"
                print(f"Indicator {indicator} {coin} {interval} status: {status_str}")

    return "report ack"


def condition_update():
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
        tls=True,
        tlsAllowInvalidCertificates=True,
    )
    db = client.indicators_db
    coll = db.indicators_coll

    _update = request.json
    print(f"Received direct condition update request: {in_order(_update)}")
    user = _update["user"]
    strat = _update.get("strat")
    conditions = _update["conditions"]
    for condition in conditions:
        value = _update["conditions"][condition]
        expiration = dt.datetime.now() + dt.timedelta(weeks=52)
        value = screen_for_str_bools(value)

        result = coll.update_one(
            {"_id": user},
            {
                "$set": {
                    f"{strat}.conditions.{condition}.value": value,
                    f"{strat}.conditions.{condition}.expiration": expiration,
                }
            },
            upsert=True,
        )

        if result.raw_result["nModified"] > 0:
            print(f"Direct updated {user} {strat} {condition} to {value}")
        else:
            print(
                f"{user} {strat} {condition} value {value} same as existing, nothing to update"
            )
    return "conditions updated"


def config_update():
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
        tls=True,
        tlsAllowInvalidCertificates=True,
    )
    db = client.indicators_db
    coll = db.indicators_coll

    _update = request.json
    print(f"Received direct config update request: {in_order(_update)}")
    user = _update["user"]
    strat = _update.get("strat")
    config = _update["config"]

    tp_pct = config.get("tp_pct")
    tp_trail = config.get("tp_trail")
    sl_pct = config.get("sl_pct")
    leverage = config.get("leverage")
    units = config.get("units")
    one_entry_per_trend = screen_for_str_bools(config.get("one_entry_per_trend"))
    cooldown = config.get("cooldown")
    set_breakeven = config.get("set_breakeven")
    breakeven_trigger_pct = config.get("breakeven_trigger_pct")
    breakeven_sl_pct = config.get("breakeven_sl_pct")

    if tp_pct or tp_pct == 0:
        coll.update_one(
            {"_id": user}, {"$set": {f"{strat}.config.tp_pct": tp_pct}}, upsert=True
        )
    if tp_trail or (
        not tp_trail and "tp_trail" in config
    ):  # cover tp_trail = null scenario
        coll.update_one(
            {"_id": user}, {"$set": {f"{strat}.config.tp_trail": tp_trail}}, upsert=True
        )
    if sl_pct or sl_pct == 0:
        coll.update_one(
            {"_id": user}, {"$set": {f"{strat}.config.sl_pct": sl_pct}}, upsert=True
        )
    if leverage:
        coll.update_one(
            {"_id": user}, {"$set": {f"{strat}.config.leverage": leverage}}, upsert=True
        )
    if units:
        coll.update_one(
            {"_id": user}, {"$set": {f"{strat}.config.units": units}}, upsert=True
        )
    if (one_entry_per_trend == True) or (one_entry_per_trend == False):
        coll.update_one(
            {"_id": user},
            {"$set": {f"{strat}.config.one_entry_per_trend": one_entry_per_trend}},
            upsert=True,
        )
    if cooldown or cooldown == 0:
        coll.update_one(
            {"_id": user}, {"$set": {f"{strat}.config.cooldown": cooldown}}, upsert=True
        )
    if (set_breakeven == True) or (set_breakeven == False):
        coll.update_one(
            {"_id": user},
            {"$set": {f"{strat}.config.set_breakeven": set_breakeven}},
            upsert=True,
        )
    if breakeven_trigger_pct or breakeven_trigger_pct == 0:
        coll.update_one(
            {"_id": user},
            {"$set": {f"{strat}.config.breakeven_trigger_pct": breakeven_trigger_pct}},
            upsert=True,
        )
    if breakeven_sl_pct or breakeven_trigger_pct == 0:
        coll.update_one(
            {"_id": user},
            {"$set": {f"{strat}.config.breakeven_sl_pct": breakeven_sl_pct}},
            upsert=True,
        )

    print(f"Completed direct config update request for {user} {strat}")
    return "config updated"


class AlertHandler:
    def __init__(self):
        # user ccbot, password hugegainz, default database ccbot
        # template: "mongodb+srv://ccbot:<password>@cluster0.4y4dc.mongodb.net/<default_db>?retryWrites=true&w=majority"
        client = pymongo.MongoClient(
            "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
            tls=True,
            tlsAllowInvalidCertificates=True,
        )
        db = client.indicators_db
        self.coll = db.indicators_coll

        # process in alert
        self.alert = request.json
        self.user = self.alert["user"]
        self.strat = self.alert.get("strat")
        self.condition = self.alert.get("condition")
        self.value = self.alert.get("value")
        exp_length = self.alert.get("expiration")
        if not exp_length:
            exp_time = dt.datetime.now() + dt.timedelta(weeks=52)
        else:
            exp_time = dt.datetime.now() + dt.timedelta(seconds=exp_length)
        self.expiration = exp_time
        self.value = screen_for_str_bools(self.value)

        # get details from config
        self.api_key = USER_ATTR[self.user]["c3_api_key"]
        self.secret = USER_ATTR[self.user]["c3_secret"]
        self.email = USER_ATTR[self.user]["email"]
        self.email_enabled = USER_ATTR[self.user]["email_enabled"]
        self.logic = USER_ATTR[self.user]["strats"][self.strat]["logic"]
        self.coin = USER_ATTR[self.user]["strats"][self.strat]["coin"]
        self.pair = USER_ATTR[self.user]["strats"][self.strat]["pair"]
        self.account_id = USER_ATTR[self.user]["strats"][self.strat]["account_id"]
        self.py3c = Py3CW(key=self.api_key, secret=self.secret)

        # pull state and get details
        self.state = self.coll.find_one({"_id": self.user})[self.strat]
        print(f"Current {self.user} {self.strat} state: {self.state}")
        config = self.state.get("config")
        if not config:
            # strat doesn't have a config yet, set a default and re-pull
            self.coll.update_one(
                {"_id": self.user},
                {
                    "$set": {
                        f"{self.strat}.config.tp_pct": DEFAULT_STRAT_CONFIG["tp_pct"],
                        f"{self.strat}.config.tp_trail": DEFAULT_STRAT_CONFIG[
                            "tp_trail"
                        ],
                        f"{self.strat}.config.sl_pct": DEFAULT_STRAT_CONFIG["sl_pct"],
                        f"{self.strat}.config.leverage": DEFAULT_STRAT_CONFIG[
                            "leverage"
                        ],
                        f"{self.strat}.config.units": DEFAULT_STRAT_CONFIG["units"],
                    }
                },
                upsert=True,
            )
            self.state = self.coll.find_one({"_id": self.user})[self.strat]
        # check status of previous trade, if there is one (whether open or closed)
        trade_id = self.state["status"].get("trade_id")
        if trade_id:
            self.trade_status = trade_status(self.py3c, trade_id, self.user, self.strat)
        else:
            self.trade_status = None

        # pull config and status items
        self.tp_pct = self.state["config"]["tp_pct"]
        self.tp_trail = self.state["config"]["tp_trail"]
        self.sl_pct = self.state["config"]["sl_pct"]
        self.leverage = self.state["config"]["leverage"]
        self.units = self.state["config"]["units"]
        self.one_entry_per_trend = self.state["config"].get("one_entry_per_trend")
        self.cooldown = self.state["config"].get("cooldown")
        self.last_trend_entered = self.state["status"].get("last_trend_entered")

        if self.condition:
            # we need to update state before running
            result = self.coll.update_one(
                {"_id": self.user},
                {
                    "$set": {
                        f"{self.strat}.conditions.{self.condition}.value": self.value,
                        f"{self.strat}.conditions.{self.condition}.expiration": self.expiration,
                    }
                },
                upsert=True,
            )
            if result.raw_result["nModified"] > 0:
                self.state = self.coll.find_one({"_id": self.user})[self.strat]
                print(
                    f"Switched {self.user} {self.strat} {self.condition} to {self.value} with expiration {self.expiration}. New state: {self.state}"
                )

            else:
                print(
                    f"DEBUG {self.user} {self.strat} {self.condition} value {self.value} same as existing, nothing to update"
                )
                return

        self.run_logic(self.alert)

    def run_logic(self, alert):
        if self.logic == "epsilon":
            self.run_logic_epsilon(alert)
            return
        elif self.logic == "rho":
            self.run_logic_rho(alert)
            return
        elif self.logic == "":
            print(
                f"No logic configured for {self.user} {self.strat}, skipping trade decision."
            )
            return
        print(
            f"\n !!!! ERROR ERROR ERROR !!!! Something unexpected went wrong trying to run logic for {self.user} {self.strat}"
        )
        raise Exception

    def run_logic_epsilon(self, alert):
        if self.trade_status and get_current_trade_direction(self.trade_status, self.user, self.strat):
            print(f"DEBUG {self.user} {self.strat} already in trade, nothing to do")
            return

        indicatorz = self.coll.find_one({"_id": "indicators"})
        change = indicatorz["KST"][self.coin]["15m"]["change"]

        trade_threshold = alert["threshold"]
        enter_long = change > trade_threshold
        enter_short = change < (-1 * trade_threshold)
        if (enter_long and self.last_trend_entered == "long" and self.one_entry_per_trend) or (
            enter_short and self.last_trend_entered == "short" and self.one_entry_per_trend
        ):
            print(
                f"DEBUG {self.user} {self.strat} already entered this trend, nothing to do"
            )
            return
        elif enter_long:
            print(f"Opening {self.user} {self.strat} long")
            trade_id = open_trade(
                self.py3c,
                account_id=self.account_id,
                pair=self.pair,
                _type="buy",
                leverage=self.leverage,
                units=self.units,
                tp_pct=self.tp_pct,
                tp_trail=self.tp_trail,
                sl_pct=self.sl_pct,
                user=self.user,
                strat=self.strat
            )
            self.coll.update_one(
                {"_id": self.user},
                {
                    "$set": {
                        f"{self.strat}.status.trade_id": trade_id,
                        f"{self.strat}.status.last_trend_entered": "long",
                        f"{self.strat}.status.breakeven_set": False,
                    }
                },
                upsert=True,
            )
        elif enter_short:
            print(f"Opening {self.user} {self.strat} short")
            trade_id = open_trade(
                self.py3c,
                account_id=self.account_id,
                pair=self.pair,
                _type="sell",
                leverage=self.leverage,
                units=self.units,
                tp_pct=self.tp_pct,
                tp_trail=self.tp_trail,
                sl_pct=self.sl_pct,
                user=self.user,
                strat=self.strat
            )
            self.coll.update_one(
                {"_id": self.user},
                {
                    "$set": {
                        f"{self.strat}.status.trade_id": trade_id,
                        f"{self.strat}.status.last_trend_entered": "short",
                        f"{self.strat}.status.breakeven_set": False,
                    }
                },
                upsert=True,
            )
        else:
            print(
                f"{self.user} {self.strat}: change {change} is within trade threshold of {trade_threshold}, nothing to do"
            )
            return

    def run_logic_rho(self, alert):

        if self.trade_status and get_current_trade_direction(self.trade_status, self.user, self.strat):
            print(
                f"DEBUG {self.user} {self.strat} skipping logic because already in a trade"
            )
            return
        elif self.trade_status and is_trade_closed(self.trade_status):
            # check if we're out of cooldown
            closed_time = parser.parse(self.trade_status["data"]["closed_at"])
            now = dt.datetime.now(pytz.UTC)
            if self.cooldown and ((now - closed_time).total_seconds() < self.cooldown):
                print(
                    f"DEBUG {self.user} {self.strat} skipping logic because still in cooldown"
                )
                return

        try:
            COND_1_VALUE = self.state["conditions"]["condition_one"]["value"]
            COND_1_EXP = self.state["conditions"]["condition_one"]["expiration"]
            COND_2_VALUE = self.state["conditions"]["condition_two"]["value"]
            COND_2_EXP = self.state["conditions"]["condition_two"]["expiration"]
            COND_3_VALUE = self.state["conditions"]["condition_three"]["value"]
            COND_3_EXP = self.state["conditions"]["condition_three"]["expiration"]
            COND_4_VALUE = self.state["conditions"]["condition_four"]["value"]
            COND_4_EXP = self.state["conditions"]["condition_four"]["expiration"]
        except KeyError:
            print(
                f"{self.user} {self.strat} Incomplete dataset, skipping decision"
            )
            return "Incomplete dataset, skipping decision"

        # screen out expired signals
        time_now = dt.datetime.now()
        if COND_1_EXP <= time_now:
            print(
                f"DEBUG {self.user} {self.strat} skipping logic because condition_one expired at {COND_1_EXP.ctime()}"
            )
            return
        if COND_2_EXP <= time_now:
            print(
                f"DEBUG {self.user} {self.strat} skipping logic because condition_two expired at {COND_2_EXP.ctime()}"
            )
            return
        if COND_3_EXP <= time_now:
            print(
                f"DEBUG {self.user} {self.strat} skipping logic because condition_three expired at {COND_3_EXP.ctime()}"
            )
            return
        if COND_4_EXP <= time_now:
            print(
                f"DEBUG {self.user} {self.strat} skipping logic because condition_four expired at {COND_4_EXP.ctime()}"
            )
            return

        enter_long = (
            COND_1_VALUE == "long"
            and COND_2_VALUE == "long"
            and COND_3_VALUE == "long"
            and COND_4_VALUE == "long"
        )
        enter_short = (
            COND_1_VALUE == "short"
            and COND_2_VALUE == "short"
            and COND_3_VALUE == "short"
            and COND_4_VALUE == "short"
        )
        if (
            enter_long
            and self.last_trend_entered == "long"
            and self.one_entry_per_trend
        ) or (
            enter_short
            and self.last_trend_entered == "short"
            and self.one_entry_per_trend
        ):
            print(
                f"DEBUG {self.user} {self.strat} already entered this trend, nothing to do"
            )
            return
        elif enter_long:
            print(
                f"Stars align: Opening {self.user} {self.strat} long and clearing conditions. Trigger condition was {self.alert['condition']}"
            )
            trade_id = open_trade(
                self.py3c,
                account_id=self.account_id,
                pair=self.pair,
                _type="buy",
                leverage=self.leverage,
                units=self.units,
                tp_pct=self.tp_pct,
                tp_trail=self.tp_trail,
                sl_pct=self.sl_pct,
                user=self.user,
                strat=self.strat
            )
            self.coll.update_one(
                {"_id": self.user},
                {
                    "$set": {
                        f"{self.strat}.status.trade_id": trade_id,
                        f"{self.strat}.status.last_trend_entered": "long",
                        f"{self.strat}.status.breakeven_set": False,
                    }
                },
                upsert=True,
            )
            # clear expirations
            self.coll.update_one(
                {"_id": self.user},
                {
                    "$unset": {
                        f"{self.strat}.conditions.condition_one.expiration": "",
                        f"{self.strat}.conditions.condition_two.expiration": "",
                        f"{self.strat}.conditions.condition_three.expiration": "",
                        f"{self.strat}.conditions.condition_four.expiration": "",
                        f"{self.strat}.conditions.condition_one.value": "",
                        f"{self.strat}.conditions.condition_two.value": "",
                        f"{self.strat}.conditions.condition_three.value": "",
                        f"{self.strat}.conditions.condition_four.value": "",
                    }
                },
            )
            return
        elif enter_short:
            print(
                f"Stars align: Opening {self.user} {self.strat} short and clearing conditions. Trigger condition was {self.alert['condition']}"
            )
            trade_id = open_trade(
                self.py3c,
                account_id=self.account_id,
                pair=self.pair,
                _type="sell",
                leverage=self.leverage,
                units=self.units,
                tp_pct=self.tp_pct,
                tp_trail=self.tp_trail,
                sl_pct=self.sl_pct,
                user=self.user,
                strat=self.strat
            )
            self.coll.update_one(
                {"_id": self.user},
                {
                    "$set": {
                        f"{self.strat}.status.trade_id": trade_id,
                        f"{self.strat}.status.last_trend_entered": "short",
                        f"{self.strat}.status.breakeven_set": False,
                    }
                },
                upsert=True,
            )
            # clear expirations
            self.coll.update_one(
                {"_id": self.user},
                {
                    "$unset": {
                        f"{self.strat}.conditions.condition_one.expiration": "",
                        f"{self.strat}.conditions.condition_two.expiration": "",
                        f"{self.strat}.conditions.condition_three.expiration": "",
                        f"{self.strat}.conditions.condition_four.expiration": "",
                        f"{self.strat}.conditions.condition_one.value": "",
                        f"{self.strat}.conditions.condition_two.value": "",
                        f"{self.strat}.conditions.condition_three.value": "",
                        f"{self.strat}.conditions.condition_four.value": "",
                    }
                },
            )
            return

        print(
            f"DEBUG {self.user} {self.strat} not opening a trade because signals don't line up"
        )


if __name__ == "__main__":
    app.run(debug=True)
