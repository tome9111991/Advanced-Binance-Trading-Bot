import pandas as pd
import numpy as np
from datetime import datetime
from colorama import Fore, Style
from small_capital_strategy import small_capital_strategy
import utils
import config

# Importiere die adaptive Strategie
# Hinweis: Wir importieren das Modul hier für die Funktion get_strategy_signal
# In der adaptive_strategy.py wird strategies importiert, daher müssen wir Zirkelbezüge vermeiden


def sma_crossover_strategy(df):
    """SMA Crossover Handelsstrategie"""
    signal = 0
    info = {
        'strategy': 'SMA Crossover',
        'description': 'Kaufen wenn SMA(kurz) über SMA(lang) kreuzt, verkaufen wenn umgekehrt',
        'parameters': f'SMA(kurz): {config.SMA_SHORT_PERIOD}, SMA(lang): {config.SMA_LONG_PERIOD}'
    }
    
    if 'sma_5' in df.columns and 'sma_20' in df.columns:
        # Stelle sicher, dass genügend Datenpunkte vorhanden sind
        if len(df) < 3:  # Benötigen mindestens 2 Punkte für Vergleich + aktuell
            info['signal_details'] = "Nicht genügend Daten für Signalgenerierung"
            return signal, info
            
        # Kaufsignal: Kurzer SMA kreuzt über langen SMA
        if df['sma_5'].iloc[-2] <= df['sma_20'].iloc[-2] and df['sma_5'].iloc[-1] > df['sma_20'].iloc[-1]:
            signal = 1
            info['signal_details'] = f"{Fore.GREEN}Kaufsignal: SMA(5) kreuzte über SMA(20){Style.RESET_ALL}"
        
        # Verkaufssignal: Kurzer SMA kreuzt unter langen SMA
        elif df['sma_5'].iloc[-2] >= df['sma_20'].iloc[-2] and df['sma_5'].iloc[-1] < df['sma_20'].iloc[-1]:
            signal = -1
            info['signal_details'] = f"{Fore.RED}Verkaufssignal: SMA(5) kreuzte unter SMA(20){Style.RESET_ALL}"
        else:
            # Aktueller SMA-Trend
            trend = "steigend" if df['sma_5'].iloc[-1] > df['sma_5'].iloc[-2] else "fallend"
            relation = "über" if df['sma_5'].iloc[-1] > df['sma_20'].iloc[-1] else "unter"
            info['signal_details'] = f"SMA(5) ist {relation} SMA(20) und {trend}"
        
        # Abstand zwischen SMAs
        distance_percent = abs(df['sma_5'].iloc[-1] - df['sma_20'].iloc[-1]) / df['sma_20'].iloc[-1] * 100
        info['analysis'] = f"SMA-Abstand: {distance_percent:.2f}%"
    
    return signal, info

def rsi_strategy(df):
    """RSI basierte Handelsstrategie"""
    signal = 0
    info = {
        'strategy': 'RSI',
        'description': f'Kaufen wenn RSI unter {config.RSI_OVERSOLD}, verkaufen wenn über {config.RSI_OVERBOUGHT}',
        'parameters': f'RSI Periode: {config.RSI_PERIOD}'
    }
    
    if 'rsi' in df.columns:
        # Stelle sicher, dass genügend Datenpunkte vorhanden sind
        if len(df) < 3:  # Benötigen mindestens 2 Punkte für Vergleich + aktuell
            info['signal_details'] = "Nicht genügend Daten für Signalgenerierung"
            return signal, info
            
        current_rsi = df['rsi'].iloc[-1]
        prev_rsi = df['rsi'].iloc[-2]
        
        # Kaufsignal: RSI unter dem überkauften Niveau und steigend
        if current_rsi < config.RSI_OVERSOLD and current_rsi > prev_rsi:
            signal = 1
            info['signal_details'] = f"{Fore.GREEN}Kaufsignal: RSI ({current_rsi:.2f}) ist überkauft und steigt{Style.RESET_ALL}"
        
        # Verkaufssignal: RSI über dem überverkauften Niveau und fallend
        elif current_rsi > config.RSI_OVERBOUGHT and current_rsi < prev_rsi:
            signal = -1
            info['signal_details'] = f"{Fore.RED}Verkaufssignal: RSI ({current_rsi:.2f}) ist überverkauft und fällt{Style.RESET_ALL}"
        else:
            # Aktueller RSI-Status
            rsi_status = "überkauft" if current_rsi < 30 else ("überverkauft" if current_rsi > 70 else "neutral")
            trend = "steigend" if current_rsi > prev_rsi else "fallend"
            info['signal_details'] = f"RSI ist {rsi_status} ({current_rsi:.2f}) und {trend}"
        
        # RSI-Divergenz prüfen (nicht vollständig implementiert)
        info['analysis'] = f"RSI Aktuelle Periode: {current_rsi:.2f}"
    
    return signal, info

def macd_strategy(df):
    """MACD basierte Handelsstrategie"""
    signal = 0
    info = {
        'strategy': 'MACD',
        'description': 'Kaufen wenn MACD über Signal-Linie kreuzt, verkaufen wenn umgekehrt',
        'parameters': f'Schnell: {config.MACD_FAST}, Langsam: {config.MACD_SLOW}, Signal: {config.MACD_SIGNAL}'
    }
    
    if 'macd' in df.columns and 'macd_signal' in df.columns and 'macd_hist' in df.columns:
        # Stelle sicher, dass genügend Datenpunkte vorhanden sind
        if len(df) < 3:  # Benötigen mindestens 2 Punkte für Vergleich + aktuell
            info['signal_details'] = "Nicht genügend Daten für Signalgenerierung"
            return signal, info
            
        macd = df['macd'].iloc[-1]
        macd_signal = df['macd_signal'].iloc[-1]
        macd_hist = df['macd_hist'].iloc[-1]
        macd_prev = df['macd'].iloc[-2]
        macd_signal_prev = df['macd_signal'].iloc[-2]
        
        # Kaufsignal: MACD kreuzt über Signal-Linie
        if macd_prev <= macd_signal_prev and macd > macd_signal:
            signal = 1
            info['signal_details'] = f"{Fore.GREEN}Kaufsignal: MACD kreuzte über Signal-Linie{Style.RESET_ALL}"
        
        # Verkaufssignal: MACD kreuzt unter Signal-Linie
        elif macd_prev >= macd_signal_prev and macd < macd_signal:
            signal = -1
            info['signal_details'] = f"{Fore.RED}Verkaufssignal: MACD kreuzte unter Signal-Linie{Style.RESET_ALL}"
        else:
            # Aktueller MACD-Status
            position = "über" if macd > macd_signal else "unter"
            trend = "steigend" if macd > macd_prev else "fallend"
            info['signal_details'] = f"MACD ist {position} der Signal-Linie und {trend}"
        
        # MACD-Histogramm-Analyse
        hist_trend = "steigend" if macd_hist > df['macd_hist'].iloc[-2] else "fallend"
        info['analysis'] = f"MACD-Histogramm: {macd_hist:.2f} ({hist_trend})"
    
    return signal, info

def bollinger_bands_strategy(df):
    """Bollinger Bands basierte Handelsstrategie"""
    signal = 0
    info = {
        'strategy': 'Bollinger Bands',
        'description': 'Kaufen wenn Preis unter unterem Band, verkaufen wenn über oberem Band',
        'parameters': f'Periode: {config.BOLLINGER_PERIOD}, StdDev: {config.BOLLINGER_STD_DEV}'
    }
    
    if 'bb_upper' in df.columns and 'bb_middle' in df.columns and 'bb_lower' in df.columns:
        # Stelle sicher, dass genügend Datenpunkte vorhanden sind
        if len(df) < 3:  # Benötigen mindestens 2 Punkte für Vergleich + aktuell
            info['signal_details'] = "Nicht genügend Daten für Signalgenerierung"
            return signal, info
            
        close = df['close'].iloc[-1]
        upper = df['bb_upper'].iloc[-1]
        middle = df['bb_middle'].iloc[-1]
        lower = df['bb_lower'].iloc[-1]
        
        # Kaufsignal: Preis unter unterem Band
        if close < lower:
            signal = 1
            info['signal_details'] = f"{Fore.GREEN}Kaufsignal: Preis ({close:.2f}) unter unterem Bollinger Band ({lower:.2f}){Style.RESET_ALL}"
        
        # Verkaufssignal: Preis über oberem Band
        elif close > upper:
            signal = -1
            info['signal_details'] = f"{Fore.RED}Verkaufssignal: Preis ({close:.2f}) über oberem Bollinger Band ({upper:.2f}){Style.RESET_ALL}"
        else:
            # Wo ist der Preis relativ zu den Bändern
            percent_b = (close - lower) / (upper - lower) * 100
            info['signal_details'] = f"Preis ist {percent_b:.1f}% innerhalb der Bollinger Bänder"
        
        # Bandbreite und Volatilität
        bandwidth = (upper - lower) / middle * 100
        info['analysis'] = f"Bollinger Bandbreite: {bandwidth:.2f}%"
    
    return signal, info

def multi_indicator_strategy(df):
    """Strategie basierend auf mehreren Indikatoren"""
    # Stelle sicher, dass genügend Datenpunkte vorhanden sind
    if len(df) < 3:  # Benötigen mindestens 2 Punkte für Vergleich + aktuell
        info = {
            'strategy': 'Multi-Indikator',
            'description': 'Kombiniert SMA, RSI, MACD und Bollinger Bands',
            'signal_details': "Nicht genügend Daten für Signalgenerierung"
        }
        return 0, info
        
    # Gewichte der einzelnen Strategien
    weights = {
        'sma': 0.2,
        'rsi': 0.2,
        'macd': 0.3,
        'bollinger': 0.3
    }
    
    # Signale von den einzelnen Strategien abrufen
    sma_signal, sma_info = sma_crossover_strategy(df)
    rsi_signal, rsi_info = rsi_strategy(df)
    macd_signal, macd_info = macd_strategy(df)
    bb_signal, bb_info = bollinger_bands_strategy(df)
    
    # Gewichtetes Signal berechnen
    weighted_signal = (
        sma_signal * weights['sma'] +
        rsi_signal * weights['rsi'] +
        macd_signal * weights['macd'] +
        bb_signal * weights['bollinger']
    )
    
    # Final Signal bestimmen (1, -1 oder 0)
    if weighted_signal > 0.3:
        final_signal = 1
    elif weighted_signal < -0.3:
        final_signal = -1
    else:
        final_signal = 0
    
    # Informationen über die Strategie
    info = {
        'strategy': 'Multi-Indikator',
        'description': 'Kombiniert SMA, RSI, MACD und Bollinger Bands',
        'parameters': f'Gewichte: SMA={weights["sma"]}, RSI={weights["rsi"]}, MACD={weights["macd"]}, BB={weights["bollinger"]}',
        'signal_details': (
            f"{Fore.GREEN}Kaufsignal{Style.RESET_ALL}" if final_signal == 1 else
            f"{Fore.RED}Verkaufssignal{Style.RESET_ALL}" if final_signal == -1 else
            f"Kein Signal (Halten)"
        ),
        'analysis': f"Gewichtetes Signal: {weighted_signal:.2f}",
        'individual_signals': {
            'sma': sma_signal,
            'rsi': rsi_signal,
            'macd': macd_signal,
            'bollinger': bb_signal
        },
        'individual_info': {
            'sma': sma_info,
            'rsi': rsi_info,
            'macd': macd_info,
            'bollinger': bb_info
        }
    }
    
    return final_signal, info

def aggressive_test_strategy(df):
    """Übermäßig aggressive Strategie NUR für Testzwecke"""
    signal = 0
    info = {
        'strategy': 'EXTREM AGGRESSIVE TESTSTRATEGIE',
        'description': 'Handelt bei kleinsten Preisänderungen - NUR FÜR TESTS!',
        'parameters': 'Sehr niedriger Schwellenwert für Preisänderungen'
    }
    
    # Nur ausführen, wenn genügend Daten vorhanden sind
    if len(df) < 3:
        info['signal_details'] = "Nicht genügend Daten für Signalgenerierung"
        return 0, info
    
    # Aktuelle und vorherige Schlusskurse
    current_price = df['close'].iloc[-1]
    prev_price = df['close'].iloc[-2]
    
    # Berechne kurze Preisänderung in Prozent
    price_change_pct = ((current_price - prev_price) / prev_price) * 100
    
    # Extrem niedrige Schwellenwerte für das Trading
    # 0.1% Änderung ist schon ein Signal - normalerweise viel zu niedrig!
    if price_change_pct > 0.1:  # Nur 0.1% Anstieg
        signal = 1
        info['signal_details'] = f"{Fore.GREEN}Kaufsignal: Preis stieg um {price_change_pct:.2f}% (sehr aggressiv){Style.RESET_ALL}"
    elif price_change_pct < -0.1:  # Nur 0.1% Rückgang
        signal = -1
        info['signal_details'] = f"{Fore.RED}Verkaufssignal: Preis fiel um {abs(price_change_pct):.2f}% (sehr aggressiv){Style.RESET_ALL}"
    else:
        info['signal_details'] = f"Keine Signalgenerierung: Preisänderung zu gering ({price_change_pct:.2f}%)"
    
    info['analysis'] = f"Aktuelle Preisänderung: {price_change_pct:.4f}% | Schwellenwert: 0.1%"
    
    return signal, info

def get_strategy_signal(df, strategy_name):
    """Generiert ein Handelssignal basierend auf der gewählten Strategie"""
    print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Generiere Handelssignal mit Strategie: {strategy_name}...{Style.RESET_ALL}")
    
    try:
        # Stelle sicher, dass das DataFrame nicht leer ist
        if df.empty or len(df) < 3:
            print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Nicht genügend Daten für Signalgenerierung.{Style.RESET_ALL}")
            info = {
                'strategy': strategy_name,
                'description': 'Nicht ausgeführt - unzureichende Daten',
                'signal_details': "Nicht genügend Daten für Signalgenerierung"
            }
            return 0, info
        
        # Strategie über Factory holen
        from strategy_factory import StrategyFactory
        strategy_func = StrategyFactory.get_strategy(strategy_name)
        
        if strategy_func:
            signal, info = strategy_func(df)
            
            if signal == 1:
                print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Kaufsignal generiert!{Style.RESET_ALL}")
            elif signal == -1:
                print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Verkaufssignal generiert!{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Kein Handelssignal (Halten).{Style.RESET_ALL}")
            
            return signal, info
        else:
            raise ValueError(f"Strategie {strategy_name} nicht gefunden.")
    
    except Exception as e:
        utils.log_error(e, f"Fehler bei der Signalgenerierung mit Strategie {strategy_name}")
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler bei der Signalgenerierung: {str(e)}{Style.RESET_ALL}")
        
        # Stelle ein sicheres Fallback bereit
        info = {
            'strategy': strategy_name,
            'description': 'Fehler bei der Ausführung',
            'signal_details': f"Fehler: {str(e)}"
        }
        return 0, info