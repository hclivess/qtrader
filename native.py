from qtrade_client.api import QtradeAPI


def load_credentials():
    with open("secret") as authfile:
        return authfile.read()


# String is of the format "[key_id]:[key]"
client_native = QtradeAPI("https://api.qtrade.io", key=load_credentials())

# result = client.post("/v1/user/sell_limit", amount="1", price="0.0001", market_id=12)
# print(result)

# Only closed orders
print(client_native.orders(open=False))
# Print all orders before ID 25
print(client_native.orders(older_than=25))
# Print all orders after ID 25
print(client_native.orders(newer_than=25))
