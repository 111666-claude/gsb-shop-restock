"""商店限购与每天刷新。

缺陷：限购按累计购买次数（不按天）、余额不足也扣成负数、刷新时刻没有重置计数。
"""


class ShopError(ValueError):
    """输入不合法。缺陷：不带物品名。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class Shop:
    """一个商店。stock 形如 {item: (price, daily_limit)}。"""

    def __init__(self, stock, refresh_hour=5):
        self.stock = dict(stock)
        self.refresh_hour = refresh_hour
        self.purchases = {}
        self.last_day = None


def buy(shop, item, day, money):
    """买一件。缺陷：按累计次数判限购、余额不足不拦。"""
    if item not in shop.stock:
        raise ShopError("没有这个商品：%s" % item)
    price, limit = shop.stock[item]
    shop.purchases[item] = shop.purchases.get(item, 0) + 1
    if shop.purchases[item] > limit:
        raise ShopError("超过每日限购：%s" % item)
    money -= price
    return money, shop.purchases[item]
