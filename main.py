import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler

import logging
from flask import Flask, request
import datetime as dt
from alphabot.py3cw.request import Py3CW
import traceback

import alphabot.helpers as h
from alphabot.trade_checkup import trade_checkup
from alphabot.updaters import config_update
from alphabot.config import USER_ATTR, LOG_LEVEL
import alphabot.trading as trading
from alphabot.report import report


app = Flask(__name__)

# logging_client = google.cloud.logging.Client()
# handler = CloudLoggingHandler(logging_client)
# logger = logging.getLogger("cloudLogger")
# logger.setLevel(LOG_LEVEL)
# logger.addHandler(handler)


def get_logger():
    print("getting logger")
    logging_client = google.cloud.logging.Client()
    handler = CloudLoggingHandler(logging_client)
    logger = logging.getLogger("cloudLogger")
    logger.setLevel(LOG_LEVEL)
    logger.addHandler(handler)
    return logger


@app.route("/", methods=["GET", "POST"])
def main():
    # logger = get_logger()
    logger = None
    try:
        if request.method == "GET":
            return "Crypto Bros reporting for duty! None yet died of natural causes!"
        # print(f"got request: {request.json}")
        route = request.json.get("route")
        # print(f"got route: {route}")
        if route == "report":
            return report(logger)
        if route == "config_update":
            return config_update(request, logger)
        if route == "trade_checkup":
            return trade_checkup(logger)
        else:
            AlertHandler(logger)

            return "ok"
    except Exception as err:
        print(f"Caught exception while handling request {request} with {request.data}")
        traceback.print_exc()
        h.send_email(
            to="lathamfell@gmail.com", subject="AlphaBot Error", body=f"{request.data}"
        )
        return "request not processed due to server error"


class AlertHandler:
    def __init__(self, logger):
        # user ccbot, password hugegainz, default database ccbot
        # template: "mongodb+srv://ccbot:<password>@cluster0.4y4dc.mongodb.net/<default_db>?retryWrites=true&w=majority"
        self.coll = h.get_mongo_coll()
        # process in alert
        self.alert = request.json
        print(f"Got alert: {self.alert}")
        self.user = self.alert["user"]
        self.strat = self.alert.get("strat")
        self.condition = self.alert.get("condition")
        self.value = self.alert.get("value")
        self.price = self.alert.get("price")
        exp_length = self.alert.get("expiration")
        if not exp_length:
            exp_time = dt.datetime.now() + dt.timedelta(weeks=52)
        else:
            exp_time = dt.datetime.now() + dt.timedelta(seconds=exp_length)
        self.expiration = exp_time
        self.value = h.screen_for_str_bools(self.value)

        # get details from internal config
        self.api_key = USER_ATTR[self.user]["c3_api_key"]
        self.secret = USER_ATTR[self.user]["c3_secret"]
        self.email = USER_ATTR[self.user]["email"]
        self.email_enabled = USER_ATTR[self.user]["email_enabled"]
        self.logic = USER_ATTR[self.user]["strats"][self.strat]["logic"]
        self.coin = USER_ATTR[self.user]["strats"][self.strat]["coin"]
        self.pair = USER_ATTR[self.user]["strats"][self.strat]["pair"]
        self.account_id = USER_ATTR[self.user]["strats"][self.strat]["account_id"]
        self.interval = USER_ATTR[self.user]["strats"][self.strat].get("interval")
        self.pct_sell_per_exit_signal = USER_ATTR[self.user]["strats"][self.strat].get(
            "pct_sell_per_exit_signal"
        )
        self.simulate_leverage = USER_ATTR[self.user]["strats"][self.strat].get(
            "simulate_leverage"
        )
        self.entry_order_type = USER_ATTR[self.user]["strats"][self.strat]["entry_order_type"]
        self.tp_order_type = USER_ATTR[self.user]["strats"][self.strat]["tp_order_type"]
        self.sl_order_type = USER_ATTR[self.user]["strats"][self.strat]["sl_order_type"]

        # API helper
        self.py3c = Py3CW(key=self.api_key, secret=self.secret)

        # pull state
        try:
            self.state = self.coll.find_one({"_id": self.user})[self.strat]
        except KeyError:
            print(f"{self.user} {self.strat} not in db yet")
            self.state = {}

        # pull status and user defined config
        config = self.state.get("config")
        if not config:
            h.set_up_default_strat_config(
                coll=self.coll, user=self.user, strat=self.strat
            )
            self.state = self.coll.find_one({"_id": self.user})[self.strat]
            config = self.state["config"]

        self.tp_pct = config["tp_pct"]
        self.tp_pct_2 = config.get("tp_pct_2")
        # logger.debug(f"got tp_pct {self.tp_pct} and tp_pct_2 {self.tp_pct_2} for alert {self.alert}")
        self.sl_pct = config["sl_pct"]
        self.sl_trail = config["sl_trail"]
        self.leverage = config["leverage"]
        self.units = config["units"]
        self.description = config.get("description")
        self.loss_limit_fraction = config.get("loss_limit_fraction")
        self.pct_of_starting_assets = config.get("pct_of_starting_assets")

        # check status of previous trade, if there is one (whether open or closed)
        try:
            trade_id = self.state["status"].get("trade_id")
        except KeyError:
            print(f"{self.user} {self.strat} no status in db yet")
            self.state["status"] = {}
            trade_id = None
        if trade_id:
            self.trade_status = trading.trade_status(
                self.py3c, trade_id, self.description, logger
            )
            print(f"{self.description} __init__ AH trade status: {self.trade_status}")
        else:
            self.trade_status = None

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
                    f"{self.user} {self.strat} switched {self.condition} to {self.value} with expiration "
                    f"{self.expiration}. New state: {self.state}"
                )

            else:
                print(
                    f"{self.user} {self.strat} {self.condition} value {self.value} same as existing, nothing to update"
                )
                return
        self.run_logic(self.alert, logger)

    def run_logic(self, alert, logger):
        if self.logic == "gamma":
            self.run_logic_gamma(alert, logger)
            return
        if self.logic == "omega":
            self.run_logic_omega(alert, logger)
            return

        elif self.logic == "":
            print(
                f"{self.user} {self.strat} No logic configured, skipping trade decision."
            )
            return
        print(
            f"{self.user} {self.strat} Something unexpected went wrong trying to run logic"
        )
        raise Exception

    def run_logic_gamma(self, alert, logger):
        direction = h.get_current_trade_direction(
            _trade_status=self.trade_status,
            user=self.user,
            strat=self.strat,
            logger=logger,
        )
        if (alert.get("close_long") and direction == "long") or (
            alert.get("close_short") and direction == "short"
        ):
            # exit criteria met
            trade_id = self.state["status"]["trade_id"]
            if (not alert.get("partial")) or self.state["status"][
                "took_partial_profit"
            ]:  # signal close, must close by market
                print(
                    f"{self.description} {direction} {trade_id} closing full position due to exit signal"
                )
                trading.close_trade(
                    py3c=self.py3c,
                    trade_id=trade_id,
                    user=self.user,
                    strat=self.strat,
                    description=self.description,
                    logger=logger,
                )
                return
            else:  # only close half
                print(
                    f"{self.description} {direction} {trade_id} closing partial position due to partial exit signal"
                )
                trading.take_partial_profit(
                    py3c=self.py3c,
                    trade_id=trade_id,
                    description=self.description,
                    user=self.user,
                    strat=self.strat,
                    logger=logger,
                )
                # update status so we don't do another partial close
                self.coll.update_one(
                    {"_id": self.user},
                    {"$set": {f"{self.strat}.status.took_partial_profit": True}},
                )
                return
        elif alert.get("close_long") or alert.get("close_short"):
            return

        _type = None
        if alert.get("long"):
            _type = "buy"
        elif alert.get("short"):
            _type = "sell"

        if direction:
            # close current trade first: signal close, so must close by market
            trade_id = self.state["status"]["trade_id"]
            trading.close_trade(
                py3c=self.py3c,
                trade_id=trade_id,
                user=self.user,
                strat=self.strat,
                description=self.description,
                logger=logger,
            )

        trading.open_trade(
            py3c=self.py3c,
            account_id=self.account_id,
            pair=self.pair,
            _type=_type,
            leverage=self.leverage,
            simulate_leverage=self.simulate_leverage,
            units=self.units,
            tp_pct=self.tp_pct,
            tp_pct_2=self.tp_pct_2,
            sl_pct=self.sl_pct,
            sl_trail=self.sl_trail,
            entry_order_type=self.entry_order_type,
            tp_order_type=self.tp_order_type,
            sl_order_type=self.sl_order_type,
            user=self.user,
            strat=self.strat,
            description=self.description,
            logger=logger,
            price=self.price,
            coll=self.coll,
            loss_limit_fraction=self.loss_limit_fraction,
            pct_of_starting_assets=self.pct_of_starting_assets
        )

    def run_logic_omega(self, alert, logger):
        direction = h.get_current_trade_direction(
            _trade_status=self.trade_status,
            user=self.user,
            strat=self.strat,
            logger=logger
        )
        htf_shadow = self.state["status"].get("htf_shadow")
        print(f"{self.strat} current HTF shadow: {htf_shadow}")
        new_htf_shadow = None
        _type = None

        # does current trade need to be closed.  If so, close by market because this is signal close
        if (alert.get("open_short_htf") and direction == "long") or \
                (alert.get("open_long_htf") and direction == "short"):
            trade_id = self.state["status"]["trade_id"]
            trading.close_trade(
                py3c=self.py3c,
                trade_id=trade_id,
                user=self.user,
                strat=self.strat,
                description=self.description,
                logger=logger,
            )
            direction = None
            print(f"{self.strat} HTF signal against current trade: closing")

        if direction:
            # if we are still in a trade there is no need to enter another
            return

        # check for HTF entry criteria
        if alert.get("open_short_htf"):
            new_htf_shadow = htf_shadow = "short"
            _type = "sell"
            print(f"{self.strat} HTF signal: opening short")
        elif alert.get("open_long_htf"):
            new_htf_shadow = htf_shadow = "long"
            _type = "buy"
            print(f"{self.strat} HTF signal: opening long")

        # check for LTF entry criteria
        if alert.get("open_short_ltf") and htf_shadow == "short":
            print(f"{self.strat} LTF in shadow, opening short")
            _type = "sell"
        elif alert.get("open_long_ltf") and htf_shadow == "long":
            print(f"{self.strat} LTF in shadow, opening long")
            _type = "buy"

        # update HTF shadow if needed
        if new_htf_shadow:
            self.coll.update_one(
                {"_id": self.user},
                {"$set": {
                    f"{self.strat}.status.htf_shadow": new_htf_shadow
                }}
            )
            print(f"{self.strat} HTF shadow updated to {new_htf_shadow}")

        if _type:
            trading.open_trade(
                py3c=self.py3c,
                account_id=self.account_id,
                pair=self.pair,
                _type=_type,
                leverage=self.leverage,
                simulate_leverage=self.simulate_leverage,
                units=self.units,
                tp_pct=self.tp_pct,
                tp_pct_2=self.tp_pct_2,
                sl_pct=self.sl_pct,
                sl_trail=self.sl_trail,
                user=self.user,
                strat=self.strat,
                description=self.description,
                logger=logger,
                price=self.price,
                coll=self.coll,
                loss_limit_fraction=self.loss_limit_fraction,
                pct_of_starting_assets=self.pct_of_starting_assets
            )


if __name__ == "__main__":
    app.run(debug=True)
