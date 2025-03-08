import time
from datetime import datetime
import getpass
import colorama
from colorama import Fore, Style
import sys

# Import der Module
import exchange_handler
import indicators
import strategies
import risk_management
import performance
import utils
import config

# Farbige Ausgabe initialisieren
colorama.init(autoreset=True)

def get_api_credentials():
    """
    Versucht API-Daten aus der Config zu lesen und fragt sie nur ab, wenn sie nicht gefunden werden
    """
    # Prüfe, ob API-Daten in der Config vorhanden sind
    api_key = getattr(config, 'API_KEY', None)
    api_secret = getattr(config, 'API_SECRET', None)
    
    # Wenn beide in der Config vorhanden sind, verwende diese
    if api_key and api_secret:
        print(f"{Fore.GREEN}API-Konfiguration aus config.py geladen.{Style.RESET_ALL}")
        return api_key, api_secret
    
    # Andernfalls vom Benutzer abfragen
    print(Fore.YELLOW + "\n=== API Konfiguration ===" + Style.RESET_ALL)
    print(f"{Fore.CYAN}Keine API-Daten in config.py gefunden, bitte manuell eingeben:{Style.RESET_ALL}")
    api_key = input(Fore.CYAN + "API-Schlüssel: " + Style.RESET_ALL)
    api_secret = getpass.getpass(Fore.CYAN + "API-Secret: " + Style.RESET_ALL)
    return api_key, api_secret

# Additional CLI arguments for signal analysis

if len(sys.argv) > 1 and sys.argv[1] == "--analyze-signals":
    time_period = sys.argv[2] if len(sys.argv) > 2 else "all"
    utils.print_rejected_signals_report(time_period)
    sys.exit(0)

def run_bot(exchange):
    """Hauptfunktion zum Ausführen des Trading-Bots"""
    
    base_currency = config.get_base_currency()
    quote_currency = config.get_quote_currency()
    
    trading_mode = "Binance Futures Testnet" if config.USE_TESTNET else "Binance Spot Live"
    print(f"\n{Fore.CYAN}Bot gestartet für {config.SYMBOL} auf {trading_mode}...{Style.RESET_ALL}")
    
    # Prüfe Kontostand
    try:
        balance = exchange.fetch_balance()
        if config.USE_TESTNET:
            quote_balance = balance[quote_currency]['free']
        else:
            quote_balance = balance.get(quote_currency, {}).get('free', 0)
        print(f"{Fore.GREEN}Bot erfolgreich initialisiert!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Verfügbares {quote_currency}: {quote_balance:.2f}{Style.RESET_ALL}")
    except Exception as e:
        utils.log_error(e, "Fehler beim Abrufen des Kontostands")
        quote_balance = 0
    
    # Prüfe aktuelle Position über die API
    current_position, position_info = exchange_handler.get_position(exchange, config.SYMBOL)
    
    # Lade gespeicherte Position
    saved_position_size, saved_position_type, saved_entry_price = utils.load_position_state()

    # Positionskonfliktlösung
    if current_position == 0 and saved_position_size != 0:
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Positionskonflikt erkannt: API meldet keine Position, lokaler Speicher zeigt {saved_position_type} {abs(saved_position_size)} {base_currency} @ {saved_entry_price} {quote_currency}{Style.RESET_ALL}")
        
        # Option 1: Vertraue der API
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Lösung: Vertraue der API. Keine Position aktiv.{Style.RESET_ALL}")
        # Aktualisiere lokalen Speicher, um ihn mit der API zu synchronisieren
        utils.save_position_state(0, "KEINE", 0)
        
        # Option 2 (auskommentiert): Vertraue dem lokalen Speicher
        # Nur in bestimmten Fällen aktivieren, wenn die API unzuverlässig ist
        '''
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Lösung: Vertraue lokalem Speicher. Setze Position manuell.{Style.RESET_ALL}")
        current_position = saved_position_size
        position_info['size'] = saved_position_size
        position_info['type'] = saved_position_type
        position_info['entry_price'] = saved_entry_price
        '''
    elif current_position != 0 and saved_position_size == 0:
        # API zeigt Position, lokaler Speicher nicht
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Positionskonflikt erkannt: API meldet {position_info['type']} {abs(current_position)} {base_currency}, lokaler Speicher keine Position{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Lösung: Aktualisiere lokalen Speicher basierend auf API-Daten{Style.RESET_ALL}")
        utils.save_position_state(
            current_position, 
            position_info['type'], 
            position_info.get('entry_price', 0)
        )
    elif current_position != 0 and saved_position_size != 0 and (current_position != saved_position_size or position_info['type'] != saved_position_type):
        # Beide zeigen Positionen, aber unterschiedliche
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Positionskonflikt erkannt: API meldet {position_info['type']} {abs(current_position)} {base_currency}, lokaler Speicher {saved_position_type} {abs(saved_position_size)} {base_currency}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Lösung: Vertraue der API. Aktualisiere lokalen Speicher.{Style.RESET_ALL}")
        utils.save_position_state(
            current_position, 
            position_info['type'], 
            position_info.get('entry_price', 0)
        )
    
    # Initialisierung der Variablen
    last_action = None
    entry_price = position_info.get('entry_price', 0)
    # Setze Entry-Preis, wenn er noch nicht gesetzt ist
    if entry_price == 0 and current_position != 0 and saved_entry_price != 0:
        entry_price = saved_entry_price
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Einstiegspreis aus lokalem Speicher wiederhergestellt: {entry_price} {quote_currency}{Style.RESET_ALL}")
    
    current_price = 0
    
    # Zähler für regelmäßige Positionsüberprüfung
    position_check_counter = 0
    
    # Performance-Tracking initialisieren
    performance_tracker = performance.PerformanceTracker()
    
    # Tracking für API-Fehler
    consecutive_failures = 0
    
    try:
        while True:
            try:
                # Hole und analysiere Daten
                df = exchange_handler.get_historical_data(exchange, config.SYMBOL, config.TIMEFRAME, config.LIMIT)
                if df.empty:
                    consecutive_failures += 1
                    wait_time = min(config.UPDATE_INTERVAL * consecutive_failures, 300)  # Max 5 Minuten warten
                    print(f"{Fore.RED}Keine gültigen Daten verfügbar. Warte {wait_time} Sekunden... (Fehler #{consecutive_failures}){Style.RESET_ALL}")
                    
                    # Aktualisiere Anzeige mit Fehlerstatus, aber führe keine Trades aus
                    utils.update_display(
                        df, 
                        current_position, 
                        quote_balance, 
                        f"{Fore.RED}Keine Daten verfügbar - Trading pausiert{Style.RESET_ALL}", 
                        {"allow_trade": False, "reason": "Keine Marktdaten verfügbar"},
                        {"strategy": config.ACTIVE_STRATEGY, "description": "Ausführung pausiert - Warte auf gültige Daten"},
                        performance_tracker,
                        position_info
                    )
                    time.sleep(wait_time)
                    continue
                
                # Zurücksetzen des Fehlerzählers bei erfolgreicher Datenabfrage
                consecutive_failures = 0
                
                # Berechne alle Indikatoren
                df = indicators.calculate_all_indicators(df)
                
                # Verwende lokale Position statt API-Abfrage bei jedem Zyklus
                saved_position_size, saved_position_type, saved_entry_price = utils.load_position_state()
                current_position = saved_position_size
                position_info = {
                                'size': saved_position_size,
                                'type': saved_position_type,
                                'entry_price': saved_entry_price,
                                'liquidation_price': 0,
                                'unrealized_pnl': 0,
                                'leverage': 1
                                }
                
                try:
                    balance = exchange.fetch_balance()
                    if config.USE_TESTNET:
                        quote_balance = balance[quote_currency]['free']
                    else:
                        quote_balance = balance.get(quote_currency, {}).get('free', 0)
                except Exception as balance_error:
                    utils.log_error(balance_error, f"Fehler beim Aktualisieren des {quote_currency}-Kontostands - verwende letzten bekannten Wert")
                    # Wir verwenden weiterhin den letzten bekannten Wert von quote_balance
                
                # Aktuelle Werte
                current_price = df['close'].iloc[-1]
                
                # Speichere die aktuelle Position für einen eventuellen Neustart
                utils.save_position_state(current_position, position_info.get('type', 'KEINE'), position_info.get('entry_price', 0))
                
                # Generiere Handelssignal basierend auf der gewählten Strategie
                if config.ACTIVE_STRATEGY == 'SMALL_CAPITAL':
                    from small_capital_strategy import get_small_capital_strategy_instance
                    small_cap_strategy = get_small_capital_strategy_instance()
                    try:
                        signal, strategy_info = small_cap_strategy.smart_small_capital_strategy(df, actual_balance=quote_balance)
                    except Exception as e:
                        # Verbesserte Fehlerbehandlung
                        error_msg = f"Fehler bei Ausführung der SMALL_CAPITAL Strategie: {str(e)}"
                        utils.log_error(e, error_msg)
                        
                        # Erstelle ein Fehler-Strategie-Info-Objekt
                        strategy_info = {
                            'strategy': 'SMALL_CAPITAL (Fehler)',
                            'description': error_msg,
                            'signal_details': f"Fehler: {str(e)}",
                            # Füge einen leeren selected_strategy-Wert hinzu, um Fehler zu vermeiden
                            'selected_strategy': 'NONE'
                        }
                        signal = 0  # Kein Signal bei Fehler
                
                elif config.ACTIVE_STRATEGY == 'DAY_TRADER':
                    # Spezialbehandlung für Day Trader Strategie
                    from day_trader_strategy import get_day_trader_strategy_instance
                    day_trader = get_day_trader_strategy_instance()
                    try:
                        signal, strategy_info = day_trader.day_trader_strategy(df, actual_balance=quote_balance)
                        
                        # Aktualisiere Trade-Informationen für die Selbstoptimierung
                        if last_action and "Position geschlossen" in last_action:
                            try:
                                import re
                                profit_match = re.search(r"G/V: .*?([-+]?\d+\.\d+)", last_action)
                                if profit_match:
                                    profit = float(profit_match.group(1))
                                    # Einstiegspreis aus position_info oder entry_price
                                    entry_p = position_info.get('entry_price', entry_price)
                                    day_trader.record_trade_result('SELL', entry_p, current_price, profit)
                            except Exception as e:
                                print(f"{Fore.YELLOW}Info: Fehler beim Aktualisieren der Trade-Informationen: {e}{Style.RESET_ALL}")
                    except Exception as e:
                        # Verbesserte Fehlerbehandlung
                        error_msg = f"Fehler bei Ausführung der DAY_TRADER Strategie: {str(e)}"
                        utils.log_error(e, error_msg)
                        
                        # Erstelle ein Fehler-Strategie-Info-Objekt
                        strategy_info = {
                            'strategy': 'DAY_TRADER (Fehler)',
                            'description': error_msg,
                            'signal_details': f"Fehler: {str(e)}",
                            # Füge einen leeren selected_strategy-Wert hinzu, um Fehler zu vermeiden
                            'selected_strategy': 'NONE'
                        }
                        signal = 0  # Kein Signal bei Fehler
                
                else:
                    try:
                        signal, strategy_info = strategies.get_strategy_signal(df, config.ACTIVE_STRATEGY)
                    except Exception as e:
                        # Verbesserte Fehlerbehandlung
                        error_msg = f"Fehler bei Ausführung der {config.ACTIVE_STRATEGY} Strategie: {str(e)}"
                        utils.log_error(e, error_msg)
                        
                        # Erstelle ein Fehler-Strategie-Info-Objekt
                        strategy_info = {
                            'strategy': f"{config.ACTIVE_STRATEGY} (Fehler)",
                            'description': error_msg,
                            'signal_details': f"Fehler: {str(e)}",
                            # Füge einen leeren selected_strategy-Wert hinzu, um Fehler zu vermeiden
                            'selected_strategy': 'NONE'
                        }
                        signal = 0  # Kein Signal bei Fehler
                
                # Risikomanagement
                risk_result = risk_management.check_risk(df, current_position, current_price, entry_price, quote_balance)
                
                # Trading-Entscheidung
                execute_trade = risk_result['allow_trade'] and signal != 0
                
                # Führe Trade aus, wenn Signal und Risikomanagement es erlauben
                if execute_trade:
                    if config.USE_TESTNET:
                        # FUTURES TESTNET MODE
                        if signal > 0 and current_position <= 0:  # Kaufsignal
                            if current_position < 0:  # Schließe Short-Position zuerst
                                closed_order = exchange_handler.execute_trade(exchange, config.SYMBOL, 'buy', abs(current_position), current_price)
                                if closed_order:
                                    last_action = f"{Fore.YELLOW}SHORT Position geschlossen{Style.RESET_ALL}"
                                    # Berechne Gewinn/Verlust
                                    if entry_price > 0:
                                        trade_profit = abs(current_position) * (entry_price - current_price)
                                        performance_tracker.add_trade('SHORT', entry_price, current_price, current_position, trade_profit)
                                        profit_color = Fore.GREEN if trade_profit > 0 else Fore.RED
                                        last_action += f" (G/V: {profit_color}{trade_profit:.2f} {quote_currency}{Style.RESET_ALL})"
                            
                            # Berechne optimale Positionsgröße basierend auf Risikomanagement
                            position_size = risk_management.calculate_position_size(quote_balance, current_price, config.QUANTITY)
                            
                            # Öffne Long-Position
                            open_order = exchange_handler.execute_trade(exchange, config.SYMBOL, 'buy', position_size, current_price)
                            if open_order:
                                last_action = f"{Fore.GREEN}LONG Position eröffnet @ {current_price:.2f} {quote_currency}{Style.RESET_ALL}"
                                last_action += f" | Gesamtwert: {position_size * current_price:.2f} {quote_currency}"
                                entry_price = current_price
                                
                                # Sofortiges Positionsupdate nach Trade
                                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Trade ausgeführt - Aktualisiere Position...{Style.RESET_ALL}")
                                time.sleep(1)  # Kurze Pause für API-Synchronisation
                                
                                # Hole aktualisierte Position
                                current_position, position_info = exchange_handler.get_position(exchange, config.SYMBOL)
                                
                                # Speichere die Position in der lokalen Datei
                                utils.save_position_state(
                                    current_position, 
                                    position_info.get('type', 'KEINE'), 
                                    entry_price
                                )
                            
                        elif signal < 0 and current_position >= 0:  # Verkaufssignal
                            if current_position > 0:  # Schließe Long-Position zuerst
                                closed_order = exchange_handler.execute_trade(exchange, config.SYMBOL, 'sell', current_position, current_price)
                                if closed_order:
                                    last_action = f"{Fore.YELLOW}LONG Position geschlossen{Style.RESET_ALL}"
                                    # Berechne Gewinn/Verlust
                                    if entry_price > 0:
                                        trade_profit = current_position * (current_price - entry_price)
                                        performance_tracker.add_trade('LONG', entry_price, current_price, current_position, trade_profit)
                                        profit_color = Fore.GREEN if trade_profit > 0 else Fore.RED
                                        last_action += f" (G/V: {profit_color}{trade_profit:.2f} {quote_currency}{Style.RESET_ALL})"
                                        last_action += f" | Gesamtwert: {abs(current_position) * current_price:.2f} {quote_currency}"
                            
                            # Berechne optimale Positionsgröße basierend auf Risikomanagement
                            position_size = risk_management.calculate_position_size(quote_balance, current_price, config.QUANTITY)
                            
                            # Öffne Short-Position
                            open_order = exchange_handler.execute_trade(exchange, config.SYMBOL, 'sell', position_size, current_price)
                            if open_order:
                                last_action = f"{Fore.RED}SHORT Position eröffnet @ {current_price:.2f} {quote_currency}{Style.RESET_ALL}"
                                entry_price = current_price
                                
                                # Sofortiges Positionsupdate nach Trade
                                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Trade ausgeführt - Aktualisiere Position...{Style.RESET_ALL}")
                                time.sleep(1)  # Kurze Pause für API-Synchronisation
                                
                                # Hole aktualisierte Position
                                current_position, position_info = exchange_handler.get_position(exchange, config.SYMBOL)
                                
                                # Speichere die Position in der lokalen Datei
                                utils.save_position_state(
                                    current_position, 
                                    position_info.get('type', 'KEINE'), 
                                    entry_price
                                )
                    else:
                        # SPOT LIVE MODE
                        # Im Spot-Handel können wir nur kaufen, wenn wir Quote-Währung haben, und verkaufen, wenn wir Base-Währung haben                       
                        if signal > 0:  # Kaufsignal
                            # Überprüfe Quote-Währung-Guthaben
                            try:
                                balance = exchange.fetch_balance()
                                quote_balance = balance.get(quote_currency, {}).get('free', 0)
                                
                                # Verwende calculate_quantity für flexible Positionsgrößenberechnung
                                position_size = exchange_handler.calculate_quantity(exchange, current_price, quote_balance)
                                trade_value = position_size * current_price
                                
                                if quote_balance > trade_value:
                                    # Kaufe Base-Währung
                                    open_order = exchange_handler.execute_trade(exchange, config.SYMBOL, 'buy', position_size, current_price)
                                    if open_order:
                                        last_action = f"{Fore.GREEN}Kauf von {position_size} {base_currency} @ {current_price:.2f} {quote_currency}{Style.RESET_ALL}"
                                        last_action += f" | Gesamtwert: {position_size * current_price:.2f} {quote_currency}"
                                        entry_price = current_price
                                        
                                        # Sofortiges Positionsupdate nach Trade
                                        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Trade ausgeführt - Aktualisiere Position...{Style.RESET_ALL}")
                                        time.sleep(1)  # Kurze Pause für API-Synchronisation
                                        
                                        # Hole aktualisierte Position
                                        current_position, position_info = exchange_handler.get_position(exchange, config.SYMBOL)
                                        
                                        # Speichere die Position in der lokalen Datei
                                        utils.save_position_state(
                                            current_position, 
                                            position_info.get('type', 'KEINE'), 
                                            entry_price
                                        )
                                        
                                        # Wenn Small Capital Strategie aktiv, letzte Kaufdaten aktualisieren
                                        if config.ACTIVE_STRATEGY == 'SMALL_CAPITAL':
                                            small_cap_strategy = get_small_capital_strategy_instance()
                                            small_cap_strategy.last_buy_price = current_price
                                            small_cap_strategy.last_trade_time = datetime.now()
                                            small_cap_strategy.last_trade_type = 'BUY'
                                            
                                else:
                                    print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Nicht genug {quote_currency} für Kauf: {quote_balance:.2f} verfügbar, {trade_value:.2f} benötigt{Style.RESET_ALL}")
                            except Exception as balance_error:
                                utils.log_error(balance_error, f"Fehler beim Überprüfen des {quote_currency}-Guthabens")
                                print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Konnte {quote_currency}-Guthaben nicht überprüfen: {str(balance_error)}{Style.RESET_ALL}")
                        
                        elif signal < 0 and current_position > 0:  # Verkaufssignal und Base-Währung im Besitz
                            # Berechne zu verkaufende Menge
                            sell_size = min(current_position, config.QUANTITY)
                            
                            # Verwende calculate_quantity für prozentuale Positionsgrößen
                            if config.QUANTITY_TYPE == 'PERCENTAGE':
                                # Verkaufe Prozentsatz des aktuellen Bestands
                                sell_size = current_position * config.QUANTITY
                                sell_size = min(current_position, sell_size)  # Nicht mehr als wir haben
                            
                            # Verkaufe Base-Währung
                            sell_order = exchange_handler.execute_trade(exchange, config.SYMBOL, 'sell', sell_size, current_price)
                            if sell_order:
                                last_action = f"{Fore.RED}Verkauf von {sell_size} {base_currency} @ {current_price:.2f} {quote_currency}{Style.RESET_ALL}"
                                
                                # Berechne Gewinn/Verlust wenn möglich
                                if entry_price > 0:
                                    trade_profit = sell_size * (current_price - entry_price)
                                    performance_tracker.add_trade('SPOT', entry_price, current_price, sell_size, trade_profit)
                                    profit_color = Fore.GREEN if trade_profit > 0 else Fore.RED
                                    last_action += f" (G/V: {profit_color}{trade_profit:.2f} {quote_currency}{Style.RESET_ALL})"
                                    last_action += f" | Gesamtwert: {sell_size * current_price:.2f} {quote_currency}"
                                
                                # Sofortiges Positionsupdate nach Trade
                                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Trade ausgeführt - Aktualisiere Position...{Style.RESET_ALL}")
                                time.sleep(1)  # Kurze Pause für API-Synchronisation
                                
                                # Hole aktualisierte Position
                                current_position, position_info = exchange_handler.get_position(exchange, config.SYMBOL)
                                
                                # Speichere die Position in der lokalen Datei
                                utils.save_position_state(
                                    current_position, 
                                    position_info.get('type', 'KEINE'), 
                                    0  # Nach Verkauf kein Entry-Preis mehr
                                )
                                
                                # Wenn Small Capital Strategie aktiv, letzte Verkaufsdaten aktualisieren
                                if config.ACTIVE_STRATEGY == 'SMALL_CAPITAL':
                                    small_cap_strategy = get_small_capital_strategy_instance()
                                    small_cap_strategy.last_sell_price = current_price
                                    small_cap_strategy.last_trade_time = datetime.now()
                                    small_cap_strategy.last_trade_type = 'SELL'
                else:
                    # Wenn Risikomanagement den Trade nicht erlaubt
                    if signal != 0 and not risk_result['allow_trade']:
                        risk_reason = risk_result.get('reason', 'Unbekannter Risikogrund')
                        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Handelssignal ignoriert wegen Risikomanagement: {risk_reason}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Kein neues Handelssignal. Aktuelle Empfehlung: HALTEN{Style.RESET_ALL}")
                
                # Update Anzeige mit allen Informationen
                utils.update_display(
                    df, 
                    current_position, 
                    quote_balance, 
                    last_action, 
                    risk_result,
                    strategy_info,
                    performance_tracker,
                    position_info
                )
                
                # Erhöhe den Zähler für Positionsüberprüfung
                position_check_counter += 1
                
                # Regelmäßige Positions-Überprüfung
                if position_check_counter % 20 == 0:  # Jeder 20. Zyklus
                    print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Führe regelmäßige Positions-Überprüfung durch...{Style.RESET_ALL}")
                    
                    # Position über API abrufen
                    api_position, api_position_info = exchange_handler.get_position(exchange, config.SYMBOL)
                    
                    # Lokal gespeicherte Position laden
                    saved_position_size, saved_position_type, saved_entry_price = utils.load_position_state()
                    
                    # Prüfen ob Diskrepanz besteht
                    if api_position != saved_position_size:
                        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Positions-Diskrepanz entdeckt: API zeigt {api_position}, lokal gespeichert ist {saved_position_size}{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Synchronisiere mit API-Daten...{Style.RESET_ALL}")
                        
                        # Lokale Position aktualisieren
                        utils.save_position_state(
                            api_position, 
                            api_position_info.get('type', 'KEINE'), 
                            api_position_info.get('entry_price', saved_entry_price if api_position != 0 else 0)
                        )
                        
                        # Aktualisiere lokale Variablen
                        current_position = api_position
                        position_info = api_position_info
                        if api_position != 0:
                            entry_price = api_position_info.get('entry_price', saved_entry_price)
                
                # Warte vor dem nächsten Update
                time.sleep(config.UPDATE_INTERVAL)
                
            except Exception as e:
                consecutive_failures += 1
                utils.log_error(e, "Fehler im Hauptloop des Bots")
                
                # Erhöhe Wartezeit bei mehreren aufeinanderfolgenden Fehlern
                wait_time = min(config.UPDATE_INTERVAL * consecutive_failures, 300)  # Max 5 Minuten
                print(f"{Fore.RED}Fehler im Hauptloop. Warte {wait_time} Sekunden vor dem nächsten Versuch... (Fehler #{consecutive_failures}){Style.RESET_ALL}")
                time.sleep(wait_time)
    
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Bot wird beendet...{Style.RESET_ALL}")
        
        # Performance-Bericht anzeigen
        performance_tracker.print_summary()
        
        # Offene Positionen schließen
        if current_position != 0:
            print(f"{Fore.YELLOW}Schließe offene Positionen...{Style.RESET_ALL}")
            try:
                if current_position > 0:
                    exchange_handler.execute_trade(exchange, config.SYMBOL, 'sell', current_position, current_price)
                else:
                    exchange_handler.execute_trade(exchange, config.SYMBOL, 'buy', abs(current_position), current_price)
                print(f"{Fore.GREEN}Positionen erfolgreich geschlossen.{Style.RESET_ALL}")
            except Exception as e:
                utils.log_error(e, "Fehler beim Schließen offener Positionen")
        
        print(f"{Fore.GREEN}Bot erfolgreich beendet!{Style.RESET_ALL}")

def main():
    utils.print_banner()
    
    base_currency = config.get_base_currency()
    quote_currency = config.get_quote_currency()
    
    # Zeige Hinweis zum aktuellen Modus
    if config.USE_TESTNET:
        print(f"{Fore.CYAN}Bot läuft im FUTURES TESTNET Modus{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Es wird kein echtes Geld gehandelt.{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Bot läuft im SPOT LIVE Modus{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}In diesem Modus können Sie nur Long-Positionen halten (keine Shorts).{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Sie benötigen {quote_currency} zum Kaufen und {base_currency} zum Verkaufen.{Style.RESET_ALL}")
    
    # Zeige prominente Warnung für Live-Trading
    if not config.USE_TESTNET:
        print(f"\n{Fore.RED}▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓{Style.RESET_ALL}")
        print(f"{Fore.RED}▓                                                       ▓{Style.RESET_ALL}")
        print(f"{Fore.RED}▓             !!! LIVE-TRADING AKTIVIERT !!!            ▓{Style.RESET_ALL}")
        print(f"{Fore.RED}▓         SIE HANDELN JETZT MIT ECHTEM GELD!            ▓{Style.RESET_ALL}")
        print(f"{Fore.RED}▓                                                       ▓{Style.RESET_ALL}")
        print(f"{Fore.RED}▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓{Style.RESET_ALL}")
        
        confirmation = input(f"\n{Fore.YELLOW}Sind Sie ABSOLUT SICHER, dass Sie mit ECHTEM GELD handeln möchten? (j/ja/n/nein): {Style.RESET_ALL}")
        if confirmation.lower() not in ['j', 'ja', 'y', 'yes']:
            print(f"\n{Fore.GREEN}Live-Trading abgebrochen. Um im Testnet-Modus zu handeln, ändern Sie USE_TESTNET=True in config.py{Style.RESET_ALL}")
            return
    
    try:
        # Frage nach API-Daten (neue Funktion, die zuerst in config.py nachschaut)
        api_key, api_secret = get_api_credentials()
        
        # Hinweis zum Verbindungsmodus
        if config.USE_TESTNET:
            print(f"\n{Fore.YELLOW}Verbinde mit Binance Futures Testnet...{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}Verbinde mit Binance Spot Live...{Style.RESET_ALL}")
        
        # Initialisiere Exchange
        exchange = exchange_handler.initialize_exchange(api_key, api_secret)
        if exchange is None:
            print(f"{Fore.RED}Exchange konnte nicht initialisiert werden.{Style.RESET_ALL}")
            return
            
        # Teste API-Verbindung wurde bereits in initialize_exchange durchgeführt
        
        # Konfiguration anzeigen
        print(f"\n{Fore.CYAN}Konfiguration:{Style.RESET_ALL}")
        print(f"Symbol: {Fore.YELLOW}{config.SYMBOL}{Style.RESET_ALL}")
        print(f"Zeitintervall: {Fore.YELLOW}{config.TIMEFRAME}{Style.RESET_ALL}")
        
        # Zeige Handelsmenge basierend auf QUANTITY_TYPE
        if config.QUANTITY_TYPE == 'ABSOLUTE':
            print(f"Handelsmenge: {Fore.YELLOW}{config.QUANTITY} {base_currency}{Style.RESET_ALL}")
        else:
            print(f"Handelsmenge: {Fore.YELLOW}{config.QUANTITY*100}% des verfügbaren {quote_currency}-Guthabens{Style.RESET_ALL}")
            
        print(f"Update-Intervall: {Fore.YELLOW}{config.UPDATE_INTERVAL} Sekunden{Style.RESET_ALL}")
        print(f"Aktive Strategie: {Fore.YELLOW}{config.ACTIVE_STRATEGY}{Style.RESET_ALL}\n")
        
        # Bestätigung vom Benutzer einholen
        confirmation = input(f"{Fore.YELLOW}Möchten Sie den Bot starten? (j/ja/n/nein): {Style.RESET_ALL}")
        if confirmation.lower() in ['j', 'ja', 'y', 'yes']:
            run_bot(exchange)
        else:
            print(f"\n{Fore.RED}Bot-Start abgebrochen.{Style.RESET_ALL}")
    
    except Exception as e:
        utils.log_error(e, "Unerwarteter Fehler in der Hauptfunktion")
        print(f"\n{Fore.RED}Ein unerwarteter Fehler ist aufgetreten. Details wurden in bot_error.log gespeichert.{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        utils.log_error(e, "Kritischer Fehler außerhalb der Hauptfunktion", wait_for_input=True)
        print(f"\n{Fore.RED}Kritischer Fehler: {e}{Style.RESET_ALL}")
        print(f"{Fore.RED}Details wurden in bot_error.log gespeichert.{Style.RESET_ALL}")