from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import Config
import logging
import math

logger = logging.getLogger(__name__)

class BinanceClient:
    def __init__(self):
        self.client = Client(
            Config.BINANCE_API_KEY,
            Config.BINANCE_API_SECRET,
            testnet=Config.BINANCE_TESTNET
        )
        if Config.BINANCE_TESTNET:
            self.client.API_URL = Config.BINANCE_TESTNET_URL
        
        self.symbol_info_cache = {}
    
    def get_symbol_info(self, symbol: str):
        """Cache info symbol"""
        if symbol not in self.symbol_info_cache:
            info = self.client.get_symbol_info(symbol)
            self.symbol_info_cache[symbol] = info
        return self.symbol_info_cache[symbol]
    
    def get_precision(self, symbol: str):
        """Précision lot"""
        info = self.get_symbol_info(symbol)
        
        lot_filter = next(f for f in info['filters'] if f['filterType'] == 'LOT_SIZE')
        step_size = float(lot_filter['stepSize'])
        min_qty = float(lot_filter['minQty'])
        
        price_filter = next(f for f in info['filters'] if f['filterType'] == 'PRICE_FILTER')
        tick_size = float(price_filter['tickSize'])
        
        notional_filter = next(f for f in info['filters'] if f['filterType'] == 'NOTIONAL')
        min_notional = float(notional_filter['minNotional'])
        
        qty_precision = int(round(-math.log(step_size, 10), 0))
        price_precision = int(round(-math.log(tick_size, 10), 0))
        
        return {
            'qty_precision': qty_precision,
            'price_precision': price_precision,
            'min_qty': min_qty,
            'min_notional': min_notional,
            'step_size': step_size
        }
    
    def adjust_quantity(self, symbol: str, quantity: float):
        """Ajuste quantité selon rules Binance"""
        prec = self.get_precision(symbol)
        
        # Arrondi au step_size
        qty = round(quantity, prec['qty_precision'])
        
        # Ajuste au step_size
        step = prec['step_size']
        qty = math.floor(qty / step) * step
        qty = round(qty, prec['qty_precision'])
        
        return max(qty, prec['min_qty'])
    
    def get_account_balance(self):
        """Balance USDT"""
        try:
            account = self.client.get_account()
            usdt = next((float(b['free']) for b in account['balances'] if b['asset'] == 'USDT'), 0.0)
            logger.info(f"Balance USDT: {usdt}")
            return usdt
        except BinanceAPIException as e:
            logger.error(f"Erreur balance: {e}")
            return 0.0
    
    def get_klines(self, symbol: str, interval: str, limit: int = 100):
        """Klines"""
        try:
            return self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        except BinanceAPIException as e:
            logger.error(f"Erreur klines: {e}")
            return []
    
    def get_current_price(self, symbol: str):
        """Prix actuel"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            logger.error(f"Erreur prix: {e}")
            return 0.0
    
    def place_order(self, symbol: str, side: str, quantity: float, price: float = None):
        """Place ordre avec checks"""
        try:
            prec = self.get_precision(symbol)
            current_price = price or self.get_current_price(symbol)
            
            # Ajuste quantité
            quantity = self.adjust_quantity(symbol, quantity)
            
            # Check notional MIN
            notional = quantity * current_price
            if notional < prec['min_notional']:
                logger.error(f"❌ Notional ${notional:.2f} < min ${prec['min_notional']}")
                
                # AUTO-ADJUST au minimum
                quantity = (prec['min_notional'] * 1.1) / current_price  # +10% sécurité
                quantity = self.adjust_quantity(symbol, quantity)
                notional = quantity * current_price
                
                logger.info(f"✅ Ajusté → Qty: {quantity}, Notional: ${notional:.2f}")
            
            logger.info(f"📝 Ordre: {side} {quantity} {symbol} @ ${current_price:,.2f} (${notional:.2f})")
            
            if price:
                price = round(price, prec['price_precision'])
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type='LIMIT',
                    timeInForce='GTC',
                    quantity=quantity,
                    price=price
                )
            else:
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type='MARKET',
                    quantity=quantity
                )
            
            logger.info(f"✅ Ordre #{order['orderId']} placé")
            return order
            
        except BinanceAPIException as e:
            logger.error(f"❌ Erreur ordre: {e}")
            return None
    
    def place_stop_loss(self, symbol: str, quantity: float, stop_price: float):
        """Stop loss"""
        try:
            prec = self.get_precision(symbol)
            quantity = self.adjust_quantity(symbol, quantity)
            stop_price = round(stop_price, prec['price_precision'])
            limit_price = round(stop_price * 0.995, prec['price_precision'])
            
            order = self.client.create_order(
                symbol=symbol,
                side='SELL',
                type='STOP_LOSS_LIMIT',
                timeInForce='GTC',
                quantity=quantity,
                price=limit_price,
                stopPrice=stop_price
            )
            logger.info(f"✅ Stop loss: {order}")
            return order
        except BinanceAPIException as e:
            logger.error(f"❌ Erreur stop: {e}")
            return None
    
    def get_open_orders(self, symbol: str = None):
        """Ordres ouverts"""
        try:
            return self.client.get_open_orders(symbol=symbol) if symbol else self.client.get_open_orders()
        except BinanceAPIException as e:
            logger.error(f"Erreur ordres: {e}")
            return []
    
    def cancel_order(self, symbol: str, order_id: int):
        """Annule ordre"""
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f"Annulé: {result}")
            return result
        except BinanceAPIException as e:
            logger.error(f"Erreur annulation: {e}")
            return None