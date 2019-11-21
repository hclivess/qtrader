from dateutil import parser
import time
from datetime import datetime
from decimal import Decimal as dec
from decimal import getcontext, Context, Overflow, DivisionByZero, InvalidOperation, ROUND_HALF_EVEN
import json
import requests
from auth import QtradeAuth

getcontext()
Context(prec=8, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999,
        capitals=1, clamp=0, flags=[], traps=[Overflow, DivisionByZero,
        InvalidOperation])

def part_percentage(part, whole):
    return dec(100.0) * part/whole

def load_credentials():
    with open("secret") as authfile:
        return authfile.read()

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

class Config:
    def __init__(self, currency, id, sell_amount, buy_amount, ttl, spread_pct_min):
        self.currency_id = 20
        self.currencies = [f"{currency}"]
        self.pair = f"{currency}_BTC"
        self.sell_amount = 16
        self.buy_amount = 12
        self.order_ttl = 240
        self.spread_pct_min = 1
        # trade_price_percentage = 5
        self.orders_placed = []
        self.market_api = api.get(f"https://api.qtrade.io/v1/ticker/{self.pair}").json()

def age(timestamp):
    timestamp_ISO_8601 = parser.isoparse(timestamp)
    epoch_ts = datetime.timestamp(timestamp_ISO_8601)
    return int(time.time() - epoch_ts)

if __name__ == "__main__":


    # Create a session object to make repeated API calls easy!
    api = requests.Session()
    # Create an authenticator with your API key

    with open("config.json") as configfile:
        config = json.loads(configfile.read())

    api.auth = QtradeAuth(load_credentials())

    conf = Config(currency="BIS", 
                  id=20, 
                  sell_amount=18, 
                  buy_amount=12,
                  ttl=120, 
                  spread_pct_min=1)
    
    while True:
        res = api.get('https://api.qtrade.io/v1/user/me').json()
        print(res)

        try:
            # Make a call to API
            # move data to object
            pair_market = PairMarket()


            pair_market.ask = dec(conf.market_api["data"]["ask"])
            pair_market.bid = dec(conf.market_api["data"]["bid"])
            pair_market.day_avg_price = dec(conf.market_api["data"]["day_avg_price"])
            pair_market.day_change = dec(conf.market_api["data"]["day_change"])
            pair_market.day_high = dec(conf.market_api["data"]["day_high"])
            pair_market.day_low = dec(conf.market_api["data"]["day_low"])
            pair_market.day_open = dec(conf.market_api["data"]["day_open"])
            pair_market.day_volume_base = dec(conf.market_api["data"]["day_volume_base"])
            pair_market.day_volume_market = dec(conf.market_api["data"]["day_volume_market"])
            pair_market.id = int(conf.market_api["data"]["id"])
            pair_market.id_hr = conf.market_api["data"]["id_hr"]
            pair_market.last = dec(conf.market_api["data"]["last"])

            pair_market.day_spread = dec(abs(pair_market.day_low - pair_market.day_high))

            print(pair_market.spread)
            print("ask", pair_market.ask)
            print("bid", pair_market.bid)
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
            print("day_spread", pair_market.day_spread)

            spread_percentage = 100 - part_percentage(pair_market.bid, pair_market.ask)
            print("spread_percentage", '%.8f' % spread_percentage)

            order_api = api.get(f"https://api.qtrade.io/v1/user/market/{conf.pair}").json()
            pair_orders = PairOrders()

            pair_orders.base_balance = order_api["data"]["base_balance"]
            pair_orders.closed_orders = order_api["data"]["closed_orders"]
            pair_orders.market_balance = order_api["data"]["market_balance"]
            pair_orders.open_orders = order_api["data"]["open_orders"]

            print(pair_orders.base_balance)
            print(pair_orders.closed_orders)
            print(pair_orders.market_balance)
            print(pair_orders.open_orders)

            if spread_percentage >= conf.spread_pct_min:
                #place a sell order
                balances = api.get("https://api.qtrade.io/v1/user/balances").json()
                print(balances)

                for balance in balances["data"]["balances"]:
                    #print(balance)
                    if balance["currency"] in conf.currencies:
                        #print(balance["balance"])
                        if float(balance["balance"]) > conf.sell_amount:

                            #sell order
                            #discount = percentage(trade_price_percentage, pair_market.bid)
                            req = {'amount': str(conf.sell_amount),
                                   'market_id': conf.currency_id,
                                   'price': '%.8f' % pair_market.ask}
                            result = api.post("https://api.qtrade.io/v1/user/sell_limit", json=req).json()
                            print(result)
                            print(f"Placed sell order {result['data']['order']['id']}")
                            conf.orders_placed.append(result['data']['order']['id'])
                        else:
                            print(f"Insufficient balance for {balance['currency']}")
                #place a sell order

                # place a buy order
                balances = api.get("https://api.qtrade.io/v1/user/balances").json()
                print(balances)

                for balance in balances["data"]["balances"]:
                    # print(balance)
                    if balance["currency"] == "BTC":
                        # print(balance["balance"])
                        if float(balance["balance"]) > conf.buy_amount * pair_market.bid:  # if one can afford to buy trade_buy_amount

                            # sell order
                            # discount = percentage(trade_price_percentage, pair_market.bid)
                            req = {'amount': str(conf.buy_amount),
                                   'market_id': conf.currency_id,
                                   'price': '%.8f' % pair_market.bid}
                            result = api.post("https://api.qtrade.io/v1/user/buy_limit", json=req).json()
                            print(result)
                            print(f"Placed buy order {result['data']['order']['id']}")
                            conf.orders_placed.append(result['data']['order']['id'])
                        else:
                            print(f"Insufficient balance for {balance['currency']}, only {balance['balance']}")
                # place a buy order
            else:
                print("Skipping orders, spread too small")

            #go through orders
            for order in pair_orders.open_orders:
                #print(order["created_at"])
                order_id = int(order["id"])
                print(order_id)
                age_of_order = age(order["created_at"])
                if age_of_order > conf.order_ttl:
                    print(f"Order {order_id} is too old ({age_of_order}), deleting")

                    req = {'id': order_id}
                    result = api.post("https://api.qtrade.io/v1/user/cancel_order", json=dict(req))
                    print(result)
                    conf.orders_placed.remove(order_id)
                else:
                    print(f"Keeping order {order_id} in place, only {age_of_order} seconds old")
            #go through orders

            time.sleep(60)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)