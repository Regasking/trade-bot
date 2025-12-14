import requests
import json
import pandas as pd
import ta
from config import Config
from models import MarketAnalysis, TradeSignal
import logging

logger = logging.getLogger(__name__)

class MistralAgent:
    def __init__(self):
        self.api_key = Config.MISTRAL_API_KEY
        self.base_url = "https://api.mistral.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def calculate_indicators(self, klines):
        """Calcule indicateurs techniques"""
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])

        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['volume'] = pd.to_numeric(df['volume'])

        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()

        # MACD
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df['close'])
        df['bb_high'] = bb.bollinger_hband()
        df['bb_low'] = bb.bollinger_lband()

        # EMA
        df['ema_20'] = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator()
        df['ema_50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()

        return df.tail(1).to_dict('records')[0]

    def analyze_market(self, symbol: str, klines, current_price: float, balance: float):
        """Demande analyse à Mistral"""

        indicators = self.calculate_indicators(klines)

        prompt = f"""Tu es un expert trading crypto. Analyse {symbol} et retourne UNIQUEMENT un JSON valide.

DONNÉES ACTUELLES:
- Prix: ${current_price:.2f}
- RSI: {indicators['rsi']:.2f}
- MACD: {indicators['macd']:.4f}
- MACD Signal: {indicators['macd_signal']:.4f}
- BB High: {indicators['bb_high']:.2f}
- BB Low: {indicators['bb_low']:.2f}
- EMA 20: {indicators['ema_20']:.2f}
- EMA 50: {indicators['ema_50']:.2f}

RÈGLES STRICTES:
- Risk max: {Config.MAX_RISK_PERCENT}% du capital (${balance * Config.MAX_RISK_PERCENT / 100:.2f})
- Stop loss: {Config.STOP_LOSS_PERCENT}% obligatoire
- Take profit: minimum 2:1 ratio risk/reward

Retourne ce JSON exact:
{{
  "action": "BUY|SELL|HOLD",
  "trend": "BULLISH|BEARISH|NEUTRAL",
  "confidence": 0-100,
  "entry_price": {current_price},
  "stop_loss": prix_stop,
  "take_profit": prix_tp,
  "position_size_usd": montant_max,
  "reasoning": "Explication courte"
}}"""

        try:
            payload = {
                "model": "mistral-small",  # Changé de mistral-large-latest à mistral-small
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.1
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            analysis_text = result['choices'][0]['message']['content'].strip()

            # Nettoyer la réponse Mistral (elle peut contenir des blocs de code markdown)
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text[7:]  # Enlever ```json
            if analysis_text.startswith('```'):
                analysis_text = analysis_text[3:]  # Enlever ```
            if analysis_text.endswith('```'):
                analysis_text = analysis_text[:-3]  # Enlever ``` à la fin
            
            analysis_text = analysis_text.strip()

            # Parse JSON
            analysis_json = json.loads(analysis_text)

            analysis = MarketAnalysis(
                symbol=symbol,
                trend=analysis_json['trend'],
                confidence=analysis_json['confidence'],
                entry_price=analysis_json['entry_price'],
                stop_loss=analysis_json['stop_loss'],
                take_profit=analysis_json['take_profit'],
                position_size_usd=analysis_json['position_size_usd'],
                reasoning=analysis_json['reasoning']
            )

            signal = TradeSignal(
                action=analysis_json['action'],
                symbol=symbol,
                analysis=analysis
            )

            logger.info(f"Mistral analyse {symbol}: {signal.action} (conf: {analysis.confidence}%)")
            return signal

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur HTTP Mistral: {e}")
            return TradeSignal(action="HOLD", symbol=symbol)
        except json.JSONDecodeError as e:
            logger.error(f"Erreur parsing JSON Mistral: {e}")
            logger.error(f"Réponse brute: {analysis_text}")
            return TradeSignal(action="HOLD", symbol=symbol)
        except Exception as e:
            logger.error(f"Erreur Mistral: {e}")
            return TradeSignal(action="HOLD", symbol=symbol)