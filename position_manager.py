from binance_client import BinanceClient
import logging

logger = logging.getLogger(__name__)

class PositionManager:
    def __init__(self, binance_client: BinanceClient):
        self.binance = binance_client
    
    def calculate_position_size(self, balance: float, confidence: float, market_trend: str) -> float:
        """Taille position adaptative"""
        
        # Risk de base selon confiance IA
        if confidence >= 80:
            base_risk = 0.03  # 3%
        elif confidence >= 70:
            base_risk = 0.025  # 2.5%
        elif confidence >= 60:
            base_risk = 0.02  # 2%
        elif confidence >= 50:
            base_risk = 0.015  # 1.5%
        else:
            return 0  # Pas de trade si confiance < 50%
        
        # Multiplicateur selon tendance marché
        if market_trend == "BULL":
            multiplier = 1.2  # Plus agressif en bull
        elif market_trend == "BEAR":
            multiplier = 0.5  # Très prudent en bear
        else:  # SIDEWAYS
            multiplier = 0.8
        
        final_risk = base_risk * multiplier
        position_size = balance * final_risk
        
        logger.info(f"Position size: ${position_size:.2f} (risk: {final_risk*100:.2f}%, conf: {confidence}%, trend: {market_trend})")
        
        return position_size
    
    def update_trailing_stop(self, symbol: str, position: dict, current_price: float) -> dict:
        """Met à jour trailing stop-loss"""
        
        entry = position['entry']
        current_stop = position['stop_loss']
        
        # Commence trailing si profit > 2%
        profit_pct = ((current_price - entry) / entry) * 100
        
        if profit_pct > 2:
            # Nouveau stop = prix actuel -2%
            new_stop = current_price * 0.98
            
            # Mise à jour seulement si meilleur
            if new_stop > current_stop:
                logger.info(f"🔄 Trailing stop {symbol}: ${current_stop:.2f} → ${new_stop:.2f} (profit: {profit_pct:.2f}%)")
                
                return {
                    'stop_loss': new_stop,
                    'updated': True,
                    'profit_locked': ((new_stop - entry) / entry) * 100
                }
        
        return {'stop_loss': current_stop, 'updated': False}
    
    def should_add_to_position(self, position: dict, current_price: float) -> bool:
        """Détermine si pyramiding possible"""
        
        entry = position['entry']
        profit_pct = ((current_price - entry) / entry) * 100
        
        # Pyramiding si:
        # 1. Profit >= 3%
        # 2. Pas déjà pyramided
        # 3. Moins de 3 entrées totales
        
        if profit_pct >= 3 and position.get('pyramid_count', 0) < 2:
            logger.info(f"🔺 Pyramiding possible {position.get('symbol')}: profit {profit_pct:.2f}%")
            return True
        
        return False
    
    def calculate_pyramid_size(self, original_size: float, pyramid_count: int) -> float:
        """Taille pour pyramiding"""
        
        # Première pyramide: 50% de l'original
        # Deuxième pyramide: 25% de l'original
        
        if pyramid_count == 0:
            return original_size * 0.5
        elif pyramid_count == 1:
            return original_size * 0.25
        else:
            return 0