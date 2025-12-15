# 🤖 Bot Trading IA - Binance 24/7

Bot de trading automatisé utilisant Mistral AI pour analyser les marchés crypto et exécuter des trades sur Binance.

## 🎯 Fonctionnalités

- ✅ **Trading automatique** sur BTCUSDT, ETHUSDT, SOLUSDT
- ✅ **Analyse IA** via Mistral toutes les 4h
- ✅ **Gestion du risque** : 2% max par trade, stop-loss 3%
- ✅ **Notifications Discord** en temps réel
- ✅ **Support Testnet** pour tester sans risque
- ✅ **Protection** : max 2 positions simultanées

## 📋 Prérequis

- Python 3.11+
- Compte Binance (Testnet ou Live)
- Clé API Mistral
- Webhook Discord

## 🚀 Installation Locale

### 1. Clone le repository
```bash
git clone https://github.com/TON_USERNAME/bot-trading-ia.git
cd bot-trading-ia
```

### 2. Créé environnement virtuel
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Installe dépendances
```bash
pip install -r requirements.txt
```

### 4. Configure `.env`
```bash
cp .env.example .env
# Édite .env avec tes clés API
```

### 5. Lance le bot
```bash
python main.py
```

## ⚙️ Configuration

Créé un fichier `.env` avec :
```env
# Binance API (Testnet: https://testnet.binance.vision/)
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_secret
BINANCE_TESTNET=true

# Mistral AI (https://console.mistral.ai/)
MISTRAL_API_KEY=your_mistral_key

# Discord Webhook (Server Settings → Integrations → Webhooks)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/xxx

# Trading Parameters
MAX_RISK_PERCENT=2.0
MAX_POSITIONS=2
STOP_LOSS_PERCENT=3.0
CHECK_INTERVAL_HOURS=4
```

## 🐳 Déploiement Docker

### Build local
```bash
docker build -t bot-trading .
docker run --env-file .env bot-trading
```

### Docker Compose
```bash
docker-compose up -d
```

## ☁️ Déploiement Koyeb

### Via GitHub

1. **Push sur GitHub**
```bash
git add .
git commit -m "Ready for production"
git push origin main
```

2. **Koyeb Setup**
- Créé compte sur [koyeb.com](https://koyeb.com)
- New App → GitHub → Sélectionne `bot-trading-ia`
- Builder: **Dockerfile**
- Ajoute variables d'environnement depuis `.env`
- Deploy

3. **Vérification**
- Logs → Doit voir "Discord notification envoyée"
- Discord → Vérifie les messages du bot

## 📊 Utilisation

### Surveillance

Le bot envoie des notifications Discord pour :
- ✅ Démarrage/Arrêt
- 🟢 Achats (BUY)
- 🔴 Ventes (SELL)
- ⛔ Stop-loss déclenchés
- 🎯 Take-profit atteints

### Logs
```bash
# Voir logs en temps réel
tail -f bot.log

# Docker logs
docker logs -f bot-trading

# Koyeb logs
# Via interface web
```

## 🔒 Sécurité

- ⚠️ **Ne commit JAMAIS le fichier `.env`**
- ⚠️ **Teste TOUJOURS sur Testnet d'abord**
- ⚠️ **Utilise des clés API avec restrictions IP**
- ⚠️ **Active l'authentification 2FA sur Binance**
- ⚠️ **Commence avec de petits montants en live**

## 📈 Stratégie

### Indicateurs utilisés
- RSI (14 périodes)
- MACD
- Bollinger Bands
- EMA 20/50

### Règles de trading
- **Timeframe** : 4 heures
- **Risk/Trade** : 2% du capital
- **Stop-Loss** : -3%
- **Take-Profit** : +6% (ratio 2:1)
- **Max positions** : 2 simultanées

### Logique IA (Mistral)

L'IA analyse :
1. Indicateurs techniques
2. Tendance du marché
3. Niveau de confiance
4. Ratio risk/reward

**Seuils de confiance** :
- < 50% → HOLD
- 50-70% → Trade modéré
- > 70% → Trade agressif

## 🧪 Tests

### Test API Mistral
```bash
python test_mistral_api.py
```

### Test Binance
```bash
python test_system.py
```

### Test Discord
```bash
python test_discord.py
```

## 📁 Architecture
```
bot-trading-ia/
├── main.py              # Point d'entrée
├── binance_client.py    # Client Binance
├── mistral_agent.py     # Agent IA Mistral
├── discord_bot.py       # Notifications Discord
├── config.py            # Configuration
├── models.py            # Modèles de données
├── requirements.txt     # Dépendances Python
├── Dockerfile           # Image Docker
├── .dockerignore        # Exclusions Docker
├── .env.example         # Template configuration
└── README.md            # Documentation
```

## ⚠️ Avertissements

- Le trading comporte des risques de perte
- Les performances passées ne garantissent pas les résultats futurs
- L'IA peut prendre de mauvaises décisions
- Toujours tester sur Testnet pendant 7 jours minimum
- Ne trader que l'argent que vous pouvez vous permettre de perdre

## 🛠️ Dépannage

### Erreur "LOT_SIZE"
→ Montant trop petit, augmente `MAX_RISK_PERCENT` ou capital

### Erreur "NOTIONAL"
→ Valeur trade < 10 USDT, augmente position

### Pas de notifications Discord
→ Vérifie webhook URL dans `.env`

### API Mistral timeout
→ Vérifie clé API et quota

## 📞 Support

- **Issues** : [GitHub Issues](https://github.com/TON_USERNAME/bot-trading-ia/issues)
- **Discord** : [Ton serveur Discord]
- **Email** : ton@email.com

## 📜 Licence

MIT License - Libre d'utilisation

## 🙏 Crédits

- **Binance API** : python-binance
- **Mistral AI** : Analyse de marché
- **TA-Lib** : Indicateurs techniques

---

**⚡ Fait avec passion pour le trading algorithmique**