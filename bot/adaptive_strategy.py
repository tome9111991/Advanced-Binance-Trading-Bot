import os
import pandas as pd
import numpy as np
from datetime import datetime
from colorama import Fore, Style
import utils
import config

class AdaptiveStrategy:
    """
    Adaptive Meta-Strategie, die dynamisch die beste Trading-Strategie für
    aktuelle Marktbedingungen auswählt und anwendet.
    """
    
    def __init__(self, lookback_period=20):
        """
        Initialisiert die adaptive Strategie.
        
        Parameters:
        lookback_period (int): Anzahl der vergangenen Perioden zur Bewertung von Strategien
        """
        self.lookback_period = lookback_period
        self.strategy_performance = {}  # Speichert Performance-Metriken für jede Strategie
        self.current_strategy = None    # Aktuell ausgewählte Strategie
        self.market_regime = None       # Aktuelles Marktregime (bullish, bearish, ranging, volatile)
        
        # Verfügbare Strategien und ihre Funktionsverweise
        # Wir importieren die Strategien spät, um Zirkelbezüge zu vermeiden
        self.available_strategies = {
            'SMA_CROSSOVER': None,  # Wird beim ersten Aufruf von setup_strategies initialisiert
            'RSI': None,
            'MACD': None,
            'BOLLINGER_BANDS': None,
            'MULTI_INDICATOR': None
        }
        
        # Performance-Tracking für jede Strategie
        self.strategy_signals = {strat: [] for strat in self.available_strategies}
        
        # Historische Signale und tatsächliche Ergebnisse
        self.historical_signals = []
        self.historical_results = []
        
        # Tracking der Wechsel
        self.strategy_changes = []
        
        # Gewichte für unterschiedliche Marktregime
        # Für jedes Regime, welche Strategie besser geeignet ist (Gewichtung)
        self.regime_weights = {
            'bullish': {
                'SMA_CROSSOVER': 0.7,
                'RSI': 0.5,
                'MACD': 0.8,
                'BOLLINGER_BANDS': 0.3,
                'MULTI_INDICATOR': 0.6
            },
            'bearish': {
                'SMA_CROSSOVER': 0.4,
                'RSI': 0.7,
                'MACD': 0.6,
                'BOLLINGER_BANDS': 0.8,
                'MULTI_INDICATOR': 0.6
            },
            'ranging': {
                'SMA_CROSSOVER': 0.3,
                'RSI': 0.8,
                'MACD': 0.4,
                'BOLLINGER_BANDS': 0.9,
                'MULTI_INDICATOR': 0.5
            },
            'volatile': {
                'SMA_CROSSOVER': 0.2,
                'RSI': 0.5,
                'MACD': 0.6,
                'BOLLINGER_BANDS': 0.7,
                'MULTI_INDICATOR': 0.9
            }
        }
    
    def setup_strategies(self):
        """
        Initialisiert die Strategiefunktionen.
        Wird separat aufgerufen, um Zirkelbezüge zu vermeiden.
        """
        import strategies
        
        self.available_strategies = {
            'SMA_CROSSOVER': strategies.sma_crossover_strategy,
            'RSI': strategies.rsi_strategy,
            'MACD': strategies.macd_strategy,
            'BOLLINGER_BANDS': strategies.bollinger_bands_strategy,
            'MULTI_INDICATOR': strategies.multi_indicator_strategy
        }
    
    def detect_market_regime(self, df):
        """
        Erkennt das aktuelle Marktregime basierend auf verschiedenen Indikatoren.
        
        Parameters:
        df (pandas.DataFrame): DataFrame mit Marktdaten und berechneten Indikatoren
        
        Returns:
        str: Erkanntes Marktregime ('bullish', 'bearish', 'ranging', 'volatile')
        """
        if len(df) < 20:  # Benötigen mindestens 20 Datenpunkte für vernünftige Analyse
            return 'unknown'
        
        # Preisdynamik der letzten Perioden analysieren
        recent_df = df.tail(20)
        
        # Trend bestimmen (bullish oder bearish)
        price_change = (recent_df['close'].iloc[-1] - recent_df['close'].iloc[0]) / recent_df['close'].iloc[0]
        
        # Volatilität messen
        if 'atr' in recent_df.columns:
            volatility = recent_df['atr'].mean() / recent_df['close'].mean()
        else:
            # Alternativ: Standardabweichung der Returns als Volatilitätsmaß
            returns = recent_df['close'].pct_change().dropna()
            volatility = returns.std()
        
        # Ranging-Markt erkennen (seitwärts)
        if 'bb_width' in recent_df.columns:
            bb_width = recent_df['bb_width'].mean()
            is_narrow_range = bb_width < 0.03  # Enge Bollinger Bänder deuten auf Seitwärtsbewegung hin
        else:
            # Alternativ: Differenz zwischen Hoch und Tief im Verhältnis zum Durchschnittspreis
            high_low_range = (recent_df['high'] - recent_df['low']).mean() / recent_df['close'].mean()
            is_narrow_range = high_low_range < 0.02
        
        # RSI zur Bestimmung von überkauft/überverkauft
        if 'rsi' in recent_df.columns:
            avg_rsi = recent_df['rsi'].mean()
            rsi_range = recent_df['rsi'].max() - recent_df['rsi'].min()
        else:
            avg_rsi = 50  # Neutraler Wert, wenn kein RSI verfügbar
            rsi_range = 20  # Mittlere Range
        
        # Markt-Regime bestimmen
        if volatility > 0.03:  # Hohe Volatilität
            regime = 'volatile'
        elif abs(price_change) < 0.01 and is_narrow_range:  # Kleiner Kurswechsel und enge Range
            regime = 'ranging'
        elif price_change > 0.01:  # Positiver Trend
            regime = 'bullish'
        elif price_change < -0.01:  # Negativer Trend
            regime = 'bearish'
        else:
            regime = 'ranging'  # Standardfall: Seitwärtsbewegung
        
        print(f"{Fore.CYAN}[{datetime.now().strftime('%H:%M:%S')}] Erkanntes Marktregime: {regime.upper()} "
              f"(Preisänderung: {price_change*100:.2f}%, Volatilität: {volatility*100:.2f}%){Style.RESET_ALL}")
        
        return regime
    
    def evaluate_strategy_performance(self, df):
        """
        Bewertet die Performance der einzelnen Strategien in der aktuellen Marktphase.
        
        Parameters:
        df (pandas.DataFrame): DataFrame mit Marktdaten und berechneten Indikatoren
        
        Returns:
        dict: Dictionary mit Bewertungen für jede Strategie
        """
        # Erhöhe die Mindestanzahl an benötigten Datenpunkten
        if len(df) < self.lookback_period + 10:  # Erhöhter Puffer
            # Nicht genügend Daten, Standardgewichte verwenden
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Nicht genügend Daten für Strategiebewertung. Verwende Standardgewichte.{Style.RESET_ALL}")
            return {strat: 0.5 for strat in self.available_strategies}
        
        evaluations = {}
        
        # Aktueller Preis und historische Daten
        current_price = df['close'].iloc[-1]
        historical_prices = df['close'].iloc[-self.lookback_period-5:-5].values
        
        for strategy_name, strategy_func in self.available_strategies.items():
            if strategy_func is None:
                self.setup_strategies()
                strategy_func = self.available_strategies[strategy_name]
            
            # Berechne hypothetische Handelssignale für die letzten N Perioden
            strategy_signals = []
            try:
                for i in range(len(historical_prices) - 4):
                    # Stelle sicher, dass das temporäre DataFrame genügend Daten für die Strategie hat
                    temp_df = df.iloc[-(self.lookback_period+5-i):-5+i].copy()
                    
                    # Überspringe, wenn temp_df zu klein für sinnvolle Analyse ist
                    if len(temp_df) < 3:  # Stelle sicher, dass mindestens 3 Datenpunkte vorhanden sind
                        continue
                        
                    # Füge einen try-except-Block hinzu, um potenzielle Fehler in der Strategiefunktion zu behandeln
                    try:
                        signal, _ = strategy_func(temp_df)
                        strategy_signals.append(signal)
                    except Exception as e:
                        print(f"{Fore.RED}Fehler bei Strategieausführung {strategy_name}: {str(e)}{Style.RESET_ALL}")
                        continue
            except Exception as e:
                print(f"{Fore.RED}Fehler bei Strategiebewertung {strategy_name}: {str(e)}{Style.RESET_ALL}")
                evaluations[strategy_name] = 0.5  # Neutraler Wert bei Fehler
                continue
                
            # Berechne hypothetische Renditen basierend auf den Signalen
            returns = []
            position = 0
            
            for i, signal in enumerate(strategy_signals[:-1]):
                if i == 0:
                    continue
                
                # Position aktualisieren basierend auf Signal
                if signal == 1 and position <= 0:  # Kaufsignal
                    position = 1
                elif signal == -1 and position >= 0:  # Verkaufssignal
                    position = -1
                
                # Berechne Rendite für diese Periode
                price_change = (historical_prices[i+1] - historical_prices[i]) / historical_prices[i]
                strategy_return = position * price_change  # Positive Rendite bei korrekter Richtung
                returns.append(strategy_return)
            
            # Berechne Gesamtrendite und Trefferquote
            if returns:
                cumulative_return = np.sum(returns)
                win_rate = np.sum([r > 0 for r in returns]) / len(returns) if returns else 0
                
                # Sharpe Ratio (einfache Version)
                avg_return = np.mean(returns) if returns else 0
                std_return = np.std(returns) if len(returns) > 1 else 0.01
                sharpe = avg_return / std_return if std_return > 0 else 0
                
                # Kombinierte Bewertung (Rendite, Trefferquote, Sharpe Ratio)
                score = 0.4 * cumulative_return + 0.4 * win_rate + 0.2 * sharpe
                
                # Begrenzen auf vernünftige Werte
                score = max(0.1, min(1.0, score + 0.5))  # +0.5 als Offset, damit Werte zwischen 0.1 und 1.0 liegen
            else:
                score = 0.5  # Neutraler Wert, wenn keine Daten
            
            evaluations[strategy_name] = score
        
        return evaluations
    
    def select_best_strategy(self, df):
        """
        Wählt die beste Strategie für die aktuellen Marktbedingungen aus.
        
        Parameters:
        df (pandas.DataFrame): DataFrame mit Marktdaten und berechneten Indikatoren
        
        Returns:
        str: Name der ausgewählten Strategie
        """
        # Überprüfe, ob ausreichend Daten vorhanden sind
        if len(df) < 20:  # Mindestanzahl an Daten für zuverlässige Regimeerkennung
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Nicht genügend Daten für Regimeerkennung, verwende Standardstrategie.{Style.RESET_ALL}")
            return 'MULTI_INDICATOR'  # Standardstrategie als Fallback
            
        # Marktregime erkennen
        self.market_regime = self.detect_market_regime(df)
        
        # Performance der Strategien bewerten
        performance_scores = self.evaluate_strategy_performance(df)
        
        # Gewichtung basierend auf Marktregime
        regime_weights = self.regime_weights.get(self.market_regime, 
                                              {strat: 0.5 for strat in self.available_strategies})
        
        # Kombinierte Bewertung (Performance + Regime-Eignung)
        combined_scores = {}
        for strategy in self.available_strategies:
            # 60% Performance, 40% Regime-Eignung
            score = 0.6 * performance_scores.get(strategy, 0.5) + 0.4 * regime_weights.get(strategy, 0.5)
            combined_scores[strategy] = score
        
        # Beste Strategie auswählen
        best_strategy = max(combined_scores.items(), key=lambda x: x[1])[0]
        
        # Debug-Ausgabe
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Strategie-Auswahl:{Style.RESET_ALL}")
        for strategy, score in combined_scores.items():
            selected_marker = " ◀ AUSGEWÄHLT" if strategy == best_strategy else ""
            print(f"  {strategy}: {score:.2f}{selected_marker}")
        
        # Speichere die aktuelle Strategie
        self.current_strategy = best_strategy

        # Speichere Strategiewechsel, wenn konfiguriert
        if config.SAVE_STRATEGY_CHANGES and self.strategy_changes:
            self.save_strategy_changes()

            # Log von Strategie-Scores für Debugging
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Strategie-Auswahl:{Style.RESET_ALL}")
        
        return best_strategy
    
    def update_historical_data(self, signal, actual_price_change):
        """
        Aktualisiert die historischen Daten mit dem letzten Signal und dem tatsächlichen Ergebnis.
        
        Parameters:
        signal (int): Generiertes Handelssignal (-1, 0, 1)
        actual_price_change (float): Tatsächliche Preisänderung nach dem Signal
        """
        self.historical_signals.append(signal)
        self.historical_results.append(actual_price_change)
        
        # Beschränke die Größe der Historien-Arrays
        max_history = 500
        if len(self.historical_signals) > max_history:
            self.historical_signals = self.historical_signals[-max_history:]
            self.historical_results = self.historical_results[-max_history:]
    
    def adaptive_strategy(self, df):
        """
        Implementierung der adaptiven Strategie.
        
        Parameters:
        df (pandas.DataFrame): DataFrame mit Marktdaten und berechneten Indikatoren
        
        Returns:
        tuple: (signal, info) mit dem Handelssignal und zusätzlichen Informationen
        """
        # Überprüfe, ob ausreichend Daten für Analyse vorhanden sind
        if df.empty or len(df) < 10:
            info = {
                'strategy': 'ADAPTIVE',
                'description': 'Wählt dynamisch die beste Strategie basierend auf aktuellen Marktbedingungen',
                'signal_details': 'Nicht genügend Daten für Signalgenerierung',
                'analysis': 'Unzureichende Daten'
            }
            return 0, info
            
        # Initialisiere Strategien, falls noch nicht geschehen
        if None in self.available_strategies.values():
            self.setup_strategies()
        
        try:
            # Beste Strategie für aktuelle Marktbedingungen auswählen
            best_strategy = self.select_best_strategy(df)
            strategy_func = self.available_strategies[best_strategy]
            self.current_strategy = best_strategy
            
            # Signal von der ausgewählten Strategie generieren
            signal, strategy_info = strategy_func(df)
            
            # Zusätzliche Informationen für die adaptive Strategie
            info = {
                'strategy': 'ADAPTIVE',
                'description': 'Wählt dynamisch die beste Strategie basierend auf aktuellen Marktbedingungen',
                'parameters': f'Lookback-Periode: {self.lookback_period}, Aktuelles Regime: {self.market_regime}',
                'selected_strategy': best_strategy,
                'signal_details': strategy_info.get('signal_details', 'Keine Details verfügbar'),
                'analysis': f"Ausgewählte Strategie: {best_strategy}, Marktregime: {self.market_regime.upper() if self.market_regime else 'Unbekannt'}"
            }
            
            return signal, info
            
        except Exception as e:
            utils.log_error(e, "Fehler bei der Ausführung der adaptiven Strategie")
            print(f"{Fore.RED}[{datetime.now().strftime('%H:%M:%S')}] Fehler bei adaptiver Strategie: {str(e)}{Style.RESET_ALL}")
            
            # Fallback auf einfachste Strategie im Fehlerfall
            info = {
                'strategy': 'ADAPTIVE (Fehler)',
                'description': 'Fehler bei Ausführung der adaptiven Strategie',
                'signal_details': f"Fehler: {str(e)}"
            }
            return 0, info


# Globale Instanz der adaptiven Strategie
_adaptive_strategy_instance = None

def get_adaptive_strategy_instance():
    """
    Singleton-Zugriff auf die adaptive Strategie-Instanz.
    
    Returns:
    AdaptiveStrategy: Instanz der adaptiven Strategie
    """
    global _adaptive_strategy_instance
    if _adaptive_strategy_instance is None:
        _adaptive_strategy_instance = AdaptiveStrategy()
    return _adaptive_strategy_instance

def adaptive_strategy(df):
    """
    Wrapper-Funktion für die adaptive Strategie, kompatibel mit dem vorhandenen Strategie-Interface.
    
    Parameters:
    df (pandas.DataFrame): DataFrame mit Marktdaten und berechneten Indikatoren
    
    Returns:
    tuple: (signal, info) mit dem Handelssignal und zusätzlichen Informationen
    """
    try:
        strategy = get_adaptive_strategy_instance()
        return strategy.adaptive_strategy(df)
    except Exception as e:
        utils.log_error(e, "Fehler im globalen adaptiven Strategie-Wrapper")
        info = {
            'strategy': 'ADAPTIVE (kritischer Fehler)',
            'description': 'Unerwarteter Fehler in der adaptiven Strategie',
            'signal_details': f"Fehler: {str(e)}"
        }
        return 0, info
    
def save_strategy_changes(self):
    """Speichert Strategiewechsel in eine CSV-Datei"""
    try:
        if not self.strategy_changes:
            return
            
        # Konvertiere die Liste zu einem DataFrame
        changes_df = pd.DataFrame(self.strategy_changes)
        
        # Speichere in CSV - mit 'a' für append-Modus
        if os.path.exists(config.STRATEGY_CHANGES_FILE):
            # Wenn die Datei existiert, anhängen ohne Header
            changes_df.to_csv(config.STRATEGY_CHANGES_FILE, mode='a', header=False, index=False)
        else:
            # Wenn die Datei nicht existiert, neu erstellen mit Header
            changes_df.to_csv(config.STRATEGY_CHANGES_FILE, index=False)
            
        # Liste leeren, um doppelte Einträge zu vermeiden
        self.strategy_changes = []
        
    except Exception as e:
        utils.log_error(e, "Fehler beim Speichern der Strategiewechsel")
        
    except Exception as e:
        utils.log_error(e, "Fehler beim Speichern der Strategiewechsel")