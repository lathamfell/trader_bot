Deploy:

* Ensure requirements.txt is up to date: `pip3 freeze > requirements.txt`.
* Ensure gcloud CLI and Google App Engine SDK are installed on host.
* Open a terminal (like GitBash) that can run gcloud.
* Ensure `gcloud init` has been run, with proper google account and project configured.
  This project is norse-botany-313902.
* Navigate to this dir (contains app.yaml).
* `gcloud app deploy --version 1`.
* NOTE: if substantive change made to app logic or TradingView input alerts, `db_flusher.py` should be run after deployment is complete to reset app state.
  

TradingView alerts:
* Any indicator or condition can be used, the only important datapoints from the bot
perspective is whether the signal is "buy" or "sell" and what the timeframe is.
* Alerts should be created to buy and sell on low, medium and high timeframes.  Six alerts total.
* Each alert should send the data in this format:
  
`{"user": "latham", "strat": "btc", "condition": "LTF", "value": "long"}`
  
`{"user": "latham", "strat": "eth", "condition": "MTF", "value": "short"}`
  
`{"user": "latham", "strat": "xrp", "condition": "HTF", "value": "short"}`

`{"user": "malcolm", "strat": "ltc", "condition": "VTL", "value": true}`

* 'user' must be a user whose 3Commas API information has been included in the app config.
* 'coin' must be a coin whose associated bot ids have been included in the app config.  
* 'condition' must be one of 'LTF', 'MTF', 'HTF', or 'VTL'.
* 'value' must be 'long' or 'short' for the LTF/MTF/HTF, or true or false for VTL.
* The webhook is:
* `https://norse-botany-313902.wl.r.appspot.com`

Development:
* Activate venv: `.\venv\Scripts\activate.bat`

DB Update:
https://tinyurl.com/23h3x4rm/update
{"user": "latham", "strat": "eth2", "MTF": "short" }

Optionally, add expiration:
{"user": "latham", "strat": "eth2", "MTF": "short", "expiration": 1800 }
