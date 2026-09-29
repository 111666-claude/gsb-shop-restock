"""商店限购与每天刷新。

限购按天独立计数，服务器日期（每天 05:00 刷新）变化时清零；
余额不足拒绝购买，余额不变。
"""

from datetime import datetime, timedelta


class ShopError(ValueError):
    """购买被拒绝（商品不存在、超过每日限购或余额不足）。"""

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


def server_day(moment, refresh_hour=5):
    """把服务器时区的某个时刻折算成「服务器日期」：每天 refresh_hour 点刷新。

    05:00 刷新时，凌晨 00:00-04:59 仍属于前一天。
    """
    return (moment - timedelta(hours=refresh_hour)).date()


def buy(shop, item, day, money):
    """买一件。day 为服务器日期（05:00 刷新后的日期，可用 server_day 折算）。

    日期变化时清零当天购买计数；超过每日限购或余额不足时抛 ShopError，
    余额与计数均不变。
    """
    if item not in shop.stock:
        raise ShopError("没有这个商品：%s" % item)
    price, limit = shop.stock[item]
    if day != shop.last_day:
        shop.purchases.clear()
        shop.last_day = day
    bought = shop.purchases.get(item, 0)
    if bought >= limit:
        raise ShopError("超过每日限购：%s" % item)
    if money < price:
        raise ShopError("余额不足：%s" % item)
    shop.purchases[item] = bought + 1
    return money - price, bought + 1
