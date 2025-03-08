import pandas as pd
import numpy as np
from datetime import datetime
import math
from sklearn.cluster import KMeans
from scipy import stats
import matplotlib.pyplot as plt
from colorama import Fore, Style

class MarketRegimeDetector:
    """
    Verbesserte Klasse zur Erkennung von Marktphasen mit fortgeschrittenen Techniken.
    """
    
    def __init__(self):
        self.regimes = {
            'strong_uptrend': {'description': 'Starker Aufwärtstrend, hohe Kaufkraft'},
            'weak_uptrend': {'description': 'Schwacher Aufwärtstrend, abnehmende Kaufkraft'},
            'strong_downtrend': {'description': 'Starker Abwärtstrend, hoher Verkaufsdruck'},
            'weak_downtrend': {'description': 'Schwacher Abwärtstrend, nachlassender Verkaufsdruck'},
            'ranging_narrow': {'description': 'Enge Seitwärtsbewegung, geringe Volatilität'},
            'ranging_wide': {'description': 'Breite Seitwärtsbewegung, höhere Volatilität'},
            'breakout_potential': {'description': 'Potentieller Ausbruch aus Range'},
            'high_volatility': {'description': 'Hohe Volatilität, ungerichtete Bewegung'},
            'low_volatility': {'description': 'Sehr geringe Volatilität, Ruhe vor dem Sturm'}
        }
        
        # Optimale Strategien für verschiedene Marktphasen
        self.regime_strategy_weights = {
            'strong_uptrend': {
                'SMA_CROSSOVER': 0.8,
                'RSI': 0.4,
                'MACD': 0.9,
                'BOLLINGER_BANDS': 0.3,
                'MULTI_INDICATOR': 0.7
            },
            'weak_uptrend': {
                'SMA_CROSSOVER': 0.6,
                'RSI': 0.5,
                'MACD': 0.8,
                'BOLLINGER_BANDS': 0.4,
                'MULTI_INDICATOR': 0.7
            },
            'strong_downtrend': {
                'SMA_CROSSOVER': 0.3,
                'RSI': 0.8,
                'MACD': 0.7,
                'BOLLINGER_BANDS': 0.6,
                'MULTI_INDICATOR': 0.7
            },
            'weak_downtrend': {
                'SMA_CROSSOVER': 0.4,
                'RSI': 0.7,
                'MACD': 0.6,
                'BOLLINGER_BANDS': 0.5,
                'MULTI_INDICATOR': 0.7
            },
            'ranging_narrow': {
                'SMA_CROSSOVER': 0.2,
                'RSI': 0.9,
                'MACD': 0.3,
                'BOLLINGER_BANDS': 0.8,
                'MULTI_INDICATOR': 0.6
            },
            'ranging_wide': {
                'SMA_CROSSOVER': 0.3,
                'RSI': 0.8,
                'MACD': 0.4,
                'BOLLINGER_BANDS': 0.9,
                'MULTI_INDICATOR': 0.7
            },
            'breakout_potential': {
                'SMA_CROSSOVER': 0.6,
                'RSI': 0.7,
                'MACD': 0.8,
                'BOLLINGER_BANDS': 0.9,
                'MULTI_INDICATOR': 0.8
            },
            'high_volatility': {
                'SMA_CROSSOVER': 0.3,
                'RSI': 0.5,
                'MACD': 0.6,
                'BOLLINGER_BANDS': 0.7,
                'MULTI_INDICATOR': 0.9
            },
            'low_volatility': {
                'SMA_CROSSOVER': 0.4,
                'RSI': 0.6,
                'MACD': 0.5,
                'BOLLINGER_BANDS': 0.8,
                'MULTI_INDICATOR': 0.7
            }
        }

    def detect_regime(self, df, lookback_period=50):
        """
        Erkennt das aktuelle Marktregime mit fortgeschrittenen Techniken und adaptiven Schwellenwerten.
        
        Parameters:
        df (pandas.DataFrame): DataFrame mit OHLCV-Daten und Indikatoren
        lookback_period (int): Anzahl der zu analysierenden Perioden
        
        Returns:
        str: Erkanntes Marktregime
        """
        # Prüfe auf ausreichende Daten
        min_required_data = max(20, lookback_period // 2)  # Mindestens 20 Datenpunkte oder die Hälfte
        
        if len(df) < min_required_data:
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: Unzureichende Daten für Regimeerkennung. Benötigt {lookback_period}, hat {len(df)}. Verwende adaptive Analyse.{Style.RESET_ALL}")
            
            # Statt einen festen Standardwert zu verwenden, analysieren wir die verfügbaren Daten
            if len(df) < 5:  # Bei extrem wenigen Daten
                return 'neutral'  # Neutraler Wert statt biased 'weak_uptrend'
            
            # Sehr einfache Regime-Bestimmung basierend auf den wenigen verfügbaren Daten
            recent_df = df.tail(min(len(df), 5)).copy()
            price_change = (recent_df['close'].iloc[-1] - recent_df['close'].iloc[0]) / recent_df['close'].iloc[0]
            
            if price_change > 0.02:
                return 'weak_uptrend'
            elif price_change < -0.02:
                return 'weak_downtrend'
            else:
                return 'ranging_narrow'
        
        # Ab hier normales Verfahren mit ausreichend Daten
        recent_df = df.tail(lookback_period).copy()
        
        # Adaptive Schwellenwerte basierend auf historischer Volatilität
        price_volatility = recent_df['close'].pct_change().std() * np.sqrt(lookback_period)
        
        # Berechne adaptive Schwellenwerte basierend auf Marktbedingungen
        trend_threshold = max(0.5 * price_volatility, 0.01)  # Mindestens 1%
        volatility_threshold_high = max(1.5 * price_volatility, 0.03)  # Mindestens 3%
        volatility_threshold_low = max(0.3 * price_volatility, 0.01)  # Mindestens 1%
        range_threshold_narrow = max(0.3 * price_volatility, 0.015)  # Mindestens 1.5%
        range_threshold_wide = max(1.2 * price_volatility, 0.04)  # Mindestens 4%
        
        # Feature 1: Trendstärke und -richtung mit adaptiven Schwellenwerten
        price_change = (recent_df['close'].iloc[-1] - recent_df['close'].iloc[0]) / recent_df['close'].iloc[0]
        linear_reg = stats.linregress(range(len(recent_df)), recent_df['close'].values)
        trend_strength = abs(linear_reg.slope) / np.mean(recent_df['close'])
        r_squared = linear_reg.rvalue ** 2
        
        # Feature 2: Volatilität mit adaptiven Schwellenwerten
        if 'atr' in recent_df.columns:
            volatility = recent_df['atr'].mean() / recent_df['close'].mean()
        else:
            returns = recent_df['close'].pct_change().dropna()
            volatility = returns.std()
        
        # Feature 3: Seitwärtsbewegung (Range-Erkennung) mit adaptiven Schwellenwerten
        if 'bb_width' in recent_df.columns:
            bb_width_avg = recent_df['bb_width'].mean()
            # Normalisiere bb_width basierend auf historischen Daten
            bb_width_percentile = np.percentile(recent_df['bb_width'].dropna(), [25, 50, 75])
            is_narrow_range = bb_width_avg < bb_width_percentile[0]  # Unterste 25%
            is_wide_range = bb_width_avg > bb_width_percentile[2]    # Oberste 25%
        else:
            recent_df['high_low_ratio'] = (recent_df['high'] - recent_df['low']) / recent_df['close']
            high_low_percentile = np.percentile(recent_df['high_low_ratio'].dropna(), [25, 50, 75])
            is_narrow_range = recent_df['high_low_ratio'].mean() < high_low_percentile[0]
            is_wide_range = recent_df['high_low_ratio'].mean() > high_low_percentile[2]
        
        # Feature 4: Volumen-Analyse (falls verfügbar) mit adaptiver Normalisierung
        if 'volume' in recent_df.columns and not recent_df['volume'].isna().all():
            recent_df['volume_sma'] = recent_df['volume'].rolling(window=10).mean()
            # Normalisiere Volumen
            norm_volume = recent_df['volume'] / recent_df['volume'].mean()
            recent_volume = norm_volume.iloc[-5:].mean() 
            volume_trend = (recent_volume / norm_volume.mean()) - 1
            volume_spike = recent_df['volume'].iloc[-1] > 2 * recent_df['volume_sma'].iloc[-1]
        else:
            volume_trend = 0
            volume_spike = False
        
        # Feature 5: Momentum mit adaptiven Schwellenwerten
        if 'rsi' in recent_df.columns and not recent_df['rsi'].isna().all():
            rsi_latest = recent_df['rsi'].iloc[-1]
            # Adaptive RSI-Schwellenwerte basierend auf historischer RSI-Verteilung
            rsi_percentiles = np.percentile(recent_df['rsi'].dropna(), [10, 30, 70, 90])
            rsi_extreme_low = rsi_latest < rsi_percentiles[0]  # Unterste 10%
            rsi_extreme_high = rsi_latest > rsi_percentiles[3]  # Oberste 10%
            rsi_extreme = rsi_extreme_low or rsi_extreme_high
        else:
            # Alternatives Momentum-Maß mit adaptiven Schwellenwerten
            momentum = recent_df['close'].diff(5).iloc[-1] / recent_df['close'].iloc[-6] if len(recent_df) > 6 else 0
            momentum_threshold = max(1.2 * price_volatility, 0.03)
            rsi_extreme = abs(momentum) > momentum_threshold
        
        # Feature 6: Erkennung potenzieller Ausbrüche mit adaptiven Schwellenwerten
        if 'bb_upper' in recent_df.columns and 'bb_lower' in recent_df.columns:
            # Adaptive Nähe zu Bollinger Bändern
            band_distance = (recent_df['bb_upper'] - recent_df['bb_lower']) / recent_df['close']
            band_distance_pct = np.percentile(band_distance.dropna(), [10, 90])
            
            near_upper_threshold = 1 - (band_distance_pct[0] / 2)  # Näher am oberen Band
            near_lower_threshold = 1 + (band_distance_pct[0] / 2)  # Näher am unteren Band
            
            near_upper = recent_df['close'].iloc[-1] > near_upper_threshold * recent_df['bb_upper'].iloc[-1]
            near_lower = recent_df['close'].iloc[-1] < near_lower_threshold * recent_df['bb_lower'].iloc[-1]
            breakout_potential = near_upper or near_lower
        else:
            # Alternative Ausbruchs-Erkennung mit adaptiven Schwellenwerten
            recent_high = recent_df['high'].max()
            recent_low = recent_df['low'].min()
            price_range = (recent_high - recent_low) / np.mean(recent_df['close'])
            range_percentile = max(0.03, price_range * 0.9)
            
            close_to_extreme = (
                (recent_df['close'].iloc[-1] > recent_high - (range_percentile * recent_df['close'].mean())) or 
                (recent_df['close'].iloc[-1] < recent_low + (range_percentile * recent_df['close'].mean()))
            )
            breakout_potential = close_to_extreme and (is_narrow_range or volatility < volatility_threshold_low)
        
        # Kombiniere Faktoren, um das Marktregime zu bestimmen
        if breakout_potential:
            regime = 'breakout_potential'
        elif volatility > volatility_threshold_high:
            regime = 'high_volatility'
        elif volatility < volatility_threshold_low:
            regime = 'low_volatility'
        elif is_narrow_range and abs(price_change) < trend_threshold:
            regime = 'ranging_narrow'
        elif is_wide_range and abs(price_change) < trend_threshold:
            regime = 'ranging_wide'
        elif price_change > 0:  # Aufwärtstrend
            if trend_strength > trend_threshold and r_squared > 0.7:
                regime = 'strong_uptrend'
            else:
                regime = 'weak_uptrend'
        else:  # Abwärtstrend
            if trend_strength > trend_threshold and r_squared > 0.7:
                regime = 'strong_downtrend'
            else:
                regime = 'weak_downtrend'
        
        # Debug-Ausgabe
        print(f"{Fore.CYAN}[{datetime.now().strftime('%H:%M:%S')}] Market Regime Analysis:{Style.RESET_ALL}")
        print(f"  Price Change: {price_change*100:.2f}% (Threshold: {trend_threshold*100:.2f}%)")
        print(f"  Trend Strength: {trend_strength*1000:.2f} (R² = {r_squared:.2f})")
        print(f"  Volatility: {volatility*100:.2f}% (High: {volatility_threshold_high*100:.2f}%, Low: {volatility_threshold_low*100:.2f}%)")
        print(f"  Range Type: {'Narrow' if is_narrow_range else ('Wide' if is_wide_range else 'Medium')}")
        print(f"  Breakout Potential: {breakout_potential}")
        print(f"  Detected Regime: {regime.upper()} - {self.regimes[regime]['description']}")
        
        return regime

class MarketPatternRecognizer:
    """
    Erkennt häufige Chartmuster und -formationen in den Marktdaten.
    """
    
    def __init__(self):
        self.patterns = {
            'double_top': 0,
            'double_bottom': 0,
            'head_and_shoulders': 0,
            'reverse_head_and_shoulders': 0,
            'triangle': 0,
            'flag': 0,
            'wedge': 0
        }
        self.confidence_threshold = 0.65  # Mindestvertrauen für Mustererkennung
    
    def detect_double_top(self, df, lookback=30):
        """Erkennt Double-Top-Formationen"""
        if len(df) < lookback:
            return False, 0
        
        # Einfache Implementierung - suche nach zwei Hochs in ähnlicher Höhe
        recent = df.tail(lookback)
        
        # Finde lokale Maxima
        recent['is_local_max'] = (recent['high'] > recent['high'].shift(1)) & (recent['high'] > recent['high'].shift(-1))
        local_maxima = recent[recent['is_local_max']]['high'].values
        
        if len(local_maxima) < 2:
            return False, 0
        
        # Prüfe auf zwei ähnliche Hochs mit einem Tal dazwischen
        for i in range(len(local_maxima) - 1):
            if abs(local_maxima[i] - local_maxima[i+1]) / local_maxima[i] < 0.02:  # Ähnliche Höhe (2% Toleranz)
                # Finde das Minimum zwischen den beiden Maxima
                idx1 = recent[recent['high'] == local_maxima[i]].index[0]
                idx2 = recent[recent['high'] == local_maxima[i+1]].index[0]
                
                if idx2 - idx1 > 3:  # Genügend Abstand zwischen den Hochs
                    between_min = recent.loc[idx1:idx2, 'low'].min()
                    max_avg = (local_maxima[i] + local_maxima[i+1]) / 2
                    
                    # Genügend Tal zwischen den Hochs?
                    if (max_avg - between_min) / max_avg > 0.03:  # Mindestens 3% Preisunterschied
                        confidence = min(1.0, (max_avg - between_min) / max_avg * 10)  # Konfidenz basierend auf Tiefe des Tals
                        return True, confidence
        
        return False, 0
    
    def detect_patterns(self, df):
        """Erkennt verschiedene Chartmuster in den Daten"""
        # Hier würde eine komplexere Implementierung für alle Muster stehen
        # Für dieses Beispiel verwenden wir nur die Double-Top-Erkennung
        
        self.patterns['double_top'] = 0
        double_top_detected, confidence = self.detect_double_top(df)
        
        if double_top_detected and confidence > self.confidence_threshold:
            self.patterns['double_top'] = confidence
            print(f"{Fore.MAGENTA}[PATTERN] Double Top erkannt (Konfidenz: {confidence:.2f}){Style.RESET_ALL}")
            
        # Für andere Muster würden hier ähnliche Erkennungsfunktionen aufgerufen
        
        # Rückgabeformat: {pattern_name: confidence}
        return {k: v for k, v in self.patterns.items() if v > self.confidence_threshold}

class VolumeAnalyzer:
    """
    Führt detaillierte Volumenanalyse durch, um Kaufdruck oder Verkaufsdruck zu erkennen.
    """
    
    def analyze_volume(self, df, lookback=20):
        """
        Analysiert Volumenmuster, um Marktdruck zu identifizieren.
        
        Returns:
        dict: Volumenmuster und deren Stärke
        """
        if 'volume' not in df.columns or len(df) < lookback:
            return {'volume_pressure': 'unknown', 'strength': 0}
        
        recent = df.tail(lookback).copy()
        
        # Volumen-Indikator: Positives vs. Negatives Volumen
        recent['vol_pos'] = np.where(recent['close'] > recent['open'], recent['volume'], 0)
        recent['vol_neg'] = np.where(recent['close'] < recent['open'], recent['volume'], 0)
        
        # Berechne Verhältnis von positivem zu negativem Volumen
        total_pos_vol = recent['vol_pos'].sum()
        total_neg_vol = recent['vol_neg'].sum()
        
        # Vermeidung von Division durch Null
        if total_neg_vol == 0:
            vol_ratio = 10  # Hoher Wert für reinen Kaufdruck
        else:
            vol_ratio = total_pos_vol / total_neg_vol
        
        # Durchschnittliches Volumen und aktuelle Abweichung
        avg_volume = recent['volume'].mean()
        recent_volume = recent['volume'].tail(3).mean()
        volume_change = (recent_volume / avg_volume) - 1
        
        # Erkennung von Volumenspitzen
        has_volume_spike = any(recent['volume'].tail(3) > 2 * avg_volume)
        
        # Interpretiere Ergebnisse
        if vol_ratio > 2:
            pressure = 'strong_buying'
            strength = min(1.0, vol_ratio / 5)
        elif vol_ratio > 1.3:
            pressure = 'weak_buying'
            strength = min(1.0, vol_ratio / 3)
        elif vol_ratio < 0.5:
            pressure = 'strong_selling'
            strength = min(1.0, 1 / vol_ratio / 5)
        elif vol_ratio < 0.75:
            pressure = 'weak_selling'
            strength = min(1.0, 1 / vol_ratio / 3)
        else:
            pressure = 'neutral'
            strength = 0.5
        
        # Verstärke Signalstärke, wenn es eine Volumenspitze gibt
        if has_volume_spike:
            strength = min(1.0, strength * 1.3)
        
        # Verstärke/Abschwäche basierend auf aktueller Volumentendenz
        strength = strength * (1 + 0.5 * volume_change)
        strength = max(0.1, min(1.0, strength))
        
        return {
            'volume_pressure': pressure,
            'strength': strength,
            'volume_ratio': vol_ratio,
            'volume_change': volume_change,
            'has_spike': has_volume_spike
        }

class AdvancedMarketAnalysis:
    """
    Kombiniert verschiedene Analysetechniken, um ein umfassendes Marktbild zu erstellen.
    """
    
    def __init__(self):
        self.regime_detector = MarketRegimeDetector()
        self.pattern_recognizer = MarketPatternRecognizer()
        self.volume_analyzer = VolumeAnalyzer()
        
        # Tracking von Marktveränderungen
        self.previous_regime = None
        self.regime_change_time = None
        
        # Analytische Ergebnisse
        self.current_analysis = {}
        
    def analyze(self, df):
        """
        Führt eine vollständige Marktanalyse durch.
        
        Parameters:
        df (pandas.DataFrame): DataFrame mit OHLCV-Daten und Indikatoren
        
        Returns:
        dict: Umfassende Analyse-Ergebnisse
        """
        if len(df) < 30:
            return {'regime': 'insufficient_data', 'confidence': 0}
        
        # 1. Erkenne Marktregime
        current_regime = self.regime_detector.detect_regime(df)
        
        # Erkenne Regimewechsel
        if self.previous_regime is not None and current_regime != self.previous_regime:
            self.regime_change_time = datetime.now()
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Marktregime-Wechsel: {self.previous_regime} -> {current_regime}{Style.RESET_ALL}")
        
        self.previous_regime = current_regime
        
        # 2. Erkenne Chartmuster
        patterns = self.pattern_recognizer.detect_patterns(df)
        
        # 3. Analyse des Volumens
        volume_analysis = self.volume_analyzer.analyze_volume(df)
        
        # 4. Integrative Analyse
        combined_analysis = {
            'regime': current_regime,
            'regime_description': self.regime_detector.regimes[current_regime]['description'],
            'patterns': patterns,
            'volume': volume_analysis,
            'timestamp': datetime.now()
        }
        
        # Strategie-Vorschlag basierend auf der Analyse
        strategy_weights = self.regime_detector.regime_strategy_weights[current_regime].copy()
        
        # Anpassung der Gewichtungen basierend auf erkannten Mustern
        if 'double_top' in patterns and patterns['double_top'] > 0.7:
            # Double Top deutet auf mögliche Trendwende nach unten hin
            strategy_weights['RSI'] += 0.2  # RSI kann Überkaufbedingungen gut erkennen
            strategy_weights['BOLLINGER_BANDS'] += 0.1  # Bandbreite kann Volatilitätsänderungen erkennen
        
        # Anpassung basierend auf Volumendruck
        if volume_analysis['volume_pressure'] == 'strong_buying':
            strategy_weights['MACD'] += 0.1  # MACD kann Momentumänderungen gut erfassen
            strategy_weights['SMA_CROSSOVER'] += 0.1  # SMAs können Trendbestätigungen gut erfassen
        elif volume_analysis['volume_pressure'] == 'strong_selling':
            strategy_weights['RSI'] += 0.1  # RSI kann Überverkaufsbedingungen gut erkennen
        
        # Normalisiere Gewichte (optional)
        total_weight = sum(strategy_weights.values())
        strategy_weights = {k: v/total_weight for k, v in strategy_weights.items()}
        
        combined_analysis['recommended_strategy_weights'] = strategy_weights
        combined_analysis['confidence'] = min(1.0, (1 + volume_analysis['strength']) / 2)
        
        # Speichere die aktuelle Analyse zur späteren Verwendung
        self.current_analysis = combined_analysis
        
        return combined_analysis

class RiskAdjuster:
    """
    Passt Risikoparameter dynamisch basierend auf Marktbedingungen an.
    """
    
    def __init__(self, base_risk_per_trade=0.02):
        self.base_risk_per_trade = base_risk_per_trade
        self.max_risk_adjustment = 0.5  # Maximale Anpassung von +/- 50%
    
    def adjust_risk(self, market_analysis):
        """
        Passt Risikoparameter basierend auf der Marktanalyse an.
        
        Parameters:
        market_analysis (dict): Ergebnis der Marktanalyse
        
        Returns:
        dict: Angepasste Risikoparameter
        """
        regime = market_analysis.get('regime', 'unknown')
        confidence = market_analysis.get('confidence', 0.5)
        
        # Basisrisikoparameter
        risk_per_trade = self.base_risk_per_trade
        stop_loss_percent = 0.02
        take_profit_percent = 0.04
        
        # Risikoanpassung basierend auf Marktregime
        regime_risk_multipliers = {
            'strong_uptrend': 1.2,      # Höheres Risiko in starken Aufwärtstrends
            'weak_uptrend': 1.0,        # Normales Risiko in schwachen Aufwärtstrends
            'strong_downtrend': 0.7,    # Deutlich reduziertes Risiko in starken Abwärtstrends
            'weak_downtrend': 0.8,      # Reduziertes Risiko in schwachen Abwärtstrends
            'ranging_narrow': 0.9,      # Leicht reduziertes Risiko in engen Ranges
            'ranging_wide': 1.0,        # Normales Risiko in breiten Ranges
            'breakout_potential': 1.1,  # Leicht erhöhtes Risiko bei Ausbruchspotential
            'high_volatility': 0.6,     # Stark reduziertes Risiko bei hoher Volatilität
            'low_volatility': 1.1       # Leicht erhöhtes Risiko bei niedriger Volatilität
        }
        
        # Risikoanpassung basierend auf Konfidenz der Analyse
        confidence_adjustment = 0.5 + (confidence * 0.5)  # 0.5 bis 1.0
        
        # Anwenden der Anpassungen
        risk_multiplier = regime_risk_multipliers.get(regime, 1.0) * confidence_adjustment
        
        # Begrenzen der Anpassung
        risk_multiplier = max(1 - self.max_risk_adjustment, min(1 + self.max_risk_adjustment, risk_multiplier))
        
        # Anpassen der Risikoparameter
        adjusted_risk_per_trade = risk_per_trade * risk_multiplier
        
        # Anpassen von Stop-Loss und Take-Profit basierend auf Volatilität
        volume_strength = market_analysis.get('volume', {}).get('strength', 0.5)
        
        if regime in ['high_volatility', 'breakout_potential']:
            # Breitere Stops bei hoher Volatilität
            stop_loss_percent *= 1.3
            take_profit_percent *= 1.3
        elif regime in ['low_volatility', 'ranging_narrow']:
            # Engere Stops bei niedriger Volatilität
            stop_loss_percent *= 0.8
            take_profit_percent *= 0.8
        
        # Anpassen des Verhältnisses von Take-Profit zu Stop-Loss
        if volume_strength > 0.7 and regime in ['strong_uptrend', 'breakout_potential']:
            # Höheres Take-Profit-Ziel bei starkem Volumen in Aufwärtsbewegungen
            take_profit_percent *= 1.2
        
        return {
            'risk_per_trade': adjusted_risk_per_trade,
            'stop_loss_percent': stop_loss_percent,
            'take_profit_percent': take_profit_percent,
            'risk_multiplier': risk_multiplier,
            'confidence': confidence
        }
