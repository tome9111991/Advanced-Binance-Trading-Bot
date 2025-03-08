# Konfigurationseinstellungen für den Trading Bot

# API-Konfiguration (Optional - bei Bedarf ausfüllen)
# Wenn diese Angaben gefüllt sind, wird keine manuelle Eingabe in der Konsole mehr gefordert
API_KEY = ""  # Füge hier deinen API-Schlüssel ein
API_SECRET = ""  # Füge hier dein API-Secret ein

# Umgebungseinstellungen
USE_TESTNET = True  # True für Testnet, False für echten Handel

# Handels-Konfiguration
SYMBOL = 'BTC/USDT'  # Trading-Paar
TIMEFRAME = '15m'    # Zeitintervall für Candlestick-Daten
LIMIT = 100          # Anzahl der zu holenden Candlesticks
QUANTITY_TYPE = 'PERCENTAGE'  # 'ABSOLUTE' oder 'PERCENTAGE'
QUANTITY = 0.2  # 20% des verfügbaren Guthabens
UPDATE_INTERVAL = 15 # Sekunden zwischen Updates

# Strategie-Konfiguration
# Verfügbare Strategien:
# - Für Futures (volle Funktionalität):
#   * 'SMA_CROSSOVER' - Simple Moving Average Crossover (Long & Short)
#   * 'RSI' - Relative Strength Index (Long & Short)
#   * 'MACD' - Moving Average Convergence Divergence (Long & Short)
#   * 'BOLLINGER_BANDS' - Bollinger Bands (Long & Short)
#   * 'MULTI_INDICATOR' - Kombination mehrerer Indikatoren (Long & Short)
#   * 'ADAPTIVE' - Adaptive Strategie mit dynamischer Strategiewahl
#   * 'ENHANCED_ADAPTIVE' - Erweiterte adaptive Strategie mit Marktregime-Erkennung
#
# - Für Spot (eingeschränkte Funktionalität):
#   * 'SMA_CROSSOVER', 'RSI', 'MACD', 'BOLLINGER_BANDS', 'MULTI_INDICATOR' 
#     (nur Long und Verkauf bestehender Positionen)
#   * 'SMALL_CAPITAL', 'DAY_TRADER' - Speziell für Spot mit kleinem Kapital optimiert
#
# - Nur für Testnet/Testzwecke:
#   * 'AGGRESSIVE_TEST' - Extrem aggressive Strategie, nur für Tests
#
ACTIVE_STRATEGY = 'DAY_TRADER'  # Wähle die optimale Strategie für deinen Trading-Modus

# Adaptive Strategie-Konfiguration
ADAPTIVE_LOOKBACK_PERIOD = 30  # Anzahl der Perioden für die Strategiebewertung
STRATEGY_CHANGE_THRESHOLD = 0.15  # Minimaler Performancevorteil für Strategiewechsel (15%)

# Indikatoren-Konfiguration
SMA_SHORT_PERIOD = 5
SMA_LONG_PERIOD = 20
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BOLLINGER_PERIOD = 20
BOLLINGER_STD_DEV = 2

# Risikomanagement-Konfiguration
MAX_RISK_PER_TRADE = 0.02  # 2% des Kontos pro Trade riskieren
STOP_LOSS_PERCENT = 0.02   # 2% Stopp-Loss ab Einstiegspunkt
TAKE_PROFIT_PERCENT = 0.04 # 4% Take-Profit ab Einstiegspunkt
USE_TRAILING_STOP = True
TRAILING_STOP_PERCENT = 0.01  # 1% Trailing-Stopp
MAX_DRAWDOWN = 0.10  # Maximaler Drawdown 10%
DAILY_LOSS_LIMIT = 0.05  # 5% tägliches Verlustlimit

# Erweiterte Risikomanagement-Optionen
ENABLE_DYNAMIC_RISK_ADJUSTMENT = True  # Dynamische Anpassung des Risikos basierend auf Marktbedingungen
ENABLE_ADAPTIVE_POSITION_SIZING = True  # Positionsgröße basierend auf Marktanalyse anpassen

# Performance-Tracking
SAVE_PERFORMANCE_DATA = True
PERFORMANCE_FILE = 'bot_performance.csv'
SAVE_STRATEGY_CHANGES = True  # Speichere Strategiewechsel in separater Datei
STRATEGY_CHANGES_FILE = 'strategy_changes.csv'

# Live-Handel Sicherheitsmaßnahmen (nur relevant wenn USE_TESTNET = False)
CONFIRM_TRADES = True  # Bestätigung vor jedem Trade anfordern
MAX_TRADE_VALUE = 15  # Maximaler Wert pro Trade in USDT
ENABLE_EMAIL_ALERTS = False  # E-Mail-Benachrichtigungen aktivieren
EMAIL_ADDRESS = ""  # Deine E-Mail-Adresse

# Day Trading Strategie-Konfiguration
DAY_TRADER_OPTIMIZATION_ACTIVE = True            # Selbstoptimierung aktivieren/deaktivieren
DAY_TRADER_OPTIMIZATION_INTERVAL = 12            # Stunden zwischen Optimierungen
DAY_TRADER_SIGNAL_THRESHOLD = 0.65               # Anfängliche Signalschwelle (0.0-1.0)
DAY_TRADER_MIN_TRADE_INTERVAL = 300              # Anfängliches Mindestintervall zwischen Trades (Sekunden)
DAY_TRADER_DAILY_PROFIT_TARGET = 0.03            # Anfängliches tägliches Gewinnziel (3%)
DAY_TRADER_MAX_DAILY_LOSS = 0.02                 # Anfänglicher maximaler täglicher Verlust (2%)

# Parameter-Bereiche für Optimierung
DAY_TRADER_PARAM_RANGES = {
    'signal_threshold': [0.6, 0.65, 0.7, 0.75],     # Zu testende Signalschwellen
    'min_trade_interval': [240, 300, 360, 420],     # Zu testende Handelsintervalle (Sekunden)
    'daily_profit_target': [0.02, 0.025, 0.03, 0.035], # Zu testende tägliche Gewinnziele
    'max_daily_loss': [0.015, 0.02, 0.025, 0.03]    # Zu testende maximale tägliche Verluste
}

# Rejected Signal Logging Configuration
LOG_REJECTED_SIGNALS = True        # Enable/disable logging of rejected trade signals
DISPLAY_REJECTED_SIGNALS = True    # Show rejected signals in console output

# Hilfsfunktionen zur Extraktion von Währungsinformationen
def get_base_currency():
    """Gibt die Base-Währung des konfigurierten Trading-Paars zurück"""
    if '/' in SYMBOL:
        return SYMBOL.split('/')[0]
    return 'BTC'  # Fallback

def get_quote_currency():
    """Gibt die Quote-Währung des konfigurierten Trading-Paars zurück"""
    if '/' in SYMBOL:
        return SYMBOL.split('/')[1]
    return 'USDT'  # Fallback

# Fallback-Werte für coin-spezifische Parameter
COIN_FALLBACKS = {
    'BTC': {'precision': 5, 'min_amount': 0.00001},
    'ETH': {'precision': 4, 'min_amount': 0.0001},
    'SOL': {'precision': 1, 'min_amount': 0.1},
    # Weitere Coins hier hinzufügen
}