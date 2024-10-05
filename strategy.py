import pandas as pd
import pandas_ta as pta
import sqlite3
import logging

logger = logging.getLogger(__name__)


def hvi(dataframe, period=10):
    HV = dataframe['volume'].rolling(window=period).max()
    HVI = dataframe['volume'] * 100 / HV.shift(1)
    return HVI

class Strategy:
    def __init__(self):
        self.conn = sqlite3.connect('data.db', check_same_thread=False)

    def read_price(self):
        logging.info("Reading price data")
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM RUNE_USDT_prices")
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        print(df)
        return df
    
    def calc_indicators(self, df):
        logger.info("Calculating indicators")
        
        # Calculate SMAs with sufficient data points
        df['sma20'] = pta.sma(df['close'], length=20)
        
        # Calculate sma100 only if there are enough data points
        if len(df['close']) >= 100:  # Ensure enough data points for sma100
            df['sma100'] = pta.sma(df['close'], length=100)
        else:
            df['sma100'] = float('nan')  # Set sma100 to NA if not enough data points

        df['hvi'] = hvi(df, period=10)

        # Supertrend
        periodo = 7
        atr_multiplicador = 3.0
        df['ST_long'] = pta.supertrend(df['high'], df['low'], df['close'], length=periodo, multiplier=atr_multiplicador)[f'SUPERTl_{periodo}_{atr_multiplicador}']
        df['ST_short'] = pta.supertrend(df['high'], df['low'], df['close'], length=periodo, multiplier=atr_multiplicador)[f'SUPERTs_{periodo}_{atr_multiplicador}']
        print(df)
        return df

    def entry_signals(self, df):
        df['enter_long'] = 0
        df['enter_short'] = 0
        df.loc[
            (df['close'] > df['sma20']) &
            (df['close'] > df['sma100']) &
            (df['hvi'] > 100) &
            (df['close'] > df['ST_long']),
            'enter_long'] = 1
        df.loc[
            (df['close'] < df['sma20']) &
            (df['close'] < df['sma100']) &
            (df['hvi'] > 100) &
            (df['close'] < df['ST_short']),
            'enter_short'] = 1
        print(df)
        return df
    
    def exit_signals(self, df):
        df['exit_long'] = 0
        df['exit_short'] = 0
        df.loc[
            (df['close'] < df['ST_long']),
            'exit_long'] = 1
        df.loc[
            (df['close'] > df['ST_short']),
            'exit_short'] = 1
        print(df)
        return df

strat = Strategy()
df = strat.read_price()
strat.calc_indicators(df)
#strat.entry_signals(df)
#strat.exit_signals(df)