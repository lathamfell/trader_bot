import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler

import logging
from flask import Flask, request
import datetime as dt
from alphabot.py3cw.request import Py3CW
import traceback
import json5

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
        return "AB request not processed due to server error, or other Exception thrown"


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
        self.alert_price = self.alert.get("price")
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
        self.dca_pct = config.get("dca_pct")
        self.dca_weights = config.get("dca_weights")
        self.signal_dca = config.get("signal_dca")
        self.dca_prices = config.get("dca_prices")
        self.dca_stage = self.state['status'].get('dca_stage')
        self.dca_stages = self.state['status'].get("dca_stages")
        self.sl_trail = config["sl_trail"]
        self.leverage = config["leverage"]
        self.unit_allocation_pct = config["units"]
        self.description = config.get("description")
        self._type = None

        # check status of previous trade, if there is one (whether open or closed)
        try:
            self.trade_id = self.state["status"].get("trade_id")
        except KeyError:
            print(f"{self.user} {self.strat} no status in db yet")
            self.state["status"] = {}
            self.trade_id = None
        if self.trade_id:
            self.trade_status = trading.trade_status(
                self.py3c, self.trade_id, self.description, logger
            )
            print(f"{self.description} trade status: {self.trade_status}")
        else:
            self.trade_status = None


        """
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
        """
        self.run_logic(self.alert, logger)




    def run_logic(self, alert, logger):
        if self.logic == "alpha":
            self.run_logic_alpha(alert, logger)
            return
        #if self.logic == "beta":
        #    self.run_logic_beta(alert, logger)
        #    return

        elif self.logic == "":
            print(
                f"{self.user} {self.strat} No logic configured, skipping trade decision."
            )
            return
        print(
            f"{self.user} {self.strat} Something unexpected went wrong trying to run logic"
        )
        raise Exception

    def run_logic_alpha(self, alert, logger):
        # tri A with signal exit
        direction = h.get_current_trade_direction(
            _trade_status=self.trade_status,
            user=self.user,
            strat=self.strat,
            logger=logger
        )
        htf_shadow = self.state["status"].get("htf_shadow")
        print(f"{self.strat} current HTF shadow: {htf_shadow}")
        new_htf_shadow = None

        ltf_shadow = self.state["status"].get("ltf_shadow")
        print(f"{self.strat} current LTF shadow: {ltf_shadow}")
        new_ltf_shadow = None

        entry_signal = None

        # check for shadow update
        if alert.get("shadow_short_htf"):
            new_htf_shadow = htf_shadow = "short"
        elif alert.get("shadow_long_htf"):
            new_htf_shadow = htf_shadow = "long"
        elif alert.get("shadow_short_ltf"):
            new_ltf_shadow = ltf_shadow = "short"
        elif alert.get("shadow_long_ltf"):
            new_ltf_shadow = ltf_shadow = "long"

        # update shadows in db if needed
        if new_htf_shadow:
            self.coll.update_one(
                {"_id": self.user},
                {"$set": {
                    f"{self.strat}.status.htf_shadow": new_htf_shadow
                }}
            )
            print(f"{self.strat} HTF shadow updated to {new_htf_shadow}")
        if new_ltf_shadow:
            self.coll.update_one(
                {"_id": self.user},
                {"$set": {
                    f"{self.strat}.status.ltf_shadow": new_ltf_shadow
                }}
            )
            print(f"{self.strat} LTF shadow updated to {new_ltf_shadow}")

        # does current trade need to be closed.  If so, close by market because this is signal close
        if (alert.get("open_short_htf") and direction == "long") or \
                (alert.get("open_long_htf") and direction == "short"):
            trading.close_trade(
                py3c=self.py3c,
                trade_id=self.trade_id,
                user=self.user,
                strat=self.strat,
                description=self.description,
                logger=logger,
            )
            direction = None
            print(f"{self.strat} HTF signal against current trade: closing")

        if direction:
            if self.signal_dca:
                # check if we got a DCA signal
                if alert.get("dca_short_signal") and direction == "short":
                    print(f"{self.description} got dca short signal and current trade is short")
                    # check price against dca prices
                    cur_price = float(self.trade_status['data']['current_price']['last'])
                    print(f"{self.description} current BTC price is {cur_price}")
                    for dca_stage in self.dca_stages:
                        if dca_stage['stage'] <= self.dca_stage:
                            print(f"{self.description} already executed DCA stage {dca_stage['stage']}, skipping")
                            continue
                        if cur_price >= dca_stage['price']:
                            print(
                                f"{self.description} for DCA stage {dca_stage['stage']}, current price is >= "
                                f"DCA price of {dca_stage['price']}. Performing DCA.")
                            # perform DCA
                            trading.add_funds(
                                description=self.description, py3c=self.py3c, user=self.user, strat=self.strat,
                                logger=logger, dca_stage=dca_stage, trade_id=self.trade_id, order_type='market')
                        else:
                            print(
                                f"{self.description} for DCA stage {dca_stage['stage']}, current price is not >= "
                                f"DCA price of {dca_stage['price']}. Not performing DCA."
                            )
                if alert.get("dca_long_signal") and direction == "long":
                    print(f"{self.description} got dca long signal and current trade is long")
                    # check price against dca prices
                    cur_price = float(self.trade_status['data']['current_price']['last'])
                    print(f"{self.description} current BTC price is {cur_price}")
                    for dca_stage in self.dca_stages:
                        if dca_stage['stage'] <= self.dca_stage:
                            print(f"{self.description} already executed DCA stage {dca_stage['stage']}, skipping")
                            continue
                        if cur_price <= dca_stage['price']:
                            print(
                                f"{self.description} for DCA stage {dca_stage['stage']}, current price is <= "
                                f"DCA price of {dca_stage['price']}. Performing DCA.")
                            # perform DCA
                            trading.add_funds(
                                description=self.description, py3c=self.py3c, user=self.user, strat=self.strat,
                                logger=logger, dca_stage=dca_stage, trade_id=self.trade_id, order_type='market')
                        else:
                            print(
                                f"{self.description} for DCA stage {dca_stage['stage']}, current price is not <= "
                                f"DCA price of {dca_stage['price']}. Not performing DCA."
                            )

            # if we are still in a trade there is no need to enter another
            return

        # check for HTF entry criteria
        if alert.get("open_short_htf"):
            print(f"{self.strat} HTF signal: opening short")
            entry_signal = "HTF"
            self._type = "sell"
        elif alert.get("open_long_htf"):
            print(f"{self.strat} HTF signal: opening long")
            entry_signal = "HTF"
            self._type = "buy"

        # check for LTF entry criteria
        if alert.get("open_short_ltf") and htf_shadow == "short":
            print(f"{self.strat} LTF in shadow, opening short")
            entry_signal = "LTF"
            self._type = "sell"
        elif alert.get("open_long_ltf") and htf_shadow == "long":
            print(f"{self.strat} LTF in shadow, opening long")
            entry_signal = "LTF"
            self._type = "buy"

        # check for LLTF entry criteria
        if alert.get("open_short_lltf") and htf_shadow == "short" and ltf_shadow == "short":
            print(f"{self.strat} LLTF in double shadow, opening short")
            entry_signal = "LLTF"
            self._type = "sell"
        elif alert.get("open_long_lltf") and htf_shadow == "long" and ltf_shadow == "long":
            print(f"{self.strat} LLTF in double shadow, opening long")
            entry_signal = "LLTF"
            self._type = "buy"

        if self._type:
            self.tf_idx = h.get_tf_idx(tf=entry_signal)
            trading.open_trade(
                py3c=self.py3c,
                account_id=self.account_id,
                pair=self.pair,
                _type=self._type,
                leverage=self.leverage[self.tf_idx],
                unit_allocation_pct=self.unit_allocation_pct[self.tf_idx],
                tp_pct=self.tp_pct[self.tf_idx],
                #tp_pct_2=self.tp_pct_2[tf_idx] if self.tp_pct_2 else None,
                sl_pct=self.sl_pct[self.tf_idx],
                dca_pct=self.dca_pct[self.tf_idx] if self.dca_pct else None,
                dca_weights=self.dca_weights[self.tf_idx] if self.dca_weights else None,
                signal_dca=self.signal_dca,
                sl_trail=self.sl_trail[self.tf_idx],
                entry_order_type=self.entry_order_type,
                tp_order_type=self.tp_order_type,
                sl_order_type=self.sl_order_type,
                user=self.user,
                strat=self.strat,
                description=self.description,
                logger=logger,
                alert_price=self.alert_price,
                coll=self.coll,
                entry_signal=entry_signal
            )
    """
    def run_logic_beta(self, alert, logger):
        # dub A with signal exit
        direction = h.get_current_trade_direction(
            _trade_status=self.trade_status,
            user=self.user,
            strat=self.strat,
            logger=logger
        )
        htf_shadow = self.state["status"].get("htf_shadow")
        print(f"{self.strat} current HTF shadow: {htf_shadow}")
        new_htf_shadow = None

        _type = entry_signal = None

        # check for shadow update
        if alert.get("shadow_short_htf"):
            new_htf_shadow = htf_shadow = "short"
        elif alert.get("shadow_long_htf"):
            new_htf_shadow = htf_shadow = "long"

        # update shadows in db if needed
        if new_htf_shadow:
            self.coll.update_one(
                {"_id": self.user},
                {"$set": {
                    f"{self.strat}.status.htf_shadow": new_htf_shadow
                }}
            )
            print(f"{self.strat} HTF shadow updated to {new_htf_shadow}")

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
            print(f"{self.strat} HTF signal: opening short")
            entry_signal = "HTF"
            _type = "sell"
        elif alert.get("open_long_htf"):
            print(f"{self.strat} HTF signal: opening long")
            entry_signal = "HTF"
            _type = "buy"

        # check for LTF entry criteria
        if alert.get("open_short_ltf") and htf_shadow == "short":
            print(f"{self.strat} LTF in shadow, opening short")
            entry_signal = "LTF"
            _type = "sell"
        elif alert.get("open_long_ltf") and htf_shadow == "long":
            print(f"{self.strat} LTF in shadow, opening long")
            entry_signal = "LTF"
            _type = "buy"

        if _type:
            tf_idx = h.get_tf_idx(tf=entry_signal)
            trading.open_trade(
                py3c=self.py3c,
                account_id=self.account_id,
                pair=self.pair,
                _type=_type,
                leverage=self.leverage[tf_idx],
                unit_allocation_pct=self.units[tf_idx],
                tp_pct=self.tp_pct[tf_idx],
                #tp_pct_2=self.tp_pct_2[tf_idx] if self.tp_pct_2 else None,
                sl_pct=self.sl_pct[tf_idx],
                dca_pct=self.dca_pct[tf_idx] if self.dca_pct else None,
                dca_weights=self.dca_weights[tf_idx] if self.dca_weights else None,
                signal_dca=self.signal_dca,
                sl_trail=self.sl_trail[tf_idx],
                entry_order_type=self.entry_order_type,
                tp_order_type=self.tp_order_type,
                sl_order_type=self.sl_order_type,
                user=self.user,
                strat=self.strat,
                description=self.description,
                logger=logger,
                alert_price=self.alert_price,
                coll=self.coll,
                entry_signal=entry_signal
            )
    """






if __name__ == "__main__":
    app.run(debug=True)
