"""商店限购与每天刷新。

限购按服务器日独立计数：服务器日变化（默认每天 05:00 刷新）时当天计数
清零；余额不足时抛 ShopError，余额与计数都不变。
"""

from datetime import datetime, timedelta


class ShopError(ValueError):
    """购买不合法：商品不存在、超过当日限购或余额不足。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class Shop:
    """一个商店。stock 形如 {item: (price, daily_limit)}。

    purchases 只保存当前服务器日各商品的已购次数，服务器日变化时整体
    清零，因此内存占用为 O(商品数)。last_day 记录当前服务器日标识。
    """

    def __init__(self, stock, refresh_hour=5):
        self.stock = dict(stock)
        self.refresh_hour = refresh_hour
        self.purchases = {}
        self.last_day = None


def server_day(at, refresh_hour=5):
    """把服务器时区的时刻折算成限购日（datetime.date）。

    刷新时刻之前（00:00 到 04:59:59）仍算前一个服务器日，到达刷新时刻
    （05:00:00）起算新的一天。
    """
    day = at.date()
    if at.hour < refresh_hour:
        day = day - timedelta(days=1)
    return day


def _day_key(shop, day):
    # 整数（如 20260929）/ date 等直接作为服务器日标识；datetime 按
    # shop.refresh_hour 折算成服务器日。
    if isinstance(day, datetime):
        return server_day(day, shop.refresh_hour)
    return day


def buy(shop, item, day, money):
    """买一件，返回 (剩余余额, 当天已购次数)。

    day 是服务器日标识（如 YYYYMMDD 整数、date），也可以直接传服务器
    时区的 datetime，按商店的 refresh_hour 折算限购日。

    商品不存在、当天已购次数达到 daily_limit 或余额小于售价时抛
    ShopError；失败时余额与购买计数都保持不变，因此同一批购买重复
    执行得到相同结果。
    """
    if item not in shop.stock:
        raise ShopError("没有这个商品：%s" % item)
    day = _day_key(shop, day)
    price, limit = shop.stock[item]
    bought = shop.purchases.get(item, 0) if shop.last_day == day else 0
    if bought >= limit:
        raise ShopError("超过每日限购：%s" % item)
    if money < price:
        raise ShopError("余额不足：%s" % item)
    # 所有校验通过后才提交状态：跨天清零、计数加一、扣款。
    if shop.last_day != day:
        shop.purchases = {}
        shop.last_day = day
    bought += 1
    shop.purchases[item] = bought
    return money - price, bought
