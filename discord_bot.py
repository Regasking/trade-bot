import requests
from config import Config
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DiscordNotifier:
    def __init__(self):
        self.webhook_url = Config.DISCORD_WEBHOOK_URL

    def send_message(self, message: str, color: int = 3447003):
        """Envoie message Discord avec embed"""
        try:
            data = {
                "embeds": [{
                    "description": message,
                    "color": color,
                    "timestamp": datetime.utcnow().isoformat(),
                    "footer": {
                        "text": "🤖 Binance Trading Bot"
                    }
                }]
            }

            response = requests.post(self.webhook_url, json=data)

            if response.status_code == 204:
                logger.info("✅ Discord notification envoyée")
            else:
                logger.error(f"❌ Erreur Discord: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"❌ Erreur Discord: {e}")

    def notify_trade(self, action: str, symbol: str, price: float, quantity: float, reasoning: str):
        """Notification d'achat/vente"""
        color = 3066993 if action == "BUY" else 15158332  # Vert ou Rouge
        emoji = "🟢" if action == "BUY" else "🔴"

        notional = price * quantity

        msg = f"""
{emoji} **{action} {symbol}**

💰 **Prix:** ${price:,.2f}
📊 **Quantité:** {quantity:.6f}
💵 **Montant:** ${notional:,.2f}
💡 **Analyse IA:** {reasoning}
        """
        self.send_message(msg.strip(), color)

    def notify_stop_loss(self, symbol: str, entry: float, exit: float, loss: float):
        """Notification stop loss"""
        pct = ((exit - entry) / entry * 100)

        msg = f"""
⛔ **STOP LOSS DÉCLENCHÉ - {symbol}**

📉 **Prix entrée:** ${entry:,.2f}
📉 **Prix sortie:** ${exit:,.2f}
💸 **Perte:** ${abs(loss):,.2f} ({pct:.2f}%)
        """
        self.send_message(msg.strip(), 15158332)  # Rouge

    def notify_take_profit(self, symbol: str, entry: float, exit: float, profit: float):
        """Notification take profit"""
        pct = ((exit - entry) / entry * 100)

        msg = f"""
🎯 **TAKE PROFIT ATTEINT - {symbol}**

📈 **Prix entrée:** ${entry:,.2f}
📈 **Prix sortie:** ${exit:,.2f}
💰 **Profit:** ${profit:,.2f} (+{pct:.2f}%)
        """
        self.send_message(msg.strip(), 3066993)  # Vert

    def notify(self, message: str):
        """Message simple"""
        self.send_message(message, 3447003)  # Bleu