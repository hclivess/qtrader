from qtrade_client.api import QtradeAPI
import random
import json
import time
import os
import sys
from log import Logger
from datetime import datetime

import requests
from dateutil import parser

from auth import QtradeAuth

DEBUG = False
DEMO = False
DEMO_MARKETS = ["NYZO", "BIS"]

log_obj = Logger("qtrader.log", "WARNING")
log = log_obj.logger


def part_percentage(part, whole):
    return float(100.0) * part / whole


def load_credentials():
    if os.path.exists("secret"):
        with open("secret") as authfile:
            return authfile.read()
    else:
        while True:
            with open("secret", "w") as authfile:
                auth = input("Enter your qTrade authentication data: ")
                if ":" in auth:
                    authfile.write(auth)
                    return auth
                else:
                    pass


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
        self.api = api.get(
            f"https://api.qtrade.io/v1/user/market/{conf.pair}"
        ).json()

        self.base_balance = self.api["data"]["base_balance"]
        self.closed_orders = self.api["data"]["closed_orders"]
        self.market_balance = self.api["data"]["market_balance"]
        self.open_orders = api.auth_native.orders(open=True)


class PairMarket:
    def __init__(self, configuration):
        self.ask = float(conf.market_api["data"]["ask"])
        self.bid = float(conf.market_api["data"]["bid"])
        self.spread = float(abs(self.ask - self.bid))

        self.day_avg_price = float(conf.market_api["data"]["day_avg_price"])
        self.day_change = float(conf.market_api["data"]["day_change"])
        self.day_high = float(conf.market_api["data"]["day_high"])
        self.day_low = float(conf.market_api["data"]["day_low"])
        self.day_open = float(conf.market_api["data"]["day_open"])
        self.day_volume_base = float(conf.market_api["data"]["day_volume_base"])
        self.day_volume_market = float(conf.market_api["data"]["day_volume_market"])
        self.id = int(conf.market_api["data"]["id"])
        self.id_hr = conf.market_api["data"]["id_hr"]
        self.last_price = float(conf.market_api["data"]["last"])
        self.day_spread = float(abs(self.day_high - self.day_low))
        self.spread_pct = 100 - part_percentage(self.bid, self.ask)


def pick_currency(balances_dict, currency_name):

    for entry in balances_dict["data"]["balances"]:
        if entry["currency"] == currency_name:
            return Balance(entry)

    else:
        entry = {"currency": currency_name, "balance": 0}
        return Balance(entry)


class Balance:
    def __init__(self, balance_dict):
        self.name = balance_dict["currency"]
        self.balance = float(balance_dict["balance"])


class Config:
    def __init__(self, **kwargs):
        self.orders_placed = []
        self.name = kwargs["name"]
        self.pair = f"{kwargs['name']}_BTC"
        if DEMO:
            self.sell_amount = 0
        else:
            self.sell_amount = float(kwargs["sell_amount"])
        self.buy_amount = float(kwargs["buy_amount"])
        self.buy_longevity = int(kwargs["buy_longevity"])
        self.sell_longevity = int(kwargs["sell_longevity"])
        self.spread_pct_min = float(kwargs["spread_pct_min"])
        self.market_api = None
        self.refresh_api()
        self.market_id = self.market_api["data"]["id"]
        self.price_adjustment = float(kwargs["price_adjustment"])
        log.warning("market_api", self.market_api)
        self.max_buy_price = float(kwargs["max_buy_price"])
        self.min_sell_price = float(kwargs["min_sell_price"])
        self.last_refreshed = None
        self.max_stash = float(kwargs["max_stash"])
        self.min_stash = float(kwargs["min_stash"])
        self.random_size = float(kwargs["random_size"])
        self.end_pause = float(kwargs["end_pause"])

    def count_orders(self):
        self.orders_count = len(self.orders_placed)
        return self.orders_count

    def refresh_api(self):
        self.last_refreshed = time.time()
        self.market_api = api.get(f"https://api.qtrade.io/v1/ticker/{self.pair}").json()


def age(timestamp):
    timestamp_ISO_8601 = parser.isoparse(timestamp)
    epoch_ts = datetime.timestamp(timestamp_ISO_8601)
    return int(time.time() - epoch_ts)


def buy(conf, pair_market):
    # place a buy order
    log.warning("Checking to place a buy order")
    if pair_market.bid >= conf.max_buy_price:
        log.warning("Market price too high to buy now")
    elif conf.buy_amount <= 0:
        log.warning(f"Not configured to buy (buy set to {conf.buy_amount})")

    else:
        btc = pick_currency(balances, "BTC")
        altcoin = pick_currency(balances, conf.name)
        random_value = randomize(conf.random_size)
        buy_value = conf.buy_amount + random_value
        final_price = pair_market.bid + conf.price_adjustment

        if altcoin.balance >= conf.max_stash:
            log.warning("Maximum stash reached, will not create new buy orders")

        # log.warning(balance["balance"])

        elif (
            btc.balance >= buy_value * final_price
        ):  # if one can afford to buy, sometimes fails because we can't refresh api on every order

            # discount = percentage(trade_price_percentage, pair_market.bid)
            req = {
                "amount": "%.4f" % buy_value,
                "market_id": conf.market_id,
                "price": "%.8f" % final_price,
            }

            result = api.post(
                "https://api.qtrade.io/v1/user/buy_limit", json=req
            ).json()
            log.warning(result)
            order_id = int(result["data"]["order"]["id"])
            log.warning(f"Placed buy order {order_id}")
            conf.orders_placed.append({"id": order_id, "order_type": "buy"})
        else:
            log.warning(
                f"Insufficient balance ({'%.8f' % btc.balance}) for {conf.name} ({conf.buy_amount} units)"
            )

    # place a buy order


def randomize(random_size_value):
    randomized = float(
        "%.4f" % random.uniform((-random_size_value), (random_size_value))
    )
    return randomized


def sell(conf, pair_market):
    log.warning("Checking to place a sell order")
    # place a sell order
    if pair_market.ask <= conf.min_sell_price:
        log.warning("Market price too low to sell now")

    elif conf.sell_amount <= 0:
        log.warning(f"Not configured to sell (sell set to {conf.sell_amount})")

    else:
        altcoin = pick_currency(balances, conf.name)
        random_value = randomize(conf.random_size)
        sell_value = conf.sell_amount + random_value
        final_price = pair_market.ask - conf.price_adjustment

        if altcoin.balance <= conf.min_stash:
            log.warning("Minimum stash reached, will not create new sell orders")

        elif altcoin.balance >= sell_value:

            # sell order
            req = {
                "amount": "%.4f" % sell_value,
                "market_id": conf.market_id,
                "price": "%.8f" % final_price,
            }
            result = api.post(
                "https://api.qtrade.io/v1/user/sell_limit", json=req
            ).json()
            log.warning(result)
            order_id = result["data"]["order"]["id"]
            log.warning(f"Placed sell order {order_id}")
            conf.orders_placed.append({"id": order_id, "order_type": "sell"})
        else:
            log.warning(
                f"Insufficient balance ({'%.8f' % altcoin.balance}) for {conf.name} ({conf.buy_amount} units)"
            )

    # place a sell order


def pick_longevity_from_type(order_type, conf):
    if order_type == "buy_limit":
        return conf.buy_longevity
    elif order_type == "sell_limit":
        return conf.sell_longevity
    else:
        return None


def loop_pair_orders(conf, pair_orders):
    # go through orders
    for order in pair_orders.open_orders:
        if order["market_id"] == conf.market_id:
            # log.warning(order["created_at"])
            order_id = int(order["id"])
            order_type = order["order_type"]
            age_of_order = age(order["created_at"])

            longevity = pick_longevity_from_type(order_type, conf)
            if age_of_order > longevity:
                log.warning(
                    f"Removing old {order_type} order {order_id}, ({age_of_order}/{longevity}) seconds old"
                )

                req = {"id": order_id}
                result = api.post(
                    "https://api.qtrade.io/v1/user/cancel_order", json=dict(req)
                )
                log.warning(result)

                for entry in conf.orders_placed:
                    if entry["id"] == order_id:
                        conf.orders_placed.remove(entry)
            else:
                log.warning(
                    f"{order_type} order {order_id} retained, {age_of_order}/{longevity} seconds old"
                )
    # go through orders

    log.warning(f"Total {conf.name} orders: {conf.orders_placed}")
    log.warning(f"Total number of {conf.name} orders: {conf.count_orders()}")


def market_stats(conf, pair_market):
    log.warning(f"base_balance {pair_orders.base_balance}")
    log.warning(f"closed_orders {pair_orders.closed_orders[:10]}")
    log.warning(f"market_balance {pair_orders.market_balance}")
    log.warning(f"open_orders {pair_orders.open_orders}")

    log.warning(
        f"api last refresh: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(conf.last_refreshed))}"
    )
    log.warning(f"spread: {'%.8f' % pair_market.spread}")
    log.warning(f"ask: {'%.8f' % pair_market.ask}")
    log.warning(f"bid: {'%.8f' % pair_market.bid}")
    log.warning(f"day_avg_price: {'%.8f' % pair_market.day_avg_price}")
    log.warning(f"day_change: {'%.8f' % pair_market.day_change}")
    log.warning(f"day_high: {'%.8f' % pair_market.day_high}")
    log.warning(f"day_low: {'%.8f' % pair_market.day_low}")
    log.warning(f"day_open: {'%.8f' % pair_market.day_open}")
    log.warning(f"day_volume_base: {'%.8f' % pair_market.day_volume_base}")
    log.warning(f"day_volume_market: {'%.8f' % pair_market.day_volume_market}")
    log.warning(f"id: {pair_market.id}")
    log.warning(f"id_hr: {pair_market.id_hr}")
    log.warning(f"last_price: {'%.8f' % pair_market.last_price}")
    log.warning(f"day_spread: {'%.8f' % pair_market.day_spread}")
    log.warning(f"spread_pct: {'%.8f' % pair_market.spread_pct}")


if __name__ == "__main__":

    # Create a session object to make repeated API calls easy!
    api = requests.Session()
    # Create an authenticator with your API key

    api.auth_native = QtradeAPI(
        "https://api.qtrade.io", key=load_credentials()
    )  # use in the future

    api.auth = QtradeAuth(load_credentials())

    # load currencies
    active_currencies = []
    with open("config.json") as confile:
        confile_contents = json.loads(confile.read())
        for currency in confile_contents:
            log.warning(f"Loaded {currency}")

            active_currencies.append(
                Config(
                    name=currency["name"],
                    sell_amount=currency["sell_amount"],
                    buy_amount=currency["buy_amount"],
                    buy_longevity=currency["buy_longevity"],
                    sell_longevity=currency["sell_longevity"],
                    spread_pct_min=currency["spread_pct_min"],
                    price_adjustment=float(currency["price_adjustment"]),
                    max_buy_price=currency["max_buy_price"],
                    min_sell_price=currency["min_sell_price"],
                    max_stash=currency["max_stash"],
                    min_stash=currency["min_stash"],
                    random_size=currency["random_size"],
                    end_pause=currency["end_pause"],
                )
            )

    # load currencies

    while True:
        me = api.get("https://api.qtrade.io/v1/user/me").json()
        log.warning(me)

        try:
            for conf in active_currencies:
                if DEMO and conf.name not in DEMO_MARKETS:
                    log.warning("Demo mode active, skipping market")
                    break

                log.warning(f"Working on {conf.pair}")
                conf.refresh_api()
                # Make a call to API
                # move data to object
                pair_market = PairMarket(conf)

                pair_orders = PairOrders()

                market_stats(conf, pair_market)

                loop_pair_orders(conf, pair_orders)  # pair conf is different

                if pair_market.spread_pct < conf.spread_pct_min:
                    log.warning(
                        f"No new orders, spread {pair_market.spread_pct} too small"
                    )

                else:

                    balances = api.get("https://api.qtrade.io/v1/user/balances").json()
                    log.warning(balances)

                    sell(conf, pair_market)
                    buy(conf, pair_market)

                log.warning(f"Taking a break for {conf.end_pause} seconds")
                time.sleep(conf.end_pause)

        except Exception as e:
            log.warning(f"Exception {e}")
            if DEBUG:
                raise

        log.warning("Loop ended, waiting for 60 seconds")
        time.sleep(60)
