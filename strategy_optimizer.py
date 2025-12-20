from typing import Dict, List
import logging
import os

# Configuration seuil via variable env
TRADE_THRESHOLD = int(os.getenv('TRADE_THRESHOLD', '5'))

logger = logging.getLogger(__name__)

class StrategyOptimizer:
    """Optimise la stratégie de trading en combinant plusieurs analyses"""
    
    def __init__(self):
        self.min_score = TRADE_THRESHOLD
        logger.info(f"🎯 Seuil de trading configuré: {self.min_score}/10")
    
    def should_trade(self, symbol: str, multi_tf: dict, mistral: dict, sentiment: dict, **kwargs) -> dict:
        """
        Décide si on doit trader basé sur tous les signaux
        **kwargs accepte tous les paramètres supplémentaires
        """
        score = 0
        reasons = []
        
        # 1. Analyse Multi-Timeframe (poids: 4 points)
        tf_signal = multi_tf.get('signal', 'HOLD')
        if tf_signal == 'STRONG_BUY':
            score += 4
            reasons.append("Multi-TF: STRONG_BUY (+4)")
        elif tf_signal == 'BUY':
            score += 3
            reasons.append("Multi-TF: BUY (+3)")
        elif tf_signal == 'HOLD':
            score += 1
            reasons.append("Multi-TF: HOLD (+1)")
        elif tf_signal == 'SELL':
            score += 0
            reasons.append("Multi-TF: SELL (0)")
        else:  # STRONG_SELL
            score += 0
            reasons.append("Multi-TF: STRONG_SELL (0)")
        
        # 2. Mistral AI (poids: 3 points)
        mistral_action = mistral.get('action', 'HOLD')
        mistral_conf = mistral.get('confidence', 0)
        
        if mistral_action == 'BUY':
            if mistral_conf >= 80:
                score += 3
                reasons.append(f"Mistral: BUY {mistral_conf}% (+3)")
            elif mistral_conf >= 65:
                score += 2
                reasons.append(f"Mistral: BUY {mistral_conf}% (+2)")
            else:
                score += 1
                reasons.append(f"Mistral: BUY {mistral_conf}% (+1)")
        elif mistral_action == 'HOLD':
            reasons.append(f"Mistral: HOLD {mistral_conf}% (0)")
        else:  # SELL
            score -= 1
            reasons.append(f"Mistral: SELL {mistral_conf}% (-1)")
        
        # 3. Sentiment (Fear & Greed) (poids: 3 points)
        sentiment_value = sentiment.get('value', 50)
        sentiment_label = sentiment.get('label', 'NEUTRAL')
        
        if sentiment_label == 'EXTREME_FEAR':
            score += 3
            reasons.append(f"Sentiment: EXTREME_FEAR {sentiment_value} (+3)")
        elif sentiment_label == 'FEAR':
            score += 2
            reasons.append(f"Sentiment: FEAR {sentiment_value} (+2)")
        elif sentiment_label == 'NEUTRAL':
            score += 1
            reasons.append(f"Sentiment: NEUTRAL {sentiment_value} (+1)")
        elif sentiment_label == 'GREED':
            score += 0
            reasons.append(f"Sentiment: GREED {sentiment_value} (0)")
        else:  # EXTREME_GREED
            score -= 1
            reasons.append(f"Sentiment: EXTREME_GREED {sentiment_value} (-1)")
        
        # Décision finale
        should_trade_decision = score >= TRADE_THRESHOLD
        
        result = {
            'should_trade': should_trade_decision,
            'score': score,
            'reasons': reasons
        }
        
        if should_trade_decision:
            logger.info(f"✅ Trade validé pour {symbol}! Score: {score}/{TRADE_THRESHOLD}")
            for reason in reasons:
                logger.info(f"  └─ {reason}")
        else:
            logger.info(f"❌ Trade refusé pour {symbol}. Score: {score}/{TRADE_THRESHOLD}")
        
        return result
    
    def get_position_size(self, balance: float, risk_percent: float = 2.0) -> float:
        """Calcule la taille de position basée sur le risque"""
        position_size = balance * (risk_percent / 100)
        logger.info(f"💰 Taille position: ${position_size:.2f}")
        return position_size
    
    def calculate_tp_sl(self, entry_price: float, atr: float, risk_reward: float = 1.5) -> dict:
        """Calcule TP/SL dynamiques"""
        sl = entry_price - (2 * atr)
        distance_sl = entry_price - sl
        tp = entry_price + (distance_sl * risk_reward)
        
        return {
            'tp': tp,
            'sl': sl,
            'risk_reward': risk_reward,
            'atr': atr
        }
    
    def should_pyramid(self, current_profit_percent: float, pyramid_threshold: float = 2.0) -> bool:
        """Détermine si on doit pyramider"""
        return current_profit_percent >= pyramid_threshold
    
    def adjust_trailing_stop(self, entry_price: float, current_price: float, 
                            current_sl: float, trailing_percent: float = 1.5) -> float:
        """Ajuste le trailing stop loss"""
        new_sl = current_price * (1 - trailing_percent / 100)
        if new_sl > current_sl:
            return new_sl
        return current_sl