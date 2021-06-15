from flask import Flask, request
import pymongo
import yagmail
import json
import datetime as dt
from py3cw.request import Py3CW

from config import USER_ATTR

DEBUG = True  # turn all debug messages
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
            logic = USER_ATTR[user]['strats'][strat]['logic']
            state = coll.find_one({'_id': user}).get(strat)

            trade_status = 'idle'
            if state['status']['in_long']:
                trade_status = 'long'
            if state['status']['in_short']:
                trade_status = 'short'

            state_str = ''
            if state:
                state_str = f"State: {state}.  "

            print(f"{user} {strat} is {trade_status}.  {state_str}Logic: {logic}")
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


@app.route("/cond_update", methods=["POST"])
def strat_cond_update():
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority", tls=True, tlsAllowInvalidCertificates=True)
    db = client.indicators_db
    coll = db.indicators_coll

    _update = request.json
    print(f"Received direct condition update request: {in_order(_update)}")
    user = _update['user']
    strat = _update.get('strat')
    conditions = _update["conditions"]
    for condition in conditions:
        value = _update[condition]
        expiration = dt.datetime.now() + dt.timedelta(weeks=52)
        value = screen_for_str_bools(value)

        result = coll.update_one({'_id': user}, {"$set": {
            f"{strat}.conditions.{condition}.value": value,
            f"{strat}.conditions.{condition}.expiration": expiration
        }}, upsert=True)

        if result.raw_result['nModified'] > 0:
            print(f"Direct updated {user} {strat} {condition} to {value}")
        else:
            print(f"{user} {strat} {condition} value {value} same as existing, nothing to update")
    return "update complete"


@app.route("/conf_update", methods=["POST"])
def strat_conf_update():
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority", tls=True, tlsAllowInvalidCertificates=True)
    db = client.indicators_db
    coll = db.indicators_coll

    _update = request.json
    print(f"Received direct config update request: {in_order(_update)}")
    user = _update['user']
    strat = _update.get('strat')
    config = _update["config"]

    tp_pct = config.get("tp_pct")
    tp_trail = config.get("tp_trail")
    sl_pct = config.get("sl_pct")
    leverage = config.get("leverage")
    units = config.get("units")

    if tp_pct:
        coll.update_one({'_id': user}, {"$set": {
            f"{strat}.config.tp_pct": tp_pct
        }}, upsert=True)
    if tp_trail:
        coll.update_one({'_id': user}, {"$set": {
            f"{strat}.config.tp_trail": tp_trail
        }}, upsert=True)
    if sl_pct:
        coll.update_one({'_id': user}, {"$set": {
            f"{strat}.config.sl_pct": sl_pct
        }}, upsert=True)
    if leverage:
        coll.update_one({'_id': user}, {"$set": {
            f"{strat}.config.leverage": leverage
        }}, upsert=True)
    if units:
        coll.update_one({'_id': user}, {"$set": {
            f"{strat}.config.units": units
        }}, upsert=True)

    print(f"Complete direct config update request for {user} {strat}")


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
        raise Exception(f"Unknown indicator {indicator} received")

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
    if DEBUG:
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
        self.value = screen_for_str_bools(self.value)

        # get details from config
        self.api_key = USER_ATTR[self.user]['c3_api_key']
        self.secret = USER_ATTR[self.user]['c3_secret']
        self.email = USER_ATTR[self.user]['email']
        self.email_enabled = USER_ATTR[self.user]['email_enabled']
        self.logic = USER_ATTR[self.user]['strats'][self.strat]['logic']
        self.coin = USER_ATTR[self.user]['strats'][self.strat]['coin']
        self.pair = USER_ATTR[self.user]['strats'][self.strat]['pair']
        self.account_id = USER_ATTR[self.user]['strats'][self.strat]['account_id']
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
            print(f"No logic configured for {self.user} {self.strat}, skipping trade decision.")
            return
        raise Exception(f"Something unexpected went wrong trying to route logic for {self.user} {self.strat}")

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

        in_long = self.state['status'].get('in_long')
        in_short = self.state['status'].get('in_short')

        if UULTF == 'buy' and ULTF == 'buy' and LTF == 'buy' and MTF == 'buy' and HTF == 'buy' and UHTF == 'buy':
            if not in_long:
                print(f"Opening {self.user} {self.strat} long.  Reason: all 6 TFs buy")
                trade_id = open_trade(self.py3c, account_id=self.account_id, pair=self.pair, _type='buy')
                self.coll.update_one({'_id': self.user}, {"$set": {
                    f"{self.strat}.status.trade_id": trade_id,
                    f"{self.strat}.status.in_long": True
                }})
                return
        elif in_long:
            print(f"Closing {self.user} {self.strat} long")
            trade_id = self.state['status']['trade_id']
            close_trade(self.py3c, trade_id)
            return
        if DEBUG:
            print(f"Stars misaligned for {self.user} {self.strat} long, or already in deal, nothing to do")

        if UULTF == 'sell' and ULTF == 'sell' and LTF == 'sell' and MTF == 'sell' and HTF == 'sell' and UHTF == 'sell':
            if not in_short:
                print(f"Opening {self.user} {self.strat} short.  Reason: all 6 TFs sell")
                trade_id = open_trade(self.py3c, account_id=self.account_id, pair=self.pair, _type='sell')
                self.coll.update_one({'_id': self.user}, {"$set": {
                    f"{self.strat}.status.trade_id": trade_id,
                    f"{self.strat}.status.in_long": True
                }}, upsert=True)
                return
        else:
            if in_short:
                print(f"Closing {self.user} {self.strat} short")
                trade_id = self.state['status']['trade_id']
                close_trade(self.py3c, trade_id)
                return
        if DEBUG:
            print(f"Stars misaligned for {self.user} {self.strat} short, or already in deal, nothing to do")

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

        in_long = self.state['status'].get('in_long')
        in_short = self.state['status'].get('in_short')

        if UULTF == 'buy' and ULTF == 'buy' and LTF == 'buy' and MTF == 'buy' and HTF == 'buy' and UHTF == 'buy':
            if not in_long:
                print(f"Opening {self.user} {self.strat} long.  Reason: all 6 TFs buy")
                trade_id = open_trade(self.py3c, account_id=self.account_id, pair=self.pair, _type='buy')
                self.coll.update_one({'_id': self.user}, {"$set": {
                    f"{self.strat}.status.trade_id": trade_id,
                    f"{self.strat}.status.in_long": True
                }}, upsert=True)
                return
        else:
            if in_long:
                print(f"Closing {self.user} {self.strat} long")
                trade_id = self.state['status']['trade_id']
                close_trade(self.py3c, trade_id)
                return
        if DEBUG:
            print(f"Stars misaligned for {self.user} {self.strat} long, or already in deal, nothing to do")

        if UULTF == 'sell' and ULTF == 'sell' and LTF == 'sell' and MTF == 'sell' and HTF == 'sell' and UHTF == 'sell':
            if not in_short:
                print(f"Opening {self.user} {self.strat} short.  Reason: all 6 TFs sell")
                trade_id = open_trade(self.py3c, account_id=self.account_id, pair=self.pair, _type='sell')
                self.coll.update_one({'_id': self.user}, {"$set": {
                    f"{self.strat}.status.trade_id": trade_id,
                    f"{self.strat}.status.in_long": True
                }}, upsert=True)
                return
        else:
            if in_short:
                print(f"Closing {self.user} {self.strat} short")
                trade_id = self.state['status']['trade_id']
                close_trade(self.py3c, trade_id)
                return
        if DEBUG:
            print(f"Stars misaligned for {self.user} {self.strat} short, or already in deal, nothing to do")

    def run_logic_epsilon(self, alert):
        strat_in_deal = self.state['status'].get('in_long') or self.state['status'].get('in_short')

        if strat_in_deal:
            if DEBUG:
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
            if DEBUG:
                print(f"DEBUG {self.user} {self.strat} already entered this trend, nothing to do")
                return
        elif enter_long:
            print(f"Opening {self.user} {self.strat} long")
            trade_id = open_trade(self.py3c, account_id=self.account_id, pair=self.pair, _type='buy')
            self.coll.update_one({'_id': self.user}, {"$set": {
                f"{self.strat}.status.trade_id": trade_id,
                f"{self.strat}.status.in_long": True,
                f"{self.strat}.status.last_trend_entered": "long"
            }}, upsert=True)
        elif enter_short:
            print(f"Opening {self.user} {self.strat} short")
            trade_id = open_trade(self.py3c, account_id=self.account_id, pair=self.pair, _type='sell')
            self.coll.update_one({'_id': self.user}, {"$set": {
                f"{self.strat}.status.trade_id": trade_id,
                f"{self.strat}.status.in_short": True,
                f"{self.strat}.status.last_trend_entered": 'short'
            }}, upsert=True)
        else:
            print(f"{self.user} {self.strat}: change {change} is within deal threshold of {deal_threshold}, nothing to do")
            return

    def run_logic_rho(self, alert):
        strat_in_deal = self.state['status'].get('in_long') or self.state['status'].get('in_short')

        if strat_in_deal:
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
            trade_id = open_trade(self.py3c, account_id=self.account_id, pair=self.pair, _type='buy')
            self.coll.update_one({'_id': self.user}, {"$set": {
                f"{self.strat}.status.trade_id": trade_id,
                f"{self.strat}.status.in_long": True
            }}, upsert=True)
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
            trade_id = open_trade(self.py3c, account_id=self.account_id, pair=self.pair, _type='sell')
            self.coll.update_one({'_id': self.user}, {"$set": {
                f"{self.strat}.status.trade_id": trade_id,
                f"{self.strat}.status.in_short": True
            }}, upsert=True)
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




@app.route("/", methods=["GET", "POST"])
def main():
    AlertHandler(req=request)
    return "ok"


def close_trade(py3c, trade_id):
    error, data = py3c.request(entity="smart_trades_v2", action="close_by_market", action_id=trade_id)
    if error.get("error"):
        raise Exception(f"Error closing trade {trade_id}, {error['msg']}")
    return data


def open_trade(py3c, account_id, pair, _type, leverage=1, units=1, tp_pct=0.2, tp_trail=None, sl_pct=0.2):
    base_trade = get_base_trade(account_id, pair, leverage, units)
    base_trade_error, base_trade_data = py3c.request(entity="smart_trades_v2", action="new", payload=base_trade)
    if base_trade_error.get("error"):
        raise Exception(f"Error opening trade of type {_type} for account {account_id}, {base_trade_error['msg']}")

    trade_id = str(base_trade_data['id'])
    trade_entry = round(float(base_trade_data['position']['price']['value']), 2)
    tp_price = round(trade_entry * (1 + tp_pct/100))
    sl_price = round(trade_entry * (1 - sl_pct/100))

    update_trade = get_update_trade(
        trade_id=trade_id, _type=_type, units=units, tp_price=tp_price, tp_trail=tp_trail, sl_price=sl_price, sl_pct=sl_pct)
    update_trade_error, update_trade_data = py3c.request(entity="smart_trades_v2", action="new", payload=update_trade)
    if update_trade_error.get("error"):
        raise Exception(f"Error updating trade, {update_trade_error['msg']}")
    return trade_id


def get_base_trade(account_id, pair, _type, leverage, units):
    return {
        "account_id": account_id,
        "pair": pair,
        "leverage": {
            "enabled": True,
            "type": "isolated",
            "value": leverage
        },
        "position": {
            "type": _type,  # 'buy' / 'sell'
            "units": {
                "value": units
            },
            "order_type": "market"
        },
        "take_profit": {
            "enabled": False
        },
        "stop_loss": {
            "enabled": False
        }
    }


def get_update_trade(trade_id, _type, units, tp_price, sl_price, sl_pct, tp_trail=None):
    update_trade = {
        "id": trade_id,
        "position": {
            "type": _type,
            "units": {
                "value": units
            },
            "order_type": "market"
        },
        "take_profit": {
            "enabled": True,
            "steps": [
                {
                    "order_type": "market",
                    "price": {
                        "value": tp_price,
                        "type": "last"
                    },
                    "volume": 100
                }
            ]
        },
        "stop_loss": {
            "enabled": True,
            "order_type": "market",
            "conditional": {
                "price": {
                    "value": sl_price,
                    "type": "last"
                },
                "trailing": {
                    "enabled": True,
                    "percent": sl_pct
                }
            }
        }
    }
    if tp_trail:
        update_trade['take_profit']['steps'][0]['trailing'] = {
            "enabled": True,
            "percent": tp_trail
        }
    return update_trade


def send_email(to, subject, body=None):
    yagmail.SMTP('lathamfell@gmail.com', 'lrhnapmiegubspht').send(to, subject, body)


def in_order(dict):
    return json.dumps(dict, sort_keys=True)


def screen_for_str_bools(value):
    if isinstance(value, str):
        if value == 'true':
            return True
        if value == 'false':
            return False
    return value


if __name__ == '__main__':
    app.run(debug=True)
