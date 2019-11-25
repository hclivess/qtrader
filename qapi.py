from qtrade_client.api import QtradeAPI
import json
import time
from log import log
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

DEMO = False

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

log = log("qtrader.log", "WARNING", True)


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
        self.spread_pct = 100 - part_percentage(self.bid, self.ask)


def pick_currency(balances_dict, currency_name):
    for entry in balances_dict["data"]["balances"]:
        if entry["currency"] == currency_name:
            return Balance(entry)


class Balance:
    def __init__(self, balance_dict):
        self.name = balance_dict["currency"]
        self.balance = float(balance_dict["balance"])


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
        if DEMO:
            self.sell_amount = 0
        else:
            self.sell_amount = sell_amount
        self.buy_amount = buy_amount
        self.order_ttl = ttl
        self.spread_pct_min = spread_pct_min
        self.market_api = None
        self.refresh_api()
        self.currency_id = self.market_api["data"]["id"]
        self.price_adjustment = price_adjustment
        log.warning("market_api", self.market_api)
        self.max_buy_price = max_buy_price
        self.min_sell_price = min_sell_price
        self.last_refreshed = None

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
    if pair_market.bid >= conf.max_buy_price:
        log.warning("Market price too high to buy now")
    elif conf.buy_amount <= 0:
        log.warning(f"Not configured to buy (buy set to {conf.buy_amount})")
    else:
        currency = pick_currency(balances, "BTC")

        # log.warning(balance["balance"])
        if (
            currency.balance > conf.buy_amount * pair_market.bid
        ):  # if one can afford to buy trade_buy_amount

            # discount = percentage(trade_price_percentage, pair_market.bid)
            req = {
                "amount": str(conf.buy_amount),
                "market_id": conf.currency_id,
                "price": "%.8f" % (pair_market.bid + conf.price_adjustment),
            }

            result = api.post(
                "https://api.qtrade.io/v1/user/buy_limit", json=req
            ).json()
            log.warning(result)
            order_id = int(result["data"]["order"]["id"])
            log.warning(f"Placed buy order {order_id}")
            conf.orders_placed.append({"order_id": order_id, "order_type": "buy"})
        else:
            log.warning(
                f"Insufficient balance ({currency.balance}) for {currency.name} ({conf.buy_amount} orders)"
            )

    # place a buy order


def sell(conf, pair_market):
    # place a sell order
    if pair_market.ask <= conf.min_sell_price:
        log.warning("Market price too low to sell now")
    elif conf.sell_amount <= 0:
        log.warning(f"Not configured to sell (sell set to {conf.sell_amount})")

    else:
        currency = pick_currency(balances, conf.name)
        # log.warning(balance["balance"])
        if currency.balance > conf.sell_amount:

            # sell order
            req = {
                "amount": str(conf.sell_amount),
                "market_id": conf.currency_id,
                "price": "%.8f" % (pair_market.ask - conf.price_adjustment),
            }
            result = api.post(
                "https://api.qtrade.io/v1/user/sell_limit", json=req
            ).json()
            log.warning(result)
            order_id = result["data"]["order"]["id"]
            log.warning(f"Placed sell order {order_id}")
            conf.orders_placed.append({"order_id": order_id, "order_type": "sell"})
        else:
            log.warning(
                f"Insufficient balance ({currency.balance} for {currency.name} ({conf.buy_amount} units)"
            )

    # place a sell order


def loop_pair_orders(conf, pair_orders):
    # go through orders
    for order in pair_orders.open_orders:
        # log.warning(order["created_at"])
        order_id = int(order["id"])
        age_of_order = age(order["created_at"])
        if age_of_order > conf.order_ttl:
            log.warning(
                f"Removing old order {order_id}, ({age_of_order}/{conf.order_ttl}) seconds old"
            )

            req = {"id": order_id}
            result = api.post(
                "https://api.qtrade.io/v1/user/cancel_order", json=dict(req)
            )
            log.warning(result)
            if (
                order_id in conf.orders_placed
            ):  # if it has not been placed by someone else
                for key in :
                    if key["id"] == order_id:
                        conf.orders_placed.remove(order_id)
                        del conf.orders_placed[key]
        else:
            log.warning(
                f"Order {order_id} retained, {age_of_order}/{conf.order_ttl} seconds old"
            )
    # go through orders

    log.warning(f"{conf.name} orders: {conf.orders_placed}")
    log.warning(f"Number of {conf.name} orders: {conf.count_orders()}")


def market_stats(conf, pair_market):
    log.warning(f"api last refresh: {conf.last_refreshed}")
    log.warning(f"spread: {'%.8f' % pair_market.spread}")
    log.warning(f"ask: {pair_market.ask}")
    log.warning(f"bid: {pair_market.bid}")
    log.warning(f"day_avg_price: {pair_market.day_avg_price}")
    log.warning(f"day_change: {pair_market.day_change}")
    log.warning(f"day_high: {pair_market.day_high}")
    log.warning(f"day_low: {pair_market.day_low}")
    log.warning(f"day_open: {pair_market.day_open}")
    log.warning(f"day_volume_base: {pair_market.day_volume_base}")
    log.warning(f"day_volume_market: {pair_market.day_volume_market}")
    log.warning(f"id: {pair_market.id}")
    log.warning(f"id_hr: {pair_market.id_hr}")
    log.warning(f"last_price: {pair_market.last_price}")
    log.warning(f"day_spread: {pair_market.day_spread}")
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
        log.warning(me)

        try:
            for conf in active_currencies:

                log.warning(f"Working on {conf.pair}")
                conf.refresh_api()
                # Make a call to API
                # move data to object
                pair_market = PairMarket(conf)

                market_stats(conf, pair_market)

                order_api = api.get(
                    f"https://api.qtrade.io/v1/user/market/{conf.pair}"
                ).json()
                pair_orders = PairOrders()

                pair_orders.base_balance = order_api["data"]["base_balance"]
                pair_orders.closed_orders = order_api["data"]["closed_orders"]
                pair_orders.market_balance = order_api["data"]["market_balance"]
                # pair_orders.open_orders = order_api["data"]["open_orders"]  # old way
                pair_orders.open_orders = api.auth_native.orders(open=True)

                log.warning(pair_orders.base_balance)
                log.warning(pair_orders.closed_orders)
                log.warning(pair_orders.market_balance)
                log.warning(pair_orders.open_orders)

                if pair_market.spread_pct < conf.spread_pct_min:
                    log.warning(
                        f"No new orders, spread {pair_market.spread_pct} too small"
                    )

                else:

                    balances = api.get("https://api.qtrade.io/v1/user/balances").json()
                    log.warning(balances)

                    sell(conf, pair_market)
                    buy(conf, pair_market)

                loop_pair_orders(conf, pair_orders)

        except Exception as e:
            log.warning(f"Error: {e}")
            time.sleep(60)

        time.sleep(60)
