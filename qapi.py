from qtrade_client.api import QtradeAPI
import json
import time
from datetime import datetime
from decimal import Decimal as dec
from decimal import (
    getcontext,
    Context,
    Overflow,
    DivisionByZero,
    InvalidOperation,
    ROUND_HALF_EVEN,
)

import requests
from dateutil import parser

from auth import QtradeAuth

getcontext()
Context(
    prec=8,
    rounding=ROUND_HALF_EVEN,
    Emin=-999999,
    Emax=999999,
    capitals=1,
    clamp=0,
    flags=[],
    traps=[Overflow, DivisionByZero, InvalidOperation],
)


def part_percentage(part, whole):
    return dec(100.0) * part / whole


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
    def __init__(self, configuration):
        self.ask = dec(conf.market_api["data"]["ask"])
        self.bid = dec(conf.market_api["data"]["bid"])
        self.spread = dec(abs(self.ask - self.bid))

        self.day_avg_price = dec(conf.market_api["data"]["day_avg_price"])
        self.day_change = dec(conf.market_api["data"]["day_change"])
        self.day_high = dec(conf.market_api["data"]["day_high"])
        self.day_low = dec(conf.market_api["data"]["day_low"])
        self.day_open = dec(conf.market_api["data"]["day_open"])
        self.day_volume_base = dec(conf.market_api["data"]["day_volume_base"])
        self.day_volume_market = dec(conf.market_api["data"]["day_volume_market"])
        self.id = int(conf.market_api["data"]["id"])
        self.id_hr = conf.market_api["data"]["id_hr"]
        self.last_price = dec(conf.market_api["data"]["last"])
        self.day_spread = dec(abs(self.day_high - self.day_low))
        self.spread_percentage = 100 - part_percentage(self.bid, self.ask)


class Balances:
    def __init__(self):
        pass


class Config:
    def __init__(
        self,
        name,
        sell_amount,
        buy_amount,
        ttl,
        spread_pct_min,
        price_adjustment,
        max_buy_price,
        min_sell_price,
    ):
        self.orders_placed = []
        self.name = name
        self.pair = f"{name}_BTC"
        self.sell_amount = sell_amount
        self.buy_amount = buy_amount
        self.order_ttl = ttl
        self.spread_pct_min = spread_pct_min
        self.market_api = api.get(f"https://api.qtrade.io/v1/ticker/{self.pair}").json()
        self.currency_id = self.market_api["data"]["id"]
        self.price_adjustment = price_adjustment
        print("market_api", self.market_api)
        self.max_buy_price = max_buy_price
        self.min_sell_price = min_sell_price

    def count_orders(self):
        self.orders_count = len(self.orders_placed)
        return self.orders_count


def age(timestamp):
    timestamp_ISO_8601 = parser.isoparse(timestamp)
    epoch_ts = datetime.timestamp(timestamp_ISO_8601)
    return int(time.time() - epoch_ts)


def pick_currency(currency_list, currency_name):
    for entry in currency_list["data"]["balances"]:
        if entry["currency"] == currency_name:
            return entry


if __name__ == "__main__":

    # Create a session object to make repeated API calls easy!
    api = requests.Session()
    # Create an authenticator with your API key

    api.auth_native = QtradeAPI("https://api.qtrade.io", key=load_credentials())  # use in the future
    api.auth = QtradeAuth(load_credentials())

    # load currencies
    active_currencies = []
    with open("config.json") as confile:
        confile_contents = json.loads(confile.read())
        for currency in confile_contents:
            print(f"Loaded {currency}")

            active_currencies.append(
                Config(
                    name=currency["name"],
                    sell_amount=currency["sell_amount"],
                    buy_amount=currency["buy_amount"],
                    ttl=currency["ttl"],
                    spread_pct_min=currency["spread_pct_min"],
                    price_adjustment=dec(currency["price_adjustment"]),
                    max_buy_price=currency["max_buy_price"],
                    min_sell_price=currency["min_sell_price"],
                )
            )

    # load currencies

    while True:
        me = api.get("https://api.qtrade.io/v1/user/me").json()
        print(me)

        for conf in active_currencies:
            try:
                print(f"Working on {conf.pair}")
                # Make a call to API
                # move data to object
                pair_market = PairMarket(conf)

                print("spread", "%.8f" % pair_market.spread)
                print("ask", pair_market.ask)
                print("bid", pair_market.bid)
                print("day_avg_price", pair_market.day_avg_price)
                print("day_change", pair_market.day_change)
                print("day_high", pair_market.day_high)
                print("day_low", pair_market.day_low)
                print("day_open", pair_market.day_open)
                print("day_volume_base", pair_market.day_volume_base)
                print("day_volume_market", pair_market.day_volume_market)
                print("id", pair_market.id)
                print("id_hr", pair_market.id_hr)
                print("last_price", pair_market.last_price)
                print("day_spread", pair_market.day_spread)
                print("spread_percentage", "%.8f" % pair_market.spread_percentage)

                order_api = api.get(
                    f"https://api.qtrade.io/v1/user/market/{conf.pair}"
                ).json()
                pair_orders = PairOrders()

                pair_orders.base_balance = order_api["data"]["base_balance"]
                pair_orders.closed_orders = order_api["data"]["closed_orders"]
                pair_orders.market_balance = order_api["data"]["market_balance"]
                #pair_orders.open_orders = order_api["data"]["open_orders"]  # old way
                pair_orders.open_orders = api.auth_native.orders(open=True)

                print(pair_orders.base_balance)
                print(pair_orders.closed_orders)
                print(pair_orders.market_balance)
                print(pair_orders.open_orders)

                if pair_market.spread_percentage < conf.spread_pct_min:
                    print(
                        f"Not adding new orders, spread of {pair_market.spread_percentage} too small"
                    )

                else:
                    balances = api.get("https://api.qtrade.io/v1/user/balances").json()
                    print(balances)

                    # place a sell order
                    if pair_market.ask <= conf.min_sell_price:
                        print("Market price too low to sell now")
                    elif conf.sell_amount <= 0:
                        print(
                            f"Not configured to sell (sell amount to {conf.sell_amount})"
                        )

                    else:

                        c = pick_currency(balances, conf.name)
                        # print(balance["balance"])
                        if float(c["balance"]) > conf.sell_amount:

                            # sell order
                            req = {
                                "amount": str(conf.sell_amount),
                                "market_id": conf.currency_id,
                                "price": "%.8f"
                                % (pair_market.ask - conf.price_adjustment),
                            }
                            result = api.post(
                                "https://api.qtrade.io/v1/user/sell_limit", json=req
                            ).json()
                            print(result)
                            order_id = result["data"]["order"]["id"]
                            print(f"Placed sell order {order_id}")
                            conf.orders_placed.append(order_id)
                        else:
                            print(
                                f"Insufficient balance ({c['balance']}) for {c['currency']} ({conf.buy_amount} units)"
                            )

                    # place a sell order

                    # place a buy order
                    if pair_market.bid >= conf.max_buy_price:
                        print("Market price too high to buy now")
                    elif conf.buy_amount <= 0:
                        print(f"Not configured to buy (buy set to {conf.buy_amount})")
                    else:
                        c = pick_currency(balances, "BTC")

                        # print(balance["balance"])
                        if (
                            float(c["balance"]) > conf.buy_amount * pair_market.bid
                        ):  # if one can afford to buy trade_buy_amount

                            # sell order
                            # discount = percentage(trade_price_percentage, pair_market.bid)
                            req = {
                                "amount": str(conf.buy_amount),
                                "market_id": conf.currency_id,
                                "price": "%.8f"
                                % (pair_market.bid + conf.price_adjustment),
                            }

                            result = api.post(
                                "https://api.qtrade.io/v1/user/buy_limit", json=req
                            ).json()
                            print(result)
                            order_id = int(result["data"]["order"]["id"])
                            print(f"Placed buy order {order_id}")
                            conf.orders_placed.append(order_id)
                        else:
                            print(
                                f"Insufficient balance ({c['balance']}) for {c['currency']} ({conf.buy_amount} orders)"
                            )

                    # place a buy order

                # go through orders
                for order in pair_orders.open_orders:
                    # print(order["created_at"])
                    order_id = int(order["id"])
                    age_of_order = age(order["created_at"])
                    if age_of_order > conf.order_ttl:
                        print(f"Order {order_id} is too old ({age_of_order}), deleting")

                        req = {"id": order_id}
                        result = api.post(
                            "https://api.qtrade.io/v1/user/cancel_order", json=dict(req)
                        )
                        print(result)
                        if (
                            order_id in conf.orders_placed
                        ):  # if it has not been placed by someone else
                            conf.orders_placed.remove(order_id)
                    else:
                        print(
                            f"Keeping order {order_id} in place, only {age_of_order} seconds old"
                        )
                # go through orders

                print(f"Our orders: {conf.orders_placed}")
                print(f"Number of our orders: {conf.count_orders()}")

            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)

        time.sleep(60)
