import logging
import threading
from typing import Optional
from config import TELEGRAM_TOKEN
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackContext

class TelegramBot:
    def __init__(self, trading_engine) -> None:
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.trading_engine = trading_engine
        self.trading_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()  # Lock for thread safety

        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("stats", self.stats))
        self.application.add_handler(CommandHandler("stop", self.stop))
        self.application.add_handler(CommandHandler("balance", self.balance))
        self.application.add_handler(CommandHandler("positions", self.positions))
        self.application.add_handler(CommandHandler("runbot", self.runbot))
        self.application.add_handler(CommandHandler("stopbot", self.stopbot))
        self.application.add_handler(CommandHandler("status", self.status))

        self.reply_keyboard = [['/start', '/stats', '/stop'], ['/balance', '/positions', '/status'], ['/runbot', '/stopbot']]
        self.reply_markup = ReplyKeyboardMarkup(self.reply_keyboard, resize_keyboard=True)

    async def start(self, update: Update, context: CallbackContext) -> None:
        await update.message.reply_text(
            "Welcome To AutoTrader",
            reply_markup=self.reply_markup
        )

    async def stats(self, update: Update, context: CallbackContext) -> None:
        try:
            stats = self.trading_engine.show_trade_stats()
            await update.message.reply_text(stats)
        except Exception as e:
            logging.error(f"Error fetching stats: {e}")
            await update.message.reply_text("An error occurred while fetching stats.")

    async def stop(self, update: Update, context: CallbackContext) -> None:
        await update.message.reply_text("Bot stopped!")

    async def balance(self, update: Update, context: CallbackContext) -> None:
        try:
            balance = self.trading_engine.get_balance()
            if balance is not None:
                await update.message.reply_text(f"Balance: {balance}")
            else:
                await update.message.reply_text("Unable to fetch balance.")
        except Exception as e:
            logging.error(f"Error fetching balance: {e}")
            await update.message.reply_text("An error occurred while fetching the balance.")

    async def positions(self, update: Update, context: CallbackContext) -> None:
        try:
            positions = self.trading_engine.show_open_positions()
            await update.message.reply_text(positions)
        except Exception as e:
            logging.error(f"Error fetching positions: {e}")
            await update.message.reply_text("An error occurred while fetching open positions.")

    async def status(self, update: Update, context: CallbackContext) -> None:
        try:
            status = self.trading_engine.get_trade_status()
            await update.message.reply_text(status)
        except Exception as e:
            logging.error(f"Error fetching status: {e}")
            await update.message.reply_text("An error occurred while fetching the status.")

    async def runbot(self, update: Update, context: CallbackContext) -> None:
        with self.lock:
            if not self.trading_engine.is_running:
                self.trading_engine.is_running = True
                self.trading_thread = threading.Thread(target=self.trading_engine.start_trading, daemon=True)
                self.trading_thread.start()
                logging.info("Trading bot started.")
                await update.message.reply_text("Trading bot started!")
            else:
                logging.info("Attempted to start bot when it's already running.")
                await update.message.reply_text("Trading bot is already running.")

    async def stopbot(self, update: Update, context: CallbackContext) -> None:
        with self.lock:
            if self.trading_engine.is_running:
                self.trading_engine.stop_trading()
                if self.trading_thread:
                    self.trading_thread.join()
                logging.info("Trading bot stopped.")
                await update.message.reply_text("Trading bot stopped!")
            else:
                logging.info("Attempted to stop bot when it's not running.")
                await update.message.reply_text("Trading bot is not running.")

    def run(self) -> None:
        try:
            logging.info("Telegram bot is starting...")
            self.application.run_polling()
        except Exception as e:
            logging.error(f"Error running the bot: {e}")
