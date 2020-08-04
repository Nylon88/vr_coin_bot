import numpy as np
import talib
from time import sleep

from ccxt_api import CcxtApi


from app.models.Candle_Db import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmaTrade:
    def __init__(self):
        # __init__で設定すればおk
        self.ccxt_api = CcxtApi()
        self.buy_status_sma = {}
        self.tools = GetTools()

        for i in range(300):
            self.buy_status_sma[i] = 'reset'
        self.sell_status_sma = {}
        for i in range(300):
            self.sell_status_sma[i] = 'reset'

    def latest_clu_sma(self, many):
        try:
            candle_info = CandleInfo.get_table_info(many)
            while True:
                if len(candle_info) != many:
                    logger.warning(f'action=latest_clu_sma again after 5s')
                    sleep(5)
                    candle_info = CandleInfo.get_table_info(many)
                else:
                    break
            closes = []
            for row in candle_info:
                closes.append(row[1])
            sma_data = talib.SMA(np.array(closes, dtype='f8'), timeperiod=many)
            # logger.info(f'action=latest_clu_sma() sma_data={many}日間:{sma_data[many-1]}')
            return sma_data[many - 1]
        except Exception as e:
            logger.error(f'action=latest_clu_sma() error={e}')

    def before_clu_sma(self, many):
        try:
            candle_info = CandleInfo.get_table_info(many + 1)
            while True:
                if len(candle_info) != many + 1:
                    logger.warning(f'action=before_clu_sma again after 5s')
                    sleep(5)
                    candle_info = CandleInfo.get_table_info(many + 1)
                else:
                    break
            closes = []
            for row in candle_info[:many]:
                closes.append(row[1])
            sma_data = talib.SMA(np.array(closes, dtype='f8'), timeperiod=many)
            # logger.info(f'action=before_clu_sma() sma_data={many}日間:{sma_data[many-1]}')
            return sma_data[many - 1]
        except Exception as e:
            logger.error(f'action=before_clu_sma() error={e}')

    # 買いの判断をする
    def jud_buy(self, jud_buy_sma, before_vr_long_sma, before_sma, latest_vr_long_sma, latest_sma):
        try:
            # 各smaによる判定
            if jud_buy_sma == 'down':
                if latest_vr_long_sma <= latest_sma:
                    jud_buy_sma = 'up'
            elif jud_buy_sma == 'up':  # upの時実行
                if latest_vr_long_sma > latest_sma:  # 'up'の状態でvr_long_smaを下回った時実行
                    jud_buy_sma = 'down'
            else:  # 'reset'の時実行
                if before_vr_long_sma > before_sma:  # 一度vr_long_smaより下がらないと判定されない
                    jud_buy_sma = 'down'
                    if latest_vr_long_sma <= latest_sma:
                        jud_buy_sma = 'up'

            return jud_buy_sma
        except Exception as e:
            logger.error(f'action=jud_buy() error={e}')

    def jud_buy_sma_periods_kai(self, periods: list) -> list:
        logger.info(f'action=jud_buy_sma_kai() 今回使うsma={periods}')
        before_sma = {}
        latest_sma = {}
        statuses_sma = []
        # 一番長い期間を抽出する
        vr_long_sma = max(periods)
        periods.remove(vr_long_sma)
        # periodに残ったものをvr_long_smaと比較していく
        # before_sma_vr_long_smaとlatest_sma_vr_long_smaを取得する
        before_sma[vr_long_sma] = self.before_clu_sma(vr_long_sma)
        latest_sma[vr_long_sma] = self.latest_clu_sma(vr_long_sma)

        # 各period内のsmaを計算する
        for period in periods:
            before_sma[period] = self.before_clu_sma(period)
            latest_sma[period] = self.latest_clu_sma(period)
            self.buy_status_sma[period] = self.jud_buy(self.buy_status_sma[period], before_sma[vr_long_sma],
                                                       before_sma[period], latest_sma[vr_long_sma], latest_sma[period])
            statuses_sma.append(self.buy_status_sma[period])
        return statuses_sma

    def buy_kai(self, amount=1, periods=None) -> int:
        if periods is None:
            periods = [200, 5, 8, 13]
        statuses_sma = self.jud_buy_sma_periods_kai(periods)

        # 一個でも'up'でないモノがあればトレードしない
        for status in statuses_sma:
            if status != 'up':
                logger.info(f'action=buy_kai() No trade')
                # periodsのリセット
                periods = [200, 5, 8, 13]
                return 0
        # 全部'up'だった為、注文をする
        result = self.ccxt_api.create_order(side='buy', amount=amount)
        logger.info(f'action=buy_kai() result={result}')
        # 買った時buy_status_smaを'reset'にする
        for period in periods:
            self.buy_status_sma[period] = 'reset'

        # 120秒後に買った分を売る
        sleep(120)
        result = self.ccxt_api.create_order(side='sell', amount=amount)
        logger.info(f'action=buy_kai() result={result}')

        return 120

    def interval_buy_trade(self, interval):
        logger.info(f'Start buy_trade')
        self.tools.interval_exe(self.buy_kai, interval)

    # 売りの判断をする
    def jud_sell(self, jud_sell_sma, before_vr_long_sma, before_sma, latest_vr_long_sma, latest_sma):
        try:
            if jud_sell_sma == 'up':
                if latest_vr_long_sma >= latest_sma:
                    jud_sell_sma = 'down'
            elif jud_sell_sma == 'down':  # downの時実行
                if latest_vr_long_sma < latest_sma:  # 'down'の状態でvr_long_smaを上回った時実行
                    jud_sell_sma = 'up'
            else:  # 'reset'の時実行
                if before_vr_long_sma < before_sma:  # 一度vr_long_smaより上がらないと判定されない
                    jud_sell_sma = 'up'
                    if latest_vr_long_sma >= latest_sma:
                        jud_sell_sma = 'down'

            return jud_sell_sma
        except Exception as e:
            logger.error(f'action=jud_sell() error={e}')

    def jud_sell_sma_periods_kai(self, periods: list) -> list:
        logger.info(f'action=jud_sell_sma_kai() 今回使うsma={periods}')
        before_sma = {}
        latest_sma = {}
        statuses_sma = []
        # 一番長い期間を抽出する
        vr_long_sma = max(periods)
        periods.remove(vr_long_sma)
        # periodに残ったものをvr_long_smaと比較していく
        # before_sma_vr_long_smaとlatest_sma_vr_long_smaを取得する
        before_sma[vr_long_sma] = self.before_clu_sma(vr_long_sma)
        latest_sma[vr_long_sma] = self.latest_clu_sma(vr_long_sma)

        # period内のsmaを計算する
        for period in periods:
            before_sma[period] = self.before_clu_sma(period)
            latest_sma[period] = self.latest_clu_sma(period)
            self.sell_status_sma[period] = self.jud_sell(self.sell_status_sma[period], before_sma[vr_long_sma],
                                                         before_sma[period], latest_sma[vr_long_sma],
                                                         latest_sma[period])
            statuses_sma.append(self.sell_status_sma[period])
        return statuses_sma

    def sell_kai(self, amount=1, periods=None) -> int:
        if periods is None:
            periods = [200, 5, 8, 13]
        statuses_sma = self.jud_sell_sma_periods_kai(periods)
        # statusが全て'down'であれば買い
        for status in statuses_sma:
            if status != 'down':
                logger.info(f'action=sell_kai() No trade')
                # periodsのリセット
                periods = [200, 5, 8, 13]
                return 0
        result = self.ccxt_api.create_order(side='sell', amount=amount)
        logger.info(f'action=sell_kai() result={result}')
        # 買った時buy_status_smaを'reset'にする
        for period in periods:
            self.sell_status_sma[period] = 'reset'

        # 120秒後に売った分を買う
        sleep(120)
        result = self.ccxt_api.create_order(side='buy', amount=amount)
        logger.info(f'action=sell_kai() result={result}')
        return 120

    def interval_sell_trade(self, interval):
        logger.info(f'Start sell_trade')
        self.tools.interval_exe(self.sell_kai, interval)