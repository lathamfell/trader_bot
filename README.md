Deploy:

* Ensure requirements.txt is up to date: `pip3 freeze > requirements.txt`.
* Ensure gcloud CLI and Google App Engine SDK are installed on host.
* Open a terminal (like GitBash) that can run gcloud.
* Ensure `gcloud init` has been run, with proper google account and project configured.
  This project is norse-botany-313902.
* Navigate to this dir (contains app.yaml).
* `gcloud app deploy --version 1`.
* NOTE: if substantive change made to app logic or TradingView input alerts, `db_flusher.py` should be run after deployment is complete to reset app state.

To connect to BetaBot:
Navigate to location of pem file. (~/Documents on Chronos PC)
`ssh -i "alphabot-aws-key-pair.pem" ubuntu@ec2-100-25-132-178.compute-1.amazonaws.com`
To kick off BetaBot:
`cd /home/betabot`
`nohup python3 -u main.py &`
To monitor BetaBot:
`tail -F nohup.out` in the same directory.
To stop BetaBot:
`pgrep -lf python`
`kill <pid>`

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

Direct condition update:
{ "route": "condition_update", "user": "latham", "strat": "eth5", "conditions": {"UULTF": "buy", "UHTF": "buy" } }

Config update:
{"route": "config_update", "user": "latham", "strat": "eth5", "config": {"tp_pct": 0.4, "tp_trail": null, "sl_pct": 0.4, "leverage": 2, "units": 2 }}
