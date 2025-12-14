# 🤖 Bot Trading IA Binance 24/7

## Setup Rapide

### 1. Binance Testnet
1. Va sur https://testnet.binance.vision/
2. Créé compte → API Key
3. Copie `API_KEY` + `SECRET`

### 2. Claude API
1. https://console.anthropic.com/
2. Créé clé API

### 3. Telegram Bot
1. Parle à @BotFather
2. `/newbot` → nom + username
3. Copie token
4. Démarre bot + récupère chat_id avec @userinfobot

### 4. Installation
```bash
cp .env.example .env
# Édite .env avec tes clés

pip install -r requirements.txt
python test_system.py  # OBLIGATOIRE
python main.py
```

### 5. Docker (Koyeb)
```bash
docker-compose up -d
```

## ⚠️ SÉCURITÉ
- ✅ **TESTNET SEULEMENT** au début
- ✅ Valide 1 semaine minimum
- ✅ Risk 2% max par trade
- ❌ Jamais clés API en clair dans code

## 📊 Logs
```bash
tail -f bot.log
```

## 🛑 Arrêt
```bash
# Local
Ctrl+C

# Docker
docker-compose down
```