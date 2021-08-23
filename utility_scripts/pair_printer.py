import json

from alphabot.config import USER_ATTR
from alphabot.py3cw.request import Py3CW


def main():
    # change this to whatever you need
    user = "latham"

    api_key = USER_ATTR[user]["c3_api_key"]
    secret = USER_ATTR[user]["c3_secret"]
    py3c = Py3CW(key=api_key, secret=secret)

    # bybit market code is 'bybit'
    error, data = py3c.request(entity="accounts", action="market_pairs", payload={"market_code": "bybit"})
    print(json.dumps(data, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
