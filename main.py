from flask import Flask, request
import pymongo
import requests, hmac, hashlib
import yagmail
import json

DEBUG = False  # turn all debug messages
DEBUG2 = True  # just specific ones related to what I'm working on

app = Flask(__name__)

C3_BASE_URL = "https://api.3commas.io"
# Bot operations permissions: BOTS_WRITE, Security: SIGNED
C3_BOT_ENABLE_QUERY = "/public/api/ver1/bots/{}/enable"  # fill in bot id
C3_BOT_DISABLE_QUERY = "/public/api/ver1/bots/{}/disable"
C3_BOT_CANCEL_DEAL_QUERY = "/public/api/ver1/bots/{}/cancel_all_deals"
C3_BOT_INFO_QUERY = "/public/api/ver1/bots/{}/show"
C3_BOT_START_DEAL_QUERY = "/public/api/ver1/bots/{}/start_new_deal"
C3_BOT_MARKET_CLOSE_QUERY = "/public/api/ver1/bots/{}/panic_sell_all_deals"
C3_BOT_ENABLE_URL = C3_BASE_URL + C3_BOT_ENABLE_QUERY
C3_BOT_DISABLE_URL = C3_BASE_URL + C3_BOT_DISABLE_QUERY
C3_BOT_CANCEL_DEAL_URL = C3_BASE_URL + C3_BOT_CANCEL_DEAL_QUERY
C3_BOT_INFO_URL = C3_BASE_URL + C3_BOT_INFO_QUERY
C3_BOT_START_DEAL_URL = C3_BASE_URL + C3_BOT_START_DEAL_QUERY
C3_BOT_MARKET_CLOSE_URL = C3_BASE_URL + C3_BOT_MARKET_CLOSE_QUERY

USER_ATTR = {
    'malcolm': {
        'c3_api_key': '196c18afb3854a8a8d058ef0678a196bcf4a3a387bf146e4b3ebbcfc2ccd2d06',
        'c3_secret': b"0f845e0f203088e4d2f8674c89a00fac07a1408f755f16d7b4652259b51324b69004157e23fabe5a61ec014ee2f56a1a45fe54cf867ac7b15c6ae70591780b1c4a313a74acf7d6da3a65e452d9f30b3d566eef387448211c02e3636a80aab9ab5901e073",
        'email': 'malcerlee@gmail.com',
        'email_enabled': False,
        'strats': {
            'btc': {
                'long_bot': 4007368,
                'short_bot': 4007430,
                'logic': 'pi',
                'coin': 'btc'
            },
            'eth': {
                'long_bot': 4011262,
                'short_bot': 4011268,
                'logic': 'pi',
                'coin': 'eth'
            }
        }
    },
    'latham': {
        'c3_api_key': "0939ce229b1b4df7b000d82f6f3db6992b059536fe1c4a60aaa7982d8d78478a",
        'c3_secret': b"1e6ce831caf3a76aa87a262a21ab548375608482134e1a00718dfe03affda15ab3cd40d117919960c69b2b48c6774c58cf4992b3d247cb6cadce07205d56b55206e401b512d580abba3c670bb989ebd32d2d6795c94db7130fb75cd436fb34ea69104b21",
        'email': 'lathamfell@gmail.com',
        'email_enabled': False,
        'strats': {
            'btc1': {
                'long_bot': 4179669,
                'short_bot': 4379268,
                'logic': 'pi',
                'coin': 'btc',
            },
            'btc2': {
                'long_bot': 4501882,
                'short_bot': 4501885,
                'logic': 'pi',
                'coin': 'btc'
            },
            'btc3': {
                'long_bot': 4542082,
                'short_bot': 4542088,
                'logic': 'pi',
                'coin': 'btc'
            },
            'btc4': {
                'long_bot': 4555949,
                'short_bot': 4555970,
                'logic': 'gamma',
                'coin': 'btc'
            },
            'eth1': {
                'long_bot': 4398211,
                'short_bot': 4398205,
                'logic': 'pi',
                'coin': 'eth'
            },
            'eth2': {
                'long_bot': 4546006,
                'short_bot': 4546013,
                'logic': 'pi',
                'coin': 'eth'
            },
            'eth3': {
                'long_bot': 4546032,
                'short_bot': 4546034,
                'logic': 'omicron',
                'coin': 'eth'
            },
            'eth4': {
                'long_bot': 4555975,
                'short_bot': 4555978,
                'logic': 'alpha',
                'coin': 'eth'
            }
        }
    },
    'test': {
        'c3_api_key': "0939ce229b1b4df7b000d82f6f3db6992b059536fe1c4a60aaa7982d8d78478a",
        'c3_secret': b"1e6ce831caf3a76aa87a262a21ab548375608482134e1a00718dfe03affda15ab3cd40d117919960c69b2b48c6774c58cf4992b3d247cb6cadce07205d56b55206e401b512d580abba3c670bb989ebd32d2d6795c94db7130fb75cd436fb34ea69104b21",
        'email': 'lathamfell+test@gmail.com',
        'email_enabled': True,
        'strats': {
            #'btc': {
            #    'long_bot': 4179712,
            #    'short_bot': 4352212,
            #    'logic': 'delta'
            #}
        }
    }
}


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

            deal_status = 'idle'
            if bot_in_deal(long_bot_id, api_key, secret):
                deal_status = 'long'
            elif bot_in_deal(short_bot_id, api_key, secret):
                deal_status = 'short'

            state_str = ''
            if state:
                state_str = f"State: {in_order(state)}.  "

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
    if not strat:
        strat = _update['coin']  # backwards compatible until everyone can switch from 'coin' to 'strat' in their alerts
    conditions = [
        'UHTF', 'HTF', 'MTF', 'LTF', 'ULTF', 'UULTF', 'MA', 'MAL', 'MAS', 'HTFMAL', 'MTFMAL', 'LTFMAL',
        'HTFMAS', 'MTFMAS', 'LTFMAS'
    ]
    for condition in conditions:
        if condition in _update:
            value = _update[condition]
            if isinstance(value, str):
                # translate bool strs to bool type
                if value == 'true':
                    value = True
                elif value == 'false':
                    value = False
            # set db value
            result = coll.update_one({'_id': user}, {"$set": {f"{strat}.{condition}": value}}, upsert=True)
            if result.raw_result['nModified'] > 0:
                print(f"Direct updated {user} {strat} {condition} to {value}")
            else:
                print(f"{user} {strat} {condition} value {value} same as existing, nothing to update")
    new_state = coll.find_one({'_id': user})[strat]
    print(f"{user} {strat} state: {in_order(new_state)}")
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

    return "indicator updated"


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
        if not self.strat:
            self.strat = self.alert['coin']  # backwards compatible until everyone can switch to 'strat' in alerts
        self.condition = self.alert.get('condition')
        self.value = self.alert.get('value')
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

        if self.run_logic:
            # skip directly to logic
            self.route_logic()
            return

        # otherwise we need to update state
        user_states = self.coll.find_one({'_id': self.user})

        if user_states:
            self.state = user_states.get(self.strat)
            if DEBUG:
                print(f"DEBUG Current {self.user} {self.strat} state: {in_order(self.state)}")
        else:
            print(f"No current state found for {self.user}")

        result = self.coll.update_one({'_id': self.user}, {"$set": {f"{self.strat}.{self.condition}": self.value}}, upsert=True)
        if result.raw_result['nModified'] > 0:
            self.state = self.coll.find_one({'_id': self.user})[self.strat]
            print(f"Switched {self.user} {self.strat} {self.condition} to {self.value}. New state: {in_order(self.state)}")

            self.route_logic()
        else:
            if DEBUG:
                print(f"DEBUG {self.user} {self.strat} {self.condition} value {self.value} same as existing, nothing to update")
            pass

    def route_logic(self):
        if self.logic == 'alpha':
            self.run_logic_alpha()
            return
        elif self.logic == 'beta':
            self.run_logic_beta()
            return
        elif self.logic == 'gamma':
            self.run_logic_gamma()
            return
        elif self.logic == 'delta':
            self.run_logic_delta()
            return
        elif self.logic == 'epsilon':
            self.run_logic_epsilon()
            return
        elif self.logic == 'zeta':
            self.run_logic_zeta()
            return
        elif self.logic == 'eta':
            self.run_logic_eta()
            return
        elif self.logic == 'theta':
            self.run_logic_theta()
            return
        elif self.logic == 'iota':
            self.run_logic_iota()
            return
        elif self.logic == 'kappa':
            self.run_logic_kappa()
            return
        elif self.logic == 'lambda':
            self.run_logic_lambda()
            return
        elif self.logic == 'mu':
            self.run_logic_mu()
            return
        elif self.logic == 'nu':
            self.run_logic_nu()
            return
        elif self.logic == 'xi':
            self.run_logic_xi()
            return
        elif self.logic == 'omicron':
            self.run_logic_omicron()
            return
        elif self.logic == 'pi':
            self.run_logic_pi()
            return
        elif self.logic == '':
            print(f"No logic configured for {self.user} {self.strat}, skipping bot decisions.")
            return
        raise Exception(f"Something unexpected went wrong trying to route logic for {self.user} {self.strat}")

    def run_logic_alpha(self):
        self.state = self.coll.find_one({'_id': 'indicators'})['SuperTrend'][self.coin]
        try:
            UULTF = self.state['1m']
            MTF = self.state['15m']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        if UULTF == 'buy' and MTF == 'buy':
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long.  Reason: UULTF buy and MTF buy")
                bot_open_deal(self.long_bot, self.api_key, self.secret)
                return
        else:
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                bot_close_deal(self.long_bot, self.api_key, self.secret)
                return
        if DEBUG:
            print(f"Stars misaligned for {self.user} {self.strat} long, or already in deal, nothing to do")

        if UULTF == 'sell' and MTF == 'sell':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short.  Reason: UULTF sell and MTF sell")
                bot_open_deal(self.short_bot, self.api_key, self.secret)
                return
        else:
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                bot_close_deal(self.short_bot, self.api_key, self.secret)
                return
        if DEBUG:
            print(f"Stars misaligned for {self.user} {self.strat} short, or already in deal, nothing to do")

    def run_logic_beta(self):
        self.state = self.coll.find_one({'_id': 'indicators'})['SuperTrend'][self.coin]
        try:
            MTF = self.state['15m']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        indicatorz = self.coll.find_one({'_id': 'indicators'})
        MA_pct_per_2_bars = indicatorz['MA'][self.coin]['15m']['MA_pct_per_2_bars']

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        LONG_OPEN = self.alert['long_open']
        LONG_CLOSE = self.alert['long_close']
        SHORT_OPEN = self.alert['short_open']
        SHORT_CLOSE = self.alert['short_close']

        if long_in_deal:
            if MA_pct_per_2_bars <= LONG_CLOSE:
                print(f"Closing {self.user} {self.strat} long.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} <= {LONG_CLOSE}")
                bot_close_deal(self.long_bot, self.api_key, self.secret)
            elif MTF != 'buy':
                print(f"Closing {self.user} {self.strat} long.  Reason: MTF sell")
                bot_close_deal(self.long_bot, self.api_key, self.secret)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} in long, leaving open because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not <= {LONG_CLOSE}, and MTF buy")
        elif MTF == 'buy':
            if MA_pct_per_2_bars >= LONG_OPEN:
                print(f"Opening {self.user} {self.strat} long.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} >= {LONG_OPEN} and MTF buy")
                bot_open_deal(self.long_bot, self.api_key, self.secret)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} not opening long because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not >= {LONG_OPEN}")
        elif DEBUG:
            print(f"DEBUG {self.user} {self.strat} not opening long because MTF sell")

        if short_in_deal:
            if MA_pct_per_2_bars >= SHORT_CLOSE:
                print(f"Closing {self.user} {self.strat} short.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} >= {SHORT_CLOSE}")
                bot_close_deal(self.short_bot, self.api_key, self.secret)
            elif MTF != 'sell':
                print(f"Closing {self.user} {self.strat} short.  Reason: MTF buy")
                bot_close_deal(self.short_bot, self.api_key, self.secret)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} in short, leaving open because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not >= {SHORT_CLOSE}, and MTF sell")
        elif MTF == 'sell':
            if MA_pct_per_2_bars <= SHORT_OPEN:
                print(f"Opening {self.user} {self.strat} short.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} <= {SHORT_OPEN} and MTF sell")
                bot_open_deal(self.short_bot, self.api_key, self.secret)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} not opening short because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not <= {SHORT_OPEN}")
        elif DEBUG:
            print(f"DEBUG {self.user} {self.strat} not opening short because MTF buy")

    def run_logic_gamma(self):
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

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        if UULTF == 'buy' and ULTF == 'buy' and LTF == 'buy' and MTF == 'buy' and HTF == 'buy' and UHTF == 'buy':
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long.  Reason: all 6 TFs buy")
                bot_open_deal(self.long_bot, self.api_key, self.secret)
                return
        else:
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                bot_close_deal(self.long_bot, self.api_key, self.secret)
                return
        if DEBUG:
            print(f"Stars misaligned for {self.user} {self.strat} long, or already in deal, nothing to do")

        if UULTF == 'sell' and ULTF == 'sell' and LTF == 'sell' and MTF == 'sell' and HTF == 'sell' and UHTF == 'sell':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short.  Reason: all 6 TFs sell")
                bot_open_deal(self.short_bot, self.api_key, self.secret)
                return
        else:
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                bot_close_deal(self.short_bot, self.api_key, self.secret)
                return
        if DEBUG:
            print(f"Stars misaligned for {self.user} {self.strat} short, or already in deal, nothing to do")

    def run_logic_delta(self):
        try:
            ULTF = self.state['ULTF']
            LTF = self.state['LTF']
            MTF = self.state['MTF']
            HTF = self.state['HTF']
            UHTF = self.state['UHTF']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        if ULTF == 'long' and LTF == 'long' and MTF == 'long' and HTF == 'long' and UHTF == 'long':
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                bot_open_deal(self.long_bot, self.api_key, self.secret)

        if ULTF == 'short' and LTF == 'short' and MTF == 'short' and HTF == 'short' and UHTF == 'short':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                bot_open_deal(self.short_bot, self.api_key, self.secret)

    def run_logic_epsilon(self):
        try:
            UULTF = self.state['UULTF']
            ULTF = self.state['ULTF']
            LTF = self.state['LTF']
            MTF = self.state['MTF']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        if UULTF == 'long' and ULTF == 'long' and LTF == 'long' and MTF == 'long':
            print(f'Stars align for {self.user} {self.strat} long')
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                bot_open_deal(self.long_bot, self.api_key, self.secret)
        else:
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                bot_close_deal(self.long_bot, self.api_key, self.secret)

        if UULTF == 'short' and ULTF == 'short' and LTF == 'short' and MTF == 'short':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                bot_open_deal(self.short_bot, self.api_key, self.secret)
        else:
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                bot_close_deal(self.short_bot, self.api_key, self.secret)

    def run_logic_zeta(self):
        try:
            LTF = self.state['LTF']
            MTF = self.state['MTF']
            HTF = self.state['HTF']
            UHTF = self.state['UHTF']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        if LTF == 'long' and MTF == 'long' and HTF == 'long' and UHTF == 'long':
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                bot_open_deal(self.long_bot, self.api_key, self.secret)

        if LTF == 'short' and MTF == 'short' and HTF == 'short' and UHTF == 'short':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                bot_open_deal(self.short_bot, self.api_key, self.secret)

    def run_logic_eta(self):
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

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        if UULTF == 'long' and ULTF == 'long' and LTF == 'long' and MTF == 'long' and HTF == 'long' and UHTF == 'long':
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                bot_open_deal(self.long_bot, self.api_key, self.secret)

        if UULTF == 'short' and ULTF == 'short' and LTF == 'short' and MTF == 'short' and HTF == 'short' and UHTF == 'short':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                bot_open_deal(self.short_bot, self.api_key, self.secret)

    def run_logic_theta(self):
        try:
            MAL = self.state['MAL']
            MAS = self.state['MAS']
            MTF = self.state['MTF']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        if MTF == 'long':
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                bot_close_deal(self.short_bot, self.api_key, self.secret)
            if MAL and not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                bot_open_deal(self.long_bot, self.api_key, self.secret)
            elif not MAL and long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                bot_close_deal(self.long_bot, self.api_key, self.secret)

        if MTF == 'short':
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                bot_close_deal(self.long_bot, self.api_key, self.secret)
            if MAS and not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                bot_open_deal(self.short_bot, self.api_key, self.secret)
            elif not MAS and short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                bot_close_deal(self.short_bot, self.api_key, self.secret)

    def run_logic_iota(self):
        try:
            HTF = self.state['HTF']
            LTF = self.state['LTF']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        if HTF == 'long' and LTF == 'long':
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                bot_open_deal(self.long_bot, self.api_key, self.secret)
        elif self.condition == 'LTF' and self.value == 'short':
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                bot_close_deal(self.long_bot, self.api_key, self.secret)

        if HTF == 'short' and LTF == 'short':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                bot_open_deal(self.short_bot, self.api_key, self.secret)
        elif self.condition == 'LTF' and self.value == 'long':
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                bot_close_deal(self.short_bot, self.api_key, self.secret)

    def run_logic_kappa(self):
        try:
            MA = self.state['MA']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        if MA == 'long':
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                bot_close_deal(self.short_bot, self.api_key, self.secret)
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                bot_open_deal(self.long_bot, self.api_key, self.secret)
        if MA == 'short':
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                bot_close_deal(self.long_bot, self.api_key, self.secret)
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                bot_open_deal(self.short_bot, self.api_key, self.secret)

    def run_logic_lambda(self):
        try:
            MAL = self.state['MAL']
            MAS = self.state['MAS']
            HTF = self.state['HTF']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        if HTF == 'long':
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                bot_close_deal(self.short_bot, self.api_key, self.secret)
            if MAL and not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                bot_open_deal(self.long_bot, self.api_key, self.secret)
            elif not MAL and long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                bot_close_deal(self.long_bot, self.api_key, self.secret)

        if HTF == 'short':
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                bot_close_deal(self.long_bot, self.api_key, self.secret)
            if MAS and not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                bot_open_deal(self.short_bot, self.api_key, self.secret)
            elif not MAS and short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                bot_close_deal(self.short_bot, self.api_key, self.secret)

    def run_logic_mu(self):
        try:
            LTF = self.state['LTF']
            MTF = self.state['MTF']
            HTF = self.state['HTF']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        if LTF == 'long' and MTF == 'long' and HTF == 'long':
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                bot_open_deal(self.long_bot, self.api_key, self.secret)
        else:
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                bot_close_deal(self.long_bot, self.api_key, self.secret)

        if LTF == 'short' and MTF == 'short' and HTF == 'short':
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                bot_open_deal(self.short_bot, self.api_key, self.secret)
        else:
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                bot_close_deal(self.short_bot, self.api_key, self.secret)

    def run_logic_nu(self):
        try:
            MAL = self.state['MAL']
            MAS = self.state['MAS']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        if MAL and not MAS:
            if not long_in_deal:
                print(f"Opening {self.user} {self.strat} long")
                bot_open_deal(self.long_bot, self.api_key, self.secret)
        else:
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                bot_close_deal(self.long_bot, self.api_key, self.secret)

        if MAS and not MAL:
            if not short_in_deal:
                print(f"Opening {self.user} {self.strat} short")
                bot_open_deal(self.short_bot, self.api_key, self.secret)
        else:
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                bot_close_deal(self.short_bot, self.api_key, self.secret)

    def run_logic_xi(self):
        try:
            HTF = self.state['HTF']
            MA = self.state['MA']
        except KeyError:
            print(f"Incomplete dataset for user {self.user} {self.strat}, skipping decision")
            return "Incomplete dataset, skipping decision"

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        if MA == 'long':
            if short_in_deal:
                print(f"Closing {self.user} {self.strat} short")
                bot_close_deal(self.short_bot, self.api_key, self.secret)
            if not long_in_deal and HTF == 'long':
                print(f"Opening {self.user} {self.strat} long")
                bot_open_deal(self.long_bot, self.api_key, self.secret)
        if MA == 'short':
            if long_in_deal:
                print(f"Closing {self.user} {self.strat} long")
                bot_close_deal(self.long_bot, self.api_key, self.secret)
            if not short_in_deal and HTF == 'short':
                print(f"Opening {self.user} {self.strat} short")
                bot_open_deal(self.short_bot, self.api_key, self.secret)

    def run_logic_omicron(self):
        indicatorz = self.coll.find_one({'_id': 'indicators'})
        MA_pct_per_2_bars_LTF = indicatorz['MA'][self.coin]['13m']['MA_pct_per_2_bars']
        MA_pct_per_2_bars_MTF = indicatorz['MA'][self.coin]['15m']['MA_pct_per_2_bars']
        MA_pct_per_2_bars_HTF = indicatorz['MA'][self.coin]['17m']['MA_pct_per_2_bars']

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        LONG_OPEN = self.alert['long_open']
        LONG_CLOSE = self.alert['long_close']
        SHORT_OPEN = self.alert['short_open']
        SHORT_CLOSE = self.alert['short_close']
        if DEBUG:
            print(f"Running {self.user} {self.strat}, pcts are 13m: {MA_pct_per_2_bars_LTF}, 15m: {MA_pct_per_2_bars_MTF}, 17m: {MA_pct_per_2_bars_HTF}")

        if long_in_deal:
            if MA_pct_per_2_bars_HTF <= LONG_CLOSE or MA_pct_per_2_bars_MTF <= LONG_CLOSE or MA_pct_per_2_bars_LTF <= LONG_CLOSE:
                print(f"Closing {self.user} {self.strat} long.  Reason: HTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_HTF)} or MTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_MTF)} or LTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_LTF)} <= {LONG_CLOSE}")
                bot_close_deal(self.long_bot, self.api_key, self.secret)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} in long, leaving open because no MA pcts are <= {LONG_CLOSE}")
        else:
            if MA_pct_per_2_bars_HTF >= LONG_OPEN and MA_pct_per_2_bars_MTF >= LONG_OPEN and MA_pct_per_2_bars_LTF >= LONG_OPEN:
                print(f"Opening {self.user} {self.strat} long. Reason: HTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_HTF)} and MTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_MTF)} and LTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_LTF)} >= {LONG_OPEN}")
                bot_open_deal(self.long_bot, self.api_key, self.secret)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} not in long, not opening because a MA pct not >= {LONG_OPEN}")

        if short_in_deal:
            if MA_pct_per_2_bars_HTF >= SHORT_CLOSE or MA_pct_per_2_bars_MTF >= SHORT_CLOSE or MA_pct_per_2_bars_LTF >= SHORT_CLOSE:
                print(f"Closing {self.user} {self.strat} short.  Reason: HTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_HTF)} or MTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_MTF)} or LTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_LTF)} >= {SHORT_CLOSE}")
                bot_close_deal(self.short_bot, self.api_key, self.secret)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} in short, leaving open because no MA pcts are >= {SHORT_CLOSE}")
        else:
            if MA_pct_per_2_bars_HTF <= SHORT_OPEN and MA_pct_per_2_bars_MTF <= SHORT_OPEN and MA_pct_per_2_bars_LTF <= SHORT_OPEN:
                print(f"Opening {self.user} {self.strat} short.  Reason: HTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_HTF)} and MTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_MTF)} and LTF MA pct {'{:.2f}'.format(MA_pct_per_2_bars_LTF)} <= {SHORT_OPEN}")
                bot_open_deal(self.short_bot, self.api_key, self.secret)
            elif DEBUG:
                print(f"DEBUG {self.user} {self.strat} not in short, not opening because one MA pct not <= {SHORT_OPEN}")

    def run_logic_pi(self):
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

        long_in_deal = bot_in_deal(self.long_bot, self.api_key, self.secret)
        short_in_deal = bot_in_deal(self.short_bot, self.api_key, self.secret)

        LONG_OPEN = self.alert['long_open']
        LONG_CLOSE = self.alert['long_close']
        SHORT_OPEN = self.alert['short_open']
        SHORT_CLOSE = self.alert['short_close']

        if long_in_deal:
            if MA_pct_per_2_bars <= LONG_CLOSE:
                print(f"Closing {self.user} {self.strat} long.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} <= {LONG_CLOSE}")
                bot_close_deal(self.long_bot, self.api_key, self.secret)
            elif DEBUG or DEBUG2:
                print(f"DEBUG {self.user} {self.strat} in long, leaving open because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not <= {LONG_CLOSE}")
        elif last_trend_entered == 'long':
            if DEBUG or DEBUG2:
                print(f"DEBUG {self.user} {self.strat} long staying out until trend exhaustion")
        elif MA_pct_per_2_bars >= LONG_OPEN:
            print(f"Opening {self.user} {self.strat} long.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} >= {LONG_OPEN}")
            bot_open_deal(self.long_bot, self.api_key, self.secret)
            last_trend_entered = 'long'
        elif DEBUG or DEBUG2:
            print(f"DEBUG {self.user} {self.strat} not opening long because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not >= {LONG_OPEN}")

        if short_in_deal:
            if MA_pct_per_2_bars >= SHORT_CLOSE:
                print(f"Closing {self.user} {self.strat} short.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} >= {SHORT_CLOSE}")
                bot_close_deal(self.short_bot, self.api_key, self.secret)
            elif DEBUG or DEBUG2:
                print(f"DEBUG {self.user} {self.strat} in short, leaving open because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not >= {SHORT_CLOSE}")
        elif last_trend_entered == 'short':
            if DEBUG or DEBUG2:
                print(f"DEBUG {self.user} {self.strat} short staying out until trend exhaustion")
        elif MA_pct_per_2_bars <= SHORT_OPEN:
            print(f"Opening {self.user} {self.strat} short.  Reason: MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} <= {SHORT_OPEN}")
            bot_open_deal(self.short_bot, self.api_key, self.secret)
            last_trend_entered = 'short'
        elif DEBUG or DEBUG2:
            print(f"DEBUG {self.user} {self.strat} not opening short because MA pct {'{:.2f}'.format(MA_pct_per_2_bars)} not <= {SHORT_OPEN}")

        self.coll.update_one({'_id': self.user}, {"$set": {
            f"{self.strat}.last_trend_entered": last_trend_entered
        }}, upsert=True)


@app.route("/", methods=["GET", "POST"])
def main():
    AlertHandler(req=request)
    return "ok"


def turn_on_bot(bot_id, api_key, secret):
    execute_bot_post_request(bot_id=bot_id, query=C3_BOT_ENABLE_QUERY, url=C3_BOT_ENABLE_URL, api_key=api_key, secret=secret)


def turn_off_bot(bot_id, api_key, secret):
    execute_bot_post_request(bot_id=bot_id, query=C3_BOT_DISABLE_QUERY, url=C3_BOT_DISABLE_URL, api_key=api_key, secret=secret)


def cancel_deal(bot_id, api_key, secret):
    execute_bot_post_request(bot_id=bot_id, query=C3_BOT_CANCEL_DEAL_QUERY, url=C3_BOT_CANCEL_DEAL_URL, api_key=api_key, secret=secret)


def bot_in_deal(bot_id, api_key, secret):
    r = execute_bot_get_request(bot_id=bot_id, query=C3_BOT_INFO_QUERY, url=C3_BOT_INFO_URL, api_key=api_key, secret=secret)
    data = r.json()
    return data['active_deals_count'] > 0


def bot_open_deal(bot_id, api_key, secret):
    execute_bot_post_request(bot_id=bot_id, query=C3_BOT_START_DEAL_QUERY, url=C3_BOT_START_DEAL_URL, api_key=api_key, secret=secret)


def bot_close_deal(bot_id, api_key, secret):
    execute_bot_post_request(bot_id=bot_id, query=C3_BOT_MARKET_CLOSE_QUERY, url=C3_BOT_MARKET_CLOSE_URL, api_key=api_key, secret=secret)


def execute_bot_post_request(bot_id, query, url, api_key, secret):
    payload = {"bot_id": bot_id, "api_key": "XXXXXX", "secret": "YYYYYY"}
    total_params = (query.format(bot_id) + f"?bot_id={bot_id}&api_key=XXXXXX&secret=YYYYYY").encode('utf-8')
    sig = hmac.new(secret, total_params, hashlib.sha256).hexdigest()
    headers = {"APIKEY": api_key, "Signature": sig}
    url = url.format(bot_id)
    r = requests.post(url, headers=headers, params=payload)
    if r.status_code not in [200, 201]:
        raise Exception(f"Error sending command to 3Commas. Code: {r.status_code}, {r.text}")
    return r


def execute_bot_get_request(bot_id, query, url, api_key, secret):
    payload = {"bot_id": bot_id, "api_key": "XXXXXX", "secret": "YYYYYY"}
    total_params = (query.format(bot_id) + f"?bot_id={bot_id}&api_key=XXXXXX&secret=YYYYYY").encode('utf-8')
    sig = hmac.new(secret, total_params, hashlib.sha256).hexdigest()
    headers = {"APIKEY": api_key, "Signature": sig}
    url = url.format(bot_id)
    r = requests.get(url, headers=headers, params=payload)
    if r.status_code not in [200, 201]:
        raise Exception(f"Error sending command to 3Commas. Code: {r.status_code}, {r.text}")
    return r


def send_email(to, subject, body=None):
    yagmail.SMTP('lathamfell@gmail.com', 'lrhnapmiegubspht').send(to, subject, body)


def in_order(dict):
    return json.dumps(dict, sort_keys=True)


if __name__ == '__main__':
    app.run(debug=True)
