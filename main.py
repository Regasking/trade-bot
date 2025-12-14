import time
import logging
from datetime import datetime
from config import Config
from binance_client import BinanceClient
from mistral_agent import MistralAgent
from discord_bot import DiscordNotifier
from models import TradeSignal

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.binance = BinanceClient()
        self.mistral = MistralAgent()
        self.discord = DiscordNotifier()
        self.active_positions = {}  # {symbol: {entry, quantity, stop_order_id}}
        
    def check_stop_loss_hit(self, symbol: str):
        """Vérifie si stop loss touché"""
        if symbol not in self.active_positions:
            return False
        
        current_price = self.binance.get_current_price(symbol)
        position = self.active_positions[symbol]
        
        if current_price <= position['stop_loss']:
            logger.warning(f"Stop loss HIT {symbol}: {current_price}")
            self.close_position(symbol, "STOP_LOSS")
            return True
        
        if current_price >= position['take_profit']:
            logger.info(f"Take profit HIT {symbol}: {current_price}")
            self.close_position(symbol, "TAKE_PROFIT")
            return True
        
        return False
    
    def close_position(self, symbol: str, reason: str):
        """Ferme position"""
        if symbol not in self.active_positions:
            return
        
        position = self.active_positions[symbol]
        current_price = self.binance.get_current_price(symbol)
        
        # Vend
        order = self.binance.place_order(
            symbol=symbol,
            side='SELL',
            quantity=position['quantity']
        )
        
        if order:
            pnl = (current_price - position['entry']) * position['quantity']
            
            if reason == "STOP_LOSS":
                self.discord.notify_stop_loss(
                    symbol, position['entry'], current_price, abs(pnl)
                )
            elif reason == "TAKE_PROFIT":
                self.discord.notify_take_profit(
                    symbol, position['entry'], current_price, pnl
                )
            
            del self.active_positions[symbol]
            logger.info(f"Position fermée {symbol}: PnL ${pnl:.2f}")
    
    def execute_signal(self, signal: TradeSignal):
        """Exécute signal trading"""
        
        # Max positions
        if len(self.active_positions) >= Config.MAX_POSITIONS:
            logger.info(f"Max positions atteint ({Config.MAX_POSITIONS})")
            return
        
        if signal.action == "HOLD":
            return
        
        if signal.action == "BUY":
            analysis = signal.analysis
            
            # Calcul quantité
            quantity = analysis.position_size_usd / analysis.entry_price
            
            # Place ordre BUY
            order = self.binance.place_order(
                symbol=signal.symbol,
                side='BUY',
                quantity=round(quantity, 6)
            )
            
            if order:
                # Enregistre position
                self.active_positions[signal.symbol] = {
                    'entry': analysis.entry_price,
                    'quantity': quantity,
                    'stop_loss': analysis.stop_loss,
                    'take_profit': analysis.take_profit
                }
                
                # Place stop loss
                self.binance.place_stop_loss(
                    signal.symbol,
                    round(quantity, 6),
                    analysis.stop_loss
                )
                
                # Notif
                self.discord.notify_trade(
                    "BUY",
                    signal.symbol,
                    analysis.entry_price,
                    quantity,
                    analysis.reasoning
                )
                
                logger.info(f"Position ouverte {signal.symbol}: {quantity} @ ${analysis.entry_price}")
    
    def run_cycle(self):
        """Cycle d'analyse"""
        logger.info("=== NOUVEAU CYCLE ===")
        
        # Balance
        balance = self.binance.get_account_balance()
        logger.info(f"Balance: ${balance:.2f}")
        
        # Check positions actives
        for symbol in list(self.active_positions.keys()):
            self.check_stop_loss_hit(symbol)
        
        # Analyse chaque symbole
        for symbol in Config.SYMBOLS:
            if symbol in self.active_positions:
                logger.info(f"{symbol}: Position active, skip")
                continue
            
            # Récupère données
            klines = self.binance.get_klines(symbol, Config.TIMEFRAME)
            if not klines:
                continue
            
            current_price = self.binance.get_current_price(symbol)
            if current_price == 0:
                continue
            
            # Demande à Mistral
            signal = self.mistral.analyze_market(symbol, klines, current_price, balance)
            
            # Exécute
            self.execute_signal(signal)
            
            time.sleep(2)  # Rate limit
    
    def run(self):
        """Boucle principale"""
        self.discord.notify("🤖 **Bot Trading démarré**")
        
        while True:
            try:
                self.run_cycle()
                
                # Sleep 4h
                sleep_seconds = Config.CHECK_INTERVAL_HOURS * 3600
                logger.info(f"Sleep {Config.CHECK_INTERVAL_HOURS}h...")
                time.sleep(sleep_seconds)
                
            except KeyboardInterrupt:
                logger.info("Arrêt bot...")
                self.discord.notify("⛔ Bot arrêté manuellement")
                break
            except Exception as e:
                logger.error(f"ERREUR CRITIQUE: {e}", exc_info=True)
                self.discord.notify(f"❌ Erreur: {str(e)}")
                time.sleep(60)

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()