def calculate_signal_proximity(df, strategy_name):
    """
    Berechnet, wie nahe die aktuellen Marktbedingungen an einem Handelssignal sind.
    
    Parameters:
    df (pandas.DataFrame): DataFrame mit Marktdaten und berechneten Indikatoren
    strategy_name (str): Name der aktiven Strategie
    
    Returns:
    dict: Informationen zur Nähe eines Signals
    """
    import utils  # Import für Fehlerprotokollierung
    
    proximity_info = {
        'buy_proximity': 0.0,  # 0.0 bis 1.0 (1.0 = Signal wird ausgelöst)
        'sell_proximity': 0.0,  # 0.0 bis 1.0 (1.0 = Signal wird ausgelöst)
        'description': '',
        'threshold': 0.0,
        'current_value': 0.0
    }
    
    # Überprüfe auf leere oder unzureichende Daten
    if df is None or df.empty or len(df) < 2:
        proximity_info['description'] = "Nicht genug Daten für Signalberechnung"
        return proximity_info
    
    # Überprüfe auf Fehler im Strategienamen
    if not isinstance(strategy_name, str):
        proximity_info['description'] = f"Ungültiger Strategiename: {type(strategy_name)}"
        return proximity_info
    
    # Überprüfe auf Fehler im Strategienamen
    if "FEHLER" in strategy_name.upper():
        proximity_info['description'] = f"Keine Signal-Nähe-Berechnung für Strategie mit Fehler verfügbar"
        return proximity_info
    
    # Strategie-Namen auf Großbuchstaben umwandeln, um Fehler bei Vergleichen zu vermeiden
    strategy_name = strategy_name.upper()
    
    try:
        # Aktuelle Werte
        current_price = df['close'].iloc[-1]
        
        # Strategie-spezifische Berechnungen
        if strategy_name == 'BOLLINGER_BANDS':
            if 'bb_upper' in df.columns and 'bb_lower' in df.columns and 'bb_middle' in df.columns:
                bb_upper = df['bb_upper'].iloc[-1]
                bb_lower = df['bb_lower'].iloc[-1]
                bb_middle = df['bb_middle'].iloc[-1]
                
                # Berechne relative Position innerhalb der Bänder (0 = unteres Band, 1 = oberes Band)
                band_width = bb_upper - bb_lower
                if band_width > 0:
                    relative_position = (current_price - bb_lower) / band_width
                else:
                    relative_position = 0.5  # Fallback
                
                # Berechne Nähe zu Kaufsignal (unteres Band)
                # Je näher am unteren Band, desto höher die Kauf-Nähe (linear skaliert)
                if relative_position <= 0.3:  # Unteres Drittel der Bänder
                    buy_proximity = 1.0 - (relative_position / 0.3)
                else:
                    buy_proximity = 0.0
                
                # Berechne Nähe zu Verkaufssignal (oberes Band)
                # Je näher am oberen Band, desto höher die Verkauf-Nähe (linear skaliert)
                if relative_position >= 0.7:  # Oberes Drittel der Bänder
                    sell_proximity = (relative_position - 0.7) / 0.3
                else:
                    sell_proximity = 0.0
                
                # Verbesserte Beschreibung
                band_position = "nahe unterem Band" if relative_position < 0.3 else (
                    "nahe oberem Band" if relative_position > 0.7 else "innerhalb der Bänder")
                
                proximity_info['buy_proximity'] = round(buy_proximity, 2)
                proximity_info['sell_proximity'] = round(sell_proximity, 2)
                proximity_info['description'] = f"Position in Bollinger Bändern: {relative_position:.2f} ({band_position})"
                proximity_info['threshold'] = "Kauf: Preis unter Band, Verkauf: Preis über Band"
                proximity_info['current_value'] = relative_position
        
        elif strategy_name == 'RSI':
            if 'rsi' in df.columns:
                rsi = df['rsi'].iloc[-1]
                prev_rsi = df['rsi'].iloc[-2] if len(df) > 2 else rsi
                
                # RSI Schwellenwerte aus der Konfiguration oder Standard
                rsi_oversold = 30  # Überkauft - Kaufsignal
                rsi_overbought = 70  # Überverkauft - Verkaufssignal
                
                # Berechne Nähe zu Kaufsignal (RSI unter 30)
                if rsi <= rsi_oversold:
                    # Wenn RSI unter 30 und steigend
                    if rsi > prev_rsi:
                        buy_proximity = 1.0
                    else:
                        buy_proximity = 0.7  # RSI unter 30 aber fallend
                elif rsi < 40:
                    # Linear interpolieren zwischen 30 und 40
                    buy_proximity = (40 - rsi) / 10
                else:
                    buy_proximity = 0.0
                
                # Berechne Nähe zu Verkaufssignal (RSI über 70)
                if rsi >= rsi_overbought:
                    # Wenn RSI über 70 und fallend
                    if rsi < prev_rsi:
                        sell_proximity = 1.0
                    else:
                        sell_proximity = 0.7  # RSI über 70 aber steigend
                elif rsi > 60:
                    # Linear interpolieren zwischen 60 und 70
                    sell_proximity = (rsi - 60) / 10
                else:
                    sell_proximity = 0.0
                
                # Verbesserte Beschreibung
                rsi_trend = "steigend" if rsi > prev_rsi else "fallend"
                rsi_status = "überkauft" if rsi < 30 else ("überverkauft" if rsi > 70 else "neutral")
                
                proximity_info['buy_proximity'] = round(buy_proximity, 2)
                proximity_info['sell_proximity'] = round(sell_proximity, 2)
                proximity_info['description'] = f"RSI: {rsi:.2f} ({rsi_status}, {rsi_trend})"
                proximity_info['threshold'] = f"Kauf < {rsi_oversold} & steigend, Verkauf > {rsi_overbought} & fallend"
                proximity_info['current_value'] = rsi
        
        elif strategy_name == 'MACD':
            if 'macd' in df.columns and 'macd_signal' in df.columns:
                macd = df['macd'].iloc[-1]
                macd_signal = df['macd_signal'].iloc[-1]
                prev_macd = df['macd'].iloc[-2] if len(df) > 2 else macd
                prev_macd_signal = df['macd_signal'].iloc[-2] if len(df) > 2 else macd_signal
                
                # Berechne Abstand zwischen MACD und Signal-Linie
                diff = macd - macd_signal
                prev_diff = prev_macd - prev_macd_signal
                
                # Annäherung an Kreuzung (normalisierter Wert)
                # Je näher an 0, desto näher die Kreuzung
                cross_proximity = max(0, 1 - (abs(diff) / 0.5))  # Schwellenwert: 0.5
                
                # Richtung bestimmen
                is_converging = abs(diff) < abs(prev_diff)  # Annäherung
                
                # Berechne Nähe zu Signalen
                if diff < 0:
                    # MACD unter Signal-Linie
                    if is_converging and diff > -0.2:  # Annäherung von unten und nahe genug
                        buy_proximity = cross_proximity
                        sell_proximity = 0.0
                    else:
                        buy_proximity = 0.0
                        sell_proximity = min(1.0, abs(diff))  # Verkaufssignal-Stärke
                else:
                    # MACD über Signal-Linie
                    if is_converging and diff < 0.2:  # Annäherung von oben und nahe genug
                        buy_proximity = 0.0
                        sell_proximity = cross_proximity
                    else:
                        buy_proximity = min(1.0, abs(diff))  # Kaufsignal-Stärke
                        sell_proximity = 0.0
                
                # Debugging
                # print(f"MACD: {macd}, Signal: {macd_signal}, Diff: {diff}, Prev Diff: {prev_diff}")
                # print(f"Cross proximity: {cross_proximity}, Buy: {buy_proximity}, Sell: {sell_proximity}")
                
                proximity_info['buy_proximity'] = round(buy_proximity, 2)
                proximity_info['sell_proximity'] = round(sell_proximity, 2)
                proximity_info['description'] = f"MACD-Signal Differenz: {diff:.4f}" + (" (konvergierend)" if is_converging else " (divergierend)")
                proximity_info['threshold'] = "Kreuzung der Linien"
                proximity_info['current_value'] = diff
        
        elif strategy_name == 'SMA_CROSSOVER':
            if 'sma_5' in df.columns and 'sma_20' in df.columns:
                sma_short = df['sma_5'].iloc[-1]
                sma_long = df['sma_20'].iloc[-1]
                prev_sma_short = df['sma_5'].iloc[-2] if len(df) > 2 else sma_short
                prev_sma_long = df['sma_20'].iloc[-2] if len(df) > 2 else sma_long
                
                # Berechne Abstand zwischen den SMAs in Prozent
                diff = sma_short - sma_long
                prev_diff = prev_sma_short - prev_sma_long
                
                # Abstand in Prozent vom aktuellen Preis
                diff_percent = abs(diff / current_price * 100)
                
                # Annäherung an Kreuzung (normalisierter Wert)
                cross_proximity = max(0, 1 - (diff_percent / 0.5))  # Schwellenwert: 0.5%
                
                # Richtung bestimmen
                is_converging = abs(diff) < abs(prev_diff)  # Annäherung
                
                # SMAs nähern sich einander an?
                if diff < 0:
                    # Kurzer SMA unter langem SMA
                    if is_converging:
                        # Kurzer SMA nähert sich dem langen SMA von unten
                        buy_proximity = cross_proximity
                        sell_proximity = 0.0
                    else:
                        # Kurzer SMA entfernt sich weiter vom langen SMA nach unten
                        buy_proximity = 0.0 
                        sell_proximity = min(0.5, diff_percent / 2)  # Max 0.5 für divergierende Bewegung
                else:
                    # Kurzer SMA über langem SMA
                    if is_converging:
                        # Kurzer SMA nähert sich dem langen SMA von oben
                        buy_proximity = 0.0
                        sell_proximity = cross_proximity
                    else:
                        # Kurzer SMA entfernt sich weiter vom langen SMA nach oben
                        buy_proximity = min(0.5, diff_percent / 2)  # Max 0.5 für divergierende Bewegung
                        sell_proximity = 0.0
                
                # Debugging
                # print(f"SMA5: {sma_short}, SMA20: {sma_long}, Diff: {diff}, Prev Diff: {prev_diff}")
                # print(f"Diff%: {diff_percent}, Cross prox: {cross_proximity}, Buy: {buy_proximity}, Sell: {sell_proximity}")
                
                proximity_info['buy_proximity'] = round(buy_proximity, 2)
                proximity_info['sell_proximity'] = round(sell_proximity, 2)
                proximity_info['description'] = f"SMA Abstand: {diff_percent:.2f}%" + (" (konvergierend)" if is_converging else " (divergierend)")
                proximity_info['threshold'] = "SMA Kreuzung"
                proximity_info['current_value'] = diff_percent
        
        elif strategy_name in ['MULTI_INDICATOR', 'ADAPTIVE', 'ENHANCED_ADAPTIVE', 'SMALL_CAPITAL']:
            # Für Multi-Indikator kombinieren wir die Werte anderer Strategien
            rsi_proximity = calculate_signal_proximity(df, 'RSI')
            bb_proximity = calculate_signal_proximity(df, 'BOLLINGER_BANDS')
            macd_proximity = calculate_signal_proximity(df, 'MACD')
            sma_proximity = calculate_signal_proximity(df, 'SMA_CROSSOVER')
            
            # Gewichte Strategien
            weights = {'RSI': 0.25, 'BOLLINGER_BANDS': 0.25, 'MACD': 0.25, 'SMA_CROSSOVER': 0.25}
            
            # Kombiniere gewichtete Werte
            buy_proximity = (
                rsi_proximity['buy_proximity'] * weights['RSI'] +
                bb_proximity['buy_proximity'] * weights['BOLLINGER_BANDS'] +
                macd_proximity['buy_proximity'] * weights['MACD'] +
                sma_proximity['buy_proximity'] * weights['SMA_CROSSOVER']
            )
            
            sell_proximity = (
                rsi_proximity['sell_proximity'] * weights['RSI'] +
                bb_proximity['sell_proximity'] * weights['BOLLINGER_BANDS'] +
                macd_proximity['sell_proximity'] * weights['MACD'] +
                sma_proximity['sell_proximity'] * weights['SMA_CROSSOVER']
            )
            
            # Finde den stärksten Indikator
            indicators = [
                ('RSI', rsi_proximity['buy_proximity'], rsi_proximity['sell_proximity']),
                ('BB', bb_proximity['buy_proximity'], bb_proximity['sell_proximity']),
                ('MACD', macd_proximity['buy_proximity'], macd_proximity['sell_proximity']),
                ('SMA', sma_proximity['buy_proximity'], sma_proximity['sell_proximity'])
            ]
            
            strongest_buy = max(indicators, key=lambda x: x[1])
            strongest_sell = max(indicators, key=lambda x: x[2])
            
            # Detaillierte Beschreibung
            description = "Kombinierte Indikatoren: "
            if buy_proximity > sell_proximity and buy_proximity > 0.1:
                description += f"Stärkster Kauf-Indikator: {strongest_buy[0]} ({strongest_buy[1]:.2f})"
            elif sell_proximity > buy_proximity and sell_proximity > 0.1:
                description += f"Stärkster Verkauf-Indikator: {strongest_sell[0]} ({strongest_sell[2]:.2f})"
            else:
                description += "Keine starken Signale"
            
            proximity_info['buy_proximity'] = round(buy_proximity, 2)
            proximity_info['sell_proximity'] = round(sell_proximity, 2)
            proximity_info['description'] = description
            proximity_info['threshold'] = "Gewichtete Kombination > 0.3"
            proximity_info['current_value'] = max(buy_proximity, sell_proximity)
        
        elif strategy_name == 'SMALL_CAPITAL_ADAPTIVE':
            # Verwende die gleiche Logik wie für MULTI_INDICATOR oder eine andere passende Strategie
            if 'rsi' in df.columns and 'macd' in df.columns and 'macd_signal' in df.columns:
                rsi = df['rsi'].iloc[-1]
                macd = df['macd'].iloc[-1]
                macd_signal = df['macd_signal'].iloc[-1]
                
                # RSI-basierte Nähe
                if rsi <= 30:
                    buy_proximity_rsi = 1.0
                elif rsi < 40:
                    buy_proximity_rsi = (40 - rsi) / 10
                else:
                    buy_proximity_rsi = 0.0
                    
                if rsi >= 70:
                    sell_proximity_rsi = 1.0
                elif rsi > 60:
                    sell_proximity_rsi = (rsi - 60) / 10
                else:
                    sell_proximity_rsi = 0.0
                
                # MACD-basierte Nähe
                macd_diff = macd - macd_signal
                prev_macd_diff = df['macd'].iloc[-2] - df['macd_signal'].iloc[-2] if len(df) > 2 else macd_diff
                
                # Kaufsignal: MACD kreuzt Signal-Linie von unten
                if macd_diff > 0 and prev_macd_diff <= 0:
                    buy_proximity_macd = 1.0
                elif macd_diff > 0:
                    buy_proximity_macd = 0.7  # Positiver MACD, aber kein Kreuzungssignal
                elif macd_diff > -0.0001 and macd_diff <= 0:
                    buy_proximity_macd = 0.5  # Nahe an Kreuzung
                else:
                    buy_proximity_macd = 0.0
                
                # Verkaufssignal: MACD kreuzt Signal-Linie von oben
                if macd_diff < 0 and prev_macd_diff >= 0:
                    sell_proximity_macd = 1.0
                elif macd_diff < 0:
                    sell_proximity_macd = 0.7  # Negativer MACD, aber kein Kreuzungssignal
                elif macd_diff < 0.0001 and macd_diff >= 0:
                    sell_proximity_macd = 0.5  # Nahe an Kreuzung
                else:
                    sell_proximity_macd = 0.0
                
                # Kombiniere die Nähe-Werte (Durchschnitt)
                buy_proximity = (buy_proximity_rsi + buy_proximity_macd) / 2
                sell_proximity = (sell_proximity_rsi + sell_proximity_macd) / 2
                
                proximity_info['buy_proximity'] = round(buy_proximity, 2)
                proximity_info['sell_proximity'] = round(sell_proximity, 2)
                proximity_info['description'] = f"RSI: {rsi:.1f}, MACD Diff: {macd_diff:.6f}"
                proximity_info['threshold'] = "Kauf: RSI < 30 oder MACD-Kreuzung, Verkauf: RSI > 70 oder MACD-Kreuzung"
                proximity_info['current_value'] = rsi
        
        # Fallback für unbekannte Strategien
        else:
            # Versuche, eine generische Berechnung basierend auf verfügbaren Indikatoren durchzuführen
            proximity_info['description'] = f"Keine spezifische Signal-Nähe-Berechnung für Strategie '{strategy_name}' verfügbar. Verwende generische Berechnung."
            
            # Prüfe, welche Indikatoren verfügbar sind und verwende sie
            indicators_available = []
            
            if 'rsi' in df.columns:
                indicators_available.append('RSI')
            if 'macd' in df.columns and 'macd_signal' in df.columns:
                indicators_available.append('MACD')
            if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
                indicators_available.append('BOLLINGER_BANDS')
            if 'sma_short' in df.columns and 'sma_long' in df.columns:
                indicators_available.append('SMA_CROSSOVER')
            
            # Wenn keine Indikatoren verfügbar sind, gib eine Warnung zurück
            if not indicators_available:
                proximity_info['description'] = f"Keine Indikatoren für Strategie '{strategy_name}' verfügbar"
                return proximity_info
            
            # Berechne die Signal-Nähe basierend auf verfügbaren Indikatoren
            buy_proximities = []
            sell_proximities = []
            
            for indicator in indicators_available:
                indicator_proximity = calculate_signal_proximity(df, indicator)
                buy_proximities.append(indicator_proximity['buy_proximity'])
                sell_proximities.append(indicator_proximity['sell_proximity'])
            
            # Berechne den Durchschnitt
            if buy_proximities:
                proximity_info['buy_proximity'] = round(sum(buy_proximities) / len(buy_proximities), 2)
            if sell_proximities:
                proximity_info['sell_proximity'] = round(sum(sell_proximities) / len(sell_proximities), 2)
            
            proximity_info['description'] = f"Generische Berechnung basierend auf: {', '.join(indicators_available)}"
            proximity_info['threshold'] = "Durchschnitt der verfügbaren Indikatoren > 0.3"
            proximity_info['current_value'] = max(proximity_info['buy_proximity'], proximity_info['sell_proximity'])
    
    except Exception as e:
        # Verbesserte Fehlerbehandlung
        error_msg = f"Fehler bei der Signal-Nähe-Berechnung für Strategie '{strategy_name}': {str(e)}"
        utils.log_error(e, error_msg)
        proximity_info['description'] = error_msg
    
    return proximity_info

def generate_signal_proximity_display(proximity_info):
    """
    Generiert eine verbesserte visuelle Darstellung der Signalnähe.
    
    Parameters:
    proximity_info (dict): Informationen zur Nähe eines Signals
    
    Returns:
    str: Visuelle Darstellung als String
    """
    from colorama import Fore, Style
    
    buy_proximity = proximity_info['buy_proximity']
    sell_proximity = proximity_info['sell_proximity']
    
    # Verbesserte Farbgebung
    buy_color = Fore.GREEN
    sell_color = Fore.RED
    
    # Verbesserte Beschreibung
    description = proximity_info['description']
    threshold = proximity_info['threshold']
    current_value = proximity_info['current_value']
    
    # Generiere Fortschrittsbalken mit 20 Zeichen
    buy_bar_filled = int(buy_proximity * 20)
    sell_bar_filled = int(sell_proximity * 20)
    
    buy_bar = buy_color + "█" * buy_bar_filled + Style.RESET_ALL + "░" * (20 - buy_bar_filled)
    sell_bar = sell_color + "█" * sell_bar_filled + Style.RESET_ALL + "░" * (20 - sell_bar_filled)
    
    # Verbesserte Ausgabe mit mehr Details
    output = f"\n{Fore.CYAN}=== Signal-Nähe-Indikator ==={Style.RESET_ALL}\n"
    output += f"Beschreibung: {description}\n"
    output += f"Schwellenwert: {threshold}\n"
    if isinstance(current_value, (int, float)):
        output += f"Aktueller Wert: {current_value:.4f}\n\n"
    else:
        output += f"Aktueller Wert: {current_value}\n\n"
    
    # Signal-Interpretationen
    if buy_proximity >= 0.8:
        output += f"{Fore.GREEN}STARKES KAUFSIGNAL SEHR NAH!{Style.RESET_ALL}\n"
    elif buy_proximity >= 0.5:
        output += f"{Fore.GREEN}Kaufsignal in Reichweite{Style.RESET_ALL}\n"
    elif buy_proximity > 0.2:
        output += f"{Fore.YELLOW}Potentieller Kaufimpuls entwickelt sich{Style.RESET_ALL}\n"
        
    if sell_proximity >= 0.8:
        output += f"{Fore.RED}STARKES VERKAUFSSIGNAL SEHR NAH!{Style.RESET_ALL}\n"
    elif sell_proximity >= 0.5:
        output += f"{Fore.RED}Verkaufssignal in Reichweite{Style.RESET_ALL}\n"
    elif sell_proximity > 0.2:
        output += f"{Fore.YELLOW}Potentieller Verkaufsimpuls entwickelt sich{Style.RESET_ALL}\n"
    
    if buy_proximity < 0.2 and sell_proximity < 0.2:
        output += f"{Fore.YELLOW}Aktuell kein Handelssignal in Sicht{Style.RESET_ALL}\n"
    
    output += f"Kaufsignal-Nähe ({buy_proximity:.2f}): {buy_bar}\n"
    output += f"Verkaufssignal-Nähe ({sell_proximity:.2f}): {sell_bar}\n"
    
    return output

def generate_signal_proximity_display(proximity_info):
    """
    Generiert eine verbesserte visuelle Darstellung der Signalnähe.
    
    Parameters:
    proximity_info (dict): Informationen zur Nähe eines Signals
    
    Returns:
    str: Visuelle Darstellung als String
    """
    from colorama import Fore, Style
    
    buy_proximity = proximity_info['buy_proximity']
    sell_proximity = proximity_info['sell_proximity']
    
    # Verbesserte Farbgebung
    buy_color = Fore.GREEN
    sell_color = Fore.RED
    
    # Verbesserte Beschreibung
    description = proximity_info['description']
    threshold = proximity_info['threshold']
    current_value = proximity_info['current_value']
    
    # Generiere Fortschrittsbalken mit 20 Zeichen
    buy_bar_filled = int(buy_proximity * 20)
    sell_bar_filled = int(sell_proximity * 20)
    
    buy_bar = buy_color + "█" * buy_bar_filled + Style.RESET_ALL + "░" * (20 - buy_bar_filled)
    sell_bar = sell_color + "█" * sell_bar_filled + Style.RESET_ALL + "░" * (20 - sell_bar_filled)
    
    # Verbesserte Ausgabe mit mehr Details
    output = f"\n{Fore.CYAN}=== Signal-Nähe-Indikator ==={Style.RESET_ALL}\n"
    output += f"Beschreibung: {description}\n"
    output += f"Schwellenwert: {threshold}\n"
    output += f"Aktueller Wert: {current_value}\n\n"
    
    # Füge Hinweis hinzu, wenn Signal-Nähe > 0 aber < 0.3
    if 0 < buy_proximity < 0.3:
        output += f"{Fore.YELLOW}Hinweis: Kaufsignal-Nähe ist positiv, aber unter dem Schwellenwert für ein tatsächliches Signal.{Style.RESET_ALL}\n"
    if 0 < sell_proximity < 0.3:
        output += f"{Fore.YELLOW}Hinweis: Verkaufssignal-Nähe ist positiv, aber unter dem Schwellenwert für ein tatsächliches Signal.{Style.RESET_ALL}\n"
    
    output += f"Kaufsignal-Nähe ({buy_proximity:.2f}): {buy_bar}\n"
    output += f"Verkaufssignal-Nähe ({sell_proximity:.2f}): {sell_bar}\n"
    
    return output

# Beispiel für die Integration in utils.py, update_display-Funktion:
"""
# Nach dem Risikomanagement-Abschnitt:
if strategy_info:
    print(f"\n{Fore.CYAN}=== Strategie: {strategy_info.get('strategy', 'Unbekannt')} ==={Style.RESET_ALL}")
    # ... (bestehender Code)
    
    # Signalnähe-Anzeige hinzufügen
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
"""
