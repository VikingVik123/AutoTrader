from engine import TradingEngine
from tele import TelegramBot
import logging

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,  # Set the minimum logging level to INFO
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()  # Output logs to the console
        ]
    )
    # Set the logging level for the 'httpx' logger to WARNING to suppress info-level logs
    logging.getLogger('httpx').setLevel(logging.WARNING)
    # Create instances of the trading engine and bot
    engine = TradingEngine()
    bot = TelegramBot(engine)
    
    # Run the bot
    bot.run()
