import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler

from time import sleep
import logging
from flask import Flask, request
import pymongo
import datetime as dt
from alphabot.py3cw.request import Py3CW
import traceback
from dateutil import parser
import pytz

from alphabot.indicators import handle_hull_indicator
from alphabot.helpers import (
    open_trade,
    screen_for_str_bools,
    send_email,
    trade_status,
    get_current_trade_direction,
    is_trade_closed,
    close_trade,
)
from alphabot.trade_checkup import trade_checkup
from alphabot.updaters import config_update
from alphabot.config import USER_ATTR, DEFAULT_STRAT_CONFIG, LOG_LEVEL


app = Flask(__name__)

logging_client = google.cloud.logging.Client()
handler = CloudLoggingHandler(logging_client)
logger = logging.getLogger("cloudLogger")
logger.setLevel(LOG_LEVEL)
logger.addHandler(handler)


@app.route("/", methods=["GET", "POST"])
def main():
    try:
        if request.method == "GET":
            return "Crypto Bros reporting for duty! None yet died of natural causes!"
        # logger.debug(f"got route: {request}")
        route = request.json.get("route")
        # logger.debug(f"got route: {route}")
        if route == "indicators":
            return indicators()
        if route == "report":
            return report()
        if route == "config_update":
            return config_update(request, logger)
        if route == "trade_checkup":
            return trade_checkup(logger)
        else:
            AlertHandler()
            return "ok"
    except Exception as err:
        logger.error(
            f"Caught exception while handling request {request} with {request.data}"
        )
        traceback.print_exc()
        send_email(
            to="lathamfell@gmail.com", subject="AlphaBot Error", body=f"{request.data}"
        )
        return "request not processed due to server error"


def indicators():
    _update = request.json
    indicator = _update["indicator"].lower()
    if indicator == "hull":
        handle_hull_indicator(_update, indicator, logger)
    else:
        logger.error(f"Unknown indicator {indicator} received")
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

    logger.info("** REPORT **")
    output = []
    for user in USER_ATTR:
        for strat in USER_ATTR[user]["strats"]:
            state = coll.find_one({"_id": user}).get(strat)
            status = state.get("status")
            if not status:
                # strat doesn't have a status yet, let's add it
                coll.update_one(
                    {"_id": user}, {"$set": {f"{strat}.status": {}}}, upsert=True
                )
                # re-pull
                state = coll.find_one({"_id": user}).get(strat)
            assets = status.get("paper_assets", 0)
            description = USER_ATTR[user]["strats"][strat]["description"]
            entry = {
                "assets": assets,
                "designation": f"{user} {strat}. {description}",
            }
            output.append(entry)

    sorted_entries = sorted(output, key=lambda k: k["assets"])
    for entry in sorted_entries:
        assets_no = entry['assets']
        assets_str = f"{assets_no:,}"
        logger.info(f"${assets_str}: {entry['designation']}")

    logger.info("** REPORT COMPLETE **")

    return "report ack"


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
        self.interval = USER_ATTR[self.user]["strats"][self.strat].get("interval")
        self.py3c = Py3CW(key=self.api_key, secret=self.secret)

        # pull state and get details
        try:
            self.state = self.coll.find_one({"_id": self.user})[self.strat]
        except KeyError:
            logger.debug(f"{self.user} {self.strat} not in db yet")
            self.state = {}

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
        try:
            trade_id = self.state["status"].get("trade_id")
        except KeyError:
            logger.debug(f"{self.user} {self.strat} no status in db yet")
            self.state["status"] = {}
            trade_id = None
        if trade_id:
            self.trade_status = trade_status(
                self.py3c, trade_id, self.user, self.strat, logger
            )
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
                logger.info(
                    f"{self.user} {self.strat} switched {self.condition} to {self.value} with expiration "
                    f"{self.expiration}. New state: {self.state}"
                )

            else:
                logger.debug(
                    f"{self.user} {self.strat} {self.condition} value {self.value} same as existing, nothing to update"
                )
                return
        self.run_logic(self.alert)

    def run_logic(self, alert):
        if self.logic == "alpha":
            self.run_logic_alpha(alert)
            return
        if self.logic == "beta":
            self.run_logic_beta(alert)
            return
        if self.logic == "gamma":
            self.run_logic_gamma(alert)
            return
        elif self.logic == "rho":
            self.run_logic_rho(alert)
            return
        elif self.logic == "":
            logger.info(
                f"{self.user} {self.strat} No logic configured, skipping trade decision."
            )
            return
        logger.error(
            f"{self.user} {self.strat} Something unexpected went wrong trying to run logic"
        )
        raise Exception

    def run_logic_alpha(self, alert):
        if self.trade_status and get_current_trade_direction(
            self.trade_status, self.user, self.strat, logger
        ):
            logger.debug(f"{self.user} {self.strat} already in trade, nothing to do")
            return

        if alert.get("long"):
            logger.info(f"{self.user} {self.strat} opening long")
            _type = "buy"
            direction = "long"
        elif alert.get("short"):
            logger.info(f"{self.user} {self.strat} opening short")
            _type = "sell"
            direction = "short"
        else:
            logger.error(f"{self.user} {self.strat} got unexpected signal")
            return

        trade_id = open_trade(
            self.py3c,
            account_id=self.account_id,
            pair=self.pair,
            _type=_type,
            leverage=self.leverage,
            units=self.units,
            tp_pct=self.tp_pct,
            tp_trail=self.tp_trail,
            sl_pct=self.sl_pct,
            user=self.user,
            strat=self.strat,
            note=f"{self.strat} {direction}",
            logger=logger,
        )
        self.coll.update_one(
            {"_id": self.user},
            {
                "$set": {
                    f"{self.strat}.status.trade_id": trade_id,
                    f"{self.strat}.status.tsl_reset_points_hit": [],
                    f"{self.strat}.status.tp_reset_points_hit": [],
                    f"{self.strat}.status.profit_logged": False,
                    f"{self.strat}.status.last_entry_direction": direction,
                }
            },
            upsert=True,
        )

    def run_logic_beta(self, alert):
        hull = self.coll.find_one({"_id": "indicators"})["hull"][self.coin][
            self.interval
        ]["color"]

        if self.trade_status and get_current_trade_direction(
            self.trade_status, self.user, self.strat, logger
        ):
            logger.debug(f"{self.user} {self.strat} already in trade, nothing to do")
            return

        if alert.get("long") and hull == "green":
            logger.info(f"{self.user} {self.strat} opening long")
            _type = "buy"
            direction = "long"
        elif alert.get("short") and hull == "red":
            logger.info(f"{self.user} {self.strat} opening short")
            _type = "sell"
            direction = "short"
        else:
            logger.debug(
                f"{self.user} {self.strat} potential entry blocked by Hull color: {hull}"
            )
            return
        logger.debug(f"{self.user} {self.strat} decided to open trade")
        trade_id = open_trade(
            self.py3c,
            account_id=self.account_id,
            pair=self.pair,
            _type=_type,
            leverage=self.leverage,
            units=self.units,
            tp_pct=self.tp_pct,
            tp_trail=self.tp_trail,
            sl_pct=self.sl_pct,
            user=self.user,
            strat=self.strat,
            note=f"{self.strat} {direction}",
            logger=logger,
        )
        self.coll.update_one(
            {"_id": self.user},
            {
                "$set": {
                    f"{self.strat}.status.trade_id": trade_id,
                    f"{self.strat}.status.tsl_reset_points_hit": [],
                    f"{self.strat}.status.tp_reset_points_hit": [],
                    f"{self.strat}.status.profit_logged": False,
                    f"{self.strat}.status.last_entry_direction": direction,
                }
            },
            upsert=True,
        )

    def run_logic_gamma(self, alert):
        direction = get_current_trade_direction(
            self.trade_status, self.user, self.strat, logger
        )
        if (alert.get("close_long") and direction == "long") or (
            alert.get("close_short") and direction == "short"
        ):
            # exit criteria met
            trade_id = self.state["status"]["trade_id"]
            logger.info(
                f"{self.user} {self.strat} exiting {direction} trade {trade_id} due to exit signal"
            )
            close_trade(self.py3c, trade_id, self.user, self.strat, logger)
            return
        elif alert.get("close_long") or alert.get("close_short"):
            return

        if alert.get("long"):
            new_direction = "long"
            _type = "buy"
        else:
            new_direction = "short"
            _type = "sell"

        if direction and direction != new_direction:
            # close current trade first
            trade_id = self.state["status"]["trade_id"]
            close_trade(self.py3c, trade_id, self.user, self.strat, logger)

        trade_id = open_trade(
            self.py3c,
            account_id=self.account_id,
            pair=self.pair,
            _type=_type,
            leverage=self.leverage,
            units=self.units,
            tp_pct=self.tp_pct,
            tp_trail=self.tp_trail,
            sl_pct=self.sl_pct,
            user=self.user,
            strat=self.strat,
            note=f"{self.strat} {new_direction}",
            logger=logger,
        )
        self.coll.update_one(
            {"_id": self.user},
            {
                "$set": {
                    f"{self.strat}.status.trade_id": trade_id,
                    f"{self.strat}.status.tsl_reset_points_hit": [],
                    f"{self.strat}.status.tp_reset_points_hit": [],
                    f"{self.strat}.status.profit_logged": False,
                    f"{self.strat}.status.last_entry_direction": new_direction,
                }
            },
            upsert=True,
        )

    def run_logic_rho(self, alert):

        if self.trade_status and get_current_trade_direction(
            self.trade_status, self.user, self.strat, logger
        ):
            logger.debug(
                f"{self.user} {self.strat} skipping logic because already in a trade"
            )
            return
        elif self.trade_status and is_trade_closed(self.trade_status):
            # check if we're out of cooldown
            closed_time = parser.parse(self.trade_status["data"]["closed_at"])
            now = dt.datetime.now(pytz.UTC)
            if self.cooldown and ((now - closed_time).total_seconds() < self.cooldown):
                logger.debug(
                    f"{self.user} {self.strat} skipping logic because still in cooldown"
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
            logger.info(
                f"{self.user} {self.strat} Incomplete dataset, skipping decision"
            )
            return "Incomplete dataset, skipping decision"

        # screen out expired signals
        time_now = dt.datetime.now()
        if COND_1_EXP <= time_now:
            logger.debug(
                f"{self.user} {self.strat} skipping logic because condition_one expired at {COND_1_EXP.ctime()}"
            )
            return
        if COND_2_EXP <= time_now:
            logger.debug(
                f"{self.user} {self.strat} skipping logic because condition_two expired at {COND_2_EXP.ctime()}"
            )
            return
        if COND_3_EXP <= time_now:
            logger.debug(
                f"{self.user} {self.strat} skipping logic because condition_three expired at {COND_3_EXP.ctime()}"
            )
            return
        if COND_4_EXP <= time_now:
            logger.debug(
                f"{self.user} {self.strat} skipping logic because condition_four expired at {COND_4_EXP.ctime()}"
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
            logger.debug(
                f"{self.user} {self.strat} already entered this trend, nothing to do"
            )
            return
        elif enter_long:
            logger.info(
                f"{self.user} {self.strat} Stars align: Opening long and clearing conditions. Trigger condition "
                f"was {self.alert['condition']}"
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
                strat=self.strat,
                note=f"{self.strat} long",
                logger=logger,
            )
            self.coll.update_one(
                {"_id": self.user},
                {
                    "$set": {
                        f"{self.strat}.status.trade_id": trade_id,
                        f"{self.strat}.status.last_trend_entered": "long",
                        f"{self.strat}.status.tsl_reset_points_hit": [],
                        f"{self.strat}.status.tp_reset_points_hit": [],
                        f"{self.strat}.status.profit_logged": False,
                        f"{self.strat}.status.last_entry_direction": "long",
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
            logger.info(
                f"{self.user} {self.strat} Stars align: Opening short and clearing conditions. Trigger condition "
                f"was {self.alert['condition']}"
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
                strat=self.strat,
                note=f"{self.strat} short",
                logger=logger,
            )
            self.coll.update_one(
                {"_id": self.user},
                {
                    "$set": {
                        f"{self.strat}.status.trade_id": trade_id,
                        f"{self.strat}.status.last_trend_entered": "short",
                        f"{self.strat}.status.tsl_reset_points_hit": [],
                        f"{self.strat}.status.tp_reset_points_hit": [],
                        f"{self.strat}.status.profit_logged": False,
                        f"{self.strat}.status.last_entry_direction": "short",
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

        logger.debug(
            f"{self.user} {self.strat} not opening a trade because signals don't line up"
        )


if __name__ == "__main__":
    app.run(debug=True)
