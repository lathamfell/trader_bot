from flask import Flask, request
import pymongo
import yagmail
import json
import datetime as dt
from py3cw.request import Py3CW

from config import USER_ATTR

DEBUG = False  # turn all debug messages
DEBUG2 = True  # just specific ones related to what I'm working on

app = Flask(__name__)


@app.route("/status", methods=["POST"])
def status():
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority", tls=True, tlsAllowInvalidCertificates=True)
    db = client.indicators_db
    coll = db.indicators_coll
    print("** STATUS UPDATE **")
    # user specific updates
    for user in USER_ATTR:
        for strat in USER_ATTR[user]['strats']:
            long_bot_id = USER_ATTR[user]['strats'][strat]['long_bot']
            short_bot_id = USER_ATTR[user]['strats'][strat]['short_bot']
            logic = USER_ATTR[user]['strats'][strat]['logic']
            api_key = USER_ATTR[user]['c3_api_key']
            secret = USER_ATTR[user]['c3_secret']
            state = coll.find_one({'_id': user}).get(strat)
            py3c = Py3CW(key=api_key, secret=secret)

            deal_status = 'idle'
            long_in_deal = bot_in_deal(py3c, long_bot_id)
            short_in_deal = bot_in_deal(py3c, short_bot_id)
            if long_in_deal:
                deal_status = 'long'
            if short_in_deal:
                deal_status = 'short'

            state_str = ''
            if state:
                state_str = f"State: {state}.  "

            print(f"{user} {strat} is {deal_status}.  {state_str}Logic: {logic}")
    # indicator updates
    indicatorz = coll.find_one({'_id': 'indicators'})
    del indicatorz['_id']
    for indicator in indicatorz:
        for coin in indicatorz[indicator]:
            for interval in indicatorz[indicator][coin]:
                if indicator == 'MA':
                    MA_pct_per_2_bars = round(indicatorz[indicator][coin][interval]['MA_pct_per_2_bars'], 2)
                    current = round(indicatorz[indicator][coin][interval]['current'], 2)
                    MA_1_bar_ago = round(indicatorz[indicator][coin][interval]['MA_1_bar_ago'], 2)
                    MA_2_bars_ago = round(indicatorz[indicator][coin][interval]['MA_2_bars_ago'], 2)
                    status_str = f"MA_pct_per_2_bars: {MA_pct_per_2_bars}, current: {current}, MA_1_bar_ago: {MA_1_bar_ago}, MA_2_bars_ago: {MA_2_bars_ago}"
                else:
                    continue
                    #status_str = f"{indicatorz[indicator][coin][interval]}"
                print(f"Indicator {indicator} {coin} {interval} status: {status_str}")

    return "status ack"


@app.route("/update", methods=["POST"])
def update():
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority", tls=True, tlsAllowInvalidCertificates=True)
    db = client.indicators_db
    coll = db.indicators_coll
    _update = request.json
    print(f"Received direct update request: {in_order(_update)}")
    user = _update['user']
    strat = _update.get('strat')
    conditions = [
        'UHTF', 'HTF', 'MTF', 'LTF', 'ULTF', 'UULTF', 'MA', 'MAL', 'MAS', 'HTFMAL', 'MTFMAL', 'LTFMAL',
        'HTFMAS', 'MTFMAS', 'LTFMAS', 'condition_one', 'condition_two', 'condition_three'
    ]
    for condition in conditions:
        if condition in _update:
            value = _update[condition]
            exp_length = _update.get("expiration")
            if not exp_length:
                exp_time = dt.datetime.now() + dt.timedelta(weeks=52)
            else:
                exp_time = dt.datetime.now() + dt.timedelta(seconds=exp_length)
            expiration = exp_time
            if isinstance(value, str):
                # translate bool strs to bool type
                if value == 'true':
                    value = True
                elif value == 'false':
                    value = False
            # set db value
            result = coll.update_one({'_id': user}, {"$set": {
                f"{strat}.{condition}.value": value,
                f"{strat}.{condition}.expiration": expiration
            }}, upsert=True)
            if result.raw_result['nModified'] > 0:
                print(f"Direct updated {user} {strat} {condition} to {value}")
            else:
                print(f"{user} {strat} {condition} value {value} same as existing, nothing to update")
    new_state = coll.find_one({'_id': user})[strat]
    print(f"{user} {strat} state: {new_state}")
    return "update complete"


@app.route("/indicators", methods=["POST"])
def indicators():
    _update = request.json
    if DEBUG:
        print(f"DEBUG Received indicator update: {in_order(_update)}")
    indicator = _update["indicator"]
    if indicator == 'MA':
        handle_ma_indicator(_update, indicator)
    elif indicator == 'SuperTrend':
        handle_supertrend_indicator(_update, indicator)
    elif indicator == 'KST':
        handle_kst_indicator(_update, indicator)
    else:
        print(f"Unknown indicator {indicator} received")

    return "indicator updated"


def handle_kst_indicator(_update, indicator):
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority", tls=True, tlsAllowInvalidCertificates=True)
    db = client.indicators_db
    coll = db.indicators_coll

    coin = _update["coin"]
    interval = _update["interval"]
    cur_value = round(_update["value"], 2)
    number_of_minutes_to_count_back = 16
    indicatorz = coll.find_one({'_id': 'indicators'})
    cur_kst = indicatorz.get(indicator)
    if not cur_kst:
        # starting from scratch
        change_history = {}
        recent_value_history = {}
    else:
        change_history = cur_kst[coin][interval].get('change_history', {})
        recent_value_history = cur_kst[coin][interval].get('recent_value_history', {})
        # dump the oldest one if the recent history is full
        if len(recent_value_history) >= number_of_minutes_to_count_back:
            oldest_dt = get_oldest_dt(recent_value_history)
            del recent_value_history[oldest_dt]

    # add the new one
    now = dt.datetime.now().isoformat()[5:16].replace('T', ' ')
    recent_value_history[now] = cur_value
    # calculate the pct change from oldest recent value to current value
    oldest_value = recent_value_history[get_oldest_dt(recent_value_history)]
    change = round(cur_value - oldest_value, 2)
    # add to change history
    change_history[now] = change

    coll.update_one({'_id': 'indicators'}, {"$set": {
        f"{indicator}.{coin}.{interval}.change": change,
        f"{indicator}.{coin}.{interval}.change_history": change_history,
        f"{indicator}.{coin}.{interval}.recent_value_history": recent_value_history
    }}, upsert=True)
    if DEBUG or DEBUG2:
        print(f"DEBUG Indicator {indicator} change from {oldest_value} to {cur_value} over {number_of_minutes_to_count_back} minutes is {change}")


def get_oldest_value(value_history):
    oldest_dt = get_oldest_dt(value_history)
    return value_history[oldest_dt]


def get_oldest_dt(value_history):
    oldest_dt = dt.datetime.now().isoformat()
    for historical_dt in value_history:
        if historical_dt < oldest_dt:
            oldest_dt = historical_dt
    return oldest_dt


def handle_ma_indicator(_update, indicator):
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority", tls=True, tlsAllowInvalidCertificates=True)
    db = client.indicators_db
    coll = db.indicators_coll

    coin = _update["coin"]
    interval = _update["interval"]
    value = _update["value"]
    update_pct = _update["update_pct"]

    # pull current state of indicators
    cur = coll.find_one({'_id': 'indicators'})

    if update_pct:
        # print an update for easy traceability of calculation in the logs
        MA_cur_to_print = '{:.2f}'.format(cur[indicator][coin][interval]['current'])
        MA_1_bar_to_print = '{:.2f}'.format(cur[indicator][coin][interval]['MA_1_bar_ago'])
        MA_2_bars_to_print = '{:.2f}'.format(cur[indicator][coin][interval]['MA_2_bars_ago'])
        state_to_print = f"cur: {MA_cur_to_print}, 1 bar ago: {MA_1_bar_to_print}, 2 bars ago: {MA_2_bars_to_print}"

        MA_2_bars_ago = cur[indicator][coin][interval]['MA_2_bars_ago']
        MA_pct_per_2_bars = ((value - MA_2_bars_ago) / MA_2_bars_ago) * 100
        coll.update_one({'_id': 'indicators'}, {"$set": {
            f"{indicator}.{coin}.{interval}.current": value,
            f"{indicator}.{coin}.{interval}.MA_pct_per_2_bars": MA_pct_per_2_bars
        }}, upsert=True)
        if DEBUG:
            print(f"Indicator {indicator} pct for {coin} {interval} updated to {'{:.2f}'.format(MA_pct_per_2_bars)}, based on {state_to_print}")
    else:
        MA_3_bars_ago = cur[indicator][coin][interval]['MA_2_bars_ago']
        MA_2_bars_ago = cur[indicator][coin][interval]['MA_1_bar_ago']
        MA_1_bar_ago = value
        # update db
        coll.update_one({'_id': 'indicators'}, {
            "$set": {
                f"{indicator}.{coin}.{interval}.MA_3_bars_ago": MA_3_bars_ago,
                f"{indicator}.{coin}.{interval}.MA_2_bars_ago": MA_2_bars_ago,
                f"{indicator}.{coin}.{interval}.MA_1_bar_ago": MA_1_bar_ago
            }})
        if DEBUG:
            print(f"Indicator {indicator} for {coin} {interval} updated to {'{:.2f}'.format(MA_1_bar_ago)}")


def handle_supertrend_indicator(_update, indicator):
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority", tls=True, tlsAllowInvalidCertificates=True)
    db = client.indicators_db
    coll = db.indicators_coll
    coin = _update["coin"]
    interval = _update["interval"]
    value = _update["value"]
    coll.update_one({'_id': 'indicators'}, {"$set": {
        f"{indicator}.{coin}.{interval}": value
    }})
    print(f"Indicator {indicator} for {coin} {interval} updated to {value}")


class AlertHandler:

    def __init__(self, req):
        if DEBUG:
            print(f"DEBUG Received request: {request}")
            print(f"DEBUG Data: {request.data}")
        # user ccbot, password hugegainz, default database ccbot
        # template: "mongodb+srv://ccbot:<password>@cluster0.4y4dc.mongodb.net/<default_db>?retryWrites=true&w=majority"
        client = pymongo.MongoClient(
            "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority", tls=True,
            tlsAllowInvalidCertificates=True)
        db = client.indicators_db
        self.coll = db.indicators_coll
        self.alert = req.json
        if DEBUG:
            print(f"DEBUG Received alert: {in_order(self.alert)}")
        self.user = self.alert['user']
        self.strat = self.alert.get('strat')
        self.condition = self.alert.get('condition')
        self.value = self.alert.get('value')
        exp_length = self.alert.get('expiration')
        if not exp_length:
            exp_time = dt.datetime.now() + dt.timedelta(weeks=52)
        else:
            exp_time = dt.datetime.now() + dt.timedelta(seconds=exp_length)
        self.expiration = exp_time
        self.run_logic = self.alert.get('run_logic')
        if isinstance(self.value, str):
            # translate bool strs to bool type
            if self.value == 'true':
                self.value = True
            elif self.value == 'false':
                self.value = False

        # get user, coin and bot details from config
        self.api_key = USER_ATTR[self.user]['c3_api_key']
        self.secret = USER_ATTR[self.user]['c3_secret']
        self.email = USER_ATTR[self.user]['email']
        self.email_enabled = USER_ATTR[self.user]['email_enabled']
        self.long_bot = USER_ATTR[self.user]['strats'][self.strat]['long_bot']
        self.short_bot = USER_ATTR[self.user]['strats'][self.strat]['short_bot']
        self.logic = USER_ATTR[self.user]['strats'][self.strat]['logic']
        self.coin = USER_ATTR[self.user]['strats'][self.strat]['coin']
        self.py3c = Py3CW(key=self.api_key, secret=self.secret)

        if self.run_logic:
            # skip directly to logic
            self.route_logic(self.alert)
            return

        # otherwise we need to update state
        user_states = self.coll.find_one({'_id': self.user})

        if user_states:
            self.state = user_states.get(self.strat)
            if DEBUG:
                print(f"DEBUG Current {self.user} {self.strat} state: {self.state}")
        else:
            print(f"No current state found for {self.user}")

        result = self.coll.update_one({'_id': self.user}, {"$set": {
            f"{self.strat}.{self.condition}.value": self.value,
            f"{self.strat}.{self.condition}.expiration": self.expiration
        }}, upsert=True)
        if result.raw_result['nModified'] > 0:
            self.state = self.coll.find_one({'_id': self.user})[self.strat]
            print(f"Switched {self.user} {self.strat} {self.condition} to {self.value} with expiration {self.expiration}. New state: {self.state}")

            self.route_logic(self.alert)
        else:
            if DEBUG:
                print(f"DEBUG {self.user} {self.strat} {self.condition} value {self.value} same as existing, nothing to update")
            pass

    def route_logic(self, alert):
        if self.logic == 'alpha':
            self.run_logic_alpha(alert)
            return
        elif self.logic == 'beta':
            self.run_logic_beta(alert)
            return
        elif self.logic == 'gamma':
            self.run_logic_gamma(alert)
            return
        elif self.logic == 'delta':
            self.run_logic_delta(alert)
            return
        elif self.logic == 'epsilon':
            self.run_logic_epsilon(alert)
            return
        elif self.logic == 'zeta':
            self.run_logic_zeta(alert)
            return
        elif self.logic == 'eta':
            self.run_logic_eta(alert)
            return
        elif self.logic == 'theta':
            self.run_logic_theta(alert)
            return
        elif self.logic == 'iota':
            self.run_logic_iota(alert)
            return
        elif self.logic == 'kappa':
            self.run_logic_kappa(alert)
            return
        elif self.logic == 'lambda':
            self.run_logic_lambda(alert)
            return
        elif self.logic == 'mu':
            self.run_logic_mu(alert)
            return
        elif self.logic == 'nu':
            self.run_logic_nu(alert)
            return
        elif self.logic == 'xi':
            self.run_logic_xi(alert)
            return
        elif self.logic == 'omicron':
            self.run_logic_omicron(alert)
            return
        elif self.logic == 'pi':
            self.run_logic_pi(alert)
            return
        elif self.logic == 'rho':
            self.run_logic_rho(alert)
            return
        elif self.logic == 'sigma':
            self.run_logic_sigma(alert)
            return
        elif self.logic == '':
            print(f"No logic configured for {self.user} {self.strat}, skipping bot decisions.")
            return
        raise Exception(f"Something unexpected went wrong trying to route logic for {self.user} {self.strat}")

    def run_logic_alpha(self, alert):
        self.state = self.coll.find_one({'_id': 'indicators'})['SuperTrend'][self.coin]
        try:
            UULTF = self.state['1m']
            MTF = self.state['15m']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        if UULTF == 'buy' and MTF == 'buy':
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long.  Reason: UULTF buy and MTF buy")
                open_bot_deal(self.py3c, self.long_bot)
                return
        else:
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                close_bot_deal(self.py3c, self.long_bot)
                return
        if DEBUG:
            print(f"Stars misaligned for {self.user} {self.strat} long, or already in deal, nothing to do")

        if UULTF == 'sell' and MTF == 'sell':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short.  Reason: UULTF sell and MTF sell")
                open_bot_deal(self.py3c, self.short_bot)
                return
        else:
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                close_bot_deal(self.py3c, self.short_bot)
                return
        if DEBUG:
            print(f"Stars misaligned for {self.user} {self.strat} short, or already in deal, nothing to do")

    def run_logic_beta(self, alert):
        self.state = self.coll.find_one({'_id': 'indicators'})['SuperTrend'][self.coin]
        try:
            MTF = self.state['15m']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        indicatorz = self.coll.find_one({'_id': 'indicators'})
        MA_pct_per_2_bars = indicatorz['MA'][self.coin]['15m']['MA_pct_per_2_bars']

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        LONG_OPEN = self.alert['long_open']
        LONG_CLOSE = self.alert['long_close']
        SHORT_OPEN = self.alert['short_open']
        SHORT_CLOSE = self.alert['short_close']

        if long_in_deal:
            if MA_pct_per_2_bars <= LONG_CLOSE:
                print(f"Closing {self.user} {self.strat} long.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} <= {LONG_CLOSE}")
                close_bot_deal(self.py3c, self.long_bot)
            elif MTF != 'buy':
                print(f"Closing {self.user} {self.strat} long.  Reason: MTF sell")
                close_bot_deal(self.py3c, self.long_bot)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} in long, leaving open because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not <= {LONG_CLOSE}, and MTF buy")
        elif MTF == 'buy':
            if MA_pct_per_2_bars >= LONG_OPEN:
                print(f"Opening {self.user} {self.strat} long.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} >= {LONG_OPEN} and MTF buy")
                open_bot_deal(self.py3c, self.long_bot)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} not opening long because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not >= {LONG_OPEN}")
        elif DEBUG:
            print(f"DEBUG {self.user} {self.strat} not opening long because MTF sell")

        if short_in_deal:
            if MA_pct_per_2_bars >= SHORT_CLOSE:
                print(f"Closing {self.user} {self.strat} short.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} >= {SHORT_CLOSE}")
                close_bot_deal(self.py3c, self.short_bot)
            elif MTF != 'sell':
                print(f"Closing {self.user} {self.strat} short.  Reason: MTF buy")
                close_bot_deal(self.py3c, self.short_bot)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} in short, leaving open because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not >= {SHORT_CLOSE}, and MTF sell")
        elif MTF == 'sell':
            if MA_pct_per_2_bars <= SHORT_OPEN:
                print(f"Opening {self.user} {self.strat} short.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} <= {SHORT_OPEN} and MTF sell")
                open_bot_deal(self.py3c, self.short_bot)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} not opening short because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not <= {SHORT_OPEN}")
        elif DEBUG:
            print(f"DEBUG {self.user} {self.strat} not opening short because MTF buy")

    def run_logic_gamma(self, alert):
        self.state = self.coll.find_one({'_id': 'indicators'})['SuperTrend'][self.coin]
        try:
            UULTF = self.state['1m']
            ULTF = self.state['3m']
            LTF = self.state['5m']
            MTF = self.state['15m']
            HTF = self.state['1h']
            UHTF = self.state['4h']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        if UULTF == 'buy' and ULTF == 'buy' and LTF == 'buy' and MTF == 'buy' and HTF == 'buy' and UHTF == 'buy':
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long.  Reason: all 6 TFs buy")
                open_bot_deal(self.py3c, self.long_bot)
                return
        else:
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                close_bot_deal(self.py3c, self.long_bot)
                return
        if DEBUG:
            print(f"Stars misaligned for {self.user} {self.strat} long, or already in deal, nothing to do")

        if UULTF == 'sell' and ULTF == 'sell' and LTF == 'sell' and MTF == 'sell' and HTF == 'sell' and UHTF == 'sell':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short.  Reason: all 6 TFs sell")
                open_bot_deal(self.py3c, self.short_bot)
                return
        else:
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                close_bot_deal(self.py3c, self.short_bot)
                return
        if DEBUG:
            print(f"Stars misaligned for {self.user} {self.strat} short, or already in deal, nothing to do")

    def run_logic_delta(self, alert):
        try:
            KST = self.state["KST"]["value"]
            last_trend_entered = self.state.get("last_trend_entered")
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        if long_in_deal or short_in_deal:
            if DEBUG:
                print(f"DEBUG {self.user} {self.strat} already in deal, nothing to do")
                return
        if (KST == 'long' and last_trend_entered == 'long') or (KST == 'short' and last_trend_entered == 'short'):
            if DEBUG:
                print(f"DEBUG {self.user} {self.strat} already entered this trend, nothing to do")
                return
        if KST == 'long':
            print(f"Opening {self.user} {self.strat} long")
            open_bot_deal(self.py3c, self.long_bot)
            last_trend_entered = 'long'
        elif KST == 'short':
            print(f"Opening {self.user} {self.strat} short")
            open_bot_deal(self.py3c, self.short_bot)
            last_trend_entered = 'short'

        self.coll.update_one({'_id': self.user}, {"$set": {
            f"{self.strat}.last_trend_entered": last_trend_entered
        }}, upsert=True)

    def run_logic_epsilon(self, alert):
        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        if long_in_deal or short_in_deal:
            if DEBUG or DEBUG2:
                print(f"DEBUG {self.user} {self.strat} already in deal, nothing to do")
                return

        indicatorz = self.coll.find_one({'_id': 'indicators'})
        change = indicatorz['KST'][self.coin]['15m']['change']

        last_trend_entered = None
        state = self.coll.find_one({'_id': self.user}).get(self.strat)
        if state:
            last_trend_entered = state.get('last_trend_entered')

        deal_threshold = alert['threshold']
        enter_long = change > deal_threshold
        enter_short = change < (-1 * deal_threshold)
        if (enter_long and last_trend_entered == 'long') or (enter_short and last_trend_entered == 'short'):
            if DEBUG or DEBUG2:
                print(f"DEBUG {self.user} {self.strat} already entered this trend, nothing to do")
                return
        elif enter_long:
            print(f"Opening {self.user} {self.strat} long")
            open_bot_deal(self.py3c, self.long_bot)
            last_trend_entered = 'long'
        elif enter_short:
            print(f"Opening {self.user} {self.strat} short")
            open_bot_deal(self.py3c, self.short_bot)
            last_trend_entered = 'short'
        else:
            print(f"{self.user} {self.strat}: change {change} is within deal threshold of {deal_threshold}, nothing to do")
            return

        self.coll.update_one({'_id': self.user}, {"$set": {
            f"{self.strat}.last_trend_entered": last_trend_entered
        }}, upsert=True)

    def run_logic_zeta(self, alert):
        try:
            LTF = self.state['LTF']
            MTF = self.state['MTF']
            HTF = self.state['HTF']
            UHTF = self.state['UHTF']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        if LTF == 'long' and MTF == 'long' and HTF == 'long' and UHTF == 'long':
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                open_bot_deal(self.py3c, self.long_bot)

        if LTF == 'short' and MTF == 'short' and HTF == 'short' and UHTF == 'short':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                open_bot_deal(self.py3c, self.short_bot)

    def run_logic_eta(self, alert):
        try:
            UULTF = self.state['UULTF']
            ULTF = self.state['ULTF']
            LTF = self.state['LTF']
            MTF = self.state['MTF']
            HTF = self.state['HTF']
            UHTF = self.state['UHTF']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        if UULTF == 'long' and ULTF == 'long' and LTF == 'long' and MTF == 'long' and HTF == 'long' and UHTF == 'long':
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                open_bot_deal(self.py3c, self.long_bot)

        if UULTF == 'short' and ULTF == 'short' and LTF == 'short' and MTF == 'short' and HTF == 'short' and UHTF == 'short':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                open_bot_deal(self.py3c, self.short_bot)

    def run_logic_theta(self, alert):
        self.state = self.coll.find_one({'_id': 'indicators'})['SuperTrend'][self.coin]['15m']

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)

        if self.condition == "long" and self.state == "buy" and not long_in_deal:
            print(f"Opening {self.user} {self.strat} long")
            open_bot_deal(self.py3c, self.long_bot)

    def run_logic_iota(self, alert):
        try:
            HTF = self.state['HTF']
            LTF = self.state['LTF']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        if HTF == 'long' and LTF == 'long':
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                open_bot_deal(self.py3c, self.long_bot)
        elif self.condition == 'LTF' and self.value == 'short':
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                close_bot_deal(self.py3c, self.long_bot)

        if HTF == 'short' and LTF == 'short':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                open_bot_deal(self.py3c, self.short_bot)
        elif self.condition == 'LTF' and self.value == 'long':
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                close_bot_deal(self.py3c, self.short_bot)

    def run_logic_kappa(self, alert):
        try:
            MA = self.state['MA']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        if MA == 'long':
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                close_bot_deal(self.py3c, self.short_bot)
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                open_bot_deal(self.py3c, self.long_bot)
        if MA == 'short':
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                close_bot_deal(self.py3c, self.long_bot)
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                open_bot_deal(self.py3c, self.short_bot)

    def run_logic_lambda(self, alert):
        try:
            MAL = self.state['MAL']
            MAS = self.state['MAS']
            HTF = self.state['HTF']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        if HTF == 'long':
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                close_bot_deal(self.py3c, self.short_bot)
            if MAL and not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                open_bot_deal(self.py3c, self.long_bot)
            elif not MAL and long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                close_bot_deal(self.py3c, self.long_bot)

        if HTF == 'short':
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                close_bot_deal(self.py3c, self.long_bot)
            if MAS and not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                open_bot_deal(self.py3c, self.short_bot)
            elif not MAS and short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                close_bot_deal(self.py3c, self.short_bot)

    def run_logic_mu(self, alert):
        try:
            LTF = self.state['LTF']
            MTF = self.state['MTF']
            HTF = self.state['HTF']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        if LTF == 'long' and MTF == 'long' and HTF == 'long':
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                open_bot_deal(self.py3c, self.long_bot)
        else:
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                close_bot_deal(self.py3c, self.long_bot)

        if LTF == 'short' and MTF == 'short' and HTF == 'short':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                open_bot_deal(self.py3c, self.short_bot)
        else:
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                close_bot_deal(self.py3c, self.short_bot)

    def run_logic_nu(self, alert):
        try:
            MAL = self.state['MAL']
            MAS = self.state['MAS']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        if MAL and not MAS:
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                open_bot_deal(self.py3c, self.long_bot)
        else:
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                close_bot_deal(self.py3c, self.long_bot)

        if MAS and not MAL:
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                open_bot_deal(self.py3c, self.short_bot)
        else:
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                close_bot_deal(self.py3c, self.short_bot)

    def run_logic_xi(self, alert):
        try:
            HTF = self.state['HTF']
            MA = self.state['MA']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        if MA == 'long':
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                close_bot_deal(self.py3c, self.short_bot)
            if not long_in_deal and HTF == 'long':
                print(f"Opening {self.user} {self.strat} long")
                open_bot_deal(self.py3c, self.long_bot)
        if MA == 'short':
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                close_bot_deal(self.py3c, self.long_bot)
            if not short_in_deal and HTF == 'short':
                print(f"Opening {self.user} {self.strat} short")
                open_bot_deal(self.py3c, self.short_bot)

    def run_logic_omicron(self, alert):
        indicatorz = self.coll.find_one({'_id': 'indicators'})
        MA_pct_per_2_bars_LTF = indicatorz['MA'][self.coin]['13m']['MA_pct_per_2_bars']
        MA_pct_per_2_bars_MTF = indicatorz['MA'][self.coin]['15m']['MA_pct_per_2_bars']
        MA_pct_per_2_bars_HTF = indicatorz['MA'][self.coin]['17m']['MA_pct_per_2_bars']

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        LONG_OPEN = self.alert['long_open']
        LONG_CLOSE = self.alert['long_close']
        SHORT_OPEN = self.alert['short_open']
        SHORT_CLOSE = self.alert['short_close']
        if DEBUG:
            print(f"Running {self.user} {self.strat}, pcts are 13m: {MA_pct_per_2_bars_LTF}, 15m: {MA_pct_per_2_bars_MTF}, 17m: {MA_pct_per_2_bars_HTF}")

        if long_in_deal:
            if MA_pct_per_2_bars_HTF <= LONG_CLOSE or MA_pct_per_2_bars_MTF <= LONG_CLOSE or MA_pct_per_2_bars_LTF <= LONG_CLOSE:
                print(f"Closing {self.user} {self.strat} long.  Reason: HTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_HTF)} or MTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_MTF)} or LTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_LTF)} <= {LONG_CLOSE}")
                close_bot_deal(self.py3c, self.long_bot)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} in long, leaving open because no MA pcts are <= {LONG_CLOSE}")
        else:
            if MA_pct_per_2_bars_HTF >= LONG_OPEN and MA_pct_per_2_bars_MTF >= LONG_OPEN and MA_pct_per_2_bars_LTF >= LONG_OPEN:
                print(f"Opening {self.user} {self.strat} long. Reason: HTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_HTF)} and MTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_MTF)} and LTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_LTF)} >= {LONG_OPEN}")
                open_bot_deal(self.py3c, self.long_bot)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} not in long, not opening because a MA pct not >= {LONG_OPEN}")

        if short_in_deal:
            if MA_pct_per_2_bars_HTF >= SHORT_CLOSE or MA_pct_per_2_bars_MTF >= SHORT_CLOSE or MA_pct_per_2_bars_LTF >= SHORT_CLOSE:
                print(f"Closing {self.user} {self.strat} short.  Reason: HTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_HTF)} or MTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_MTF)} or LTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_LTF)} >= {SHORT_CLOSE}")
                close_bot_deal(self.py3c, self.short_bot)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} in short, leaving open because no MA pcts are >= {SHORT_CLOSE}")
        else:
            if MA_pct_per_2_bars_HTF <= SHORT_OPEN and MA_pct_per_2_bars_MTF <= SHORT_OPEN and MA_pct_per_2_bars_LTF <= SHORT_OPEN:
                print(f"Opening {self.user} {self.strat} short.  Reason: HTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_HTF)} and MTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_MTF)} and LTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_LTF)} <= {SHORT_OPEN}")
                open_bot_deal(self.py3c, self.short_bot)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} not in short, not opening because one MA pct not <= {SHORT_OPEN}")

    def run_logic_pi(self, alert):
        indicatorz = self.coll.find_one({'_id': 'indicators'})
        MA_pct_per_2_bars = indicatorz['MA'][self.coin]['15m']['MA_pct_per_2_bars']

        last_trend_entered = None
        strat_stats = self.coll.find_one({'_id': self.user}).get(self.strat)
        if strat_stats:
            last_trend_entered = strat_stats.get('last_trend_entered')
        # see if we can clear the trend
        if last_trend_entered == 'long' and MA_pct_per_2_bars <= 0:
            print(f"{self.user} {self.strat} clearing long flag from last_trend_entered")
            last_trend_entered = None
        elif last_trend_entered == 'short' and MA_pct_per_2_bars >= 0:
            print(f"{self.user} {self.strat} clearing short flag from last_trend_entered")
            last_trend_entered = None

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        LONG_OPEN = self.alert['long_open']
        LONG_CLOSE = self.alert['long_close']
        SHORT_OPEN = self.alert['short_open']
        SHORT_CLOSE = self.alert['short_close']

        if long_in_deal:
            if MA_pct_per_2_bars <= LONG_CLOSE:
                print(f"Closing {self.user} {self.strat} long.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} <= {LONG_CLOSE}")
                close_bot_deal(self.py3c, self.long_bot)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} in long, leaving open because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not <= {LONG_CLOSE}")
        elif last_trend_entered == 'long':
            if DEBUG:
                print(f"DEBUG {self.user} {self.strat} long staying out until trend exhaustion")
        elif MA_pct_per_2_bars >= LONG_OPEN:
            print(f"Opening {self.user} {self.strat} long.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} >= {LONG_OPEN}")
            open_bot_deal(self.py3c, self.long_bot)
            last_trend_entered = 'long'
        elif DEBUG:
            print(f"DEBUG {self.user} {self.strat} not opening long because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not >= {LONG_OPEN}")

        if short_in_deal:
            if MA_pct_per_2_bars >= SHORT_CLOSE:
                print(f"Closing {self.user} {self.strat} short.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} >= {SHORT_CLOSE}")
                close_bot_deal(self.py3c, self.short_bot)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} in short, leaving open because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not >= {SHORT_CLOSE}")
        elif last_trend_entered == 'short':
            if DEBUG:
                print(f"DEBUG {self.user} {self.strat} short staying out until trend exhaustion")
        elif MA_pct_per_2_bars <= SHORT_OPEN:
            print(f"Opening {self.user} {self.strat} short.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} <= {SHORT_OPEN}")
            open_bot_deal(self.py3c, self.short_bot)
            last_trend_entered = 'short'
        elif DEBUG:
            print(f"DEBUG {self.user} {self.strat} not opening short because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not <= {SHORT_OPEN}")

        self.coll.update_one({'_id': self.user}, {"$set": {
            f"{self.strat}.last_trend_entered": last_trend_entered
        }}, upsert=True)

    def run_logic_rho(self, alert):
        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        if long_in_deal or short_in_deal:
            if DEBUG:
                print(f"DEBUG {self.user} {self.strat} skipping all logic because already in a deal")
            return

        try:
            COND_1_VALUE = self.state['condition_one']['value']
            COND_1_EXP = self.state['condition_one']['expiration']
            COND_2_VALUE = self.state['condition_two']['value']
            COND_2_EXP = self.state['condition_two']['expiration']
            COND_3_VALUE = self.state['condition_three']['value']
            COND_3_EXP = self.state['condition_three']['expiration']
            COND_4_VALUE = self.state['condition_four']['value']
            COND_4_EXP = self.state['condition_four']['expiration']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        # screen out expired signals
        time_now = dt.datetime.now()
        if COND_1_EXP <= time_now:
            if DEBUG:
                print(f"DEBUG {self.user} {self.strat} skipping logic because condition_one expired at {COND_1_EXP.ctime()}")
                return
        if COND_2_EXP <= time_now:
            if DEBUG:
                print(f"DEBUG {self.user} {self.strat} skipping logic because condition_two expired at {COND_2_EXP.ctime()}")
                return
        if COND_3_EXP <= time_now:
            if DEBUG:
                print(f"DEBUG {self.user} {self.strat} skipping logic because condition_three expired at {COND_3_EXP.ctime()}")
                return
        if COND_4_EXP <= time_now:
            if DEBUG:
                print(f"DEBUG {self.user} {self.strat} skipping logic because condition_four expired at {COND_4_EXP.ctime()}")
                return

        if COND_1_VALUE == 'long' and COND_2_VALUE == 'long' and COND_3_VALUE == 'long' and COND_4_VALUE == 'long':
            print(f"Opening {self.user} {self.strat} long and clearing conditions")
            open_bot_deal(self.py3c, self.long_bot)
            # clear expirations
            self.coll.update_one({'_id': self.user}, {"$unset": {
                f"{self.strat}.condition_one.expiration": '',
                f"{self.strat}.condition_two.expiration": '',
                f"{self.strat}.condition_three.expiration": '',
                f"{self.strat}.condition_four.expiration": '',
                f"{self.strat}.condition_one.value": '',
                f"{self.strat}.condition_two.value": '',
                f"{self.strat}.condition_three.value": '',
                f"{self.strat}.condition_four.value": ''
            }})
        elif COND_1_VALUE == 'short' and COND_2_VALUE == 'short' and COND_3_VALUE == 'short' and COND_4_VALUE == 'short':
            print(f"Opening {self.user} {self.strat} short and clearing conditions")
            open_bot_deal(self.py3c, self.short_bot)
            # clear expirations
            self.coll.update_one({'_id': self.user}, {"$unset": {
                f"{self.strat}.condition_one.expiration": '',
                f"{self.strat}.condition_two.expiration": '',
                f"{self.strat}.condition_three.expiration": '',
                f"{self.strat}.condition_four.expiration": '',
                f"{self.strat}.condition_one.value": '',
                f"{self.strat}.condition_two.value": '',
                f"{self.strat}.condition_three.value": '',
                f"{self.strat}.condition_four.value": ''
            }})
        elif DEBUG:
            print(f"DEBUG {self.user} {self.strat} not opening a deal because signals don't line up")

    def run_logic_sigma(self, alert):
        try:
            UULTF = self.state['UULTF']['value']
            ULTF = self.state['ULTF']['value']
            LTF = self.state['LTF']['value']
            MTF = self.state['MTF']['value']
            HTF = self.state['HTF']['value']
            UHTF = self.state['UHTF']['value']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.py3c, self.long_bot)
        short_in_deal = bot_in_deal(self.py3c, self.short_bot)

        if UULTF == 'buy' and ULTF == 'buy' and LTF == 'buy' and MTF == 'buy' and HTF == 'buy' and UHTF == 'buy':
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long.  Reason: all 6 TFs buy")
                open_bot_deal(self.py3c, self.long_bot)
                return
        else:
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                close_bot_deal(self.py3c, self.long_bot)
                return
        if DEBUG:
            print(f"Stars misaligned for {self.user} {self.strat} long, or already in deal, nothing to do")

        if UULTF == 'sell' and ULTF == 'sell' and LTF == 'sell' and MTF == 'sell' and HTF == 'sell' and UHTF == 'sell':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short.  Reason: all 6 TFs sell")
                open_bot_deal(self.py3c, self.short_bot)
                return
        else:
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                close_bot_deal(self.py3c, self.short_bot)
                return
        if DEBUG:
            print(f"Stars misaligned for {self.user} {self.strat} short, or already in deal, nothing to do")


@app.route("/", methods=["GET", "POST"])
def main():
    AlertHandler(req=request)
    return "ok"


def turn_on_bot(py3c, bot_id):
    error, data = py3c.request(entity="bots", action="enable", action_id=bot_id)
    if error.get("error"):
        raise Exception(f"Error turning on bot {bot_id}, {error['msg']}")
    return data


def turn_off_bot(py3c, bot_id):
    error, data = py3c.request(entity="bots", action="disable", action_id=bot_id)
    if error.get("error"):
        raise Exception(f"Error turning off bot {bot_id}, {error['msg']}")
    return data


def cancel_bot_deal(py3c, bot_id):
    error, data = py3c.request(entity="bots", action="cancel_all_deals", action_id=bot_id)
    if error.get("error"):
        raise Exception(f"Error cancelling deal for bot {bot_id}, {error['msg']}")
    return data


def bot_in_deal(py3c, bot_id):
    error, data = py3c.request(entity="bots", action="show", action_id=bot_id)
    if error.get("error"):
        raise Exception(f"Error checking status for bot {bot_id}, {error['msg']}")
    return data['active_deals_count'] > 0


def open_bot_deal(py3c, bot_id):
    error, data = py3c.request(entity="bots", action="start_new_deal", action_id=bot_id)
    if error.get("error"):
        raise Exception(f"Error opening new deal for bot {bot_id}, {error['msg']}")
    return data


def close_bot_deal(py3c, bot_id):
    error, data = py3c.request(entity="bots", action="panic_sell_all_deals", action_id=bot_id)
    if error.get("error"):
        raise Exception(f"Error closing deal for bot {bot_id}, {error['msg']}")
    return data


def close_trade(py3c, trade_id):
    error, data = py3c.request(entity="smart_trades_v2", action="close_by_market", action_id=trade_id)
    if error.get("error"):
        raise Exception(f"Error closing trade {trade_id}, {error['msg']}")
    return data


def open_trade(py3c, account_id, pair, _type, tp, tp_trail, sl):
    trade = get_trade(account_id, pair, _type, tp, tp_trail, sl)
    error, data = py3c.request(entity="smart_trades_v2", action="new", payload=trade)
    if error.get("error"):
        raise Exception(f"Error opening trade of type {_type} for account {account_id}, {error['msg']}")
    return data


def get_base_trade(account_id, pair, _type, tp, tp_trail, sl):
    return {
        "account_id": int(account_id),
        "pair": pair,
        "leverage": {
            "enabled": "true",
            "type": "isolated",
            "value": str(1)
        },
        "position": {
            "type": _type,  # 'buy' / 'sell'
            "units": {
                "value": "1"
            },
            "order_type": "market"
        },
        "take_profit": {
            "enabled": "true",
            "steps": [
                {
                    "order_type": "market",
                    "price": {
                        "type": "last",
                        "percent": str(tp)
                    },
                    "volume": "100",
                    "trailing": {
                        "enabled": "true",
                        "percent": str(tp_trail)
                    }
                }
            ]
        },
        "stop_loss": {
            "enabled": "true",
            "order_type": "market",
            "conditional": {
                "price": {
                    "type": "last",
                    "percent": str(sl)
                },
                "trailing": {
                    "enabled": "true",
                    "percent": str(sl)
                }
            }
        }
    }


def get_simple_trade():
    return {
        "account_id": 30391847,
        "pair": "ETH_ETHUSD_PERP",
        "position": {
            "type": "buy",
            "units": {
                "value": "1.0"
            },
            "order_type": "market"
        },
        "leverage": {
            "enabled": "true",
            "type": "isolated",
            "value": "1"
        },
        "take_profit": {
            "enabled": "false",
            "steps": [
                {
                    "order_type": "market",
                    "price": {
                        "value": 3000,
                        "type": "last"
                    }
                }
            ]
        },
        "stop_loss": {
            "enabled": "true",
            "order_type": "market",
            "conditional": {
                "price": {
                    "type": "last"
                },
                "trailing": {
                    "enabled": "true",
                    "percent": "0.2"
                }
            }
        }
    }


def send_email(to, subject, body=None):
    yagmail.SMTP('lathamfell@gmail.com', 'lrhnapmiegubspht').send(to, subject, body)


def in_order(dict):
    return json.dumps(dict, sort_keys=True)


if __name__ == '__main__':
    app.run(debug=True)
