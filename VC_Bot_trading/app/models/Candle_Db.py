from contextlib import contextmanager
import logging
import threading
from sqlalchemy import create_engine
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from datetime import *
import sys
from pathlib import Path

sys.path.append(str(Path('__file__').parent.parent))
from utils import GetTools


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# エンジンの作成
engine = create_engine('mysql+pymysql://hogehoge:@localhost:port/mysql?charset=utf8')
Session = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()
lock = threading.Lock()


@contextmanager
def session_scope():
    session = Session()
    try:
        lock.acquire()
        yield session
        session.commit()
    except Exception as e:
        logger.error(f'action=session_scope() error={e}')
        session.rollback()
        raise
    finally:
        lock.release()
        print('session finish')
        # 今回はthreadで実行を終了した時closeにする為、コメントアウトしている


# 作成したいモデルをベースを継承して作成
class CandleInfo(Base):
    tools = GetTools()
    # テーブルの名前
    __tablename__ = 'candle_info'

    time = Column(DateTime, primary_key=True, nullable=False)
    close = Column(Float)

    @classmethod
    def insert(cls, candle_info: list):
        # リスト型を内包したタプル型を辞書型を内包したリスト型へと変換している
        table_date = [{'time': info[0], 'close': info[1]} for info in candle_info]
        try:
            with session_scope() as session:
                session.execute(cls.__table__.insert(), table_date)
            logger.info(f'action=insert() update')
            return True
        except IntegrityError as e:
            logger.error(f'action=insert() same time No update')

    @classmethod
    def get_table_info(cls, many):
        candle_info = []
        since = cls.tools.get_ms_now(limit=many)
        since = datetime.fromtimestamp(since / 1000)
        with session_scope() as session:
            table_info = session.query(cls).filter(cls.time >= since).all()
        if table_info == []:
            return False
        for info in table_info:
            candle_info.append([info.time, info.close])
        logger.info(f'action=get_table_info() SUCCESS get candle info')
        return candle_info


def create_table():
    Base.metadata.create_all(bind=engine)
    logger.info(f'action=create_table() success')


def delete_table():
    Base.metadata.drop_all(bind=engine, tables=[CandleInfo.__table__])
    logger.info(f'action=delete_table() success')


if __name__ == '__main__':
    delete_table()



