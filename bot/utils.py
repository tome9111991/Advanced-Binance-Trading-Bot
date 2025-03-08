import os
import traceback
from datetime import datetime
from colorama import Fore, Style
import config
from signal_proximity import calculate_signal_proximity, generate_signal_proximity_display
import pandas as pd
from datetime import datetime, timedelta


# Globale Variablen
last_update_time = None
cycle_count = 0

def log_error(e, additional_info="", wait_for_input=False):
    """Schreibt Fehler in eine Datei und zeigt sie an"""
    error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_message = f"[{error_time}] ERROR: {str(e)}\n"
    if additional_info:
        error_message += f"Zusätzliche Info: {additional_info}\n"
    
    # Fehlerstapel abrufen
    error_traceback = traceback.format_exc()
    
    # In Datei schreiben
    with open("bot_error.log", "a") as f:
        f.write(error_message)
        f.write(error_traceback)
        f.write("\n" + "-"*50 + "\n")
    
    # Fehler in Konsole anzeigen
    print(f"\n{Fore.RED}====================== FEHLER ======================")
    print(f"{error_message}")
    print(f"{error_traceback}")
    print(f"Fehler wurde in bot_error.log gespeichert.")
    
    # Optional auf Eingabe warten
    if wait_for_input:
        print(f"Drücke ENTER, um fortzufahren oder STRG+C zum Beenden{Style.RESET_ALL}")
        try:
            input()
        except KeyboardInterrupt:
            raise  # Weitergeben, um den Bot zu beenden

def clear_screen():
    """Bildschirm leeren"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Banner ausgeben"""
    clear_screen()
    
    base_currency = config.get_base_currency()
    quote_currency = config.get_quote_currency()
    
    # Banner mit Testnet/Live-Indikator und Trading-Modus
    if config.USE_TESTNET:
        print(Fore.CYAN + """
    ╔══════════════════════════════════════════════════════╗
    ║          ADVANCED BINANCE FUTURES TRADING BOT        ║
    ║                    [TESTNET-MODUS]                   ║""" + Style.RESET_ALL)
        print(Fore.CYAN + f"    ║                  {config.SYMBOL} Trading                   ║" + Style.RESET_ALL)
        print(Fore.CYAN + """    ╚══════════════════════════════════════════════════════╝
    """ + Style.RESET_ALL)
    else:
        print(Fore.RED + """
    ╔══════════════════════════════════════════════════════╗
    ║          ADVANCED BINANCE SPOT TRADING BOT           ║
    ║                   [LIVE-HANDELSMODUS]                ║""" + Style.RESET_ALL)
        print(Fore.RED + f"    ║                  {config.SYMBOL} Trading                   ║" + Style.RESET_ALL)
        print(Fore.RED + """    ╚══════════════════════════════════════════════════════╝
    """ + Style.RESET_ALL)

def format_crypto_value(value, decimals=8):
    """Formatiert einen Kryptowährungsbetrag mit der richtigen Anzahl von Dezimalstellen"""
    return f"{value:.{decimals}f}"

def format_fiat_value(value, decimals=2):
    """Formatiert einen Fiat-Währungsbetrag mit der richtigen Anzahl von Dezimalstellen"""
    return f"{value:.{decimals}f}"

def format_time(timestamp):
    """Formatiert einen Zeitstempel"""
    if isinstance(timestamp, datetime):
        return timestamp.strftime("%d.%m.%Y %H:%M:%S")
    return timestamp

def update_display(df, position, balance, last_action=None, risk_result=None, strategy_info=None, performance_tracker=None, position_info=None):
    """Aktualisiert die Konsolenanzeige mit aktuellen Daten"""
    global last_update_time, cycle_count
    
    try:
        if df.empty:
            print(f"{Fore.RED}Keine Daten zum Anzeigen verfügbar.{Style.RESET_ALL}")
            return
        
        # Holen der Währungskonfiguration
        base_currency = config.get_base_currency()
        quote_currency = config.get_quote_currency()
        
        # Aktuelle Zeit für Update-Tracking
        current_time = datetime.now()
        current_time_str = current_time.strftime("%d.%m.%Y %H:%M:%S")
        
        # Update-Zyklus erhöhen
        cycle_count += 1
        
        # Berechne Zeit seit letztem Update
        time_since_last = "Erstes Update" if last_update_time is None else f"{(current_time - last_update_time).total_seconds():.1f} Sekunden"
        last_update_time = current_time
        
        # Modus anzeigen (Live/Testnet)
        mode_info = f"{Fore.RED}LIVE-HANDEL{Style.RESET_ALL}" if not config.USE_TESTNET else f"{Fore.GREEN}TESTNET{Style.RESET_ALL}"
        
        # Banner und Statusinfo
        clear_screen()
        print_banner()
        print(f"{Fore.CYAN}Update #{cycle_count} | {current_time_str} | Modus: {mode_info} | Zeit seit letztem Update: {time_since_last}{Style.RESET_ALL}")
        
        # Aktuelle Werte
        current_price = df['close'].iloc[-1]
        
        # Anzeige von Konto- und Positionsinformationen
        print(f"\n{Fore.YELLOW}Kontostand: {balance:.2f} {quote_currency} | Position: ", end="")
        if position > 0:
            print(f"{Fore.GREEN}LONG {position} {base_currency}" + Style.RESET_ALL)
        elif position < 0:
            print(f"{Fore.RED}SHORT {abs(position)} {base_currency}" + Style.RESET_ALL)
        else:
            print(f"{Fore.WHITE}KEINE" + Style.RESET_ALL)
        
        # Marktdaten
        print(f"\n{Fore.CYAN}=== Marktdaten für {base_currency}/{quote_currency} ==={Style.RESET_ALL}")
        print(f"Handelspaar: {Fore.YELLOW}{base_currency}/{quote_currency}{Style.RESET_ALL}")
        print(f"Aktueller Kurs: {Fore.YELLOW}1 {base_currency} = {current_price:.2f} {quote_currency}{Style.RESET_ALL}")
        print(f"24h Volumen: {Fore.YELLOW}{df['volume'].iloc[-1]:.2f}{Style.RESET_ALL}")
        
        # Preisänderungen
        if len(df) > 1:
            price_change_abs = current_price - df['close'].iloc[-2]
            price_change_pct = (price_change_abs / df['close'].iloc[-2]) * 100
            change_color = Fore.GREEN if price_change_abs >= 0 else Fore.RED
            change_symbol = "↑" if price_change_abs >= 0 else "↓"
            print(f"Preisänderung: {change_color}{change_symbol} {abs(price_change_abs):.2f} {quote_currency} ({price_change_pct:.2f}%){Style.RESET_ALL}")
        
        # Technische Indikatoren
        print(f"\n{Fore.CYAN}=== Technische Indikatoren ==={Style.RESET_ALL}")
        
        # SMA
        if 'sma_5' in df.columns and 'sma_20' in df.columns:
            sma_short = df['sma_5'].iloc[-1]
            sma_long = df['sma_20'].iloc[-1]
            print(f"SMA (kurz): {Fore.GREEN if sma_short > sma_long else Fore.RED}{sma_short:.2f}{Style.RESET_ALL}")
            print(f"SMA (lang): {Fore.GREEN if sma_long > sma_short else Fore.RED}{sma_long:.2f}{Style.RESET_ALL}")
            
            # SMA Trend
            if len(df) > 1:
                sma_short_prev = df['sma_5'].iloc[-2]
                sma_short_trend = "steigend" if sma_short > sma_short_prev else "fallend"
                print(f"SMA (kurz) Trend: {Fore.GREEN if sma_short > sma_short_prev else Fore.RED}{sma_short_trend}{Style.RESET_ALL}")
        
        # RSI
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            rsi_color = Fore.GREEN
            rsi_status = "neutral"
            if rsi < 30:
                rsi_color = Fore.RED
                rsi_status = "überkauft"
            elif rsi > 70:
                rsi_color = Fore.YELLOW
                rsi_status = "überverkauft"
            print(f"RSI: {rsi_color}{rsi:.2f} ({rsi_status}){Style.RESET_ALL}")
        
        # MACD
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            macd = df['macd'].iloc[-1]
            macd_signal = df['macd_signal'].iloc[-1]
            macd_hist = df['macd_hist'].iloc[-1]
            macd_color = Fore.GREEN if macd > macd_signal else Fore.RED
            print(f"MACD: {macd_color}{macd:.2f}{Style.RESET_ALL}")
            print(f"MACD Signal: {macd_color}{macd_signal:.2f}{Style.RESET_ALL}")
            print(f"MACD Histogramm: {Fore.GREEN if macd_hist > 0 else Fore.RED}{macd_hist:.2f}{Style.RESET_ALL}")
        
        # Bollinger Bands
        if 'bb_upper' in df.columns and 'bb_middle' in df.columns and 'bb_lower' in df.columns:
            bb_upper = df['bb_upper'].iloc[-1]
            bb_middle = df['bb_middle'].iloc[-1]
            bb_lower = df['bb_lower'].iloc[-1]
            
            # Position des Preises relativ zu den Bändern
            if current_price > bb_upper:
                bb_position = f"{Fore.RED}über oberem Band{Style.RESET_ALL}"
            elif current_price < bb_lower:
                bb_position = f"{Fore.GREEN}unter unterem Band{Style.RESET_ALL}"
            else:
                bb_position = f"{Fore.YELLOW}innerhalb der Bänder{Style.RESET_ALL}"
            
            print(f"Bollinger Bänder: {bb_position}")
            print(f"  Oberes Band: {bb_upper:.2f}")
            print(f"  Mittleres Band: {bb_middle:.2f}")
            print(f"  Unteres Band: {bb_lower:.2f}")
        
        # Strategie-Informationen
        if strategy_info:
            print(f"\n{Fore.CYAN}=== Strategie: {strategy_info.get('strategy', 'Unbekannt')} ==={Style.RESET_ALL}")
            if 'description' in strategy_info:
                print(f"Beschreibung: {strategy_info['description']}")
            if 'parameters' in strategy_info:
                print(f"Parameter: {strategy_info['parameters']}")
                
            # Für adaptive oder verbesserte adaptive Strategie zusätzliche Informationen anzeigen
            if strategy_info.get('strategy') in ['ADAPTIVE', 'ENHANCED_ADAPTIVE'] and 'selected_strategy' in strategy_info:
                print(f"Aktuell verwendete Strategie: {Fore.YELLOW}{strategy_info['selected_strategy']}{Style.RESET_ALL}")
                
                # Zeige Marktregime für erweiterte adaptive Strategie
                if 'market_regime' in strategy_info:
                    regime_color = Fore.GREEN if 'uptrend' in strategy_info['market_regime'] else (
                        Fore.RED if 'downtrend' in strategy_info['market_regime'] else Fore.YELLOW)
                    print(f"Marktregime: {regime_color}{strategy_info['market_regime'].upper()}{Style.RESET_ALL}")
                    
                    if 'regime_description' in strategy_info:
                        print(f"Regime-Beschreibung: {strategy_info['regime_description']}")
                    
                    if 'confidence' in strategy_info:
                        conf_color = Fore.GREEN if strategy_info['confidence'] > 0.7 else (
                            Fore.YELLOW if strategy_info['confidence'] > 0.4 else Fore.RED)
                        print(f"Konfidenz: {conf_color}{strategy_info['confidence']:.2f}{Style.RESET_ALL}")
                
                # Zeige Volumenanalyse
                if 'volume_pressure' in strategy_info:
                    vol_pressure = strategy_info['volume_pressure']
                    vol_color = Fore.GREEN if 'buying' in vol_pressure else (
                        Fore.RED if 'selling' in vol_pressure else Fore.YELLOW)
                    print(f"Volumendruck: {vol_color}{vol_pressure.upper()}{Style.RESET_ALL}")
                
                # Zeige erkannte Chartmuster
                if 'patterns' in strategy_info and strategy_info['patterns']:
                    print(f"Erkannte Chartmuster:")
                    for pattern, confidence in strategy_info['patterns'].items():
                        pattern_color = Fore.MAGENTA
                        print(f"  - {pattern_color}{pattern.replace('_', ' ').title()}{Style.RESET_ALL} (Konfidenz: {confidence:.2f})")
                
                # Zeige angepasste Risikoparameter
                if 'adjusted_risk_per_trade' in strategy_info:
                    print(f"Angepasstes Risiko pro Trade: {strategy_info['adjusted_risk_per_trade']*100:.2f}%")
                    print(f"Angepasster Stop-Loss: {strategy_info['adjusted_stop_loss']*100:.2f}%")
                    print(f"Angepasster Take-Profit: {strategy_info['adjusted_take_profit']*100:.2f}%")
            
            if 'signal_details' in strategy_info:
                print(f"Signal: {strategy_info['signal_details']}")
            
            if 'analysis' in strategy_info:
                print(f"Analyse: {strategy_info['analysis']}")
            
            # Zeige individuelle Strategiesignale für die adaptive Strategie an
            if strategy_info.get('strategy') in ['ADAPTIVE', 'ENHANCED_ADAPTIVE'] and 'strategy_performance' in strategy_info:
                print(f"\n{Fore.CYAN}Strategie-Performance:{Style.RESET_ALL}")
                for strat_name, perf in strategy_info.get('strategy_performance', {}).items():
                    if isinstance(perf, dict) and 'score' in perf:
                        score = perf['score']
                        score_color = Fore.GREEN if score > 0.7 else (Fore.YELLOW if score > 0.4 else Fore.RED)
                        print(f"  {strat_name}: {score_color}Score: {score:.2f}{Style.RESET_ALL} | Return: {perf.get('cumulative_return', 0):.2%} | Win Rate: {perf.get('win_rate', 0):.2%}")
               
        # Signalnähe-Anzeige
        if strategy_info:
            try:
                # Überprüfe, ob es sich um eine Fehlerstrategie handelt
                if 'strategy' in strategy_info and 'FEHLER' in strategy_info['strategy'].upper():
                    print(f"\n{Fore.RED}=== Signal-Nähe-Indikator ==={Style.RESET_ALL}")
                    print(f"Beschreibung: Keine Signal-Nähe-Berechnung für Strategie mit Fehler verfügbar")
                    print(f"Details: {strategy_info.get('description', 'Keine Details verfügbar')}")
                else:
                    # Normale Verarbeitung
                    if 'selected_strategy' in strategy_info:
                        # Für adaptive Strategie
                        selected_strategy = strategy_info['selected_strategy']
                        proximity_info = calculate_signal_proximity(df, selected_strategy)
                    else:
                        # Für direkte Strategie
                        proximity_info = calculate_signal_proximity(df, strategy_info.get('strategy', 'MULTI_INDICATOR'))
                    
                    # Zeige Signal-Nähe-Indikator
                    signal_proximity_display = generate_signal_proximity_display(proximity_info)
                    print(signal_proximity_display)
            except Exception as e:
                # Fehlerbehandlung für die Signal-Nähe-Anzeige
                error_msg = f"Fehler bei der Signal-Nähe-Anzeige: {str(e)}"
                log_error(e, error_msg)
                print(f"\n{Fore.RED}=== Signal-Nähe-Indikator (Fehler) ==={Style.RESET_ALL}")
                print(f"Beschreibung: {error_msg}")

        # Risikomanagement
        if risk_result:
            print(f"\n{Fore.CYAN}=== Risikomanagement ==={Style.RESET_ALL}")
            risk_color = Fore.GREEN if risk_result.get('allow_trade', True) else Fore.RED
            print(f"Trade erlaubt: {risk_color}{risk_result.get('allow_trade', True)}{Style.RESET_ALL}")
            
            if 'reason' in risk_result and risk_result['reason']:
                print(f"Grund: {risk_result['reason']}")
            
            print(f"Risikoniveau: {risk_result.get('risk_level', 'Unbekannt')}")
            
            if 'stop_loss' in risk_result and risk_result['stop_loss']:
                print(f"Stop-Loss: {risk_result['stop_loss']:.2f} {quote_currency}")
            
            if 'take_profit' in risk_result and risk_result['take_profit']:
                print(f"Take-Profit: {risk_result['take_profit']:.2f} {quote_currency}")
        
        # Position Details
        if position_info and position_info.get('size', 0) != 0:
            print(f"\n{Fore.CYAN}=== Positions-Details ==={Style.RESET_ALL}")
            position_type = position_info.get('type', 'KEINE')
            position_color = Fore.GREEN if position_type == 'LONG' else (Fore.RED if position_type == 'SHORT' else Fore.WHITE)
            
            print(f"Typ: {position_color}{position_type}{Style.RESET_ALL}")
            print(f"Größe: {abs(position_info.get('size', 0)):.6f} {base_currency}")
            print(f"Einstiegspreis: {position_info.get('entry_price', 0):.2f} {quote_currency}")
            
            # Unrealisierter Gewinn/Verlust
            unrealized_pnl = position_info.get('unrealized_pnl', 0)
            pnl_color = Fore.GREEN if unrealized_pnl > 0 else (Fore.RED if unrealized_pnl < 0 else Fore.WHITE)
            print(f"Unrealisierter G/V: {pnl_color}{unrealized_pnl:.2f} {quote_currency}{Style.RESET_ALL}")
            
            # Liquidation
            if 'liquidation_price' in position_info and position_info['liquidation_price'] > 0:
                liq_price = position_info['liquidation_price']
                distance_to_liq = abs((current_price - liq_price) / current_price * 100)
                print(f"Liquidationspreis: {Fore.RED}{liq_price:.2f} {quote_currency} (Abstand: {distance_to_liq:.2f}%){Style.RESET_ALL}")
        
        # Performance-Tracking
        if performance_tracker:
            print(f"\n{Fore.CYAN}=== Performance ==={Style.RESET_ALL}")
            print(f"Gesamtgewinn/-verlust: {Fore.GREEN if performance_tracker.total_profit >= 0 else Fore.RED}{performance_tracker.total_profit:.2f} {quote_currency}{Style.RESET_ALL}")
            
            if performance_tracker.total_trades > 0:
                win_rate = performance_tracker.winning_trades / performance_tracker.total_trades * 100
                print(f"Trades: {performance_tracker.total_trades} (Gewonnen: {performance_tracker.winning_trades}, Verloren: {performance_tracker.losing_trades})")
                print(f"Win-Rate: {Fore.GREEN}{win_rate:.1f}%{Style.RESET_ALL}")
            
            if hasattr(performance_tracker, 'consecutive_wins') and hasattr(performance_tracker, 'consecutive_losses'):
                print(f"Aktuelle Serie: ", end="")
                if performance_tracker.consecutive_wins > 0:
                    print(f"{Fore.GREEN}{performance_tracker.consecutive_wins} Gewinne in Folge{Style.RESET_ALL}")
                elif performance_tracker.consecutive_losses > 0:
                    print(f"{Fore.RED}{performance_tracker.consecutive_losses} Verluste in Folge{Style.RESET_ALL}")
                else:
                    print("Keine")
        
        # Letzte Aktion
        if last_action:
            print(f"\n{Fore.CYAN}Letzte Aktion: {last_action}{Style.RESET_ALL}")
        
        # Status und Hilfe
        print(f"\n{Fore.YELLOW}Bot Status: AKTIV - Nächstes Update in {config.UPDATE_INTERVAL} Sekunden{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Drücke STRG+C zum Beenden{Style.RESET_ALL}")
    
    except Exception as e:
        log_error(e, "Fehler bei der Aktualisierung der Anzeige")

def save_position_state(position_size, position_type, entry_price):
    """Speichert den aktuellen Positionsstatus in einer Datei"""
    try:
        with open("position_state.txt", "w") as f:
            f.write(f"{position_size},{position_type},{entry_price}")
    except Exception as e:
        print(f"{Fore.RED}Fehler beim Speichern des Positionsstatus: {str(e)}{Style.RESET_ALL}")

def load_position_state():
    """Lädt den gespeicherten Positionsstatus aus einer Datei"""
    try:
        if os.path.exists("position_state.txt"):
            with open("position_state.txt", "r") as f:
                data = f.read().strip().split(",")
                if len(data) == 3:
                    position_size = float(data[0])
                    position_type = data[1]
                    entry_price = float(data[2])
                    base_currency = config.get_base_currency()
                    quote_currency = config.get_quote_currency()
                    print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Gespeicherte Position gefunden: {position_type} {abs(position_size)} {base_currency} @ {entry_price} {quote_currency}{Style.RESET_ALL}")
                    return position_size, position_type, entry_price
        return 0, "KEINE", 0
    except Exception as e:
        print(f"{Fore.RED}Fehler beim Laden des Positionsstatus: {str(e)}{Style.RESET_ALL}")
        return 0, "KEINE", 0
    
def log_trade_signal(signal, reason, strategy_name, market_data, actual_balance=None):
    """
    Logs trade signals that weren't executed due to safety mechanisms.
    
    Parameters:
    signal (int): The original signal (-1, 0, 1)
    reason (str): Reason why the signal wasn't executed
    strategy_name (str): Name of the strategy that generated the signal
    market_data (dict): Current market data and indicators
    actual_balance (float, optional): Current account balance
    """
    if not config.LOG_REJECTED_SIGNALS:
        return  # Don't log if disabled in config
        
    log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    signal_type = "BUY" if signal > 0 else ("SELL" if signal < 0 else "NONE")
    
    # Extract key market data
    current_price = market_data.get('close', 0) if isinstance(market_data, pd.DataFrame) and not market_data.empty else 0
    
    # Create the log directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Prepare the log message
    log_message = f"[{log_time}] REJECTED {signal_type} SIGNAL\n"
    log_message += f"Strategy: {strategy_name}\n"
    log_message += f"Reason: {reason}\n"
    log_message += f"Price: {current_price}\n"
    
    if actual_balance is not None:
        log_message += f"Account Balance: {actual_balance} {config.get_quote_currency()}\n"
    
    # Add technical indicators if available
    if isinstance(market_data, pd.DataFrame) and not market_data.empty:
        log_message += "Market Indicators:\n"
        
        # RSI
        if 'rsi' in market_data.columns:
            log_message += f"  RSI: {market_data['rsi'].iloc[-1]:.2f}\n"
            
        # MACD
        if all(col in market_data.columns for col in ['macd', 'macd_signal']):
            log_message += f"  MACD: {market_data['macd'].iloc[-1]:.6f}\n"
            log_message += f"  MACD Signal: {market_data['macd_signal'].iloc[-1]:.6f}\n"
            
        # SMA
        if 'sma_5' in market_data.columns and 'sma_20' in market_data.columns:
            log_message += f"  SMA(5): {market_data['sma_5'].iloc[-1]:.2f}\n"
            log_message += f"  SMA(20): {market_data['sma_20'].iloc[-1]:.2f}\n"
            
        # Bollinger Bands
        if all(col in market_data.columns for col in ['bb_lower', 'bb_upper']):
            log_message += f"  BB Lower: {market_data['bb_lower'].iloc[-1]:.2f}\n" 
            log_message += f"  BB Upper: {market_data['bb_upper'].iloc[-1]:.2f}\n"
    
    log_message += "-" * 50 + "\n"
    
    # Write to the log file
    with open("logs/rejected_signals.log", "a") as f:
        f.write(log_message)
    
    if config.DISPLAY_REJECTED_SIGNALS:
        signal_color = Fore.GREEN if signal > 0 else Fore.RED
        print(f"{signal_color}[{log_time}] Rejected {signal_type} Signal: {reason}{Style.RESET_ALL}")

# Add to utils.py

def analyze_rejected_signals(time_period=None):
    """
    Analyzes rejected signals and generates a summary report.
    
    Parameters:
    time_period (str, optional): Time period to analyze ('day', 'week', 'month', 'all')
    
    Returns:
    dict: Summary statistics of rejected signals
    """
    if not os.path.exists("logs/rejected_signals.log"):
        print(f"{Fore.YELLOW}No rejected signals log found.{Style.RESET_ALL}")
        return {}
        
    try:
        # Read the log file
        with open("logs/rejected_signals.log", "r") as f:
            log_content = f.read()
            
        # Split into individual entries
        entries = log_content.split("-" * 50)
        entries = [e.strip() for e in entries if e.strip()]
        
        if not entries:
            print(f"{Fore.YELLOW}No rejected signals found in log.{Style.RESET_ALL}")
            return {}
            
        # Parse entries
        parsed_entries = []
        for entry in entries:
            try:
                lines = entry.split('\n')
                timestamp_str = lines[0].split('[')[1].split(']')[0]
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                
                signal_type = "BUY" if "REJECTED BUY SIGNAL" in lines[0] else "SELL"
                
                strategy = next((line.split("Strategy: ")[1] for line in lines if "Strategy: " in line), "Unknown")
                reason = next((line.split("Reason: ")[1] for line in lines if "Reason: " in line), "Unknown")
                price = float(next((line.split("Price: ")[1] for line in lines if "Price: " in line), 0))
                
                parsed_entry = {
                    "timestamp": timestamp,
                    "signal_type": signal_type,
                    "strategy": strategy,
                    "reason": reason,
                    "price": price
                }
                
                parsed_entries.append(parsed_entry)
            except Exception as e:
                print(f"{Fore.RED}Error parsing log entry: {str(e)}{Style.RESET_ALL}")
                continue
                
        # Filter by time period if specified
        if time_period:
            now = datetime.now()
            if time_period == 'day':
                start_time = now - timedelta(days=1)
            elif time_period == 'week':
                start_time = now - timedelta(weeks=1)
            elif time_period == 'month':
                start_time = now - timedelta(days=30)
            else:  # 'all' or invalid value
                start_time = datetime.min
                
            parsed_entries = [e for e in parsed_entries if e["timestamp"] >= start_time]
            
        # Generate statistics
        total_rejected = len(parsed_entries)
        buy_signals = sum(1 for e in parsed_entries if e["signal_type"] == "BUY")
        sell_signals = total_rejected - buy_signals
        
        # Group by reason
        reason_counts = {}
        for entry in parsed_entries:
            reason = entry["reason"]
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
        # Group by strategy
        strategy_counts = {}
        for entry in parsed_entries:
            strategy = entry["strategy"]
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            
        # Sort by count
        reason_counts = {k: v for k, v in sorted(reason_counts.items(), key=lambda item: item[1], reverse=True)}
        strategy_counts = {k: v for k, v in sorted(strategy_counts.items(), key=lambda item: item[1], reverse=True)}
        
        # Compile results
        results = {
            "total_rejected": total_rejected,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "reasons": reason_counts,
            "strategies": strategy_counts,
            "time_period": time_period or "all"
        }
        
        return results
    except Exception as e:
        print(f"{Fore.RED}Error analyzing rejected signals: {str(e)}{Style.RESET_ALL}")
        return {}

def print_rejected_signals_report(time_period=None):
    """
    Prints a formatted report of rejected signal analysis.
    
    Parameters:
    time_period (str, optional): Time period to analyze ('day', 'week', 'month', 'all')
    """
    analysis = analyze_rejected_signals(time_period)
    
    if not analysis:
        return
        
    time_period_str = {
        'day': 'last 24 hours',
        'week': 'last 7 days',
        'month': 'last 30 days',
        'all': 'all time'
    }.get(analysis["time_period"], analysis["time_period"])
    
    print(f"\n{Fore.CYAN}=== Rejected Signals Analysis ({time_period_str}) ==={Style.RESET_ALL}")
    print(f"Total rejected signals: {analysis['total_rejected']}")
    print(f"Buy signals: {analysis['buy_signals']} ({analysis['buy_signals']/max(1, analysis['total_rejected'])*100:.1f}%)")
    print(f"Sell signals: {analysis['sell_signals']} ({analysis['sell_signals']/max(1, analysis['total_rejected'])*100:.1f}%)")
    
    print(f"\n{Fore.YELLOW}Top rejection reasons:{Style.RESET_ALL}")
    for reason, count in list(analysis['reasons'].items())[:5]:  # Top 5
        print(f"  - {reason}: {count} ({count/analysis['total_rejected']*100:.1f}%)")
        
    print(f"\n{Fore.YELLOW}Rejected by strategy:{Style.RESET_ALL}")
    for strategy, count in analysis['strategies'].items():
        print(f"  - {strategy}: {count} ({count/analysis['total_rejected']*100:.1f}%)")
        
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
