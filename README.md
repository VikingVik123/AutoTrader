# AUTOTRADER
Your gateway to stressfree trading.

## Overview
An automated trading bot built with Python, controlled entirely through Telegram

## Features
Telegram Command Interface: Control all functionalities directly through Telegram commands.

Automated Trading Strategies: Executes buy/sell orders based on predefined strategies.

Account Management: Check balance, view open trades, and track profit/loss.

## Libraries
ccxt
pandas
pandas_ta
python_telegram_bot
requests

## Setup and Installation
1. Clone the repository
2. Navigate in project directory
3. Create and activate a virtual environment (optional but recommended)
    python -m venv venv
4. Install the required dependencies
    pip install -r requirements.txt
5. Setup environment variables
    Fill in your credentials in the config file(api key generated from binance, telegram token generated from telegram botfather)
6. run ./main.py

## Usage
1. /runbot - to start the trading bot
2. /balance - Shows the current balance of your account.
3. /stats - shows closed trades
4. /status - monitors open trades
5. /positions - shows open positions
6. /stopbot - stops the trading bot

## Future Improvements
1. Multi-Exchange Support: Allow the bot to operate on multiple exchanges simultaneously.
2. RPC Manager: Streamline communications between trading engine and telegram, also enabling realtime updates
3. Backtesting Framework: Add a feature for users to backtest strategies using historical data.
4. Trading Mode: Add a command to switch between paper and real trading 