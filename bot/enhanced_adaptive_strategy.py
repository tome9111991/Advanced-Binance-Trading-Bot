import pandas as pd
import numpy as np
from datetime import datetime
from colorama import Fore, Style
import utils
import os
import config
from advanced_market_analysis import AdvancedMarketAnalysis, RiskAdjuster

class EnhancedAdaptiveStrategy:
    """
    Verbesserte adaptive Meta-Strategie, die dynamisch die beste Trading-Strategie für
    aktuelle Marktbedingungen auswählt und anwendet.
    
    Diese Version integriert fortgeschrittene Marktanalyse, Mustererkennung und
    dynamische Risikoanpassung.
    """
    
    def __init__(self, lookback_period=20):
        """
        Initialisiert die erweiterte adaptive Strategie.
        
        Parameters:
        lookback_period (int): Anzahl der vergangenen Perioden zur Bewertung von Strategien
        """
        self.lookback_period = lookback_period
        self.market_analyzer = AdvancedMarketAnalysis()
        self.risk_adjuster = RiskAdjuster(base_risk_per_trade=config.MAX_RISK_PER_TRADE)
        
        # Strategie-Tracking
        self.current_strategy = None    # Aktuell ausgewählte Strategie
        self.strategy_performance = {}  # Speichert Performance-Metriken für jede Strategie
        
        # Historisches Tracking
        self.historical_signals = []
        self.historical_results = []
        self.historical_regimes = []
        
        # Tracking der Wechsel
        self.strategy_changes = []
        self.consecutive_same_strategy = 0
        
        # Verfügbare Strategien und ihre Funktionsverweise
        # Wird beim ersten Aufruf von setup_strategies initialisiert
        self.available_strategies = {
            'SMA_CROSSOVER': None,
            'RSI': None,
            'MACD': None,
            'BOLLINGER_BANDS': None,
            'MULTI_INDICATOR': None
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
    
    def evaluate_strategy_performance(self, df):
        """
        Bewertet die Performance der einzelnen Strategien in der aktuellen Marktphase.
        
        Parameters:
        df (pandas.DataFrame): DataFrame mit Marktdaten und berechneten Indikatoren
        
        Returns:
        dict: Dictionary mit Bewertungen für jede Strategie
        """
        if len(df) < self.lookback_period + 5:  # Benötigen Rückschaudaten plus etwas Puffer
            # Nicht genügend Daten, Standard-Gewichte verwenden
            return {strat: 0.5 for strat in self.available_strategies}
        
        evaluations = {}
        
        # Erweiterte Performance-Evaluierung mit mehreren Metriken
        for strategy_name, strategy_func in self.available_strategies.items():
            if strategy_func is None:
                self.setup_strategies()
                strategy_func = self.available_strategies[strategy_name]
            
            # Berechne Signale und simulierte Renditen für die letzten N Perioden
            signals = []
            returns = []
            position = 0
            
            for i in range(self.lookback_period):
                # Erstelle ein temporäres DataFrame bis zum aktuellen Index für historische Simulation
                hist_index = -(self.lookback_period + 5) + i
                temp_df = df.iloc[:hist_index].copy() if hist_index < -1 else df.iloc[:-1].copy()
                
                # Generiere Signal für diese historische Periode
                signal, _ = strategy_func(temp_df)
                signals.append(signal)
                
                # Position aktualisieren basierend auf Signal
                if signal == 1 and position <= 0:  # Kaufsignal
                    position = 1
                elif signal == -1 and position >= 0:  # Verkaufssignal
                    position = -1
                
                # Berechne Rendite für diese Periode
                if i > 0:  # Überspringen der ersten Periode, da wir die Rendite basierend auf vorherigem Signal berechnen
                    price_prev = df['close'].iloc[-(self.lookback_period + 5) + i - 1]
                    price_curr = df['close'].iloc[-(self.lookback_period + 5) + i]
                    period_return = (price_curr - price_prev) / price_prev
                    
                    # Rendite basierend auf Position
                    strategy_return = position * period_return
                    returns.append(strategy_return)
            
            # Berechne verschiedene Performance-Metriken
            if len(returns) > 0:
                # 1. Gesamtrendite
                cumulative_return = np.sum(returns)
                
                # 2. Sharpe Ratio (vereinfacht)
                avg_return = np.mean(returns)
                std_return = np.std(returns) if len(returns) > 1 else 0.01
                sharpe = avg_return / std_return if std_return > 0 else 0
                
                # 3. Max Drawdown
                cum_returns = np.cumsum(returns)
                running_max = np.maximum.accumulate(cum_returns)
                drawdown = running_max - cum_returns
                max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
                
                # 4. Win Rate
                win_rate = np.sum([r > 0 for r in returns]) / len(returns) if returns else 0
                
                # 5. Profit Factor
                gross_profit = np.sum([r for r in returns if r > 0]) or 0.0001  # Vermeide Division durch Null
                gross_loss = abs(np.sum([r for r in returns if r < 0])) or 0.0001
                profit_factor = gross_profit / gross_loss
                
                # Kombiniere Metriken mit Gewichtungen
                score = (
                    0.3 * cumulative_return +
                    0.2 * sharpe +
                    0.2 * (1 - max_drawdown) +  # Niedrigerer Drawdown ist besser
                    0.2 * win_rate +
                    0.1 * profit_factor
                )
                
                # Normalisiere Score
                score = max(0.1, min(1.0, score + 0.5))  # +0.5 als Offset für vernünftige Werte
            else:
                score = 0.5  # Neutraler Wert, wenn keine Daten
            
            evaluations[strategy_name] = score
            
            # Speichere detaillierte Performance für Logging
            self.strategy_performance[strategy_name] = {
                'cumulative_return': cumulative_return if 'cumulative_return' in locals() else 0,
                'sharpe': sharpe if 'sharpe' in locals() else 0,
                'max_drawdown': max_drawdown if 'max_drawdown' in locals() else 0,
                'win_rate': win_rate if 'win_rate' in locals() else 0,
                'profit_factor': profit_factor if 'profit_factor' in locals() else 0,
                'score': score
            }
        
        return evaluations
    
    def select_best_strategy(self, df):
        """
        Wählt die beste Strategie für die aktuellen Marktbedingungen aus.
        
        Parameters:
        df (pandas.DataFrame): DataFrame mit Marktdaten und berechneten Indikatoren
        
        Returns:
        str: Name der ausgewählten Strategie
        dict: Umfassende Analyseergebnisse
        """
        # Führe fortgeschrittene Marktanalyse durch
        market_analysis = self.market_analyzer.analyze(df)
        
        # Hole empfohlene Strategiegewichtungen basierend auf der Marktanalyse
        market_regime = market_analysis['regime']
        strategy_weights = market_analysis['recommended_strategy_weights']
        
        # Bewerte die tatsächliche Performance der Strategien in der jüngsten Vergangenheit
        performance_scores = self.evaluate_strategy_performance(df)
        
        # Kombiniere Marktregime-Empfehlung und tatsächliche Performance
        combined_scores = {}
        for strategy in self.available_strategies:
            # Gewichtung: 60% tatsächliche Performance, 40% Regime-Empfehlung
            score = 0.6 * performance_scores.get(strategy, 0.5) + 0.4 * strategy_weights.get(strategy, 0.5)
            combined_scores[strategy] = score
        
        # Beste Strategie auswählen
        best_strategy = max(combined_scores.items(), key=lambda x: x[1])[0]
        
        # Vermeidung von zu häufigen Strategiewechseln - Hystereseeffekt
        if self.current_strategy and best_strategy != self.current_strategy:
            # Benötige deutlich bessere Performance für einen Wechsel
            if combined_scores[best_strategy] < combined_scores.get(self.current_strategy, 0) + 0.15:
                best_strategy = self.current_strategy
                self.consecutive_same_strategy += 1
            else:
                # Protokolliere den Strategiewechsel
                self.strategy_changes.append({
                    'time': datetime.now(),
                    'from': self.current_strategy,
                    'to': best_strategy,
                    'market_regime': market_regime,
                    'reason': f"Neue Strategie ist {(combined_scores[best_strategy] - combined_scores.get(self.current_strategy, 0)) * 100:.1f}% besser"
                })
                self.consecutive_same_strategy = 0
        elif self.current_strategy and best_strategy == self.current_strategy:
            self.consecutive_same_strategy += 1
        else:
            self.consecutive_same_strategy = 0
        
        # Speichere die aktuelle Strategie
        self.current_strategy = best_strategy
        
        # Log von Strategie-Scores für Debugging
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Strategie-Auswahl (Marktregime: {market_regime}):{Style.RESET_ALL}")
        
        # Sortiere Strategien nach Score für bessere Lesbarkeit
        sorted_strategies = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        for strategy, score in sorted_strategies:
            selected_marker = " ◀ AUSGEWÄHLT" if strategy == best_strategy else ""
            perf_detail = self.strategy_performance.get(strategy, {})
            
            # Detailliertere Ausgabe für besseres Verständnis
            performance_details = f" | Return: {perf_detail.get('cumulative_return', 0):.2%}"
            performance_details += f" | Sharpe: {perf_detail.get('sharpe', 0):.2f}"
            performance_details += f" | Win Rate: {perf_detail.get('win_rate', 0):.2%}"
            
            print(f"  {strategy}: {score:.2f}{selected_marker}{performance_details}")
        
        # Risikoanalyse basierend auf aktuellen Marktbedingungen
        risk_analysis = self.risk_adjuster.adjust_risk(market_analysis)
        
        # Füge Risikoanpassung zu den Analyseergebnissen hinzu
        market_analysis['risk_adjustments'] = risk_analysis

        # Speichere die aktuelle Strategie
        self.current_strategy = best_strategy

        # Speichere Strategiewechsel, wenn konfiguriert
        if config.SAVE_STRATEGY_CHANGES and self.strategy_changes:
            self.save_strategy_changes()

            # Log von Strategie-Scores für Debugging
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Strategie-Auswahl (Marktregime: {market_regime}):{Style.RESET_ALL}")
        
        return best_strategy, market_analysis
    
    def enhanced_adaptive_strategy(self, df):
        """
        Implementierung der verbesserten adaptiven Strategie.
        
        Parameters:
        df (pandas.DataFrame): DataFrame mit Marktdaten und berechneten Indikatoren
        
        Returns:
        tuple: (signal, info) mit dem Handelssignal und zusätzlichen Informationen
        """
        # Initialisiere Strategien, falls noch nicht geschehen
        if None in self.available_strategies.values():
            self.setup_strategies()
        
        # Beste Strategie für aktuelle Marktbedingungen auswählen
        best_strategy, market_analysis = self.select_best_strategy(df)
        strategy_func = self.available_strategies[best_strategy]
        
        # Signal von der ausgewählten Strategie generieren
        signal, strategy_info = strategy_func(df)
        
        # Speichere Marktregime für historische Analyse
        self.historical_regimes.append(market_analysis['regime'])
        
        # Zusätzliche Informationen für die adaptive Strategie
        info = {
            'strategy': 'ENHANCED_ADAPTIVE',
            'description': 'Dynamische, marktregimebasierte Strategieauswahl mit erweiterter Marktanalyse',
            'parameters': f'Lookback-Periode: {self.lookback_period}, Regime: {market_analysis["regime"]}',
            'selected_strategy': best_strategy,
            'market_regime': market_analysis['regime'],
            'regime_description': market_analysis['regime_description'],
            'confidence': market_analysis['confidence'],
            'signal_details': strategy_info.get('signal_details', 'Keine Details verfügbar'),
            'analysis': f"Aktuelle Strategie: {best_strategy.upper()} | Marktregime: {market_analysis['regime'].upper()} | Konfidenz: {market_analysis['confidence']:.2f}",
            
            # Erkannte Muster
            'patterns': market_analysis.get('patterns', {}),
            
            # Volumenanalyse
            'volume_pressure': market_analysis.get('volume', {}).get('volume_pressure', 'unknown'),
            
            # Angepasste Risikoparameter
            'risk_adjustments': market_analysis.get('risk_adjustments', {}),
            
            # Einzelstrategien für Debug-Zwecke
            'strategy_performance': self.strategy_performance,
            
            # Originalstrategie-Info für Referenz
            'original_strategy_info': strategy_info
        }
        
        # Risikoanpassung anwenden (wenn konfiguriert)
        if market_analysis.get('risk_adjustments'):
            info['adjusted_risk_per_trade'] = market_analysis['risk_adjustments'].get('risk_per_trade', config.MAX_RISK_PER_TRADE)
            info['adjusted_stop_loss'] = market_analysis['risk_adjustments'].get('stop_loss_percent', config.STOP_LOSS_PERCENT)
            info['adjusted_take_profit'] = market_analysis['risk_adjustments'].get('take_profit_percent', config.TAKE_PROFIT_PERCENT)
        
        return signal, info


# Globale Instanz der verbesserten adaptiven Strategie
_enhanced_adaptive_strategy_instance = None

def get_enhanced_adaptive_strategy_instance():
    """
    Singleton-Zugriff auf die verbesserte adaptive Strategie-Instanz.
    
    Returns:
    EnhancedAdaptiveStrategy: Instanz der verbesserten adaptiven Strategie
    """
    global _enhanced_adaptive_strategy_instance
    if _enhanced_adaptive_strategy_instance is None:
        _enhanced_adaptive_strategy_instance = EnhancedAdaptiveStrategy(
            lookback_period=config.ADAPTIVE_LOOKBACK_PERIOD
        )
    return _enhanced_adaptive_strategy_instance

def enhanced_adaptive_strategy(df):
    """
    Wrapper-Funktion für die verbesserte adaptive Strategie, kompatibel mit dem vorhandenen Strategie-Interface.
    
    Parameters:
    df (pandas.DataFrame): DataFrame mit Marktdaten und berechneten Indikatoren
    
    Returns:
    tuple: (signal, info) mit dem Handelssignal und zusätzlichen Informationen
    """
    strategy = get_enhanced_adaptive_strategy_instance()
    return strategy.enhanced_adaptive_strategy(df)

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