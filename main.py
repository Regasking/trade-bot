import time
import logging
from datetime import datetime
import importlib
from config import Config
from binance_client import BinanceClient
from mistral_agent import MistralAgent
from discord_bot import DiscordNotifier
from models import TradeSignal

# Import nouvelles classes PRO
try:
    _market_mod = importlib.import_module("market_analyzer")
    _pos_mod = importlib.import_module("position_manager")
    _strat_mod = importlib.import_module("strategy_optimizer")
    MarketAnalyzer = getattr(_market_mod, "MarketAnalyzer")
    PositionManager = getattr(_pos_mod, "PositionManager")
    StrategyOptimizer = getattr(_strat_mod, "StrategyOptimizer")
    PRO_MODE = True
    logger_name = "TradingBotPRO"
except Exception:
    PRO_MODE = False
    logger_name = "TradingBot"
    print("⚠️ Mode Standard: market_analyzer, position_manager ou strategy_optimizer non trouvés")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(logger_name)

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
        
        # Activation mode PRO si modules disponibles
        if PRO_MODE:
            self.market_analyzer = MarketAnalyzer(self.binance)
            self.position_manager = PositionManager(self.binance)
            logger.info("🚀 MODE PRO ACTIVÉ: Multi-TF + Trailing SL + Pyramiding")
        else:
            logger.info("📊 MODE STANDARD")
        
    def check_stop_loss_hit(self, symbol: str):
        """Vérifie si stop loss/take profit touché"""
        if symbol not in self.active_positions:
            return False
        
        position = self.active_positions[symbol]
        current_price = self.binance.get_current_price(symbol)
        
        # Check si les ordres stop-loss existent encore
        open_orders = self.binance.get_open_orders(symbol)
        
        # Si plus d'ordres stop-loss = position fermée automatiquement
        if not open_orders:
            # Position vendue automatiquement par Binance
            pnl = (current_price - position['entry']) * position['quantity']
            
            # Détermine si c'était stop-loss ou take-profit
            if current_price <= position['stop_loss']:
                logger.warning(f"⛔ Stop loss auto-exécuté {symbol}")
                self.discord.notify_stop_loss(
                    symbol, position['entry'], current_price, abs(pnl)
                )
                reason = "STOP_LOSS"
            else:
                logger.info(f"🎯 Take profit auto-exécuté {symbol}")
                self.discord.notify_take_profit(
                    symbol, position['entry'], current_price, pnl
                )
                reason = "TAKE_PROFIT"
            
            # Stats
            self.daily_stats['trades'] += 1
            if pnl > 0:
                self.daily_stats['wins'] += 1
            else:
                self.daily_stats['losses'] += 1
            self.daily_stats['profit'] += pnl
            
            del self.active_positions[symbol]
            logger.info(f"Position auto-fermée {symbol}: PnL ${pnl:.2f}")
            return True
        
        # Check manuel si prix atteint les seuils
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
        """Ferme position manuellement"""
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
    
    def update_trailing_stops_pro(self):
        """Met à jour trailing stops (MODE PRO)"""
        if not PRO_MODE:
            return
        
        for symbol in list(self.active_positions.keys()):
            position = self.active_positions[symbol]
            current_price = self.binance.get_current_price(symbol)
            
            # Trailing stop
            trailing_result = self.position_manager.update_trailing_stop(
                symbol, position, current_price
            )
            
            if trailing_result['updated']:
                position['stop_loss'] = trailing_result['stop_loss']
                
                # Annule ancien stop + place nouveau
                open_orders = self.binance.get_open_orders(symbol)
                for order in open_orders:
                    if order['type'] == 'STOP_LOSS_LIMIT':
                        self.binance.cancel_order(symbol, order['orderId'])
                
                new_stop_order = self.binance.place_stop_loss(
                    symbol,
                    position['quantity'],
                    position['stop_loss']
                )
                
                if new_stop_order:
                    self.discord.notify(
                        f"🔄 **Trailing Stop {symbol}**\n"
                        f"Nouveau stop: ${position['stop_loss']:.2f}\n"
                        f"Profit sécurisé: {trailing_result['profit_locked']:.2f}%"
                    )
    
    def check_pyramiding_pro(self):
        """Vérifie possibilité pyramiding (MODE PRO)"""
        if not PRO_MODE:
            return
        
        for symbol in list(self.active_positions.keys()):
            position = self.active_positions[symbol]
            current_price = self.binance.get_current_price(symbol)
            
            if self.position_manager.should_add_to_position(position, current_price):
                self.add_to_position_pro(symbol, position, current_price)
    
    def add_to_position_pro(self, symbol: str, position: dict, current_price: float):
        """Ajoute à position (pyramiding)"""
        pyramid_count = position.get('pyramid_count', 0)
        original_size_usd = position['entry'] * position.get('original_quantity', position['quantity'])
        
        pyramid_size_usd = self.position_manager.calculate_pyramid_size(
            original_size_usd, pyramid_count
        )
        
        if pyramid_size_usd > 0:
            pyramid_quantity = pyramid_size_usd / current_price
            
            order = self.binance.place_order(
                symbol=symbol,
                side='BUY',
                quantity=pyramid_quantity
            )
            
            if order:
                # Mise à jour position
                if 'original_quantity' not in position:
                    position['original_quantity'] = position['quantity']
                
                total_qty = position['quantity'] + pyramid_quantity
                avg_entry = (
                    (position['entry'] * position['quantity'] + current_price * pyramid_quantity)
                    / total_qty
                )
                
                position['quantity'] = total_qty
                position['entry'] = avg_entry
                position['pyramid_count'] = pyramid_count + 1
                
                # Recalcule TP/SL
                tp_sl = self.market_analyzer.calculate_dynamic_tp_sl(symbol, avg_entry)
                position['take_profit'] = tp_sl['take_profit']
                position['stop_loss'] = tp_sl['stop_loss']
                
                self.discord.notify(
                    f"🔺 **Pyramiding {symbol}**\n"
                    f"Ajouté: {pyramid_quantity:.6f} @ ${current_price:,.2f}\n"
                    f"Nouvelle moyenne: ${avg_entry:,.2f}\n"
                    f"Pyramide #{pyramid_count + 1}"
                )
                
                logger.info(f"Pyramiding {symbol}: +{pyramid_quantity:.6f} @ ${current_price:.2f}")
    
    def execute_signal(self, signal: TradeSignal, market_context: dict = None):
        """Exécute signal trading"""
        
        if len(self.active_positions) >= Config.MAX_POSITIONS:
            logger.info(f"Max positions atteint ({Config.MAX_POSITIONS})")
            self.discord.notify(f"⚠️ Max {Config.MAX_POSITIONS} positions atteint - Signal {signal.action} {signal.symbol} ignoré")
            return
        
        if signal.action == "HOLD":
            return
        
        if signal.action == "BUY":
            analysis = signal.analysis
            balance = self.binance.get_account_balance()
            
            # MODE PRO: Filtre stratégique
            if PRO_MODE and market_context:
                decision = StrategyOptimizer.should_trade(
                    market_trend=market_context['market_trend'],
                    multi_tf=market_context['multi_tf'],
                    sentiment=market_context['sentiment'],
                    confidence=analysis.confidence
                )
                
                if not decision['should_trade']:
                    logger.info(f"Trade refusé {signal.symbol}: {decision['reason']}")
                    self.discord.notify(
                        f"🚫 **Trade refusé {signal.symbol}**\n"
                        f"Raison: {decision['reason']}\n"
                        f"Score: {decision['score']}/10"
                    )
                    return
            
            # Calcul taille position
            if PRO_MODE and market_context:
                position_size_usd = self.position_manager.calculate_position_size(
                    balance,
                    analysis.confidence,
                    market_context['market_trend']
                )
            else:
                # Mode standard: 2% fixe
                position_size_usd = balance * (Config.MAX_RISK_PERCENT / 100)
            
            if position_size_usd < 10:
                logger.warning(f"Position size trop petite: ${position_size_usd:.2f}")
                return
            
            # TP/SL dynamiques (PRO) ou fixes (Standard)
            if PRO_MODE:
                tp_sl = self.market_analyzer.calculate_dynamic_tp_sl(
                    signal.symbol,
                    analysis.entry_price
                )
            else:
                tp_sl = {
                    'take_profit': analysis.take_profit,
                    'stop_loss': analysis.stop_loss,
                    'tp_pct': 6.0,
                    'sl_pct': 3.0
                }
            
            quantity = position_size_usd / analysis.entry_price
            
            order = self.binance.place_order(
                symbol=signal.symbol,
                side='BUY',
                quantity=round(quantity, 6)
            )
            
            if order:
                self.active_positions[signal.symbol] = {
                    'symbol': signal.symbol,
                    'entry': analysis.entry_price,
                    'quantity': quantity,
                    'original_quantity': quantity,
                    'stop_loss': tp_sl['stop_loss'],
                    'take_profit': tp_sl['take_profit'],
                    'pyramid_count': 0
                }
                
                if PRO_MODE and market_context:
                    self.active_positions[signal.symbol]['market_context'] = market_context
                
                self.binance.place_stop_loss(
                    signal.symbol,
                    round(quantity, 6),
                    tp_sl['stop_loss']
                )
                
                # Notification
                notif_text = (
                    f"🟢 **BUY {signal.symbol}**\n\n"
                    f"💰 **Prix:** ${analysis.entry_price:,.2f}\n"
                    f"📊 **Quantité:** {quantity:.6f}\n"
                    f"💵 **Montant:** ${position_size_usd:,.2f}\n\n"
                    f"🎯 **Take-Profit:** ${tp_sl['take_profit']:,.2f} (+{tp_sl['tp_pct']:.1f}%)\n"
                    f"⛔ **Stop-Loss:** ${tp_sl['stop_loss']:,.2f} (-{tp_sl['sl_pct']:.1f}%)\n"
                )
                
                if PRO_MODE and market_context:
                    notif_text += (
                        f"\n📈 **Contexte PRO:**\n"
                        f"• Tendance: {market_context['market_trend']}\n"
                        f"• Multi-TF: {market_context['multi_tf']['recommendation']}\n"
                        f"• Sentiment: {market_context['sentiment']['sentiment']}\n"
                        f"• Confiance IA: {analysis.confidence}%\n"
                    )
                
                notif_text += f"\n💡 **Raison:** {analysis.reasoning}"
                
                self.discord.notify(notif_text)
                
                logger.info(f"Position ouverte {signal.symbol}: {quantity:.6f} @ ${analysis.entry_price:.2f}")
    
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
        
        mode_label = "PRO" if PRO_MODE else "Standard"
        
        self.discord.notify(
            f"📊 **Résumé Cycle ({mode_label})** - {datetime.now().strftime('%H:%M')}\n\n"
            f"{chr(10).join(positions_text)}\n\n"
            f"💰 **Balance**: ${balance:,.2f} USDT\n"
            f"📈 **Positions**: {len(self.active_positions)}/{Config.MAX_POSITIONS}\n"
            f"⏰ **Prochain cycle**: {Config.CHECK_INTERVAL_HOURS}h"
        )
    
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
        
        mode_label = "PRO" if PRO_MODE else "Standard"
        
        self.discord.notify(
            f"📊 **RAPPORT QUOTIDIEN ({mode_label})** - {datetime.now().strftime('%d/%m/%Y 07:00')}\n\n"
            f"💰 **Balance**: ${balance:,.2f} USDT\n"
            f"📈 **Positions actives**: {len(self.active_positions)}/{Config.MAX_POSITIONS}\n\n"
            f"{chr(10).join(positions_summary) if positions_summary else 'Aucune position active'}\n\n"
            f"📊 **Stats 24h**:\n"
            f"• Trades: {self.daily_stats['trades']}\n"
            f"• Wins: {self.daily_stats['wins']} | Losses: {self.daily_stats['losses']}\n"
            f"• Win Rate: {win_rate:.1f}%\n"
            f"• P&L Réalisé: ${self.daily_stats['profit']:+.2f}\n"
            f"• P&L Non réalisé: ${total_unrealized:+.2f}\n\n"
            f"🎯 **Total**: ${self.daily_stats['profit'] + total_unrealized:+.2f}"
        )
        
        # Reset stats
        self.daily_stats = {'trades': 0, 'wins': 0, 'losses': 0, 'profit': 0.0}
    
    def run_cycle(self):
        """Cycle d'analyse"""
        mode_label = "PRO" if PRO_MODE else "STANDARD"
        logger.info(f"=== NOUVEAU CYCLE ({mode_label}) ===")
        
        balance = self.binance.get_account_balance()
        logger.info(f"Balance: ${balance:.2f}")
        
        # Contexte marché global (MODE PRO)
        market_context = None
        if PRO_MODE:
            sentiment = self.market_analyzer.get_market_sentiment()
        
        # Check positions actives
        for symbol in list(self.active_positions.keys()):
            self.check_stop_loss_hit(symbol)
        
        # Update trailing stops (PRO)
        if PRO_MODE:
            self.update_trailing_stops_pro()
            self.check_pyramiding_pro()
        
        # Analyse chaque symbole
        for symbol in Config.SYMBOLS:
            if symbol in self.active_positions:
                logger.info(f"{symbol}: Position active, skip")
                continue
            
            # Contexte marché (PRO)
            if PRO_MODE:
                market_trend = self.market_analyzer.get_market_trend(symbol)
                multi_tf = self.market_analyzer.multi_timeframe_analysis(symbol)
                
                market_context = {
                    'market_trend': market_trend,
                    'multi_tf': multi_tf,
                    'sentiment': sentiment
                }
            
            klines = self.binance.get_klines(symbol, Config.TIMEFRAME)
            if not klines:
                continue
            
            current_price = self.binance.get_current_price(symbol)
            if current_price == 0:
                continue
            
            signal = self.mistral.analyze_market(symbol, klines, current_price, balance)
            
            # Notification pour chaque analyse
            if signal.action == "HOLD":
                hold_text = f"⏸️ **{symbol}**: HOLD (confiance {signal.analysis.confidence if signal.analysis else 0}%)"
                if PRO_MODE and market_context:
                    hold_text += f"\nTendance: {market_context['market_trend']}, Multi-TF: {market_context['multi_tf']['recommendation']}"
                self.discord.notify(hold_text)
            
            self.execute_signal(signal, market_context)
            
            time.sleep(2)
        
        # Résumé fin de cycle
        self.send_cycle_summary(balance)
    
    def run(self):
        """Boucle principale"""
        mode_label = "PRO 🚀" if PRO_MODE else "Standard 📊"
        self.discord.notify(f"🤖 **Bot Trading {mode_label} démarré**")
        
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