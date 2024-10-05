import sqlite3
import ccxt
import logging
from datetime import datetime
from config import API_KEY, API_SECRET

logger = logging.getLogger(__name__)

class MarketData:
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future'
            }
        })
            #'urls': {
            #    'api': {
            #        'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
            #        'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1',
            #    }}

        #self.exchange.set_sandbox_mode(True)

    def fetch_data(self, limit=1):
        logger.info("Fetching price data")
        try:
            ohlcv = self.exchange.fetch_ohlcv('RUNE/USDT', timeframe='1m', limit=limit)
            return ohlcv
        except Exception as e:
            return None

    def save_to_db(self, ohlcv):
        if not ohlcv:
            logger.error("No data to save")
            return
        try:
            conn = sqlite3.connect('data.db', check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS RUNE_USDT_prices (
                    timestamp TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL
                )
            """)
            for data in ohlcv:
                cursor.execute("""
                    INSERT INTO RUNE_USDT_prices (timestamp, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    datetime.fromtimestamp(data[0] / 1000).isoformat(),
                    data[1],
                    data[2],
                    data[3],
                    data[4],
                    data[5]
                ))
            conn.commit()
        except Exception as e:
            conn.close()

    def read_from_db(self):
        logger.info("Reading price data")
        try:
            conn = sqlite3.connect('data.db', check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM RUNE_USDT_prices")
            rows = cursor.fetchall()
            print(rows)
            return rows
            
        except Exception as e:
            return []
        finally:
            conn.close()

if __name__ == "__main__":

    market = MarketData()
    ohlcv = market.fetch_data()
    #print(ohlcv)
    market.save_to_db(ohlcv)
    market.read_from_db()

