import pandas as pd
import numpy as np
from datetime import datetime
from colorama import Fore, Style
import utils
import config

def calculate_sma(df, period=None):
    """Berechnet Simple Moving Average (SMA)"""
    if period is None:
        period_short = config.SMA_SHORT_PERIOD
        period_long = config.SMA_LONG_PERIOD
    else:
        period_short = period[0]
        period_long = period[1]
    
    # Sicherstellen, dass df nicht leer ist
    if df is None or df.empty or 'close' not in df.columns:
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler: Ungültige Daten für SMA-Berechnung{Style.RESET_ALL}")
        df[f'sma_{period_short}'] = np.nan
        df[f'sma_{period_long}'] = np.nan
        return df
    
    # NaN-Werte in 'close' verarbeiten
    if df['close'].isna().any():
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: NaN-Werte in Schlusskursdaten für SMA gefunden. Fülle mit vorherigen Werten.{Style.RESET_ALL}")
        df['close'] = df['close'].fillna(method='ffill').fillna(method='bfill')

    # SMA berechnen mit min_periods=1, um auch mit wenigen Datenpunkten zu arbeiten
    df[f'sma_{period_short}'] = df['close'].rolling(window=period_short, min_periods=1).mean()
    df[f'sma_{period_long}'] = df['close'].rolling(window=period_long, min_periods=1).mean()
    
    # Prüfung auf NaN-Werte in den Ergebnissen
    if df[f'sma_{period_short}'].isna().any() or df[f'sma_{period_long}'].isna().any():
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: NaN-Werte in SMA-Ergebnissen. Fülle fehlende Werte.{Style.RESET_ALL}")
        df[f'sma_{period_short}'] = df[f'sma_{period_short}'].fillna(method='ffill').fillna(method='bfill')
        df[f'sma_{period_long}'] = df[f'sma_{period_long}'].fillna(method='ffill').fillna(method='bfill')
    
    return df

def calculate_rsi(df, period=None):
    """Berechnet Relative Strength Index (RSI) mit verbesserter Validierung"""
    if period is None:
        period = config.RSI_PERIOD
    
    # Sicherstellen, dass genügend Daten vorhanden sind
    if df is None or df.empty or 'close' not in df.columns:
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler: Ungültige Daten für RSI-Berechnung{Style.RESET_ALL}")
        df['rsi'] = np.nan
        return df
    
    if len(df) < period + 1:
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: Unzureichende Daten für RSI-Berechnung. Benötigt mindestens {period + 1} Datenpunkte, hat {len(df)}{Style.RESET_ALL}")
        # Erstelle leere RSI-Spalte mit Standardwert 50 (neutral)
        df['rsi'] = 50
        return df
        
    # Sicherstellen, dass keine NaN-Werte im Schlusskurs vorhanden sind
    if df['close'].isna().any():
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: NaN-Werte in Schlusskursdaten für RSI gefunden. Fülle mit vorherigen Werten.{Style.RESET_ALL}")
        df['close'] = df['close'].fillna(method='ffill').fillna(method='bfill')
    
    try:
        delta = df['close'].diff()
        
        # Validiere Delta-Werte
        if delta.isna().any():
            delta = delta.fillna(0)
            
        gain = delta.where(delta > 0, 0).fillna(0)
        loss = -delta.where(delta < 0, 0).fillna(0)
        
        # Berechne den durchschnittlichen Gewinn und Verlust
        # Verwende EMA für stabilere Ergebnisse bei wenigen Daten
        avg_gain = gain.ewm(alpha=1/period, min_periods=1, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=1, adjust=False).mean()
        
        # Schutz vor Division durch Null mit kleinem Epsilon
        epsilon = 1e-10  # Sehr kleine Zahl statt 0
        avg_loss = avg_loss.replace(0, epsilon)
        
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Zusätzliche Validierung der RSI-Werte
        df['rsi'] = df['rsi'].clip(0, 100)  # Begrenze RSI auf 0-100
        
        # Fülle verbleibende NaN-Werte
        if df['rsi'].isna().any():
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: NaN-Werte in RSI-Ergebnissen. Fülle fehlende Werte.{Style.RESET_ALL}")
            df['rsi'] = df['rsi'].fillna(method='ffill').fillna(method='bfill')
            
            # Falls immer noch NaN-Werte (z.B. am Anfang), setze auf neutralen Wert
            df['rsi'] = df['rsi'].fillna(50)
        
        return df
    except Exception as e:
        utils.log_error(e, "Fehler bei der RSI-Berechnung")
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler bei der RSI-Berechnung: {str(e)}{Style.RESET_ALL}")
        df['rsi'] = np.nan
        return df

def calculate_macd(df, fast_period=None, slow_period=None, signal_period=None):
    """Berechnet Moving Average Convergence Divergence (MACD)"""
    if fast_period is None:
        fast_period = config.MACD_FAST
        slow_period = config.MACD_SLOW
        signal_period = config.MACD_SIGNAL
    
    # Sicherstellen, dass df nicht leer ist
    if df is None or df.empty or 'close' not in df.columns:
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler: Ungültige Daten für MACD-Berechnung{Style.RESET_ALL}")
        df['ema_fast'] = np.nan
        df['ema_slow'] = np.nan
        df['macd'] = np.nan
        df['macd_signal'] = np.nan
        df['macd_hist'] = np.nan
        return df
    
    # NaN-Werte in 'close' verarbeiten
    if df['close'].isna().any():
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: NaN-Werte in Schlusskursdaten für MACD gefunden. Fülle mit vorherigen Werten.{Style.RESET_ALL}")
        df['close'] = df['close'].fillna(method='ffill').fillna(method='bfill')
    
    try:
        # Berechne EMA (Exponential Moving Average) mit min_periods=1 für kleinere Datensätze
        df['ema_fast'] = df['close'].ewm(span=fast_period, min_periods=1, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=slow_period, min_periods=1, adjust=False).mean()
        
        # Berechne MACD Linie und Signal Linie
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['macd_signal'] = df['macd'].ewm(span=signal_period, min_periods=1, adjust=False).mean()
        
        # Berechne MACD Histogramm
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Prüfung auf NaN-Werte in den Ergebnissen
        for col in ['macd', 'macd_signal', 'macd_hist']:
            if df[col].isna().any():
                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: NaN-Werte in {col} gefunden. Fülle fehlende Werte.{Style.RESET_ALL}")
                df[col] = df[col].ffill().bfill()
        
        return df
        
    except Exception as e:
        utils.log_error(e, "Fehler bei der MACD-Berechnung")
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler bei der MACD-Berechnung: {str(e)}{Style.RESET_ALL}")
        df['ema_fast'] = np.nan
        df['ema_slow'] = np.nan
        df['macd'] = np.nan
        df['macd_signal'] = np.nan
        df['macd_hist'] = np.nan
        return df

def calculate_bollinger_bands(df, period=None, std_dev=None):
    """Berechnet Bollinger Bands mit verbesserter Validierung"""
    if period is None:
        period = config.BOLLINGER_PERIOD
        std_dev = config.BOLLINGER_STD_DEV
    
    # Validiere Eingabeparameter
    period = max(2, period)  # Mindestens 2 Perioden
    
    # Sicherstellen, dass df nicht leer ist
    if df is None or df.empty or 'close' not in df.columns:
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler: Ungültige Daten für Bollinger Bands Berechnung{Style.RESET_ALL}")
        df['bb_middle'] = np.nan
        df['bb_upper'] = np.nan
        df['bb_lower'] = np.nan
        df['bb_width'] = np.nan
        df['bb_percent_b'] = np.nan
        return df
    
    # Sicherstellen, dass genügend Daten vorhanden sind
    if len(df) < period:
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: Unzureichende Daten für Bollinger Bands. Benötigt mindestens {period} Datenpunkte, hat {len(df)}{Style.RESET_ALL}")
        # Erstelle leere BB-Spalten
        df['bb_middle'] = df['close']  # Setze middle band auf close als Fallback
        df['bb_upper'] = df['close'] * 1.01  # Setze upper band 1% über close
        df['bb_lower'] = df['close'] * 0.99  # Setze lower band 1% unter close
        df['bb_width'] = 0.02  # Standardbreite
        df['bb_percent_b'] = 0.5  # Neutral
        return df
    
    # Sicherstellen, dass keine NaN-Werte im Schlusskurs vorhanden sind
    if df['close'].isna().any():
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: NaN-Werte in Schlusskursdaten für Bollinger Bands gefunden. Fülle mit vorherigen Werten.{Style.RESET_ALL}")
        df['close'] = df['close'].fillna(method='ffill').fillna(method='bfill')
    
    try:
        # Berechne mittleren Bollinger Band (SMA) mit min_periods=1 für Robustheit
        df['bb_middle'] = df['close'].rolling(window=period, min_periods=1).mean()
        
        # Berechne Standardabweichung mit Validierung
        df['bb_std'] = df['close'].rolling(window=period, min_periods=1).std()
        
        # Verhindere Division durch Null oder sehr kleine Werte bei der Standardabweichung
        min_std = df['close'].mean() * 0.001  # Mindestens 0.1% des mittleren Preises
        df['bb_std'] = df['bb_std'].clip(lower=min_std)
        
        # Berechne oberes und unteres Band
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * std_dev)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * std_dev)
        
        # Berechne Bollinger Bandwidth und %B mit Schutz vor Division durch Null
        epsilon = 1e-10
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / (df['bb_middle'] + epsilon)
        
        # Sichere Division für %B
        band_diff = df['bb_upper'] - df['bb_lower']
        df['bb_percent_b'] = np.where(
            band_diff > epsilon,
            (df['close'] - df['bb_lower']) / band_diff,
            0.5  # Standardwert, wenn Bänder zusammenfallen
        )
        
        # Begrenze %B-Werte
        df['bb_percent_b'] = df['bb_percent_b'].clip(0, 1)
        
        # Prüfung auf NaN-Werte in den Ergebnissen
        for col in ['bb_middle', 'bb_upper', 'bb_lower', 'bb_width', 'bb_percent_b']:
            if df[col].isna().any():
                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: NaN-Werte in {col} gefunden. Fülle fehlende Werte.{Style.RESET_ALL}")
                df[col] = df[col].ffill().bfill()
        
        return df
    except Exception as e:
        utils.log_error(e, "Fehler bei der Bollinger Bands Berechnung")
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler bei der Bollinger Bands Berechnung: {str(e)}{Style.RESET_ALL}")
        
        # Setze alle BB-Spalten auf NaN bei Fehler
        df['bb_middle'] = np.nan
        df['bb_upper'] = np.nan
        df['bb_lower'] = np.nan
        df['bb_width'] = np.nan
        df['bb_percent_b'] = np.nan
        return df

def calculate_stochastic_oscillator(df, k_period=14, d_period=3):
    """Berechnet Stochastischer Oszillator mit verbesserter Validierung"""
    # Sicherstellen, dass df nicht leer ist
    if df is None or df.empty or not all(col in df.columns for col in ['high', 'low', 'close']):
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler: Ungültige Daten für Stochastic Oscillator Berechnung{Style.RESET_ALL}")
        df['stoch_k'] = np.nan
        df['stoch_d'] = np.nan
        return df
    
    # Prüfe auf NaN-Werte in Eingabedaten
    for col in ['high', 'low', 'close']:
        if df[col].isna().any():
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: NaN-Werte in {col} für Stochastic Oscillator gefunden. Fülle fehlende Werte.{Style.RESET_ALL}")
            df[col] = df[col].ffill().bfill()
    
    try:
        # %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
        # Verwende min_periods=1 für robuste Berechnung bei kleinen Datensätzen
        low_min = df['low'].rolling(window=k_period, min_periods=1).min()
        high_max = df['high'].rolling(window=k_period, min_periods=1).max()
        
        # Verhindere Division durch Null
        denom = high_max - low_min
        # Verwende mindestens 0.1% des mittleren Preises als minimale Range
        min_range = df['close'].mean() * 0.001
        denom = denom.clip(lower=min_range)
        
        df['stoch_k'] = 100 * ((df['close'] - low_min) / denom)
        
        # %D = 3-day SMA of %K (oder EMA für stabilere Werte)
        df['stoch_d'] = df['stoch_k'].rolling(window=d_period, min_periods=1).mean()
        
        # Begrenze die Werte auf 0-100
        df['stoch_k'] = df['stoch_k'].clip(0, 100)
        df['stoch_d'] = df['stoch_d'].clip(0, 100)
        
        # Prüfung auf NaN-Werte in den Ergebnissen
        for col in ['stoch_k', 'stoch_d']:
            if df[col].isna().any():
                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: NaN-Werte in {col} gefunden. Fülle fehlende Werte.{Style.RESET_ALL}")
                df[col] = df[col].ffill().bfill()
        
        return df
    except Exception as e:
        utils.log_error(e, "Fehler bei der Stochastic Oscillator Berechnung")
        df['stoch_k'] = np.nan
        df['stoch_d'] = np.nan
        return df

def calculate_atr(df, period=14):
    """Berechnet Average True Range (ATR) mit verbesserter Validierung"""
    # Sicherstellen, dass df nicht leer ist
    if df is None or df.empty or not all(col in df.columns for col in ['high', 'low', 'close']):
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler: Ungültige Daten für ATR-Berechnung{Style.RESET_ALL}")
        df['atr'] = np.nan
        return df
    
    # Prüfe auf NaN-Werte in Eingabedaten
    for col in ['high', 'low', 'close']:
        if df[col].isna().any():
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: NaN-Werte in {col} für ATR gefunden. Fülle fehlende Werte.{Style.RESET_ALL}")
            df[col] = df[col].ffill().bfill()
    
    try:
        # Berechne True Range
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift())
        df['tr3'] = abs(df['low'] - df['close'].shift())
        
        # Behandle NaN-Werte in der ersten Zeile
        for col in ['tr2', 'tr3']:
            df[col] = df[col].fillna(df['tr1'])
        
        # Berechne den Maximalwert für TR
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # Berechne ATR entweder als EMA (für bessere Robustheit) oder als SMA
        # Verwende min_periods=1 für robuste Berechnung
        df['atr'] = df['tr'].ewm(span=period, min_periods=1, adjust=False).mean()
        
        # Entferne Hilfsspalten
        df = df.drop(['tr1', 'tr2', 'tr3', 'tr'], axis=1)
        
        # Prüfung auf NaN-Werte im Ergebnis
        if df['atr'].isna().any():
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: NaN-Werte in ATR gefunden. Fülle fehlende Werte.{Style.RESET_ALL}")
            df['atr'] = df['atr'].fillna(method='ffill').fillna(method='bfill')
        
        return df
    except Exception as e:
        utils.log_error(e, "Fehler bei der ATR-Berechnung")
        # Bereinige Hilfsspalten im Fehlerfall
        for col in ['tr1', 'tr2', 'tr3', 'tr']:
            if col in df.columns:
                df = df.drop(col, axis=1)
        df['atr'] = np.nan
        return df

def calculate_all_indicators(df):
    """Berechnet alle technischen Indikatoren mit verbesserter Validierung"""
    print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Berechne technische Indikatoren...{Style.RESET_ALL}")
    
    # Stelle sicher, dass das DataFrame nicht leer ist
    if df is None or df.empty:
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler: Leeres DataFrame, Indikatorberechnung nicht möglich{Style.RESET_ALL}")
        return df if df is not None else pd.DataFrame()
    
    # Stelle sicher, dass die erforderlichen Spalten vorhanden sind
    required_columns = ['timestamp', 'open', 'high', 'low', 'close']
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler: Fehlende erforderliche Spalten: {missing}{Style.RESET_ALL}")
        return df
    
    try:
        # Kopie erstellen, um Originaldaten nicht zu verändern
        df_copy = df.copy()
        
        # Fülle NaN-Werte, um Fehler zu vermeiden
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df_copy.columns and df_copy[col].isna().any():
                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: NaN-Werte in {col} gefunden. Fülle fehlende Werte.{Style.RESET_ALL}")
                df_copy[col] = df_copy[col].fillna(method='ffill').fillna(method='bfill')
        
        # Grundlegende Indikatoren
        df_copy = calculate_sma(df_copy)
        df_copy = calculate_rsi(df_copy)
        
        # Fortgeschrittene Indikatoren
        df_copy = calculate_macd(df_copy)
        df_copy = calculate_bollinger_bands(df_copy)
        df_copy = calculate_stochastic_oscillator(df_copy)
        df_copy = calculate_atr(df_copy)
        
        # Komplexe Indikatoren (optional - können bei Bedarf aktiviert werden)
        # df_copy = calculate_adx(df_copy)
        # df_copy = calculate_ichimoku(df_copy)
        # df_copy = calculate_pivot_points(df_copy)
        # df_copy = calculate_volume_indicators(df_copy)
        
        # Signalgenerierung
        df_copy = generate_signals(df_copy)
        
        print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Technische Indikatoren erfolgreich berechnet.{Style.RESET_ALL}")
        
        return df_copy
    except Exception as e:
        utils.log_error(e, "Kritischer Fehler bei der Berechnung der technischen Indikatoren")
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Kritischer Fehler bei der Indikatorberechnung: {str(e)}{Style.RESET_ALL}")
        
        # Gib das Ursprungs-DataFrame zurück, um Datenverlust zu vermeiden
        return df

def generate_signals(df):
    """Generiert Signale basierend auf allen berechneten Indikatoren mit verbesserter Validierung"""
    df['signal'] = 0
    
    try:
        # SMA-Crossover-Signal
        if 'sma_5' in df.columns and 'sma_20' in df.columns:
            # Stelle sicher, dass keine NaN-Werte in den Signalberechnungen sind
            valid_sma = (~df['sma_5'].isna()) & (~df['sma_20'].isna()) & (~df['sma_5'].shift(1).isna()) & (~df['sma_20'].shift(1).isna())
            
            # Initialisiere Signal-Spalte
            df['signal_sma'] = 0
            
            # Berechne Signale nur für gültige Zeilen
            buy_signal = (df['sma_5'] > df['sma_5'].shift(1)) & (df['sma_5'] > df['sma_20']) & (df['sma_5'].shift(1) <= df['sma_20'].shift(1)) & valid_sma
            sell_signal = (df['sma_5'] < df['sma_5'].shift(1)) & (df['sma_5'] < df['sma_20']) & (df['sma_5'].shift(1) >= df['sma_20'].shift(1)) & valid_sma
            
            df.loc[buy_signal, 'signal_sma'] = 1
            df.loc[sell_signal, 'signal_sma'] = -1
        
        # RSI-Signal
        if 'rsi' in df.columns and not df['rsi'].isna().all():
            # Initialisiere Signal-Spalte
            df['signal_rsi'] = 0
            
            # Prüfe RSI-Werte gegen Schwellenwerte aus der Konfiguration
            if hasattr(config, 'RSI_OVERSOLD') and hasattr(config, 'RSI_OVERBOUGHT'):
                df.loc[df['rsi'] < config.RSI_OVERSOLD, 'signal_rsi'] = 1  # Überkauft - Kaufsignal
                df.loc[df['rsi'] > config.RSI_OVERBOUGHT, 'signal_rsi'] = -1  # Überverkauft - Verkaufssignal
            else:
                # Standardwerte, wenn Konfiguration nicht verfügbar
                df.loc[df['rsi'] < 30, 'signal_rsi'] = 1
                df.loc[df['rsi'] > 70, 'signal_rsi'] = -1
        
        # MACD-Signal
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            # Stelle sicher, dass keine NaN-Werte in den Signalberechnungen sind
            valid_macd = (~df['macd'].isna()) & (~df['macd_signal'].isna()) & (~df['macd'].shift(1).isna()) & (~df['macd_signal'].shift(1).isna())
            
            # Initialisiere Signal-Spalte
            df['signal_macd'] = 0
            
            # Berechne Signale nur für gültige Zeilen
            buy_signal = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1)) & valid_macd
            sell_signal = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1)) & valid_macd
            
            df.loc[buy_signal, 'signal_macd'] = 1
            df.loc[sell_signal, 'signal_macd'] = -1
        
        # Bollinger Bands Signal
        if 'bb_lower' in df.columns and 'bb_upper' in df.columns:
            # Stelle sicher, dass keine NaN-Werte im Close und in den Bändern sind
            valid_bb = (~df['close'].isna()) & (~df['bb_lower'].isna()) & (~df['bb_upper'].isna())
            
            # Initialisiere Signal-Spalte
            df['signal_bb'] = 0
            
            # Berechne Signale nur für gültige Zeilen
            df.loc[(df['close'] < df['bb_lower']) & valid_bb, 'signal_bb'] = 1  # Preis unter unterem Band - Kaufsignal
            df.loc[(df['close'] > df['bb_upper']) & valid_bb, 'signal_bb'] = -1  # Preis über oberem Band - Verkaufssignal
        
        # Stochastic Signal
        if 'stoch_k' in df.columns and 'stoch_d' in df.columns and not df['stoch_k'].isna().all():
            # Stelle sicher, dass keine NaN-Werte in den Signalberechnungen sind
            valid_stoch = (~df['stoch_k'].isna()) & (~df['stoch_k'].shift(1).isna())
            
            # Initialisiere Signal-Spalte
            df['signal_stoch'] = 0
            
            # Berechne Signale nur für gültige Zeilen
            df.loc[(df['stoch_k'] < 20) & (df['stoch_k'] > df['stoch_k'].shift(1)) & valid_stoch, 'signal_stoch'] = 1
            df.loc[(df['stoch_k'] > 80) & (df['stoch_k'] < df['stoch_k'].shift(1)) & valid_stoch, 'signal_stoch'] = -1
        
        # Kombiniere alle Signale (optional mit Gewichtung)
        # In dieser einfachen Version werden die Signale gleichgewichtet
        signal_columns = [col for col in df.columns if col.startswith('signal_')]
        if signal_columns:
            # Zähle die Kauf- und Verkaufssignale
            buy_signals = df[signal_columns].apply(lambda row: sum(row > 0), axis=1)
            sell_signals = df[signal_columns].apply(lambda row: sum(row < 0), axis=1)
            
            # Bestimme das Gesamtsignal
            df['signal'] = np.where(buy_signals > sell_signals, 1, 
                                   np.where(sell_signals > buy_signals, -1, 0))
            
    except Exception as e:
        utils.log_error(e, "Fehler bei der Signalgenerierung")
        print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler bei der Signalgenerierung: {str(e)}{Style.RESET_ALL}")
        # Stelle sicher, dass wir mindestens eine Signal-Spalte haben
        df['signal'] = 0
    
    return df