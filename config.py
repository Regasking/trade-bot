import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Binance
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
    BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
    
    # Claude
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    
    # Mistral
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    
    # Discord
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    # Trading
    SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    TIMEFRAME = "4h"
    MAX_RISK_PERCENT = float(os.getenv("MAX_RISK_PERCENT", "2.0"))
    MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "2"))
    STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", "3.0"))
    CHECK_INTERVAL_HOURS = int(os.getenv("CHECK_INTERVAL_HOURS", "4"))
    
    # URLs
    BINANCE_TESTNET_URL = "https://testnet.binance.vision"