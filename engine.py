import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Union
from data import MarketData
from strategy import Strategy
import time
import threading
from monitor import TradeMonitor

class TradingEngine:
    def __init__(self, dry_run: bool = True) -> None:
        self.market_data = MarketData()
        self.strategy = Strategy()
        self.symbol: str = 'RUNE/USDT'
        self.is_running: bool = False
        self.dry_run: bool = dry_run
        self.simulated_balance: float = 10000.0  # Simulated USDT balance for dry run mode
        self.simulated_orders: List[Dict[str, Union[int, str, float]]] = []  # Track simulated orders
        self.open_position: Optional[Dict[str, Union[int, str, float]]] = None  # Track the open position
        
        # Initialize database and create table if it doesn't exist
        self.initialize_database()
        self.trade_monitor = TradeMonitor()

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
        return order_size

    def place_order(self, side: str, amount: float) -> Optional[Dict[str, Union[int, str, float]]]:
        """Places an order (or simulates it if in dry run mode)."""
        current_price = self.market_data.get_current_price(self.symbol)
        if current_price is None:
            logging.error("Current price could not be fetched; order not placed.")
            return None

        if self.dry_run:
            simulated_order = {
                'id': len(self.simulated_orders) + 1,
                'timestamp': int(time.time() * 1000),
                'symbol': self.symbol,
                'side': side,
                'amount': amount,
                'price': current_price
            }

        # Update the simulated balance based on the side of the order
            if side == 'buy':
                cost = current_price * amount
                if self.simulated_balance >= cost:
                    self.simulated_balance -= cost
                    logging.info(f"Simulated buy order for {amount} {self.symbol} at {current_price}. New balance: {self.simulated_balance} USDT.")
                else:
                    logging.warning("Insufficient balance for simulated buy order.")
                    return None
            elif side == 'sell':
                # For simplicity, assume that the amount to sell is always available in the simulated context
                revenue = current_price * amount
                self.simulated_balance += revenue
                logging.info(f"Simulated sell order for {amount} {self.symbol} at {current_price}. New balance: {self.simulated_balance} USDT.")

            self.simulated_orders.append(simulated_order)
            return simulated_order
        else:
            try:
                order = self.market_data.exchange.create_market_order(self.symbol, side, amount)
                logging.info(f"Placed {side} order for {amount} {self.symbol}. Order ID: {order['id']}")
                return order
            except Exception as e:
                logging.error(f"An error occurred while placing order: {e}")
                return None

    def close_orders(self, side: str) -> None:
        """Closes open orders of the specified side (buy/sell). Simulates closing if in dry run mode."""
        current_price = self.market_data.get_current_price(self.symbol)
        if current_price is None:
            logging.error("Current price could not be fetched; cannot close orders.")
            return

        if self.dry_run:
            closed_orders = []
            for order in self.simulated_orders:
                if order['side'] == side:
                    # Calculate profit/loss based on the current price
                    if side == 'buy':
                        profit = (current_price - order['price']) * order['amount']
                        self.simulated_balance += current_price * order['amount']
                    else:  # side == 'sell'
                        profit = (order['price'] - current_price) * order['amount']
                        self.simulated_balance += current_price * order['amount']

                    self.log_closed_trade(order, current_price)
                    closed_orders.append(order)
                    logging.info(f"Closed simulated {side} order ID: {order['id']} for {self.symbol}. Profit/Loss: {profit}. New balance: {self.simulated_balance} USDT")

            # Remove closed orders from the list
            self.simulated_orders = [o for o in self.simulated_orders if o not in closed_orders]
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

            # Check if there is an open position
            if self.open_position is None:
                # Enter long or short only if there's no open position
                if latest.get('enter_long') == 1:
                    order = self.place_order('buy', order_amount)
                    if order:
                        self.open_position = order
                elif latest.get('enter_short') == 1:
                    order = self.place_order('sell', order_amount)
                    if order:
                        self.open_position = order
            else:
                # If there is an open position, check if an exit signal is given
                if self.open_position['side'] == 'buy' and latest.get('exit_long') == 1:
                    self.close_orders('buy')
                    self.open_position = None  # Clear the open position after closing
                elif self.open_position['side'] == 'sell' and latest.get('exit_short') == 1:
                    self.close_orders('sell')
                    self.open_position = None  # Clear the open position after closing

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

    def get_trade_status(self) -> str:
        """Returns a status report of the current open trade if any."""
        if self.open_position:
            current_price = self.market_data.get_current_price(self.symbol)
            if current_price is None:
                logging.error("Current price could not be fetched; cannot provide status.")
                return "Unable to fetch the current price."

            order_side = self.open_position['side']
            order_price = self.open_position['price']
            order_amount = self.open_position['amount']
            profit_loss = (current_price - order_price) * order_amount if order_side == 'buy' else (order_price - current_price) * order_amount

            status = f"""
            Open Position:
            ID: {self.open_position['id']}
            Symbol: {self.symbol}
            Side: {order_side.capitalize()}
            Amount: {order_amount}
            Entry Price: {order_price}
            Current Price: {current_price}
            Profit/Loss: {profit_loss:.2f} USDT
            """
            return status
        else:
            return "No open positions currently."


if __name__ == '__main__':

    engine = TradingEngine(dry_run=True)
    bal = engine.get_balance()
    print(bal)
    order = engine.calc_order(1000.0, 4.925)
    print(order)
    engine_test_price = engine.place_order('buy', 100)
    print(engine_test_price)
    close = engine.close_orders('sell')
    print(close)
    stat = engine.get_trade_status()
    print(stat)
