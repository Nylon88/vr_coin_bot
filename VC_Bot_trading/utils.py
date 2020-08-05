from datetime import datetime
import calendar
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GetTools:
    # 現在の時間をmsで取得し、スタートの時間を設定する
    def get_ms_now(self, limit=500):
        now = datetime.utcnow()
        unix_time = calendar.timegm(now.utctimetuple())

        since = (unix_time - 60 * limit) * 1000  # スタートの設定
        return since

    # functionに引数がないものだけ使用可能
    def interval_exe(self, function, interval):
        try:
            while (1):
                past = time.perf_counter()
                function()
                interval_time = interval - (time.perf_counter() - past)
                time.sleep(interval_time)
                logger.info(f'action= interval() {function}:１ループ終了')
        except Exception as e:
            logger.error(f'action= {function} error={e}')

    def pick_up_times_closes(self, ohlcvs) -> list:
        candle_info = []
        for ohlcv in ohlcvs:
            second_time = int(ohlcv[0]) / 1000  # msをsに変換した
            change_time = datetime.fromtimestamp(second_time).strftime('%Y-%m-%d %H:%M:00')
            close = ohlcv[4]
            info = (change_time, close)
            candle_info.append(info)
        return candle_info