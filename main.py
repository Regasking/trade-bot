import time
import logging
from datetime import datetime
from config import Config
from binance_client import BinanceClient
from mistral_agent import MistralAgent
from discord_bot import DiscordNotifier
from models import TradeSignal

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
        self.active_positions = {}
        self.daily_stats = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'profit': 0.0
        }
        self.last_daily_report = datetime.now().day
        
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
        
        order = self.binance.place_order(
            symbol=symbol,
            side='SELL',
            quantity=position['quantity']
        )
        
        if order:
            pnl = (current_price - position['entry']) * position['quantity']
            
            # Stats
            self.daily_stats['trades'] += 1
            if pnl > 0:
                self.daily_stats['wins'] += 1
            else:
                self.daily_stats['losses'] += 1
            self.daily_stats['profit'] += pnl
            
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
        
        if len(self.active_positions) >= Config.MAX_POSITIONS:
            logger.info(f"Max positions atteint ({Config.MAX_POSITIONS})")
            # Notification max positions
            self.discord.notify(f"⚠️ Max {Config.MAX_POSITIONS} positions atteint - Signal {signal.action} {signal.symbol} ignoré")
            return
        
        if signal.action == "HOLD":
            return
        
        if signal.action == "BUY":
            analysis = signal.analysis
            
            quantity = analysis.position_size_usd / analysis.entry_price
            
            order = self.binance.place_order(
                symbol=signal.symbol,
                side='BUY',
                quantity=round(quantity, 6)
            )
            
            if order:
                self.active_positions[signal.symbol] = {
                    'entry': analysis.entry_price,
                    'quantity': quantity,
                    'stop_loss': analysis.stop_loss,
                    'take_profit': analysis.take_profit
                }
                
                self.binance.place_stop_loss(
                    signal.symbol,
                    round(quantity, 6),
                    analysis.stop_loss
                )
                
                self.discord.notify_trade(
                    "BUY",
                    signal.symbol,
                    analysis.entry_price,
                    quantity,
                    analysis.reasoning
                )
                
                logger.info(f"Position ouverte {signal.symbol}: {quantity} @ ${analysis.entry_price}")
    
    def send_cycle_summary(self, balance: float):
        """Envoie résumé après chaque cycle"""
        
        positions_text = []
        for symbol in Config.SYMBOLS:
            if symbol in self.active_positions:
                pos = self.active_positions[symbol]
                current_price = self.binance.get_current_price(symbol)
                pnl_pct = ((current_price - pos['entry']) / pos['entry']) * 100
                emoji = "🟢" if pnl_pct > 0 else "🔴"
                positions_text.append(f"{emoji} **{symbol}**: {pnl_pct:+.2f}%")
            else:
                positions_text.append(f"⏸️ **{symbol}**: Pas de position")
        
        self.discord.notify(f"""
📊 **Résumé Cycle** - {datetime.now().strftime('%H:%M')}

{chr(10).join(positions_text)}

💰 **Balance**: ${balance:,.2f} USDT
📈 **Positions**: {len(self.active_positions)}/{Config.MAX_POSITIONS}
⏰ **Prochain cycle**: 1h
        """.strip())
    
    def send_daily_report(self, balance: float):
        """Rapport quotidien 7h"""
        
        win_rate = (self.daily_stats['wins'] / self.daily_stats['trades'] * 100) if self.daily_stats['trades'] > 0 else 0
        
        positions_summary = []
        total_unrealized = 0
        for symbol, pos in self.active_positions.items():
            current_price = self.binance.get_current_price(symbol)
            unrealized = (current_price - pos['entry']) * pos['quantity']
            total_unrealized += unrealized
            pnl_pct = ((current_price - pos['entry']) / pos['entry']) * 100
            emoji = "🟢" if unrealized > 0 else "🔴"
            positions_summary.append(f"{emoji} {symbol}: {pnl_pct:+.2f}% (${unrealized:+.2f})")
        
        self.discord.notify(f"""
📊 **RAPPORT QUOTIDIEN** - {datetime.now().strftime('%d/%m/%Y 07:00')}

💰 **Balance**: ${balance:,.2f} USDT
📈 **Positions actives**: {len(self.active_positions)}/{Config.MAX_POSITIONS}

{chr(10).join(positions_summary) if positions_summary else "Aucune position active"}

📊 **Stats 24h**:
• Trades: {self.daily_stats['trades']}
• Wins: {self.daily_stats['wins']} | Losses: {self.daily_stats['losses']}
• Win Rate: {win_rate:.1f}%
• P&L Réalisé: ${self.daily_stats['profit']:+.2f}
• P&L Non réalisé: ${total_unrealized:+.2f}

🎯 **Total**: ${self.daily_stats['profit'] + total_unrealized:+.2f}
        """.strip())
        
        # Reset stats
        self.daily_stats = {'trades': 0, 'wins': 0, 'losses': 0, 'profit': 0.0}
    
    def run_cycle(self):
        """Cycle d'analyse"""
        logger.info("=== NOUVEAU CYCLE ===")
        
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
            
            klines = self.binance.get_klines(symbol, Config.TIMEFRAME)
            if not klines:
                continue
            
            current_price = self.binance.get_current_price(symbol)
            if current_price == 0:
                continue
            
            signal = self.mistral.analyze_market(symbol, klines, current_price, balance)
            
            # Notification pour chaque analyse
            if signal.action == "HOLD":
                self.discord.notify(f"⏸️ **{symbol}**: HOLD (confiance {signal.analysis.confidence if signal.analysis else 0}%)")
            
            self.execute_signal(signal)
            
            time.sleep(2)
        
        # Résumé fin de cycle
        self.send_cycle_summary(balance)
    
    def run(self):
        """Boucle principale"""
        self.discord.notify("🤖 **Bot Trading démarré**")
        
        while True:
            try:
                # Check si 7h pour rapport quotidien
                now = datetime.now()
                if now.hour == 7 and now.day != self.last_daily_report:
                    balance = self.binance.get_account_balance()
                    self.send_daily_report(balance)
                    self.last_daily_report = now.day
                
                self.run_cycle()
                
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