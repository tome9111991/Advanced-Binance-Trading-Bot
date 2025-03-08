import os
import pandas as pd
import numpy as np
from datetime import datetime
from colorama import Fore, Style
import utils
import config
from advanced_market_analysis import AdvancedMarketAnalysis, RiskAdjuster

class SmallCapitalAdaptiveStrategy:
    """
    Eine angepasste adaptive Strategie, optimiert für Spot Trading mit geringem Kapital.
    
    Diese Strategie kombiniert fortgeschrittene Marktanalyse mit konservativem Risikomanagement
    und berücksichtigt die besonderen Anforderungen beim Trading mit kleinem Kapital.
    """
    
    def __init__(self, lookback_period=15):
        """
        Initialisiert die Strategie für kleines Kapital.
        
        Parameters:
        lookback_period (int): Anzahl der vergangenen Perioden zur Bewertung von Strategien
                              (reduziert für schnellere Anpassung bei kleinem Kapital)
        """
        self.lookback_period = lookback_period
        self.market_analyzer = AdvancedMarketAnalysis()
        
        # Angepasster Risk Adjuster mit niedrigerem Basisrisiko
        self.risk_adjuster = RiskAdjuster(base_risk_per_trade=0.01)  # Reduziert auf 1% pro Trade
        
        # Strategie-Tracking
        self.current_strategy = None
        self.strategy_performance = {}
        
        # Historisches Tracking
        self.historical_signals = []
        self.historical_results = []
        self.historical_regimes = []
        
        # Tracking der Wechsel
        self.strategy_changes = []
        self.consecutive_same_strategy = 0
        
        # Transaktionskostenschwelle - minimale erwartete Rendite, um Gebühren zu rechtfertigen
        self.min_expected_return = 0.0035  # 0.35% Mindestrendite für einen Trade
        
        # Verfügbare Strategien und ihre Funktionsverweise
        self.available_strategies = {
            'SMA_CROSSOVER': None,
            'RSI': None,
            'MACD': None,
            'BOLLINGER_BANDS': None,
            'MULTI_INDICATOR': None
        }
        
        # Strategie-Bias für kleine Konten (bevorzugt konservativere Strategien)
        self.small_capital_weights = {
            'SMA_CROSSOVER': 1.2,    # Höhere Gewichtung (trendfolgend, gut für bullische Märkte)
            'RSI': 1.3,              # Höhere Gewichtung (konservativ, überverkauft/überkauft)
            'MACD': 1.0,             # Neutrale Gewichtung
            'BOLLINGER_BANDS': 1.4,  # Höchste Gewichtung (mean reversion, funktioniert gut in Seitwärtsmärkten)
            'MULTI_INDICATOR': 1.1   # Leicht erhöhte Gewichtung (Diversifikation)
        }
        
        # Positionsgrößen-Manager für kleine Konten
        self.min_trade_size = 0.0005  # Minimale Trade-Größe für BTC
        self.max_allocation_percent = 0.40  # Maximale Allokation des Kapitals pro Trade (40%)
        
        # Initialisierung von Attributen, die später verwendet werden
        self.last_market_analysis = None
        self.last_buy_price = 0
        self.last_sell_price = 0
        self.trade_count = 0
        self.profitable_trades = 0
        self.last_trade_time = None
        self.last_trade_type = None
    
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
        Bewertet die Performance der einzelnen Strategien mit Fokus auf Kapitaleffizienz.
        
        Parameters:
        df (pandas.DataFrame): DataFrame mit Marktdaten und berechneten Indikatoren
        
        Returns:
        dict: Dictionary mit Bewertungen für jede Strategie
        """
        if len(df) < self.lookback_period + 5:
            return {strat: 0.5 for strat in self.available_strategies}
        
        evaluations = {}
        
        for strategy_name, strategy_func in self.available_strategies.items():
            if strategy_func is None:
                self.setup_strategies()
                strategy_func = self.available_strategies[strategy_name]
            
            # Berechne Signale und simulierte Renditen für die letzten N Perioden
            signals = []
            returns = []
            position = 0
            
            for i in range(self.lookback_period):
                hist_index = -(self.lookback_period + 5) + i
                temp_df = df.iloc[:hist_index].copy() if hist_index < -1 else df.iloc[:-1].copy()
                
                signal, _ = strategy_func(temp_df)
                signals.append(signal)
                
                # Position aktualisieren basierend auf Signal (nur Long für Spot)
                if signal == 1 and position == 0:  # Kaufsignal wenn keine Position
                    position = 1
                elif signal == -1 and position == 1:  # Verkaufssignal wenn Long-Position
                    position = 0
                
                # Berechne Rendite für diese Periode
                if i > 0 and position == 1:  # Nur für Long-Positionen (Spot Trading)
                    price_prev = df['close'].iloc[-(self.lookback_period + 5) + i - 1]
                    price_curr = df['close'].iloc[-(self.lookback_period + 5) + i]
                    period_return = (price_curr - price_prev) / price_prev
                    
                    # Berücksichtige Transaktionskosten bei Positionswechseln
                    if signals[i-1] == 1 and signals[i-2] != 1:  # Einstieg in letzter Periode
                        period_return -= 0.001  # Abzug für Eintrittgebühr (0.1%)
                    
                    strategy_return = period_return
                    returns.append(strategy_return)
                elif i > 0 and position == 0 and signals[i-1] == -1 and signals[i-2] == 1:
                    # Berücksichtige Ausstiegsgebühr beim Verkauf
                    returns.append(-0.001)  # Abzug für Austrittsgebühr (0.1%)
            
            # Berechne Performance-Metriken speziell für kleine Konten
            if len(returns) > 0:
                # 1. Nettorendite nach Gebühren
                cumulative_return = np.sum(returns)
                
                # 2. Angepasste Sharpe Ratio
                avg_return = np.mean(returns)
                std_return = np.std(returns) if len(returns) > 1 else 0.01
                sharpe = avg_return / std_return if std_return > 0 else 0
                
                # 3. Capital Efficiency Ratio - wie viel Kapital gebunden wird vs. Rendite
                trade_frequency = np.sum([1 for i in range(1, len(signals)) if signals[i] != signals[i-1]])
                capital_efficiency = cumulative_return / (trade_frequency * 0.1 + 1) if trade_frequency > 0 else 0
                
                # 4. Win Rate angepasst an kleine Konten - berücksichtigt auch Gebühren
                win_rate = np.sum([r > self.min_expected_return for r in returns]) / len(returns) if returns else 0
                
                # 5. Drawdown und Recovery
                cum_returns = np.cumsum(returns)
                running_max = np.maximum.accumulate(cum_returns)
                drawdown = running_max - cum_returns
                max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
                
                # Kombiniere Metriken mit angepasster Gewichtung für kleine Konten
                score = (
                    0.35 * cumulative_return +          # Höhere Gewichtung für Gesamtrendite
                    0.15 * sharpe +                     # Risikoadjustierte Rendite
                    0.20 * capital_efficiency +         # Kapitaleffizienz
                    0.20 * win_rate +                   # Trefferquote
                    0.10 * (1 - max_drawdown)           # Drawdown-Minimierung
                )
                
                # Wende Small-Capital-Bias an
                score *= self.small_capital_weights.get(strategy_name, 1.0)
                
                # Normalisiere Score
                score = max(0.1, min(1.0, score + 0.5))
            else:
                score = 0.5
            
            evaluations[strategy_name] = score
            
            # Speichere detaillierte Performance für Logging
            self.strategy_performance[strategy_name] = {
                'cumulative_return': cumulative_return if 'cumulative_return' in locals() else 0,
                'sharpe': sharpe if 'sharpe' in locals() else 0,
                'max_drawdown': max_drawdown if 'max_drawdown' in locals() else 0,
                'win_rate': win_rate if 'win_rate' in locals() else 0,
                'capital_efficiency': capital_efficiency if 'capital_efficiency' in locals() else 0,
                'score': score
            }
        
        return evaluations
    
    def select_best_strategy(self, df):
        """
        Wählt die beste Strategie für aktuelle Marktbedingungen mit Fokus auf klein Kapital.
        
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
            # Gewichtung für kleine Konten: 50% Performance, 30% Regime-Eignung, 20% Small-Capital-Bias
            score = (
                0.5 * performance_scores.get(strategy, 0.5) + 
                0.3 * strategy_weights.get(strategy, 0.5) +
                0.2 * (self.small_capital_weights.get(strategy, 1.0) - 1.0) / 0.4  # Normalisiert auf 0-1
            )
            combined_scores[strategy] = score
        
        # Prüfe auf bearishe Märkte - konservativer handeln
        if 'downtrend' in market_regime or market_analysis.get('volume', {}).get('volume_pressure') == 'strong_selling':
            # Senke alle Scores ab, um weniger zu handeln in fallenden Märkten
            combined_scores = {k: v * 0.8 for k, v in combined_scores.items()}
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Bärischer Markt erkannt - konservative Handelseinstellung aktiviert.{Style.RESET_ALL}")
        
        # Beste Strategie auswählen
        best_strategy = max(combined_scores.items(), key=lambda x: x[1])[0]
        
        # Hystereseeffekt - vermeidet zu häufige Strategiewechsel, die für kleine Konten teuer sind
        if self.current_strategy and best_strategy != self.current_strategy:
            # Benötige deutlich bessere Performance für einen Wechsel (20% Verbesserung)
            if combined_scores[best_strategy] < combined_scores.get(self.current_strategy, 0) + 0.20:
                best_strategy = self.current_strategy
                self.consecutive_same_strategy += 1
            else:
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
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Strategie-Auswahl für kleines Kapital (Marktregime: {market_regime}):{Style.RESET_ALL}")
        
        # Sortiere Strategien nach Score für bessere Lesbarkeit
        sorted_strategies = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        for strategy, score in sorted_strategies:
            selected_marker = " ◀ AUSGEWÄHLT" if strategy == best_strategy else ""
            perf_detail = self.strategy_performance.get(strategy, {})
            
            # Detailliertere Ausgabe
            performance_details = f" | Return: {perf_detail.get('cumulative_return', 0):.2%}"
            performance_details += f" | Win Rate: {perf_detail.get('win_rate', 0):.2%}"
            performance_details += f" | Kap.Effizienz: {perf_detail.get('capital_efficiency', 0):.2f}"
            
            print(f"  {strategy}: {score:.2f}{selected_marker}{performance_details}")
        
        # Risikoanalyse basierend auf aktuellen Marktbedingungen für kleine Konten
        risk_analysis = self.risk_adjuster.adjust_risk(market_analysis)
        
        # Zusätzliche Risikoanpassung für kleine Konten
        risk_analysis['risk_per_trade'] = min(risk_analysis['risk_per_trade'], 0.015)  # Max 1.5% Risiko pro Trade
        
        # Anpassung der Stop-Loss und Take-Profit-Verhältnisse für bessere R:R-Ratio
        risk_analysis['take_profit_percent'] = risk_analysis['stop_loss_percent'] * 2.5  # Ziel: 2.5:1 Reward/Risk
        
        # Füge Risikoanpassung zu den Analyseergebnissen hinzu
        market_analysis['risk_adjustments'] = risk_analysis
        
        # Berechne Positionsgrößenempfehlung für kleine Konten
        balance_info = {
            'recommended_position_pct': min(self.max_allocation_percent, 
                                        risk_analysis['risk_per_trade'] * 8),  # Risiko * 8 als generelle Allokation
            'min_trade_size': self.min_trade_size
        }
        market_analysis['balance_allocation'] = balance_info
        
        # Speichere die aktuelle Strategie
        self.current_strategy = best_strategy

        # Speichere Strategiewechsel, wenn konfiguriert
        if config.SAVE_STRATEGY_CHANGES and self.strategy_changes:
            self.save_strategy_changes()

            # Log von Strategie-Scores für Debugging
        print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Strategie-Auswahl (Marktregime: {market_regime}):{Style.RESET_ALL}")
        
        return best_strategy, market_analysis
    
    def calculate_small_capital_position_size(self, balance, current_price, entry_price=None):
        """
        Berechnet optimale Positionsgröße für kleine Konten mit Fokus auf Kapitaleffizienz.
        
        Parameters:
        balance (float): Verfügbares Guthaben in USDT
        current_price (float): Aktueller BTC-Preis
        entry_price (float, optional): Einstiegspreis für bestehende Positionen
        
        Returns:
        float: Empfohlene Positionsgröße in BTC
        """
        # Minimale und maximale Position je nach Kontostand
        min_position_size = self.min_trade_size  # 0.0005 BTC Minimum
        
        # Berechne maximalen Prozentsatz basierend auf Kontostand
        # Kleinere Konten haben höhere Allokationsprozentsätze, um überhaupt handeln zu können
        max_allocation_pct = self.max_allocation_percent
        if balance < 100:
            max_allocation_pct = min(0.6, max_allocation_pct * 1.5)  # Bis zu 60% für sehr kleine Konten
        
        # Maximale Position basierend auf Guthaben
        max_position_size = (balance * max_allocation_pct) / current_price
        
        # Berechne Standard-Positionsgröße basierend auf aktuellem Risiko
        std_position_size = (balance * 0.3) / current_price  # 30% als Standard-Ausgangspunkt
        
        # Berücksichtige Marktvolatilität (falls verfügbar)
        if hasattr(self, 'last_market_analysis') and 'regime' in self.last_market_analysis:
            regime = self.last_market_analysis['regime']
            # Reduziere Position in volatilen Märkten
            if 'high_volatility' in regime or 'strong_downtrend' in regime:
                std_position_size *= 0.6  # 40% Reduktion
            # Erhöhe Position in stabilen, aufwärts Märkten
            elif 'strong_uptrend' in regime:
                std_position_size *= 1.2  # 20% Erhöhung (aber immer noch unter max_allocation_pct)
        
        # Stelle sicher, dass Position zwischen Minimum und Maximum liegt
        position_size = max(min_position_size, min(std_position_size, max_position_size))
        
        # Runde auf 5 Dezimalstellen (minimale BTC-Einheit bei Binance)
        position_size = round(position_size, 5)
        
        print(f"{Fore.CYAN}[{datetime.now().strftime('%H:%M:%S')}] Positionsgröße für kleines Kapital: {position_size} BTC "
              f"({position_size * current_price:.2f} USDT, {position_size * current_price / balance * 100:.1f}% des Guthabens){Style.RESET_ALL}")
        
        return position_size

    def should_execute_trade(self, signal, current_price, balance, regime=None):
        """
        Entscheidet, ob ein Trade ausgeführt werden soll, basierend auf Signalstärke und Marktbedingungen.
        Mit optimierten, adaptiven Schwellenwerten.
        
        Parameters:
        signal (int): Handelssignal (-1, 0, 1)
        current_price (float): Aktueller Preis
        balance (float): Verfügbares Guthaben
        regime (str, optional): Aktuelles Marktregime
        
        Returns:
        bool: True wenn Trade ausgeführt werden soll, sonst False
        str: Grund für die Entscheidung
        """
        if signal == 0:
            return False, "Kein Signal"
        
        # Adaptiver Mindestkontostand basierend auf aktuellem Preis
        # Für kleine Konten wichtig, um Mindesthandelsgrößen zu berücksichtigen
        min_trade_size_btc = 0.0005  # Beispiel für Binance Minimum
        min_balance_threshold = min_trade_size_btc * current_price * 1.05  # 5% Puffer
        
        if balance < min_balance_threshold:
            return False, f"Guthaben zu niedrig ({balance:.2f} USDT < {min_balance_threshold:.2f} USDT)"
        
        # Marktregime-basierte Entscheidungslogik mit adaptiven Schwellenwerten
        market_condition_scores = {
            'strong_uptrend': 0.9,    # Sehr günstig für Käufe
            'weak_uptrend': 0.7,      # Günstig für Käufe
            'ranging_narrow': 0.6,    # Moderat günstig für beide Richtungen
            'ranging_wide': 0.5,      # Neutral
            'weak_downtrend': 0.3,    # Ungünstig für Käufe
            'strong_downtrend': 0.1,  # Sehr ungünstig für Käufe
            'high_volatility': 0.4,   # Vorsicht geboten
            'low_volatility': 0.8,    # Günstig für Ausbruchsignale
            'breakout_potential': 0.8 # Günstig für Richtungssignale
        }
        
        # Standardwert, wenn kein Regime angegeben
        market_score = market_condition_scores.get(regime, 0.5) if regime else 0.5
        
        # Berechne Zeitabstand zum letzten Trade, um Overtrading zu vermeiden
        time_factor = 1.0
        if hasattr(self, 'last_trade_time') and self.last_trade_time:
            hours_since_last_trade = (datetime.now() - self.last_trade_time).total_seconds() / 3600
            # Adaptive Zeitsperre basierend auf Marktbedingungen
            required_hours = 2 if market_score > 0.7 else (1 if market_score > 0.5 else 4)
            
            if hours_since_last_trade < required_hours:
                time_factor = hours_since_last_trade / required_hours
                if time_factor < 0.5:  # Weniger als die Hälfte der erforderlichen Zeit
                    return False, f"Zu kurze Zeit seit letztem Trade ({hours_since_last_trade:.1f}h < {required_hours}h)"
        
        # Signalstärke-Bewertung
        signal_strength = 0.0
        
        # Prüfe Performance aller Strategien für Signalbestätigung
        if hasattr(self, 'strategy_performance'):
            # Berechne durchschnittlichen Score über alle Strategien
            avg_strategy_score = np.mean([perf.get('score', 0.5) for perf in self.strategy_performance.values()])
            # Berechne Übereinstimmung des aktuellen Signals mit anderen Strategien
            signal_agreement = sum(1 for perf in self.strategy_performance.values() 
                                 if (signal > 0 and perf.get('cumulative_return', 0) > 0) or
                                    (signal < 0 and perf.get('cumulative_return', 0) < 0))
            
            # Normalisiere auf 0-1
            signal_agreement = signal_agreement / max(1, len(self.strategy_performance))
            
            # Kombiniere zu Signalstärke
            signal_strength = 0.7 * avg_strategy_score + 0.3 * signal_agreement
        else:
            signal_strength = 0.5  # Neutrale Stärke, wenn keine Performance-Daten verfügbar
            
        # Prüfe auf Preisniveaus für DCA/Profit-Taking mit adaptiven Schwellenwerten
        if hasattr(self, 'last_buy_price') and self.last_buy_price > 0:
            price_change = (current_price - self.last_buy_price) / self.last_buy_price
            
            # Adaptive Schwellenwerte basierend auf Marktbedingungen
            if signal > 0:  # Kaufsignal
                # Für Käufe: Preis sollte niedriger sein als vorheriger Kauf (DCA)
                dca_threshold = -0.02 if market_score > 0.7 else -0.05
                
                if price_change > 0.01 and market_score < 0.7:
                    return False, f"Preis {price_change*100:.1f}% höher als letzter Kauf, warte auf besseren Einstieg"
                
                if price_change < dca_threshold:
                    # DCA bei niedrigerem Preis ist gut
                    return True, f"DCA-Gelegenheit bei {price_change*100:.1f}% unter letztem Kauf"
            
            elif signal < 0:  # Verkaufssignal
                # Adaptive Profit-Taking-Schwellen
                min_profit = 0.02 if market_score > 0.7 else 0.035
                
                if price_change > min_profit:
                    return True, f"Take Profit bei {price_change*100:.1f}%"
                
                # Adaptiver Stop-Loss basierend auf Marktbedingungen
                stop_loss_threshold = -0.03 if market_score > 0.5 else -0.02
                
                if price_change < stop_loss_threshold:
                    return True, f"Stop Loss bei {price_change*100:.1f}%"
                
                # Bei moderatem Verlust und schlechten Marktbedingungen trotzdem verkaufen
                if price_change < 0 and market_score < 0.3:
                    return True, f"Verkauf bei leichtem Verlust ({price_change*100:.1f}%) wegen ungünstiger Marktbedingungen"
                    
                # Bei geringem Gewinn/Verlust und niedrigem Signal lieber halten
                if abs(price_change) < 0.015 and signal_strength < 0.6:
                    return False, "Ignoriere Verkaufssignal bei geringem Gewinn/Verlust und schwachem Signal"
        
        # Finale Entscheidung basierend auf kombinierten Faktoren
        decision_score = (0.4 * market_score + 0.4 * signal_strength + 0.2 * time_factor)
        
        # Unterschiedliche Schwellenwerte für Kauf- und Verkaufssignale
        threshold = 0.6 if signal > 0 else 0.5  # Höhere Schwelle für Käufe
        
        # Überprüfung auf extrem ungünstige Marktbedingungen (überschreibt alles)
        if signal > 0 and regime in ['strong_downtrend', 'high_volatility'] and signal_strength < 0.8:
            return False, f"Kaufsignal ignoriert wegen ungünstiger Marktbedingungen ({regime})"
        
        if decision_score >= threshold:
            return True, f"Signal bestätigt (Score: {decision_score:.2f})"
        else:
            return False, f"Signal zu schwach (Score: {decision_score:.2f} < {threshold})"
    
    def smart_small_capital_strategy(self, df, actual_balance=None):
        """
        Implementierung der optimierten Strategie für kleines Kapital.
        
        Parameters:
        df (pandas.DataFrame): DataFrame mit Marktdaten und berechneten Indikatoren
        actual_balance (float, optional): Tatsächlicher Kontostand. Wenn None, wird ein Standardwert verwendet
        
        Returns:
        tuple: (signal, info) mit dem Handelssignal und zusätzlichen Informationen
        """
        # Initialisiere Strategien, falls noch nicht geschehen
        if None in self.available_strategies.values():
            self.setup_strategies()
        
        # Standardwert für Balance, falls nicht angegeben
        if actual_balance is None:
            actual_balance = 100  # Vorsichtiger Standardwert
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Warnung: Kein Kontostand übermittelt. Verwende Standardwert: {actual_balance} USDT{Style.RESET_ALL}")
        
        # Beste Strategie für aktuelle Marktbedingungen auswählen
        best_strategy, market_analysis = self.select_best_strategy(df)
        strategy_func = self.available_strategies[best_strategy]
        
        # Signal von der ausgewählten Strategie generieren
        signal, strategy_info = strategy_func(df)
        
        # Speichere Marktregime und Analyse für spätere Verwendung
        self.last_market_analysis = market_analysis
        self.historical_regimes.append(market_analysis['regime'])
        
        # Prüfe, ob der Trade ausgeführt werden sollte
        execute_trade, reason = self.should_execute_trade(
            signal, 
            df['close'].iloc[-1], 
            balance=actual_balance,  # Tatsächlichen Kontostand verwenden
            regime=market_analysis['regime']
        )
        
        # Passe Signal an, falls der Trade nicht ausgeführt werden sollte
        if not execute_trade:
            original_signal = signal
            signal = 0
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Signal ignoriert: {reason}{Style.RESET_ALL}")
        
        # Zusätzliche Informationen für die Strategie
        info = {
            'strategy': 'SMALL_CAPITAL_ADAPTIVE',
            'description': 'Optimierte Strategie für Spot Trading mit kleinem Kapital',
            'parameters': f'Lookback: {self.lookback_period}, Marktregime: {market_analysis["regime"]}',
            'selected_strategy': best_strategy,
            'market_regime': market_analysis['regime'],
            'regime_description': market_analysis['regime_description'],
            'confidence': market_analysis['confidence'],
            'signal_details': strategy_info.get('signal_details', 'Keine Details verfügbar'),
            'execute_decision': execute_trade,
            'decision_reason': reason,
            'analysis': f"Aktuelle Strategie: {best_strategy.upper()} | Marktregime: {market_analysis['regime'].upper()} | Konfidenz: {market_analysis['confidence']:.2f}",
            
            # Erkannte Muster
            'patterns': market_analysis.get('patterns', {}),
            
            # Volumenanalyse
            'volume_pressure': market_analysis.get('volume', {}).get('volume_pressure', 'unknown'),
            
            # Angepasste Risikoparameter
            'risk_adjustments': market_analysis.get('risk_adjustments', {}),
            
            # Positionsgrößenempfehlung
            'balance_allocation': market_analysis.get('balance_allocation', {}),
            
            # Einzelstrategien für Debug-Zwecke
            'strategy_performance': self.strategy_performance,
            
            # Originalstrategie-Info für Referenz
            'original_strategy_info': strategy_info,
            
            # Original Signal vor Anpassung
            'original_signal': original_signal if 'original_signal' in locals() else signal
        }
        
        return signal, info


# Globale Instanz der Strategie für kleines Kapital
_small_capital_strategy_instance = None

def get_small_capital_strategy_instance():
    """
    Singleton-Zugriff auf die Strategie-Instanz für kleines Kapital.
    
    Returns:
    SmallCapitalAdaptiveStrategy: Instanz der optimierten Strategie
    """
    global _small_capital_strategy_instance
    if _small_capital_strategy_instance is None:
        _small_capital_strategy_instance = SmallCapitalAdaptiveStrategy(
            lookback_period=15  # Kürzerer Lookback für schnellere Anpassung
        )
    return _small_capital_strategy_instance

def small_capital_strategy(df):
    """
    Wrapper-Funktion für die Strategie, kompatibel mit dem vorhandenen Strategie-Interface.
    
    Parameters:
    df (pandas.DataFrame): DataFrame mit Marktdaten und berechneten Indikatoren
    
    Returns:
    tuple: (signal, info) mit dem Handelssignal und zusätzlichen Informationen
    """
    strategy = get_small_capital_strategy_instance()
    return strategy.smart_small_capital_strategy(df)

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