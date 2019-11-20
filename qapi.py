from dateutil import parser
from datetime import datetime
import requests
import requests.auth
import base64
import time
from hashlib import sha256
from urllib.parse import urlparse
from decimal import Decimal as dec
from decimal import getcontext, Context, Overflow, DivisionByZero, InvalidOperation, ROUND_HALF_EVEN
import json

getcontext()
Context(prec=8, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999,
        capitals=1, clamp=0, flags=[], traps=[Overflow, DivisionByZero,
        InvalidOperation])

def percentage_in(individual, whole):
    return (dec(list(whole).count(individual) / dec(len(whole)))) * 100

def percentage(percent, whole):
    return dec(percent) * dec(whole) / 100

class Order:
    def __init__(self):
        self.id = None
        self.market_amount = None
        self.market_amount_remaining = None
        self.created_at = None
        self.price = None
        self.order_type = None
        self.market_id = None
        self.open = None
        self.trades = None

class PairOrders:
    def __init__(self):
        self.base_balance = None
        self.closed_orders = None
        self.market_balance = None
        self.open_orders = None
        

class PairMarket:
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
            "Authorization": f"HMAC-SHA256 {self.key_id}:{signature.decode()}",
            "HMAC-Timestamp": timestamp
        })
        return req

def age(timestamp):
    timestamp_ISO_8601 = parser.isoparse(timestamp)
    epoch_ts = datetime.timestamp(timestamp_ISO_8601)
    return int(time.time() - epoch_ts)

if __name__ == "__main__":
    trade_currency_id = 20
    trade_currency = "BIS"
    trade_pair = "BIS_BTC"
    trade_amount = 8
    trade_order_ttl = 30
    #trade_price_percentage = 5

    # Create a session object to make repeated API calls easy!
    api = requests.Session()
    # Create an authenticator with your API key
    with open("secret") as authfile:
        auth_details = authfile.read()

    with open("config.json") as configfile:
        config = json.loads(configfile.read())

    api.auth = QtradeAuth(auth_details)

    # Make a call to API
    res = api.get('https://api.qtrade.io/v1/user/me').json()
    print(res)

    market_api = api.get(f"https://api.qtrade.io/v1/ticker/{trade_pair}").json()

    # move data to object
    pair_market = PairMarket()
    
    
    pair_market.ask = dec(market_api["data"]["ask"])
    pair_market.bid = dec(market_api["data"]["bid"])
    pair_market.day_avg_price = dec(market_api["data"]["day_avg_price"])
    pair_market.day_change = dec(market_api["data"]["day_change"])
    pair_market.day_high = dec(market_api["data"]["day_high"])
    pair_market.day_low = dec(market_api["data"]["day_low"])
    pair_market.day_open = dec(market_api["data"]["day_open"])
    pair_market.day_volume_base = dec(market_api["data"]["day_volume_base"])
    pair_market.day_volume_market = dec(market_api["data"]["day_volume_market"])
    pair_market.id = int(market_api["data"]["id"])
    pair_market.id_hr = market_api["data"]["id_hr"]
    pair_market.last = dec(market_api["data"]["last"])

    pair_market.day_spread = dec(abs(pair_market.day_low - pair_market.day_high))

    print(pair_market.spread)
    print(pair_market.ask)
    print(pair_market.bid)
    print(pair_market.day_avg_price)
    print(pair_market.day_change)
    print(pair_market.day_high)
    print(pair_market.day_low)
    print(pair_market.day_open)
    print(pair_market.day_volume_base)
    print(pair_market.day_volume_market)
    print(pair_market.id)
    print(pair_market.id_hr)
    print(pair_market.last)
    print(pair_market.day_spread)

    order_api = api.get(f"https://api.qtrade.io/v1/user/market/{trade_pair}").json()
    pair_orders = PairOrders()

    pair_orders.base_balance = order_api["data"]["base_balance"]
    pair_orders.closed_orders = order_api["data"]["closed_orders"]
    pair_orders.market_balance = order_api["data"]["market_balance"]
    pair_orders.open_orders = order_api["data"]["open_orders"]

    print(pair_orders.base_balance)
    print(pair_orders.closed_orders)
    print(pair_orders.market_balance)
    print(pair_orders.open_orders)

    while True:
        #place a sell order
        balances = api.get("https://api.qtrade.io/v1/user/balances").json()
        print(balances)

        for balance in balances["data"]["balances"]:
            #print(balance)
            if balance["currency"] == trade_currency:
                #print(balance["balance"])
                if float(balance["balance"]) > trade_amount:

                    #sell order
                    #discount = percentage(trade_price_percentage, pair_market.bid)
                    req = {'amount': str(trade_amount),
                           'market_id': trade_currency_id,
                           'price': '%.8f' % pair_market.ask}
                    result = api.post("https://api.qtrade.io/v1/user/sell_limit", json=req).json()
                    print(result)
                else:
                    print(f"Insufficient balance for {trade_currency}")
        #place a sell order

        #go through orders
        for order in pair_orders.open_orders:
            #print(order["created_at"])
            order_id = int(order["id"])
            print(order_id)
            age_of_order = age(order["created_at"])
            if age_of_order > trade_order_ttl:
                print(f"Order {order_id} is too old ({age_of_order}), deleting")

                req = {'id': order_id}
                result = api.post("https://api.qtrade.io/v1/user/cancel_order", json=dict(req))
                print(result)
            else:
                print(f"Keeping order {order_id} in place, only {age_of_order} seconds old")
        #go through orders

        time.sleep(15)