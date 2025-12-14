from dataclasses import dataclass
from typing import Literal

@dataclass
class MarketAnalysis:
    symbol: str
    trend: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    confidence: float  # 0-100
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size_usd: float
    reasoning: str

@dataclass
class TradeSignal:
    action: Literal["BUY", "SELL", "HOLD", "CLOSE"]
    symbol: str
    analysis: MarketAnalysis = None