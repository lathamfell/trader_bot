import json

from config import USER_ATTR
from py3cw.request import Py3CW


def main():
    # change this to whatever you need
    user = 'malcolm'

    api_key = USER_ATTR[user]['c3_api_key']
    secret = USER_ATTR[user]['c3_secret']
    py3c = Py3CW(key=api_key, secret=secret)

    error, data = py3c.request(entity="accounts", action="")
    print(json.dumps(data, indent=4, sort_keys=True))
    for acct in data:
        print(f"Account {acct['name']}: {acct['id']}")


if __name__ == '__main__':
    main()
