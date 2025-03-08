import ccxt
import pandas as pd
import time
from datetime import datetime
from colorama import Fore, Style
import utils
import config
import math


def initialize_exchange(api_key, api_secret):
    """Initialisiert den Binance Client - Futures für Testnet oder Spot für Live"""
    try:
        # Verwende Futures für Testnet, Spot für Live-Handel
        trading_type = 'future' if config.USE_TESTNET else 'spot'
        
        if config.USE_TESTNET:
            print(f"{Fore.CYAN}[{datetime.now().strftime('%H:%M:%S')}] Initialisiere FUTURES TESTNET-Modus{Style.RESET_ALL}")
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                    'adjustForTimeDifference': True,
                }
            }
            
            # Einfachere Testnet-Setup-Methode
            from ccxt.binance import binance
            exchange = binance(exchange_options)
            exchange.set_sandbox_mode(True)  # Aktiviert Testnet-Modus
        else:
            print(f"{Fore.CYAN}[{datetime.now().strftime('%H:%M:%S')}] Initialisiere SPOT LIVE-Modus{Style.RESET_ALL}")
            exchange_options = {
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'timeout': 30000,
                'options': {
                    'defaultType': 'spot',
                    'adjustForTimeDifference': True,
                    'recvWindow': 60000
                }
            }
            exchange = ccxt.binance(exchange_options)
        
        # Sofortige API-Validierung mit einer Methode, die auf jeden Fall API-Schlüssel erfordert
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Validiere API-Schlüssel...{Style.RESET_ALL}")
        try:
            # fetch_balance erfordert einen gültigen API-Schlüssel
            balance = exchange.fetch_balance()
            print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] API-Verbindung erfolgreich validiert!{Style.RESET_ALL}")
            
            # Zeige Kontoinformationen
            quote_currency = config.get_quote_currency()
            if config.USE_TESTNET:
                print(f"{Fore.YELLOW}Testnet {quote_currency} Balance: {balance.get(quote_currency, {}).get('free', 0):.2f}{Style.RESET_ALL}")
            else:
                non_zero = {curr: amt for curr, amt in balance['free'].items() if amt > 0}
                if non_zero:
                    print(f"{Fore.YELLOW}Verfügbare Guthaben:{Style.RESET_ALL}")
                    for currency, amount in non_zero.items():
                        print(f"{Fore.YELLOW}{currency}: {amount}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}Keine Guthaben gefunden oder alle Guthaben sind 0.{Style.RESET_ALL}")
            
            # Zusätzlich öffentliche Marktdaten laden
            markets = exchange.load_markets()
            print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Marktdaten erfolgreich geladen ({len(markets)} Märkte).{Style.RESET_ALL}")
            
            # Überprüfen, ob das konfigurierte Symbol verfügbar ist
            if config.SYMBOL not in markets:
                available_symbols = ", ".join(list(markets.keys())[:10]) + "..." if len(markets) > 10 else ", ".join(markets.keys())
                print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Warnung: Das konfigurierte Symbol {config.SYMBOL} wurde nicht in den verfügbaren Märkten gefunden!{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Verfügbare Symbole (Beispiele): {available_symbols}{Style.RESET_ALL}")
                
                # Versuche alternative Schreibweise
                alt_symbol = config.SYMBOL.replace("/", "")
                if alt_symbol in markets:
                    print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Alternative Schreibweise {alt_symbol} gefunden, verwende diese.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Fahre fort mit konfiguriertem Symbol, aber es könnte zu Problemen kommen.{Style.RESET_ALL}")
        
        except Exception as api_error:
            print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] API-Schlüssel Validierung fehlgeschlagen!{Style.RESET_ALL}")
            print(f"{Fore.RED}Fehler: {str(api_error)}{Style.RESET_ALL}")
            return None
        
        # Zeige eine deutliche Warnung beim Live-Trading NACH der API-Validierung
        if not config.USE_TESTNET:
            print(f"\n{Fore.RED}===============================================")
            print(f"{Fore.RED}!!! ACHTUNG: LIVE-TRADING MODUS AKTIVIERT !!!")
            print(f"{Fore.RED}Sie handeln jetzt mit echtem Geld im SPOT-MODUS!")
            print(f"{Fore.RED}==============================================={Style.RESET_ALL}\n")
            
            # Bei Live-Trading zusätzliche Sicherheitsabfrage
            if config.CONFIRM_TRADES:
                confirmation = input(f"{Fore.YELLOW}Sind Sie sicher, dass Sie mit echtem Geld handeln möchten? (j/n): {Style.RESET_ALL}")
                if confirmation.lower() != 'j':
                    print(f"{Fore.GREEN}Live-Trading abgebrochen. Beende Programm.{Style.RESET_ALL}")
                    return None
        else:
            print(f"{Fore.GREEN}TESTNET-MODUS aktiv. Es wird kein echtes Geld gehandelt.{Style.RESET_ALL}")
        
        return exchange
    except Exception as e:
        utils.log_error(e, "Fehler bei der Initialisierung des Exchange")
        print(f"{Fore.RED}Fehlerdetails: {str(e)}{Style.RESET_ALL}")
        return None

def get_historical_data(exchange, symbol, timeframe, limit):
    """Hole historische Candlestick-Daten mit verbesserter Fehlerbehandlung"""
    max_retries = 4
    retry_delay = 5
    
    for retry_count in range(max_retries):
        try:
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Hole Marktdaten für {symbol} (Versuch {retry_count + 1}/{max_retries})...{Style.RESET_ALL}")
            
            # Set a longer timeout for this request
            exchange.options['timeout'] = 30000
            
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv or len(ohlcv) == 0:
                print(f"{Fore.RED}Keine Daten von der API erhalten.{Style.RESET_ALL}")
                if retry_count < max_retries - 1:
                    print(f"{Fore.YELLOW}Wiederhole in {retry_delay} Sekunden...{Style.RESET_ALL}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return pd.DataFrame()
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Marktdaten erfolgreich geladen.{Style.RESET_ALL}")
            return df
            
        except Exception as e:
            error_message = str(e)
            utils.log_error(e, f"Fehler beim Abrufen der Daten für {symbol} (Versuch {retry_count + 1}/{max_retries})")
            
            if retry_count < max_retries - 1:
                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Verbindungsfehler. Wiederhole in {retry_delay} Sekunden...{Style.RESET_ALL}")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Maximale Anzahl an Wiederholungen erreicht. Konnte keine Daten abrufen.{Style.RESET_ALL}")
                # Statt Notfalldaten zu erzeugen, geben wir ein leeres DataFrame zurück
                # Die run_bot Funktion wird dies erkennen und entsprechend handeln
                return pd.DataFrame()
    
    return pd.DataFrame()  # Wenn alle Versuche fehlschlagen, leeres DataFrame zurückgeben

def execute_trade(exchange, symbol, side, quantity, current_price):
    """
    Führt einen Trade aus mit verbesserten Fehlermeldungen und automatischen Korrekturversuchen.
    
    Parameters:
    exchange: Exchange-Objekt
    symbol: Handelssymbol
    side: Handelsrichtung ('buy' oder 'sell')
    quantity: Handelsmenge
    current_price: Aktueller Preis
    
    Returns:
    dict: Order-Informationen oder None bei Fehler
    """
    try:
        base_currency = config.get_base_currency()
        quote_currency = config.get_quote_currency()
        
        # Ausführliche Ausgabe vor dem Trade
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Führe {side.upper()} Order aus: {quantity} {base_currency} @ ~{current_price:.2f} {quote_currency}{Style.RESET_ALL}")
        
        # Sicherheitscheck für Live-Trading
        if not config.USE_TESTNET:
            trade_value = quantity * current_price
            
            # Überprüfe maximalen Trade-Wert NUR FÜR KÄUFE
            if side.lower() == 'buy' and trade_value > config.MAX_TRADE_VALUE:
                print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Trade abgelehnt: Wert ({trade_value:.2f} {quote_currency}) überschreitet Maximum ({config.MAX_TRADE_VALUE} {quote_currency}){Style.RESET_ALL}")
                return None
            
            # Handelsbestätigung anfordern
            if config.CONFIRM_TRADES:
                confirmation = input(f"{Fore.YELLOW}Bestätigen Sie den Trade: {side.upper()} {quantity} {base_currency} @ ~{current_price:.2f} {quote_currency}? (j/n): {Style.RESET_ALL}")
                if confirmation.lower() != 'j':
                    print(f"{Fore.RED}Trade abgebrochen durch Benutzer.{Style.RESET_ALL}")
                    return None
        
        max_retries = 3
        current_retry = 0
        adjusted_quantity = quantity  # Startmenge
        
        while current_retry < max_retries:
            try:
                # Parameter je nach Modus anpassen
                params = {}
                if config.USE_TESTNET:
                    # Futures Testnet
                    params = {'positionSide': 'BOTH'}
                
                # Order erstellen mit passenden Parametern
                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Ausführungsversuch {current_retry+1}: {side.upper()} {adjusted_quantity} {base_currency}{Style.RESET_ALL}")
                
                order = exchange.create_market_order(
                    symbol=symbol,
                    side=side,
                    amount=adjusted_quantity,
                    params=params
                )
                
                # Trade-Ausgabe
                color = Fore.GREEN if side == 'buy' else Fore.RED
                mode_info = f"[SPOT LIVE-MODUS]" if not config.USE_TESTNET else f"[FUTURES TESTNET]"
                print(f"\n{color}[{datetime.now().strftime('%H:%M:%S')}] {mode_info} {side.upper()} Order erfolgreich ausgeführt - {adjusted_quantity} {base_currency} @ {current_price:.2f} {quote_currency}" + Style.RESET_ALL)
                total_value = adjusted_quantity * current_price
                print(f"{color}Gesamtwert des Trades: {total_value:.2f} {quote_currency}{Style.RESET_ALL}")

                return order
                
            except Exception as e:
                error_message = str(e)
                print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler beim Ausführen des Orders: {error_message}{Style.RESET_ALL}")
                
                # Automatische Anpassungen basierend auf spezifischen Fehlermeldungen
                if "LOT_SIZE" in error_message:
                    print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Lot-Size-Fehler erkannt. Versuche Mengenanpassung...{Style.RESET_ALL}")
                    
                    # Extrahiere die geforderte Step-Size aus der Fehlermeldung, wenn möglich
                    # Beispiel: "LOT_SIZE quantity should be a multiple of 0.1" 
                    import re
                    step_size_match = re.search(r"multiple of (\d*\.?\d+)", error_message)
                    
                    if step_size_match:
                        step_size = float(step_size_match.group(1))
                        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Extrahierte Step-Size aus Fehlermeldung: {step_size}{Style.RESET_ALL}")
                        
                        # Passe Menge entsprechend an
                        factor = 1.0 / step_size
                        adjusted_quantity = math.floor(adjusted_quantity * factor) / factor
                        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Angepasste Menge auf Step-Size: {adjusted_quantity}{Style.RESET_ALL}")
                    else:
                        # Wenn keine Step-Size gefunden, versuche konservative Anpassung
                        if base_currency == 'SOL':
                            # SOL oft auf 0.1 oder 0.01
                            adjusted_quantity = math.floor(adjusted_quantity * 10) / 10
                        else:
                            # Generische Anpassung für andere Coins
                            adjusted_quantity = math.floor(adjusted_quantity * 100) / 100
                        
                        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Konservative Mengenanpassung: {adjusted_quantity}{Style.RESET_ALL}")
                
                elif "MIN_NOTIONAL" in error_message:
                    print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Mindestorderwert nicht erreicht. Versuche Erhöhung...{Style.RESET_ALL}")
                    
                    # Extrahiere den Mindestorderwert, wenn möglich
                    min_notional_match = re.search(r"MIN_NOTIONAL.*?(\d+\.?\d*)", error_message)
                    
                    if min_notional_match:
                        min_notional = float(min_notional_match.group(1))
                        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Extrahierter Mindestorderwert: {min_notional} {quote_currency}{Style.RESET_ALL}")
                        
                        # Berechne neue Menge
                        new_quantity = min_notional / current_price * 1.01  # 1% Sicherheitspuffer
                        
                        # Runde entsprechend
                        if base_currency == 'SOL':
                            adjusted_quantity = math.ceil(new_quantity * 10) / 10
                        else:
                            adjusted_quantity = math.ceil(new_quantity * 100) / 100
                        
                        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Erhöhte Menge auf: {adjusted_quantity} {base_currency}{Style.RESET_ALL}")
                    else:
                        # Wenn kein Wert extrahiert werden konnte, erhöhe generisch
                        adjusted_quantity = adjusted_quantity * 1.5
                        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Generische Mengenerhöhung auf: {adjusted_quantity}{Style.RESET_ALL}")
                
                elif "PRICE_FILTER" in error_message:
                    print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Preisfilter-Fehler. Bei Market Orders nicht beeinflussbar.{Style.RESET_ALL}")
                    break  # Keine Anpassung möglich
                
                elif "INSUFFICIENT_BALANCE" in error_message:
                    print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Nicht genügend Guthaben für diesen Trade.{Style.RESET_ALL}")
                    break  # Keine sinnvolle Anpassung möglich
                
                else:
                    # Generischer Fehler ohne spezifische Handlung
                    print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Generischer API-Fehler: {error_message}{Style.RESET_ALL}")
                    if current_retry < max_retries - 1:
                        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warte 3 Sekunden vor nächstem Versuch...{Style.RESET_ALL}")
                        time.sleep(3)
                
                current_retry += 1
        
        # Wenn alle Versuche fehlgeschlagen sind
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Alle Versuche fehlgeschlagen. Trade konnte nicht ausgeführt werden.{Style.RESET_ALL}")
        utils.log_error(Exception(f"Trade konnte nach {max_retries} Versuchen nicht ausgeführt werden"), 
                       f"Fehler beim Ausführen des {side} Orders für {quantity} {symbol}")
        return None
        
    except Exception as e:
        utils.log_error(e, f"Kritischer Fehler beim Ausführen des {side} Orders für {quantity} {symbol}")
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Kritischer Fehler: {str(e)}{Style.RESET_ALL}")
        return None

def get_position(exchange, symbol):
    """Prüfe aktuelle Position - unterschiedlich je nach Modus"""
    try:
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Prüfe aktuelle Position...{Style.RESET_ALL}")
        
        base_currency = config.get_base_currency()
        quote_currency = config.get_quote_currency()
        
        # Debug-Info zum aktuellen Modus
        print(f"DEBUG: Handels-Modus: {'Futures Testnet' if config.USE_TESTNET else 'Spot Live'}")
        print(f"DEBUG: Symbol für Positionsabfrage: {symbol}")
        
        if config.USE_TESTNET:
            # Futures Testnet: Verwende fetch_positions
            max_retries = 3
            retry_delay = 3
            
            for retry_count in range(max_retries):
                try:
                    # Stelle sicher, dass das Symbol korrekt formatiert ist
                    formatted_symbol = symbol.replace('/', '')  # "BTC/USDT" -> "BTCUSDT"
                    positions = exchange.fetch_positions([formatted_symbol])
                    print(f"DEBUG: Positionen von API erhalten: {positions}")
                    
                    for position in positions:
                        api_symbol = position.get('symbol', '')
                        print(f"DEBUG: Position für Symbol '{api_symbol}' prüfen (vs. '{formatted_symbol}')")
                        
                        # VERBESSERTE SYMBOLÜBERPRÜFUNG
                        # Prüfe ob das Symbol am Anfang übereinstimmt oder teilweise übereinstimmt
                        base_quote = symbol.split('/')  # ["BTC", "USDT"]
                        if (position['symbol'] == formatted_symbol or 
                            (len(base_quote) > 1 and position['symbol'].startswith(f"{base_quote[0]}/{base_quote[1]}")) or
                            api_symbol.startswith(formatted_symbol)):
                            
                            position_size = float(position['contracts'])
                            position_type = "LONG" if position_size > 0 else ("SHORT" if position_size < 0 else "KEINE")
                            print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Aktuelle Position: {position_type} ({position_size} {base_currency}){Style.RESET_ALL}")
                            
                            # Zusätzliche Positionsdaten zurückgeben
                            position_info = {
                                 'size': position_size,
                                 'type': position_type,
                                 'entry_price': float(position['entryPrice']) if 'entryPrice' in position and position['entryPrice'] is not None else 0,
                                 'liquidation_price': float(position['liquidationPrice']) if 'liquidationPrice' in position and position['liquidationPrice'] is not None else 0,
                                 'unrealized_pnl': float(position['unrealizedPnl']) if 'unrealizedPnl' in position and position['unrealizedPnl'] is not None else 0,
                                 'leverage': float(position['leverage']) if 'leverage' in position and position['leverage'] is not None else 1
                                }
                            
                            return position_size, position_info
                    print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Aktuelle Position: KEINE{Style.RESET_ALL}")
                    return 0, {'size': 0, 'type': 'KEINE', 'entry_price': 0, 'liquidation_price': 0, 'unrealized_pnl': 0, 'leverage': 1}
                except Exception as e:
                    if retry_count < max_retries - 1:
                        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Fehler beim Abrufen der Position: {str(e)}. Wiederhole in {retry_delay} Sekunden...{Style.RESET_ALL}")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        utils.log_error(e, f"Fehler beim Abrufen der Position für {symbol}")
                        return 0, {'size': 0, 'type': 'KEINE', 'entry_price': 0, 'liquidation_price': 0, 'unrealized_pnl': 0, 'leverage': 1}
        else:
            # Spot Live: Prüfe das Guthaben der Basis-Währung
            balance = exchange.fetch_balance()
            if base_currency in balance:
                position_size = float(balance[base_currency]['free'])
                position_type = "LONG" if position_size > 0 else "KEINE"
                print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Aktuelle Position: {position_type} ({position_size} {base_currency}){Style.RESET_ALL}")
                
                # Vereinfachtes position_info für Spot
                position_info = {
                    'size': position_size,
                    'type': position_type,
                    'entry_price': 0,  # Nicht verfügbar im Spot-Trading
                    'liquidation_price': 0,  # Nicht anwendbar für Spot
                    'unrealized_pnl': 0,  # Nicht direkt verfügbar
                    'leverage': 1  # Immer 1 bei Spot
                }
                
                return position_size, position_info
            else:
                print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Aktuelle Position: KEINE{Style.RESET_ALL}")
                return 0, {'size': 0, 'type': 'KEINE', 'entry_price': 0, 'liquidation_price': 0, 'unrealized_pnl': 0, 'leverage': 1}
            
    except Exception as e:
        utils.log_error(e, f"Fehler beim Abrufen der Position für {symbol}")
        return 0, {'size': 0, 'type': 'KEINE', 'entry_price': 0, 'liquidation_price': 0, 'unrealized_pnl': 0, 'leverage': 1}

def get_market_info(exchange, symbol):
    """Hole Marktinformationen wie Mindest-Order-Größe, Tick-Größe, etc."""
    try:
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Hole Marktinformationen für {symbol}...{Style.RESET_ALL}")
        market = exchange.market(symbol)
        return market
    except Exception as e:
        utils.log_error(e, f"Fehler beim Abrufen der Marktinformationen für {symbol}")
        return None

def get_quote_currency_balance(exchange):
    """Gibt das verfügbare Guthaben in der Quote-Währung zurück"""
    try:
        quote_currency = config.get_quote_currency()
        balance = exchange.fetch_balance()
        
        if quote_currency in balance:
            return float(balance[quote_currency]['free'])
        return 0
    except Exception as e:
        utils.log_error(e, f"Fehler beim Abrufen des {quote_currency} Guthabens")
        return 0

def calculate_quantity(exchange, current_price, balance=None):
    """
    Berechnet die Handelsmenge basierend auf der Konfiguration mit automatischer Anpassung
    an die Handelsregeln verschiedener Coins.
    
    Parameters:
    exchange: Exchange-Objekt
    current_price: Aktueller Preis des Assets
    balance: Optional - Bereits abgerufenes Guthaben
    
    Returns:
    float: Berechnete Handelsmenge
    """
    try:
        base_currency = config.get_base_currency()
        quote_currency = config.get_quote_currency()
        
        # Fall 1: Wenn absolute Menge konfiguriert ist
        if config.QUANTITY_TYPE == 'ABSOLUTE':
            quantity = config.QUANTITY
        # Fall 2: Wenn Prozentsatz konfiguriert ist
        else:
            # Hole Kontoguthaben, wenn nicht übergeben
            if balance is None:
                quote_balance = get_quote_currency_balance(exchange)
            else:
                quote_balance = balance
                
            if quote_balance <= 0:
                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: Kein Guthaben verfügbar, verwende Standard-Handelsmenge{Style.RESET_ALL}")
                return config.QUANTITY
                
            # Berechne Prozentsatz des Guthabens
            quote_amount = quote_balance * config.QUANTITY
            quantity = quote_amount / current_price
            
        # ---- KRITISCHER TEIL: MARKTREGELN ANWENDEN ----
        
        # Hole detaillierte Markt-Informationen
        symbol = config.SYMBOL
        market_info = None
        try:
            market_info = exchange.market(symbol)
            print(f"{Fore.CYAN}[{datetime.now().strftime('%H:%M:%S')}] Marktinfo für {symbol} erfolgreich geladen.{Style.RESET_ALL}")
        except Exception as market_error:
            print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler beim Laden der Marktinfos für {symbol}: {str(market_error)}{Style.RESET_ALL}")
            # Versuche alternative Symbolschreibweise
            try:
                alt_symbol = symbol.replace("/", "")
                market_info = exchange.market(alt_symbol)
                print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Marktinfo mit alternativer Schreibweise {alt_symbol} geladen.{Style.RESET_ALL}")
            except Exception as alt_error:
                print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Auch alternative Symbolschreibweise fehlgeschlagen: {str(alt_error)}{Style.RESET_ALL}")
        
        # Verarbeite Marktinformationen, wenn verfügbar
        if market_info:
            # 1. Ermittle die Präzision für die Menge
            precision = None
            if 'precision' in market_info:
                if isinstance(market_info['precision'], dict) and 'amount' in market_info['precision']:
                    precision = market_info['precision']['amount']
                elif isinstance(market_info['precision'], int):
                    precision = market_info['precision']
            
            # 2. Ermittle Handelslimits
            min_amount = None
            max_amount = None
            step_size = None
            min_cost = None
            
            if 'limits' in market_info:
                if 'amount' in market_info['limits']:
                    amount_limits = market_info['limits']['amount']
                    if 'min' in amount_limits:
                        min_amount = amount_limits['min']
                    if 'max' in amount_limits:
                        max_amount = amount_limits['max']
                
                if 'cost' in market_info['limits'] and 'min' in market_info['limits']['cost']:
                    min_cost = market_info['limits']['cost']['min']
            
            # 3. Versuche, die Step-Size zu finden (kann in verschiedenen Formaten vorliegen)
            if 'precision' in market_info and 'amount' in market_info['precision']:
                precision_value = market_info['precision']['amount']
                if isinstance(precision_value, int):
                    # Wenn Präzision als Anzahl der Dezimalstellen angegeben ist
                    step_size = 1.0 / (10 ** precision_value)
                else:
                    # Wenn Präzision direkt als Schritt angegeben ist
                    step_size = precision_value
            
            # Alternativ: Suche nach Step-Size in anderen Bereichen
            if step_size is None and 'limits' in market_info and 'amount' in market_info['limits']:
                if 'min_step' in market_info['limits']['amount']:
                    step_size = market_info['limits']['amount']['min_step']
            
            # 4. Info-Ausgabe über gefundene Werte
            print(f"{Fore.CYAN}[{datetime.now().strftime('%H:%M:%S')}] Handelsinformationen für {base_currency}:{Style.RESET_ALL}")
            print(f"  Präzision: {precision}")
            print(f"  Mindestmenge: {min_amount}")
            print(f"  Maximalmenge: {max_amount}")
            print(f"  Schrittgröße: {step_size}")
            print(f"  Min. Orderwert: {min_cost} {quote_currency}")
            
            # 5. Anwenden der Handelsregeln
            
            # Mengenanpassung an Step-Size
            if step_size:
                # Abrundung auf den nächsten gültigen Step
                factor = 1.0 / step_size
                quantity = math.floor(quantity * factor) / factor
                print(f"{Fore.CYAN}[{datetime.now().strftime('%H:%M:%S')}] Menge an Schrittgröße angepasst: {quantity}{Style.RESET_ALL}")
            elif precision is not None:
                # Fallback: Wenn keine Step-Size, verwende Präzision
                quantity = math.floor(quantity * (10 ** precision)) / (10 ** precision)
                print(f"{Fore.CYAN}[{datetime.now().strftime('%H:%M:%S')}] Menge an Präzision angepasst: {quantity}{Style.RESET_ALL}")
            
            # Mindestmengenprüfung
            if min_amount and quantity < min_amount:
                old_quantity = quantity
                quantity = min_amount
                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Menge von {old_quantity} auf Minimum von {min_amount} erhöht{Style.RESET_ALL}")
            
            # Maximalmengenprüfung
            if max_amount and quantity > max_amount:
                old_quantity = quantity
                quantity = max_amount
                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Menge von {old_quantity} auf Maximum von {max_amount} begrenzt{Style.RESET_ALL}")
            
            # Mindestorderwertprüfung
            if min_cost:
                order_value = quantity * current_price
                if order_value < min_cost:
                    old_quantity = quantity
                    # Berechne minimale Menge, die den Mindestorderwert erreicht
                    quantity = min_cost / current_price
                    # Runde wieder auf Step-Size
                    if step_size:
                        factor = 1.0 / step_size
                        quantity = math.ceil(quantity * factor) / factor
                    elif precision is not None:
                        quantity = math.ceil(quantity * (10 ** precision)) / (10 ** precision)
                    
                    print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Menge von {old_quantity} auf {quantity} erhöht, um Mindestorderwert von {min_cost} {quote_currency} zu erreichen{Style.RESET_ALL}")
        else:
            # Fallback: Wenn keine Marktdaten verfügbar, verwende vorsichtige Standardeinstellungen
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Keine Marktdaten verfügbar. Verwende konservative Standardwerte für {base_currency}{Style.RESET_ALL}")
            
            # Konservative Standardwerte für gängige Kryptowährungen
            if base_currency == 'BTC':
                precision = 5
                min_amount = 0.00001
            elif base_currency == 'ETH':
                precision = 4
                min_amount = 0.0001
            elif base_currency == 'SOL':
                precision = 1
                min_amount = 0.1
            else:
                # Für unbekannte Coins, verwende moderate Werte
                precision = 2
                min_amount = 0.01
            
            print(f"{Fore.YELLOW}Standardwerte: Präzision={precision}, Mindestmenge={min_amount}{Style.RESET_ALL}")
            
            # Anwenden der Standard-Präzision
            quantity = math.floor(quantity * (10 ** precision)) / (10 ** precision)
            
            # Mindestmengenprüfung
            if quantity < min_amount:
                quantity = min_amount
                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Menge auf Standard-Mindestmenge von {min_amount} gesetzt{Style.RESET_ALL}")
        
        # Final berechnete Menge anzeigen
        print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Finale Handelsmenge: {quantity} {base_currency} (Wert: {quantity * current_price:.2f} {quote_currency}){Style.RESET_ALL}")
        
        return quantity
        
    except Exception as e:
        utils.log_error(e, f"Fehler bei der Berechnung der Handelsmenge")
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Exception bei Mengenberechnung: {str(e)}{Style.RESET_ALL}")
        # Fallback auf Standard-Menge
        return config.QUANTITY

def place_limit_order(exchange, symbol, side, amount, price):
    """Platziere eine Limit-Order"""
    try:
        base_currency = config.get_base_currency()
        quote_currency = config.get_quote_currency()
        
        # Sicherheitscheck für Live-Trading
        if not config.USE_TESTNET and config.CONFIRM_TRADES:
            confirmation = input(f"{Fore.YELLOW}Bestätigen Sie die Limit-Order: {side.upper()} {amount} {base_currency} @ {price:.2f} {quote_currency}? (j/n): {Style.RESET_ALL}")
            if confirmation.lower() != 'j':
                print(f"{Fore.RED}Limit-Order abgebrochen durch Benutzer.{Style.RESET_ALL}")
                return None
        
        # Parameter je nach Modus anpassen
        params = {}
        if config.USE_TESTNET:
            # Futures Testnet
            params = {'positionSide': 'BOTH'}
        
        # Order erstellen mit passenden Parametern
        order = exchange.create_limit_order(
            symbol=symbol,
            side=side,
            amount=amount,
            price=price,
            params=params
        )
        return order
    except Exception as e:
        utils.log_error(e, f"Fehler beim Platzieren der Limit-Order für {symbol}")
        return None

def place_stop_loss(exchange, symbol, side, amount, stop_price, limit_price=None):
    """Platziere eine Stop-Loss-Order (nur im Futures-Modus verfügbar)"""
    try:
        base_currency = config.get_base_currency()
        quote_currency = config.get_quote_currency()
        
        # Stop-Loss nur im Futures-Modus verfügbar
        if not config.USE_TESTNET:
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Stop-Loss-Orders sind im Spot-Modus nicht verfügbar.{Style.RESET_ALL}")
            return None
            
        params = {
            'stopPrice': stop_price,
            'positionSide': 'BOTH'
        }
        
        if limit_price:
            # Stop-Limit-Order
            params['price'] = limit_price
            order_type = 'STOP_LIMIT'
        else:
            # Stop-Market-Order
            order_type = 'STOP_MARKET'
        
        # Sicherheitscheck für Live-Trading
        if not config.USE_TESTNET and config.CONFIRM_TRADES:
            order_desc = f"Stop-{order_type} Order: {side.upper()} {amount} {base_currency} @ {stop_price:.2f} {quote_currency}"
            confirmation = input(f"{Fore.YELLOW}Bestätigen Sie die {order_desc}? (j/n): {Style.RESET_ALL}")
            if confirmation.lower() != 'j':
                print(f"{Fore.RED}Stop-Loss-Order abgebrochen durch Benutzer.{Style.RESET_ALL}")
                return None
                
        order = exchange.create_order(
            symbol=symbol,
            type=order_type,
            side=side,
            amount=amount,
            params=params
        )
        return order
    except Exception as e:
        utils.log_error(e, f"Fehler beim Platzieren der Stop-Loss-Order für {symbol}")
        return None

def place_take_profit(exchange, symbol, side, amount, take_profit_price, limit_price=None):
    """Platziere eine Take-Profit-Order (nur im Futures-Modus verfügbar)"""
    try:
        base_currency = config.get_base_currency()
        quote_currency = config.get_quote_currency()
        
        # Take-Profit nur im Futures-Modus verfügbar
        if not config.USE_TESTNET:
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Take-Profit-Orders sind im Spot-Modus nicht verfügbar.{Style.RESET_ALL}")
            return None
            
        params = {
            'stopPrice': take_profit_price,
            'positionSide': 'BOTH',
            'reduceOnly': True
        }
        
        if limit_price:
            # Take-Profit-Limit-Order
            params['price'] = limit_price
            order_type = 'TAKE_PROFIT_LIMIT'
        else:
            # Take-Profit-Market-Order
            order_type = 'TAKE_PROFIT_MARKET'
        
        # Sicherheitscheck für Live-Trading
        if not config.USE_TESTNET and config.CONFIRM_TRADES:
            order_desc = f"Take-Profit Order: {side.upper()} {amount} {base_currency} @ {take_profit_price:.2f} {quote_currency}"
            confirmation = input(f"{Fore.YELLOW}Bestätigen Sie die {order_desc}? (j/n): {Style.RESET_ALL}")
            if confirmation.lower() != 'j':
                print(f"{Fore.RED}Take-Profit-Order abgebrochen durch Benutzer.{Style.RESET_ALL}")
                return None
        
        order = exchange.create_order(
            symbol=symbol,
            type=order_type,
            side=side,
            amount=amount,
            params=params
        )
        return order
    except Exception as e:
        utils.log_error(e, f"Fehler beim Platzieren der Take-Profit-Order für {symbol}")
        return None

def cancel_order(exchange, order_id, symbol):
    """Storniere eine bestehende Order"""
    try:
        return exchange.cancel_order(order_id, symbol)
    except Exception as e:
        utils.log_error(e, f"Fehler beim Stornieren der Order {order_id} für {symbol}")
        return None

def cancel_all_orders(exchange, symbol):
    """Storniere alle bestehenden Orders für ein Symbol"""
    try:
        return exchange.cancel_all_orders(symbol)
    except Exception as e:
        utils.log_error(e, f"Fehler beim Stornieren aller Orders für {symbol}")
        return None

def get_open_orders(exchange, symbol=None):
    """Hole alle offenen Orders"""
    try:
        return exchange.fetch_open_orders(symbol)
    except Exception as e:
        utils.log_error(e, f"Fehler beim Abrufen der offenen Orders für {symbol}")
        return []