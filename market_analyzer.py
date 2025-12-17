import pandas as pd
import ta
from binance_client import BinanceClient
import logging

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    def __init__(self, binance_client: BinanceClient):
        self.binance = binance_client
    
    def get_market_trend(self, symbol: str) -> str:
        """Détermine tendance globale: BULL, BEAR, SIDEWAYS"""
        try:
            # Analyse sur timeframe journalier
            klines = self.binance.get_klines(symbol, "1d", 200)
            if not klines:
                return "NEUTRAL"
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['close'] = pd.to_numeric(df['close'])
            
            # EMA 50 et 200
            ema_50 = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator().iloc[-1]
            ema_200 = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator().iloc[-1]
            
            # Détermination tendance
            if ema_50 > ema_200 * 1.02:
                trend = "BULL"
            elif ema_50 < ema_200 * 0.98:
                trend = "BEAR"
            else:
                trend = "SIDEWAYS"
            
            logger.info(f"{symbol} Tendance globale: {trend} (EMA50: {ema_50:.2f}, EMA200: {ema_200:.2f})")
            return trend
            
        except Exception as e:
            logger.error(f"Erreur get_market_trend: {e}")
            return "NEUTRAL"
    
    def multi_timeframe_analysis(self, symbol: str) -> dict:
        """Analyse sur 3 timeframes"""
        try:
            # 1 jour - Tendance long terme
            daily = self._analyze_timeframe(symbol, "1d", 50)
            
            # 4 heures - Tendance moyen terme
            h4 = self._analyze_timeframe(symbol, "4h", 50)
            
            # 1 heure - Signal court terme
            h1 = self._analyze_timeframe(symbol, "1h", 50)
            
            # Score d'alignement
            alignment_score = 0
            if daily['trend'] == "BULL":
                alignment_score += 3
            if h4['trend'] == "BULL":
                alignment_score += 2
            if h1['trend'] == "BULL":
                alignment_score += 1
            
            return {
                'daily': daily,
                'h4': h4,
                'h1': h1,
                'alignment_score': alignment_score,  # 0-6
                'recommendation': self._get_recommendation(alignment_score)
            }
            
        except Exception as e:
            logger.error(f"Erreur multi_timeframe_analysis: {e}")
            return {'recommendation': 'HOLD', 'alignment_score': 0}
    
    def _analyze_timeframe(self, symbol: str, timeframe: str, limit: int) -> dict:
        """Analyse un timeframe spécifique"""
        try:
            klines = self.binance.get_klines(symbol, timeframe, limit)
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            
            # RSI
            rsi = ta.momentum.RSIIndicator(df['close'], window=14).rsi().iloc[-1]
            
            # MACD
            macd = ta.trend.MACD(df['close'])
            macd_line = macd.macd().iloc[-1]
            macd_signal = macd.macd_signal().iloc[-1]
            
            # EMA 20 vs 50
            ema_20 = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator().iloc[-1]
            ema_50 = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator().iloc[-1]
            
            # Détermination tendance
            if ema_20 > ema_50 and macd_line > macd_signal and rsi < 70:
                trend = "BULL"
            elif ema_20 < ema_50 and macd_line < macd_signal and rsi > 30:
                trend = "BEAR"
            else:
                trend = "NEUTRAL"
            
            return {
                'trend': trend,
                'rsi': rsi,
                'macd': macd_line - macd_signal,
                'ema_cross': ema_20 > ema_50
            }
            
        except Exception as e:
            logger.error(f"Erreur _analyze_timeframe: {e}")
            return {'trend': 'NEUTRAL', 'rsi': 50, 'macd': 0, 'ema_cross': False}
    
    def _get_recommendation(self, alignment_score: int) -> str:
        """Recommandation selon score d'alignement"""
        if alignment_score >= 5:
            return "STRONG_BUY"  # Tous timeframes bullish
        elif alignment_score >= 3:
            return "BUY"  # Majorité bullish
        elif alignment_score <= 1:
            return "STRONG_SELL"  # Majorité bearish
        else:
            return "HOLD"  # Mixte
    
    def calculate_dynamic_tp_sl(self, symbol: str, entry_price: float) -> dict:
        """Calcule TP/SL dynamiques selon volatilité"""
        try:
            klines = self.binance.get_klines(symbol, "4h", 50)
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            
            # ATR (Average True Range) = volatilité
            atr_indicator = ta.volatility.AverageTrueRange(
                df['high'], df['low'], df['close'], window=14
            )
            atr = atr_indicator.average_true_range().iloc[-1]
            
            atr_pct = (atr / entry_price) * 100
            
            # Ajuste TP/SL selon volatilité
            if atr_pct < 2:  # Faible volatilité
                tp_pct = 0.04  # +4%
                sl_pct = 0.02  # -2%
            elif atr_pct < 4:  # Moyenne volatilité
                tp_pct = 0.06  # +6%
                sl_pct = 0.03  # -3%
            else:  # Forte volatilité
                tp_pct = 0.10  # +10%
                sl_pct = 0.04  # -4%
            
            return {
                'take_profit': entry_price * (1 + tp_pct),
                'stop_loss': entry_price * (1 - sl_pct),
                'atr_pct': atr_pct,
                'tp_pct': tp_pct * 100,
                'sl_pct': sl_pct * 100
            }
            
        except Exception as e:
            logger.error(f"Erreur calculate_dynamic_tp_sl: {e}")
            return {
                'take_profit': entry_price * 1.06,
                'stop_loss': entry_price * 0.97,
                'atr_pct': 3.0,
                'tp_pct': 6.0,
                'sl_pct': 3.0
            }
    
    def get_market_sentiment(self) -> dict:
        """Récupère Fear & Greed Index"""
        try:
            import requests
            response = requests.get("https://api.alternative.me/fng/", timeout=5)
            data = response.json()['data'][0]
            
            fng_value = int(data['value'])
            
            if fng_value < 25:
                sentiment = "EXTREME_FEAR"
                bias = "BULLISH"  # Bon moment pour acheter
            elif fng_value < 45:
                sentiment = "FEAR"
                bias = "NEUTRAL_BULLISH"
            elif fng_value < 55:
                sentiment = "NEUTRAL"
                bias = "NEUTRAL"
            elif fng_value < 75:
                sentiment = "GREED"
                bias = "NEUTRAL_BEARISH"
            else:
                sentiment = "EXTREME_GREED"
                bias = "BEARISH"  # Éviter les achats
            
            logger.info(f"Fear & Greed Index: {fng_value} ({sentiment})")
            
            return {
                'value': fng_value,
                'sentiment': sentiment,
                'bias': bias
            }
            
        except Exception as e:
            logger.error(f"Erreur get_market_sentiment: {e}")
            return {'value': 50, 'sentiment': 'NEUTRAL', 'bias': 'NEUTRAL'}
