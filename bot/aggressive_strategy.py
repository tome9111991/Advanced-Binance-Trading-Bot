import pandas as pd
import numpy as np
from datetime import datetime
from colorama import Fore, Style
import utils
import config

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
