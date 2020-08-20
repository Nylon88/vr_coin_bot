from functools import partial

import ccxt

from app.models.Candle_Db import CandleInfo
from utils import *


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CcxtApi:
    def __init__(self):
        self.bitmex = self.generate_test()
        self.tools = GetTools()

    # 秘密鍵とパスワードはご自分でご用意ください。
    def generate_test(self, api_key='None',
                      secret='None'):
        # bitmexオブジェクトの作成
        bitmex = ccxt.bitmex({
            'apiKey': api_key,
            'secret': secret
        })
        bitmex.urls['api'] = bitmex.urls['test']

        return bitmex

    def get_balance_info(self):
        # startした時の口座残高とリアルタイムで取得した口座情報の差がprofitになる
        balance = self.bitmex.fetch_balance()
        wallet_balance = balance['info'][0]['walletBalance']
        return wallet_balance

    def get_profit_info(self, start_wallet_balance):
        now_wallet_balance = self.get_balance_info()
        profit = start_wallet_balance - now_wallet_balance
        return profit

    # もっと柔軟にコーディングする必要あり
    def get_ohlcv(self, limit):
        # ohlcvの取得
        ohlcv = self.bitmex.fetch_ohlcv(symbol='BTC/USD',
                                        timeframe='1m',
                                        since=self.tools.get_ms_now(limit),
                                        limit=limit)
        return ohlcv

    # candle情報を取ってきてdbに格納する
    def get_candle_save_db(self, limit):
        ohlcv = self.get_ohlcv(limit=limit)
        candle_info = self.tools.pick_up_times_closes(ohlcv)
        result = CandleInfo.insert(candle_info)
        return 0

    def interval_get_candle_save_db(self, interval, limit=1):
        callback = partial(self.get_candle_save_db, limit=limit)
        self.tools.interval_exe(callback, interval)

    # 成り行きの注文を入れる
    def create_order(self, symbol='BTC/USD', type='market', side=None, amount=0.0):
        success = self.bitmex.create_order(symbol, type, side, amount)
        return success
