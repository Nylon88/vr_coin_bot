from flask import Flask
from flask import render_template
from flask import jsonify
from time import sleep
from functools import partial

import sys
from pathlib import Path

sys.path.append(str(Path('__file__').resolve().parent.parent))
from app.models.Candle_Db import *
import technical_trade
import ccxt_api

app = Flask(__name__, template_folder='../templates')


@contextmanager
def trade_scoped():
    event = threading.Event()
    try:
        yield event
        logger.info(f'trade_scoped close')
    except Exception as e:
        logger.error(f'action=trade_scoped() error={e}')


# intervalにstop_のwhile判定をさせるコードを記述する
class A:
    event_buy = None
    event_sell = None
    thread_buy = None
    thread_sell = None
    start_wallet_balance = 0
    ccxt_db = ccxt_api.CcxtApi()
    sma_trade = technical_trade.SmaTrade()

    @classmethod
    def db_sv(cls, interval):
        cls.ccxt_db.interval_get_candle_save_db(interval)

    @classmethod
    def sma_buy(cls, interval):
        while(1):
            with trade_scoped() as event:
                cls.event_buy = event
                event.wait()
                event.clear()
                logger.info(f'sma_buy interval start')
                cls.sma_trade.interval_buy_trade(interval)

    @classmethod
    def sma_sell(cls, interval):
        while(1):
            with trade_scoped() as event:
                cls.event_sell = event
                event.wait()
                event.clear()
                cls.sma_trade.interval_sell_trade(interval)

    @classmethod
    def trade_start(cls):
        delete_table()
        create_table()
        callback = partial(app.run, host='127.0.0.1', port=8080)
        cls.ccxt_db.get_candle_save_db(210)
        sleep(2)

        cls.thread_db_sv = threading.Thread(target=cls.db_sv, args=(20,))
        cls.thread_fla = threading.Thread(target=callback)
        cls.thread_buy = threading.Thread(target=cls.sma_buy, args=(40,))
        cls.thread_sell = threading.Thread(target=cls.sma_sell, args=(40,))
        cls.thread_db_sv.start()
        logger.info(f'action=thread_db_sv.start()')
        cls.thread_fla.start()
        logger.info(f'action=thread_fla.start()')
        cls.thread_buy.start()
        logger.info(f'action=thread_buy.start()')
        cls.thread_sell.start()
        logger.info(f'action=thread_sell.start()')

    @classmethod
    def trade_set(cls):
        cls.start_wallet_balance = A.ccxt_db.get_balance_info()
        cls.sma_trade.tools.stop_ = False
        cls.event_buy.set()
        cls.event_sell.set()

    @classmethod
    def trade_stop(cls):
        # cls.set = False
        cls.sma_trade.tools.stop_ = True


@app.route('/')
def hello():
    return render_template('front.html')


# startボタンを押すとトレードを開始させる
@app.route('/start', methods=['GET'])
def start():
    A.trade_set()
    return jsonify('trade start')


# フロントエンドにprofitを渡す
@app.route('/profit', methods=['GET'])
def profit_info():
    profit = A.ccxt_db.get_profit_info(A.start_wallet_balance)
    return jsonify(profit)


# stopボタンを押すとトレードを終了させ　　threadingのEVENTを使ってthreadを止める
@app.route('/stop', methods=['GET'])
def stop():
    A.trade_stop()
    return jsonify('trade stop')


if __name__ == '__main__':
    A.trade_start()
