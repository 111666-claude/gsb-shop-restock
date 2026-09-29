"""命令行入口：跑商店限购样例。"""

import argparse

from .shop import Shop, ShopError, buy


def build_parser():
    parser = argparse.ArgumentParser(prog="shop-restock", description="商店限购")
    parser.add_argument("--sample", default="daily", help="daily / money")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    shop = Shop({"potion": (10, 3)})
    if args.sample == "daily":
        money = 1000
        for _ in range(3):
            money, _ = buy(shop, "potion", 20260929, money)
        try:
            buy(shop, "potion", 20260930, money)
            print("next_day_ok=True money=%d" % money)
        except ShopError as error:
            print("next_day_ok=False money=%d" % money)
    elif args.sample == "money":
        try:
            money, _ = buy(shop, "potion", 20260929, 5)
            print("money=%d" % money)
        except ShopError:
            print("money=rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
