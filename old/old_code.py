"""

def run_logic_sigma(self, alert):
    try:
        UULTF = self.state["conditions"]["UULTF"]["value"]
        ULTF = self.state["conditions"]["ULTF"]["value"]
        LTF = self.state["conditions"]["LTF"]["value"]
        MTF = self.state["conditions"]["MTF"]["value"]
        HTF = self.state["conditions"]["HTF"]["value"]
        UHTF = self.state["conditions"]["UHTF"]["value"]
    except KeyError:
        print(
            f"Incomplete dataset for user {self.user} {self.strat}, skipping decision"
        )
        return "Incomplete dataset, skipping decision"

    _trade_status = trade_status(self.py3c, self.state)  # long, short, idle

    if (
            UULTF == "buy"
            and ULTF == "buy"
            and LTF == "buy"
            and MTF == "buy"
            and HTF == "buy"
            and UHTF == "buy"
    ):
        if not _trade_status == "long":
            print(f"Opening {self.user} {self.strat} long.  Reason: all 6 TFs buy")
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
            )
            self.coll.update_one(
                {"_id": self.user},
                {"$set": {f"{self.strat}.status.trade_id": trade_id}},
                upsert=True,
            )
            return
    else:
        if _trade_status == "long":
            print(f"Closing {self.user} {self.strat} long")
            trade_id = self.state["status"]["trade_id"]
            close_trade(self.py3c, trade_id)
            return
    if DEBUG:
        print(
            f"Stars misaligned for {self.user} {self.strat} long, or already in trade, nothing to do"
        )

    if (
            UULTF == "sell"
            and ULTF == "sell"
            and LTF == "sell"
            and MTF == "sell"
            and HTF == "sell"
            and UHTF == "sell"
    ):
        if not _trade_status == "short":
            print(
                f"Opening {self.user} {self.strat} short.  Reason: all 6 TFs sell"
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
            )
            self.coll.update_one(
                {"_id": self.user},
                {"$set": {f"{self.strat}.status.trade_id": trade_id}},
                upsert=True,
            )
            return
    else:
        if _trade_status == "short":
            print(f"Closing {self.user} {self.strat} short")
            trade_id = self.state["status"]["trade_id"]
            close_trade(self.py3c, trade_id)
            return
    if DEBUG:
        print(
            f"Stars misaligned for {self.user} {self.strat} short, or already in trade, nothing to do"
        )

   def run_logic_gamma(self, alert):
        self.state = self.coll.find_one({"_id": "indicators"})["SuperTrend"][self.coin]

        try:
            UULTF = self.state["conditions"]["1m"]
            ULTF = self.state["conditions"]["3m"]
            LTF = self.state["conditions"]["5m"]
            MTF = self.state["conditions"]["15m"]
            HTF = self.state["conditions"]["1h"]
            UHTF = self.state["conditions"]["4h"]
        except KeyError:
            print(
                f"{self.user} {self.strat }Incomplete dataset, skipping decision"
            )
            return "Incomplete dataset, skipping decision"

        _trade_status = trade_status(self.py3c, self.state)  # long, short, idle

        if (
            UULTF == "buy"
            and ULTF == "buy"
            and LTF == "buy"
            and MTF == "buy"
            and HTF == "buy"
            and UHTF == "buy"
        ):
            if not _trade_status == "long":
                print(f"Opening {self.user} {self.strat} long.  Reason: all 6 TFs buy")
                trade_id = open_trade(
                    self.py3c, account_id=self.account_id, pair=self.pair, _type="buy"
                )
                self.coll.update_one(
                    {"_id": self.user},
                    {"$set": {f"{self.strat}.status.trade_id": trade_id}},
                )
                return
        elif _trade_status == "long":
            print(f"Closing {self.user} {self.strat} long")
            trade_id = self.state["status"]["trade_id"]
            close_trade(self.py3c, trade_id)
            return
        if DEBUG:
            print(
                f"Stars misaligned for {self.user} {self.strat} long, or already in trade, nothing to do"
            )

        if (
            UULTF == "sell"
            and ULTF == "sell"
            and LTF == "sell"
            and MTF == "sell"
            and HTF == "sell"
            and UHTF == "sell"
        ):
            if not _trade_status == "short":
                print(
                    f"Opening {self.user} {self.strat} short.  Reason: all 6 TFs sell"
                )
                trade_id = open_trade(
                    self.py3c, account_id=self.account_id, pair=self.pair, _type="sell"
                )
                self.coll.update_one(
                    {"_id": self.user},
                    {"$set": {f"{self.strat}.status.trade_id": trade_id}},
                    upsert=True,
                )
                return
        else:
            if _trade_status == "short":
                print(f"Closing {self.user} {self.strat} short")
                trade_id = self.state["status"]["trade_id"]
                close_trade(self.py3c, trade_id)
                return
        if DEBUG:
            print(
                f"Stars misaligned for {self.user} {self.strat} short, or already in trade, nothing to do"
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

    def handle_kst_indicator(_update, indicator, logger):
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
    logger.debug(
        f"Indicator {indicator} change from {oldest_value} to {cur_value} over {number_of_minutes_to_count_back} "
        f"minutes is {change}"
    )

def condition_update(request, logger):
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
        tls=True,
        tlsAllowInvalidCertificates=True,
    )
    db = client.indicators_db
    coll = db.indicators_coll

    _update = request.json
    user = _update["user"]
    strat = _update.get("strat")
    logger.info(
        f"{user} {strat} received direct condition update request: {in_order(_update)}"
    )
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
            logger.info(f"{user} {strat} direct updated {condition} to {value}")
        else:
            logger.info(
                f"{user} {strat} {condition} value {value} same as existing, nothing to update"
            )
    return "conditions updated"

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


import pymongo
from time import sleep

from alphabot.py3cw.request import Py3CW
from alphabot.helpers import trade_status, get_current_trade_direction, get_update_trade, close_trade

from alphabot.config import USER_ATTR


def trade_checkup(logger):
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
        tls=True,
        tlsAllowInvalidCertificates=True,
    )
    db = client.indicators_db
    coll = db.indicators_coll

    for user in USER_ATTR:
        api_key = USER_ATTR[user]["c3_api_key"]
        secret = USER_ATTR[user]["c3_secret"]
        py3c = Py3CW(key=api_key, secret=secret)
        strat_states = coll.find_one({"_id": user})
        for strat in USER_ATTR[user]["strats"]:
            try:
                trade_id = strat_states[strat]["status"].get("trade_id")
            except KeyError:
                logger.debug(f"{user} {strat} skipping TSL/TP check because it has no status")
                continue

            tsl_reset_check_for_strat(
                strat_states=strat_states,
                strat=strat,
                user=user,
                py3c=py3c,
                coll=coll,
                trade_id=trade_id,
                logger=logger
            )
            tp_reset_check_for_strat(
                strat_states=strat_states,
                strat=strat,
                user=user,
                py3c=py3c,
                coll=coll,
                trade_id=trade_id,
                logger=logger
            )
    return "TSL/TP reset check complete"


def tsl_reset_check_for_strat(
    strat_states, strat, user, py3c, coll, trade_id, logger
):
    if trade_id:
        _trade_status = trade_status(py3c, trade_id, user, strat, logger)
        trade_direction = get_current_trade_direction(
            _trade_status, user, strat, logger
        )
        if not trade_direction:
            logger.debug(
                f"{user} {strat} not in a trade, not checking TSL resets"
            )
            return
    else:
        return

    try:
        reset_tsl = strat_states[strat]["config"]["reset_tsl"]
        tsl_reset_points = strat_states[strat]["config"]["tsl_reset_points"]
    except KeyError:
        logger.warning(
            f"{user} {strat} skipping TSL reset check because {user} {strat} is missing a TSL reset config item. "
            f"Strat state is {strat_states[strat]}"
        )
        return
    if not reset_tsl:
        logger.debug(f"{user} {strat} has TSL reset disabled, skipping")
        return
    profit_pct = float(_trade_status["profit"]["percent"])

    tsl_reset_points_hit = strat_states[strat]["status"]["tsl_reset_points_hit"]
    for tsl_reset_point in tsl_reset_points:
        trigger = tsl_reset_point[0]
        new_tsl = tsl_reset_point[1]
        if trigger not in tsl_reset_points_hit:
            if profit_pct < trigger:
                logger.debug(
                    f"trade {user} {strat} {trade_id} not resetting TSL, not enough in profit: "
                    f"{profit_pct} < {tsl_reset_point[0]}"
                )
                return
            # all right, reset TSL!
            # most things are the same
            _type = _trade_status["position"]["type"]
            units = _trade_status["position"]["units"]["value"]
            tp_price = _trade_status["take_profit"]["steps"][0]["price"]["value"]
            tp_trail = _trade_status["take_profit"]["steps"][0]["trailing"]["percent"]
            sl_pct = strat_states[strat]["config"]["sl_pct"]
            # recalculate sl price
            trade_entry = round(float(_trade_status["position"]["price"]["value"]))
            if _type == "buy":
                sl_price = round(trade_entry * (1 - new_tsl / 100))
            else:  # sell
                sl_price = round(trade_entry * (1 + new_tsl / 100))

            update_trade = get_update_trade(
                trade_id=trade_id,
                _type=_type,
                units=units,
                tp_price=tp_price,
                tp_trail=tp_trail,
                sl_price=sl_price,
                sl_pct=sl_pct,
                user=user,
                strat=strat,
                logger=logger,
            )
            logger.debug(
                f"{user} {strat} Sending update trade while resetting TSL: {update_trade}"
            )
            update_trade_error, update_trade_data = py3c.request(
                entity="smart_trades_v2",
                action="update",
                action_id=trade_id,
                payload=update_trade,
            )
            if update_trade_error.get("error"):
                logger.error(
                    f"{user} {strat} Error resetting TSL, {update_trade_error['msg']}"
                )
                logger.info(
                    f"{user} {strat} Closing trade {trade_id} since we couldn't reset TSL"
                )
                sleep(1)
                close_trade(py3c, trade_id, user, strat, logger)
                raise Exception
            # update strat status so we don't do this trigger again
            tsl_reset_points_hit.append(trigger)
            coll.update_one(
                {"_id": user},
                {
                    "$set": {
                        f"{strat}.status.tsl_reset_points_hit": tsl_reset_points_hit
                    }
                },
                upsert=True,
            )
            logger.info(
                f"Trade {user} {strat} {trade_id} successfully reset TSL to {new_tsl}, response: "
                f"{update_trade_data}"
            )


def tp_reset_check_for_strat(
    strat_states, strat, user, py3c, coll, trade_id, logger
):
    if trade_id:
        _trade_status = trade_status(py3c, trade_id, user, strat, logger)
        trade_direction = get_current_trade_direction(
            _trade_status, user, strat, logger
        )
        if not trade_direction:
            logger.debug(
                f"{user} {strat} not in a trade, not checking TP resets"
            )
            return
    else:
        return

    try:
        reset_tp = strat_states[strat]["config"]["reset_tp"]
        tp_reset_points = strat_states[strat]["config"]["tp_reset_points"]
    except KeyError:
        logger.warning(
            f"{user} {strat} Skipping TP reset check: missing a TP reset config item. "
            f"Strat state is {strat_states[strat]}"
        )
        return
    if not reset_tp:
        logger.debug(f"{user} {strat} has TP reset disabled, skipping")
        return
    profit_pct = float(_trade_status["profit"]["percent"])

    tp_reset_points_hit = strat_states[strat]["status"]["tp_reset_points_hit"]
    for tp_reset_point in tp_reset_points:
        trigger = float(tp_reset_point[0])
        new_tp = float(tp_reset_point[1])
        if trigger not in tp_reset_points_hit:
            if profit_pct < trigger:
                logger.debug(
                    f"{user} {strat} trade {trade_id} not resetting TP, not enough in profit: "
                    f"{profit_pct} < {trigger}"
                )
                return
            # all right, reset TP!
            # most things are the same
            _type = _trade_status["position"]["type"]
            units = _trade_status["position"]["units"]["value"]
            sl_price = _trade_status["stop_loss"]["conditional"]["price"]["value"]
            tp_trail = _trade_status["take_profit"]["steps"][0]["trailing"]["percent"]
            sl_pct = strat_states[strat]["config"]["sl_pct"]
            # recalculate tp price
            trade_entry = round(float(_trade_status["position"]["price"]["value"]))
            if _type == "buy":
                tp_price = round(trade_entry * (1 + new_tp / 100))
            else:  # sell
                tp_price = round(trade_entry * (1 - new_tp / 100))

            logger.debug(f"{user} {strat} trade_entry was {trade_entry}, new tp price is {tp_price}")

            update_trade = get_update_trade(
                trade_id=trade_id,
                _type=_type,
                units=units,
                tp_price=tp_price,
                tp_trail=tp_trail,
                sl_price=sl_price,
                sl_pct=sl_pct,
                user=user,
                strat=strat,
                logger=logger,
            )
            logger.debug(
                f"{user} {strat} Sending update trade while resetting TP: {update_trade}"
            )
            update_trade_error, update_trade_data = py3c.request(
                entity="smart_trades_v2",
                action="update",
                action_id=trade_id,
                payload=update_trade,
            )
            if update_trade_error.get("error"):
                logger.error(
                    f"{user} {strat} Error resetting TP, {update_trade_error['msg']}"
                )
                logger.info(
                    f"{user} {strat} Closing trade {trade_id} since we couldn't reset TP"
                )
                sleep(1)
                close_trade(py3c, trade_id, user, strat, logger)
                raise Exception
            # update strat status so we don't do this trigger again
            tp_reset_points_hit.append(trigger)
            coll.update_one(
                {"_id": user},
                {
                    "$set": {
                        f"{strat}.status.tp_reset_points_hit": tp_reset_points_hit
                    }
                },
                upsert=True,
            )
            logger.info(
                f"Trade {user} {strat} {trade_id} successfully reset TP to {new_tp}, response: "
                f"{update_trade_data}"
            )

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

    def run_logic_epsilon(self, alert):
        if self.trade_status and get_current_trade_direction(
            self.trade_status, self.user, self.strat, logger
        ):
            logger.debug(f"{self.user} {self.strat} already in trade, nothing to do")
            return

        indicatorz = self.coll.find_one({"_id": "indicators"})
        change = indicatorz["KST"][self.coin][self.interval]["change"]

        trade_threshold = alert["threshold"]
        enter_long = change > trade_threshold
        enter_short = change < (-1 * trade_threshold)
        if (
            enter_long
            and self.last_trend_entered == "long"
            and self.one_entry_per_trend
        ) or (
            enter_short
            and self.last_trend_entered == "short"
            and self.one_entry_per_trend
        ):
            logger.info(
                f"{self.user} {self.strat} already entered this trend, nothing to do"
            )
            return
        elif enter_long:
            logger.info(f"{self.user} {self.strat} Opening long")
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
                        f"{self.strat}.status.last_entry_direction": direction
                    }
                },
                upsert=True,
            )
        elif enter_short:
            logger.info(f"{self.user} {self.strat} Opening short")
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
                        f"{self.strat}.status.profit_logged": False
                    }
                },
                upsert=True,
            )
        else:
            logger.debug(
                f"{self.user} {self.strat}: KST change {change} is within trade threshold of {trade_threshold}, "
                f"nothing to do"
            )
            return



def get_tp_reset(_trade_status, strat_states, strat, user, trade_id, logger):
    try:
        reset_tp = strat_states[strat]["config"]["reset_tp"]
        tp_reset_points = strat_states[strat]["config"]["tp_reset_points"]
    except KeyError:
        #logger.debug(
        #    f"{user} {strat} skipping TP reset check because {user} {strat} is missing a TP reset config item. "
        #    f"Strat state is {strat_states[strat]}"
        #)
        return None, None, None
    if not reset_tp:
        #logger.debug(f"{user} {strat} has TP reset disabled, skipping")
        return None, None, None
    profit_pct = float(_trade_status["profit"]["percent"])
    direction = strat_states[strat]["status"].get("last_entry_direction")
    tp_reset_points_hit = strat_states[strat]["status"]["tp_reset_points_hit"]
    for tp_reset_point in tp_reset_points:
        tp_trigger = tp_reset_point[0]
        new_tp = tp_reset_point[1]
        if tp_trigger not in tp_reset_points_hit:
            if profit_pct < tp_trigger:
                #logger.debug(
                #    f"trade {user} {strat} {trade_id} not resetting TP, not enough in profit: "
                #    f"{profit_pct} < {tp_reset_point[0]}"
                #)
                return None, None, None
            # all right, get new TP!
            logger.info(
                f"{user} {strat} {direction} {trade_id} resetting TP to {new_tp} because profit "
                f"{profit_pct} >= {tp_trigger}")
            _type = _trade_status["position"]["type"]
            trade_entry = round(float(_trade_status["position"]["price"]["value"]))
            if _type == "buy":
                tp_price = round(trade_entry * (1 + new_tp / 100))
            else:  # sell
                tp_price = round(trade_entry * (1 - new_tp / 100))

            return tp_price, tp_trigger, new_tp


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
                    "$set": get_default_open_trade_mongo_set_command(
                        strat=self.strat,
                        trade_id=trade_id,
                        direction="long",
                        tsl=self.sl_pct,
                    )
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
                    "$set": get_default_open_trade_mongo_set_command(
                        strat=self.strat,
                        trade_id=trade_id,
                        direction="short",
                        tsl=self.sl_pct,
                    )
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
                "$set": get_default_open_trade_mongo_set_command(
                    strat=self.strat,
                    trade_id=trade_id,
                    direction=direction,
                    tsl=self.sl_pct,
                )
            },
            upsert=True,
        )

    def run_logic_beta(self, alert):
        direction = get_current_trade_direction(
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
            logger.info(
                f"{self.user} {self.strat} exiting {direction} trade {trade_id} due to exit signal"
            )
            close_trade(self.py3c, trade_id, self.user, self.strat, logger)
            return
        elif alert.get("close_long") or alert.get("close_short"):
            return

        hull = self.coll.find_one({"_id": "indicators"})["hull"][self.coin][
            self.interval
        ]["color"]

        if alert.get("long"):
            new_direction = "long"
            _type = "buy"
        else:  # short
            new_direction = "short"
            _type = "sell"

        if direction and direction != new_direction:
            # close current trade
            trade_id = self.state["status"]["trade_id"]
            close_trade(
                py3c=self.py3c,
                trade_id=trade_id,
                user=self.user,
                strat=self.strat,
                logger=logger,
            )

        if (new_direction == "long" and hull != "green") or (
            new_direction == "short" and hull != "red"
        ):
            logger.debug(
                f"{self.user} {self.strat} potential {new_direction} entry blocked by Hull color: {hull}"
            )
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
            note=f"{self.strat} {new_direction}",
            logger=logger,
        )
        self.coll.update_one(
            {"_id": self.user},
            {
                "$set": get_default_open_trade_mongo_set_command(
                    strat=self.strat,
                    trade_id=trade_id,
                    direction=new_direction,
                    tsl=self.sl_pct,
                )
            },
            upsert=True,
        )


    def run_logic_beta(self, alert):
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
            logger.info(
                f"{self.user} {self.strat} exiting {direction} trade {trade_id} due to exit signal"
            )
            trading.close_trade(self.py3c, trade_id, self.user, self.strat, logger)
            return
        elif alert.get("close_long") or alert.get("close_short"):
            return

        guide = self.coll.find_one({"_id": "indicators"})["htf_guide"][self.coin][
            self.interval
        ]["value"]

        if alert.get("long"):
            new_direction = "long"
            _type = "buy"
        else:  # short
            new_direction = "short"
            _type = "sell"

        if direction and direction != new_direction:
            # close current trade
            trade_id = self.state["status"]["trade_id"]
            trading.close_trade(
                py3c=self.py3c,
                trade_id=trade_id,
                user=self.user,
                strat=self.strat,
                logger=logger,
            )

        trade_id = trading.open_trade(
            self.py3c,
            account_id=self.account_id,
            pair=self.pair,
            _type=_type,
            leverage=self.leverage,
            simulate_leverage=self.leverage,
            units=self.units,
            tp_pct=self.tp_pct,
            tp_trail=self.tp_trail,
            sl_pct=self.sl_pct,
            user=self.user,
            strat=self.strat,
            note=f"{self.strat} {new_direction} {self.description}",
            logger=logger,
        )
        self.coll.update_one(
            {"_id": self.user},
            {
                "$set": h.get_default_open_trade_mongo_set_command(
                    strat=self.strat,
                    trade_id=trade_id,
                    direction=new_direction,
                    tsl=self.sl_pct,
                )
            },
            upsert=True,
        )

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



def indicators():
    _update = request.json
    indicator = _update["indicator"].lower()
    if indicator == "hull" or "htf_guide":
        handle_trend_indicator(_update, indicator, logger)
    else:
        logger.error(f"Unknown indicator {indicator} received")
        raise Exception
    return "indicator updated"


"""

"""

def run_logic_gamma(self, alert, logger):
    # obsolete
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
            pass
            
            #print(
            #    f"{self.description} {direction} {trade_id} closing partial position due to partial exit signal"
            #)
            #trading.take_partial_profit(
            #    py3c=self.py3c,
            #    trade_id=trade_id,
            #    description=self.description,
            #    user=self.user,
            #    entry_order_type=self.entry_order_type,
            #    tp_order_type=self.tp_order_type,
            #    sl_order_type=self.sl_order_type,
            #    strat=self.strat,
            #    logger=logger,
            #)
            ## update status so we don't do another partial close
            #self.coll.update_one(
            #    {"_id": self.user},
            #    {"$set": {f"{self.strat}.status.took_partial_profit": True}},
            #)
            #return
            
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
        units=self.units,
        tp_pct=self.tp_pct,
        tp_pct_2=self.tp_pct_2,
        sl_pct=self.sl_pct,
        dca_pct=self.dca_pct,
        sl_trail=self.sl_trail,
        entry_order_type=self.entry_order_type,
        tp_order_type=self.tp_order_type,
        sl_order_type=self.sl_order_type,
        user=self.user,
        strat=self.strat,
        description=self.description,
        logger=logger,
        alert_price=self.alert_price,
        coll=self.coll
    )


def run_logic_omega(self, alert, logger):
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

    # check for shadow update regardless of whether trades are opened/closed
    if alert.get("open_short_htf"):
        new_htf_shadow = htf_shadow = "short"
    elif alert.get("open_long_htf"):
        new_htf_shadow = htf_shadow = "long"

    # update HTF shadow in db if needed
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
        trading.open_trade(
            py3c=self.py3c,
            account_id=self.account_id,
            pair=self.pair,
            _type=_type,
            leverage=self.leverage,
            units=self.units,
            tp_pct=self.tp_pct,
            tp_pct_2=self.tp_pct_2,
            sl_pct=self.sl_pct,
            dca_pct=self.dca_pct,
            sl_trail=self.sl_trail,
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
