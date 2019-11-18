import requests
import requests.auth
import base64
import time
import json
import binascii
from hashlib import sha256
from urllib.parse import urlparse
from decimal import Decimal as dec

class Pair():
    def __init__(self):
        self.ask = None
        self.bid = None
        self.day_avg_price = None
        self.day_change = None
        self.day_high = None
        self.day_low = None
        self.day_open = None
        self.day_volume_base = None
        self.day_volume_market = None
        self.id = None
        self.id_hr = None
        self.last = None
        self.spread = None

class QtradeAuth(requests.auth.AuthBase):
    def __init__(self, key):
        self.key_id, self.key = key.split(":")

    def __call__(self, req):
        # modify and return the request
        timestamp = str(int(time.time()))
        url_obj = urlparse(req.url)

        request_details = req.method + "\n"
        request_details += url_obj.path + url_obj.params + "\n"
        request_details += timestamp + "\n"

        if req.body:
            if isinstance(req.body, str):
                request_details += req.body + "\n"
            else:
                request_details += req.body.decode('utf8') + "\n"
        else:
            request_details += "\n"
        request_details += self.key
        hsh = sha256(request_details.encode("utf8")).digest()
        signature = base64.b64encode(hsh)
        req.headers.update({
            "Authorization": "HMAC-SHA256 {}:{}".format(self.key_id, signature.decode("utf8")),
            "HMAC-Timestamp": timestamp
        })
        return req


if __name__ == "__main__":
    # Create a session object to make repeated API calls easy!
    api = requests.Session()
    # Create an authenticator with your API key
    with open("secret") as authfile:
        auth_details = authfile.read()

    api.auth = QtradeAuth(auth_details)

    # Make a call to API
    res = api.get('https://api.qtrade.io/v1/user/me').json()
    print(res)

    bis_api = api.get("https://api.qtrade.io/v1/ticker/BIS_BTC").json()

    # move data to object
    bis_pair = Pair()
    bis_pair.ask = dec(bis_api["data"]["ask"])
    bis_pair.bid = dec(bis_api["data"]["bid"])
    bis_pair.day_avg_price = dec(bis_api["data"]["day_avg_price"])
    bis_pair.day_change = dec(bis_api["data"]["day_change"])
    bis_pair.day_high = dec(bis_api["data"]["day_high"])
    bis_pair.day_low = dec(bis_api["data"]["day_low"])
    bis_pair.day_open = dec(bis_api["data"]["day_open"])
    bis_pair.day_volume_base = dec(bis_api["data"]["day_volume_base"])
    bis_pair.day_volume_market = dec(bis_api["data"]["day_volume_market"])
    bis_pair.id = int(bis_api["data"]["id"])
    bis_pair.id_hr = bis_api["data"]["id_hr"]
    bis_pair.last = dec(bis_api["data"]["last"])

    bis_pair.spread = abs(bis_pair.ask - bis_pair.bid)

    print(bis_pair.spread)
    print(bis_pair.ask)
    print(bis_pair.bid)
    print(bis_pair.day_avg_price)
    print(bis_pair.day_change)
    print(bis_pair.day_high)
    print(bis_pair.day_low)
    print(bis_pair.day_open)
    print(bis_pair.day_volume_base)
    print(bis_pair.day_volume_market)
    print(bis_pair.id)
    print(bis_pair.id_hr)
    print(bis_pair.last)


