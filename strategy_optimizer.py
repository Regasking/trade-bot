from config import Config
import logging

logger = logging.getLogger(__name__)

class StrategyOptimizer:
    
    @staticmethod
    def should_trade(
        market_trend: str,
        multi_tf: dict,
        sentiment: dict,
        confidence: float
    ) -> dict:
        """Décision finale de trade avec tous les filtres"""
        
        # Score global
        score = 0
        reasons = []
        
        # 1. Filtre tendance marché (critique)
        if market_trend == "BEAR":
            return {
                'should_trade': False,
                'reason': 'Marché en tendance BEAR - pas de trade',
                'score': 0
            }
        
        if market_trend == "BULL":
            score += 3
            reasons.append("Tendance BULL")
        
        # 2. Multi-timeframes
        mtf_recommendation = multi_tf.get('recommendation', 'HOLD')
        
        if mtf_recommendation == "STRONG_BUY":
            score += 3
            reasons.append("Multi-TF: STRONG_BUY")
        elif mtf_recommendation == "BUY":
            score += 2
            reasons.append("Multi-TF: BUY")
        elif mtf_recommendation in ["STRONG_SELL", "SELL"]:
            return {
                'should_trade': False,
                'reason': f'Multi-TF: {mtf_recommendation}',
                'score': 0
            }
        
        # 3. Sentiment marché
        sentiment_bias = sentiment.get('bias', 'NEUTRAL')
        
        if sentiment_bias == "BULLISH":
            score += 2
            reasons.append(f"Sentiment: {sentiment['sentiment']}")
        elif sentiment_bias == "BEARISH":
            score -= 2
            reasons.append(f"Sentiment négatif: {sentiment['sentiment']}")
        
        # 4. Confiance IA
        if confidence >= 75:
            score += 2
            reasons.append(f"IA confiance élevée: {confidence}%")
        elif confidence >= 65:
            score += 1
        elif confidence < 55:
            return {
                'should_trade': False,
                'reason': f'Confiance IA trop faible: {confidence}%',
                'score': score
            }
        
        # Décision finale
        should_trade = score >= 4  # Seuil: 5 points minimum
        
        return {
            'should_trade': should_trade,
            'score': score,
            'reasons': reasons,
            'risk_level': 'HIGH' if score >= 8 else 'MEDIUM' if score >= 6 else 'LOW'
        }
    
    @staticmethod
    def adjust_for_market_conditions(
        signal: str,
        market_trend: str,
        confidence: float
    ) -> str:
        """Ajuste signal selon conditions marché"""
        
        # En BEAR market, seulement si confiance très haute
        if market_trend == "BEAR":
            if signal == "BUY" and confidence < 80:
                logger.info("Signal BUY ignoré: BEAR market et confiance < 80%")
                return "HOLD"
        
        # En SIDEWAYS, plus conservateur
        if market_trend == "SIDEWAYS":
            if signal == "BUY" and confidence < 70:
                logger.info("Signal BUY ignoré: SIDEWAYS et confiance < 70%")
                return "HOLD"
        
        return signal