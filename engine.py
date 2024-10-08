import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Union
from data import MarketData
from strategy import Strategy
import time
import threading

class TradingEngine:
    def __init__(self, dry_run: bool = True) -> None:
        self.market_data = MarketData()
        self.strategy = Strategy()
        self.symbol: str = 'RUNE/USDT'
        self.is_running: bool = False
        self.dry_run: bool = dry_run
        self.simulated_balance: float = 10000.0  # Simulated USDT balance for dry run mode
        self.simulated_orders: List[Dict[str, Union[int, str, float]]] = []  # Track simulated orders
        
        # Initialize database and create table if it doesn't exist
        self.initialize_database()

    def initialize_database(self) -> None:
        """Initializes the database and creates the closed_trades table if it does not exist."""
        try:
            conn = sqlite3.connect('app.db', check_same_thread=False)
            cursor = conn.cursor()
            # Create the closed_trades table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS closed_trades (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    symbol TEXT,
                    side TEXT,
                    amount REAL,
                    price REAL,
                    profit REAL
                )
            """)
            conn.commit()
            logging.info("Database initialized and checked for the closed_trades table.")
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
        finally:
            conn.close()

    def log_closed_trade(self, order: Dict[str, Union[int, str, float]], current_price: float) -> None:
        """Logs a closed trade to the database."""
        order_price = float(order['price'])
        amount = float(order['amount'])
        profit = (current_price - order_price) * amount if order['side'] == 'buy' else (order_price - current_price) * amount
        
        try:
            conn = sqlite3.connect('app.db', check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO closed_trades (timestamp, symbol, side, amount, price, profit) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    datetime.fromtimestamp(order['timestamp'] / 1000).isoformat(),
                    self.symbol,
                    order['side'],
                    amount,
                    order_price,
                    profit
                ))
            conn.commit()
            logging.info("Trade logged successfully.")
        except Exception as e:
            logging.error(f"Error logging closed trade: {e}")
        finally:
            conn.close()

    def show_trade_stats(self) -> str:
        """Fetches and displays trade statistics from the database."""
        try:
            conn = sqlite3.connect('app.db', check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM closed_trades")
            trades = cursor.fetchall()
        except Exception as e:
            logging.error(f"Error fetching trade stats: {e}")
            return "Error fetching trade stats"
        finally:
            conn.close()

        total_profit = sum(trade[5] for trade in trades)
        total_trades = len(trades)
        wins = [trade for trade in trades if trade[5] > 0]
        losses = [trade for trade in trades if trade[5] <= 0]
        win_rate = len(wins) / total_trades if total_trades > 0 else 0
        average_win = sum(trade[5] for trade in wins) / len(wins) if wins else 0
        average_loss = sum(trade[5] for trade in losses) / len(losses) if losses else 0
        profit_factor = sum(trade[5] for trade in wins) / abs(sum(trade[5] for trade in losses)) if losses else float('inf')
        stats = f"""
        Total Trades: {total_trades}
        Total Profit: {total_profit}
        Win Rate: {win_rate * 100:.2f}%
        Average Win: {average_win}
        Average Loss: {average_loss}
        Profit Factor: {profit_factor}
        """
        return stats

    def get_balance(self) -> Optional[float]:
        """Returns the balance in USDT. For dry run, returns the simulated balance."""
        if self.dry_run:
            print(self.simulated_balance)
            return self.simulated_balance
        try:
            balance = self.market_data.exchange.fetch_balance()
            usdt_balance = balance['total'].get('USDT')
            if usdt_balance is None:
                logging.error("USDT balance not found in the fetched balance data.")
                return None
            return usdt_balance
        except Exception as e:
            logging.error(f"An error occurred while fetching balance: {e}")
            return None
    
    def calc_order(self, usdt_balance: float, current_price: float, risk_percentage: float = 90.0) -> float:
        """Calculates the order size based on balance, price, and risk percentage."""
        risk_amount = usdt_balance * (risk_percentage / 100)
        order_size = risk_amount / current_price
        print(order_size)
        return order_size

    def place_order(self, side: str, amount: float) -> Optional[Dict[str, Union[int, str, float]]]:
        """Places an order (or simulates it if in dry run mode)."""
        if self.dry_run:
            simulated_order = {
                'id': len(self.simulated_orders) + 1,
                'timestamp': int(time.time() * 1000),
                'symbol': self.symbol,
                'side': side,
                'amount': amount,
                'price': self.market_data.get_current_price(self.symbol)
            }
            self.simulated_orders.append(simulated_order)
            logging.info(f"Simulated {side} order for {amount} {self.symbol}. Order ID: {simulated_order['id']}")
            return simulated_order
        try:
            order = self.market_data.exchange.create_market_order(self.symbol, side, amount)
            logging.info(f"Placed {side} order for {amount} {self.symbol}. Order ID: {order['id']}")
            return order
        except Exception as e:
            logging.error(f"An error occurred while placing order: {e}")
            return None

    def close_orders(self, side: str) -> None:
        """Closes open orders of the specified side (buy/sell). Simulates closing if in dry run mode."""
        if self.dry_run:
            for order in self.simulated_orders:
                if order['side'] == side:
                    current_price = self.market_data.get_current_price(self.symbol)
                    self.log_closed_trade(order, current_price)
                    logging.info(f"Simulated closing {side} order ID: {order['id']} for {self.symbol}")
            self.simulated_orders = [o for o in self.simulated_orders if o['side'] != side]
            return
        try:
            open_orders = self.market_data.exchange.fetch_open_orders(self.symbol)
            for order in open_orders:
                if order['side'] == side:
                    self.market_data.exchange.cancel_order(order['id'], self.symbol)
                    logging.info(f"Closed {side} order ID: {order['id']} for {self.symbol}")
                    self.log_closed_trade(order, float(order['price']))
        except Exception as e:
            logging.error(f"An error occurred while closing orders: {e}")

    def show_open_positions(self) -> str:
        """Returns a string representation of open positions."""
        if self.dry_run:
            positions = "Open Positions (Simulated):\n"
            for order in self.simulated_orders:
                positions += f"ID: {order['id']}, Symbol: {order['symbol']}, Side: {order['side']}, Amount: {order['amount']}, Price: {order['price']}\n"
            return positions if self.simulated_orders else "No open positions (Simulated)."
        try:
            open_orders = self.market_data.exchange.fetch_open_orders(self.symbol)
            positions = "Open Positions:\n"
            for order in open_orders:
                positions += f"ID: {order['id']}, Symbol: {order['symbol']}, Side: {order['side']}, Amount: {order['amount']}, Price: {order['price']}, Status: {order['status']}\n"
            return positions if open_orders else "No open positions."
        except Exception as e:
            logging.error(f"An error occurred while fetching open positions: {e}")
            return "An error occurred while fetching open positions."
        
    def execute_order(self) -> None:
        """Executes the trading strategy based on the latest market data."""
        try:
            ohlcv = self.market_data.fetch_data()
            logging.info(f"Fetched market data: {ohlcv}")
            self.market_data.save_to_db(ohlcv)
            df = self.strategy.read_price()
            df = self.strategy.calc_indicators(df)
            df = self.strategy.entry_signals(df)
            df = self.strategy.exit_signals(df)

            latest = df.iloc[-1]

            balance = self.get_balance()
            if balance is None:
                logging.error("Cannot execute order due to missing balance.")
                return
            current_price = latest['close']
            order_amount = self.calc_order(balance, current_price)

            if latest.get('enter_long') == 1:
                self.place_order('buy', order_amount)
            elif latest.get('enter_short') == 1:
                self.place_order('sell', order_amount)

            if latest.get('exit_long') == 1:
                self.close_orders('buy')
            elif latest.get('exit_short') == 1:
                self.close_orders('sell')
        except Exception as e:
            logging.error(f"An error occurred during order execution: {e}")

    def start_trading(self) -> None:
        """Starts the trading engine."""
        self.is_running = True
        while self.is_running:
            self.execute_order()
            time.sleep(60)

    def stop_trading(self) -> None:
        """Stops the trading engine."""
        self.is_running = False

#engine = TradingEngine(dry_run=True)
#engine.get_balance()
#engine.calc_order(1000.0, 4.925)
