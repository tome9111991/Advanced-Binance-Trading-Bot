import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from colorama import Fore, Style
import utils
import config

class SimpleDayTraderStrategy:
    """
    Optimierte Day-Trading-Strategie für kleine Kapitalbeträge.
    Angepasst für die bestehende Codebase ohne zusätzliche Abhängigkeiten.
    """
    
    def __init__(self):
        """
        Initialisiert die optimierte Day-Trading-Strategie.
        Liest Konfigurationsoptionen aus config.py.
        """
        self.last_trade_time = None
        self.last_trade_type = None
        self.last_trade_price = 0
        
        # Parameter aus der Konfiguration lesen (mit Fallbacks für Abwärtskompatibilität)
        try:
            # Schlüsselparameter
            self.signal_threshold = getattr(config, 'DAY_TRADER_SIGNAL_THRESHOLD', 0.65)
            self.min_trade_interval = getattr(config, 'DAY_TRADER_MIN_TRADE_INTERVAL', 300)
            self.daily_profit_target = getattr(config, 'DAY_TRADER_DAILY_PROFIT_TARGET', 0.03)
            self.max_daily_loss = getattr(config, 'DAY_TRADER_MAX_DAILY_LOSS', 0.02)
            
            # Selbstoptimierung
            self.optimization_active = getattr(config, 'DAY_TRADER_OPTIMIZATION_ACTIVE', False)
            self.optimization_interval = getattr(config, 'DAY_TRADER_OPTIMIZATION_INTERVAL', 24)
            
            # Parameter-Bereiche für Selbstoptimierung
            if hasattr(config, 'DAY_TRADER_PARAM_RANGES'):
                self.param_ranges = config.DAY_TRADER_PARAM_RANGES
            else:
                # Standardbereiche falls nicht konfiguriert
                self.param_ranges = {
                    'signal_threshold': [0.6, 0.65, 0.7, 0.75],
                    'min_trade_interval': [240, 300, 360, 420],
                    'daily_profit_target': [0.02, 0.025, 0.03, 0.035],
                    'max_daily_loss': [0.015, 0.02, 0.025, 0.03]
                }
            
            # Log der geladenen Konfiguration
            print(f"{Fore.CYAN}[{datetime.now().strftime('%H:%M:%S')}] Day Trader Strategie initialisiert.")
            if self.optimization_active:
                print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Selbstoptimierung aktiv (Intervall: {self.optimization_interval}h){Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Fehler beim Laden der Day Trader Konfiguration: {str(e)}. Verwende Standardwerte.{Style.RESET_ALL}")
            # Standardwerte verwenden
            self.signal_threshold = 0.65
            self.min_trade_interval = 300
            self.daily_profit_target = 0.03
            self.max_daily_loss = 0.02
            self.optimization_active = False
            self.optimization_interval = 24
            self.param_ranges = {
                'signal_threshold': [0.6, 0.65, 0.7, 0.75],
                'min_trade_interval': [240, 300, 360, 420],
                'daily_profit_target': [0.02, 0.025, 0.03, 0.035],
                'max_daily_loss': [0.015, 0.02, 0.025, 0.03]
            }
        
        # Tracking von Tageswerten
        self.daily_trades = 0
        self.daily_profit = 0
        self.current_day = datetime.now().date()
        
        # Self-Optimization Tracking
        self.last_optimization = None
        self.performance_history = []
    
    def calculate_signal_strength(self, df):
        """
        Berechnet die Signalstärke (zwischen -1 und 1) basierend auf mehreren Faktoren.
        Angepasst, um mit den vorhandenen Indikatoren zu arbeiten.
        """
        if len(df) < 10:
            return 0, "Nicht genügend Daten"
            
        try:
            current_price = df['close'].iloc[-1]
            
            # Kombiniere mehrere Signalquellen
            signal_sources = []
            
            # 1. RSI Signal
            if 'rsi' in df.columns:
                rsi = df['rsi'].iloc[-1]
                rsi_prev = df['rsi'].iloc[-2] if len(df) > 2 else rsi
                rsi_direction = 1 if rsi > rsi_prev else (-1 if rsi < rsi_prev else 0)
                
                # Kaufsignal: Überkauft und steigend
                if rsi < 30 and rsi_direction > 0:
                    signal_sources.append(('rsi_buy', 1.0))
                # Verkaufssignal: Überverkauft und fallend
                elif rsi > 70 and rsi_direction < 0:
                    signal_sources.append(('rsi_sell', -1.0))
                # Schwächere Signale
                elif rsi < 40 and rsi_direction > 0:
                    signal_sources.append(('rsi_buy_weak', 0.5))
                elif rsi > 60 and rsi_direction < 0:
                    signal_sources.append(('rsi_sell_weak', -0.5))
            
            # 2. MACD Signal
            if 'macd' in df.columns and 'macd_signal' in df.columns:
                macd = df['macd'].iloc[-1]
                macd_signal = df['macd_signal'].iloc[-1]
                macd_prev = df['macd'].iloc[-2] if len(df) > 2 else macd
                macd_signal_prev = df['macd_signal'].iloc[-2] if len(df) > 2 else macd_signal
                
                # Frische Kreuzung nach oben (Kaufsignal)
                if macd_prev <= macd_signal_prev and macd > macd_signal:
                    signal_sources.append(('macd_cross_up', 1.0))
                # Frische Kreuzung nach unten (Verkaufssignal)
                elif macd_prev >= macd_signal_prev and macd < macd_signal:
                    signal_sources.append(('macd_cross_down', -1.0))
                # Abstand zwischen MACD und Signallinie
                elif macd > macd_signal:
                    # Je größer der Abstand, desto stärker das Signal
                    distance = min(1.0, (macd - macd_signal) * 20)
                    signal_sources.append(('macd_above', distance * 0.5))
                elif macd < macd_signal:
                    distance = min(1.0, (macd_signal - macd) * 20)
                    signal_sources.append(('macd_below', -distance * 0.5))
            
            # 3. Bollinger Bands
            if 'bb_upper' in df.columns and 'bb_lower' in df.columns and 'bb_middle' in df.columns:
                upper = df['bb_upper'].iloc[-1]
                lower = df['bb_lower'].iloc[-1]
                middle = df['bb_middle'].iloc[-1]
                
                # Überverkauft (unter unterem Band)
                if current_price < lower:
                    # Je weiter unter dem Band, desto stärker das Signal
                    dist_pct = min(1.0, (lower - current_price) / lower * 3)
                    signal_sources.append(('bb_oversold', dist_pct))
                # Überkauft (über oberem Band)
                elif current_price > upper:
                    dist_pct = min(1.0, (current_price - upper) / upper * 3)
                    signal_sources.append(('bb_overbought', -dist_pct))
                
                # Band-Squeeze (enge Bänder) = Potential für Ausbruch
                band_width = (upper - lower) / middle
                if band_width < 0.025:  # Sehr enge Bänder
                    # Richtung basierend auf jüngstem Momentum
                    recent_change = (df['close'].iloc[-1] - df['close'].iloc[-3]) / df['close'].iloc[-3]
                    direction = 1 if recent_change > 0 else -1
                    signal_sources.append(('bb_squeeze', direction * 0.4))
            
            # 4. SMA Crossover
            if 'sma_5' in df.columns and 'sma_20' in df.columns:
                sma_short = df['sma_5'].iloc[-1]
                sma_long = df['sma_20'].iloc[-1]
                sma_short_prev = df['sma_5'].iloc[-2] if len(df) > 2 else sma_short
                sma_long_prev = df['sma_20'].iloc[-2] if len(df) > 2 else sma_long
                
                # Frische Kreuzung nach oben
                if sma_short_prev <= sma_long_prev and sma_short > sma_long:
                    signal_sources.append(('sma_cross_up', 0.9))
                # Frische Kreuzung nach unten
                elif sma_short_prev >= sma_long_prev and sma_short < sma_long:
                    signal_sources.append(('sma_cross_down', -0.9))
                # Abstand zwischen SMAs
                elif sma_short > sma_long:
                    # Normalisierter Abstand (max 5%)
                    dist_pct = min(1.0, (sma_short - sma_long) / sma_long * 20)
                    signal_sources.append(('sma_above', dist_pct * 0.4))
                else:
                    dist_pct = min(1.0, (sma_long - sma_short) / sma_long * 20)
                    signal_sources.append(('sma_below', -dist_pct * 0.4))
            
            # 5. Preismomentum (kurzfristig)
            price_5min_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]
            momentum_signal = min(0.8, max(-0.8, price_5min_change * 100)) # Begrenze auf +/- 0.8
            signal_sources.append(('short_momentum', momentum_signal))
            
            # 6. Volumen-Anomalien (wenn verfügbar)
            if 'volume' in df.columns and not df['volume'].isna().all():
                # Berechne durchschnittliches Volumen der letzten 10 Kerzen
                recent_volume = df['volume'].tail(10)
                avg_volume = recent_volume.mean()
                
                # Aktuelle Kerze
                current_volume = df['volume'].iloc[-1]
                current_candle = df.iloc[-1]
                
                # Volumenspike?
                if current_volume > avg_volume * 1.8:  # 80% über Durchschnitt
                    # Richtung basierend auf Kerzenfarbe
                    if current_candle['close'] > current_candle['open']:  # Bullish
                        vol_signal = min(1.0, current_volume / avg_volume * 0.3)
                        signal_sources.append(('volume_spike_up', vol_signal))
                    else:  # Bearish
                        vol_signal = min(1.0, current_volume / avg_volume * 0.3)
                        signal_sources.append(('volume_spike_down', -vol_signal))
            
            # Gewichte für verschiedene Signalquellen
            weights = {
                'rsi_buy': 0.25,
                'rsi_sell': 0.25,
                'rsi_buy_weak': 0.15,
                'rsi_sell_weak': 0.15,
                'macd_cross_up': 0.3,
                'macd_cross_down': 0.3,
                'macd_above': 0.2,
                'macd_below': 0.2,
                'bb_oversold': 0.25,
                'bb_overbought': 0.25,
                'bb_squeeze': 0.15,
                'sma_cross_up': 0.3,
                'sma_cross_down': 0.3,
                'sma_above': 0.15,
                'sma_below': 0.15,
                'short_momentum': 0.1,
                'volume_spike_up': 0.2,
                'volume_spike_down': 0.2
            }
            
            # Gewichtetes Gesamtsignal berechnen
            if signal_sources:
                weighted_sum = 0
                total_weight = 0
                
                # Detailausgabe für Debugging
                signal_details = []
                
                for source, value in signal_sources:
                    if source in weights:
                        weight = weights[source]
                        weighted_sum += value * weight
                        total_weight += weight
                        signal_details.append(f"{source}: {value:.2f} x {weight} = {value * weight:.2f}")
                
                # Normalisiertes Signal
                if total_weight > 0:
                    final_signal = weighted_sum / total_weight
                    final_signal = max(-1.0, min(1.0, final_signal))  # Begrenze auf -1 bis 1
                else:
                    final_signal = 0
                
                # Prepare signal details as string
                details_str = " | ".join(signal_details)
                return final_signal, details_str
            else:
                return 0, "Keine Signale erkannt"
                
        except Exception as e:
            print(f"{Fore.RED}Fehler bei der Signalberechnung: {str(e)}{Style.RESET_ALL}")
            return 0, f"Fehler: {str(e)}"
    
    def should_execute_trade(self, signal, signal_strength, current_price, balance=None):
        """Entscheidet, ob ein Trade ausgeführt werden soll"""
        # 1. Grundlegende Signalprüfung
        if signal == 0 or abs(signal_strength) < self.signal_threshold:
            return False, f"Signalstärke zu gering ({abs(signal_strength):.2f} < {self.signal_threshold:.2f})"
        
        # 2. Tageswechsel prüfen
        current_day = datetime.now().date()
        if current_day != self.current_day:
            # Neuer Tag - reset Tracking
            self.daily_profit = 0
            self.daily_trades = 0
            self.current_day = current_day
        
        # 3. Tagesgrenzwerte prüfen
        if self.daily_profit >= self.daily_profit_target:
            return False, f"Tägliches Gewinnziel erreicht ({self.daily_profit*100:.1f}% > {self.daily_profit_target*100:.1f}%)"
        
        if self.daily_profit <= -self.max_daily_loss:
            return False, f"Maximaler täglicher Verlust erreicht ({self.daily_profit*100:.1f}% < -{self.max_daily_loss*100:.1f}%)"
        
        # 4. Zeitabstand zwischen Trades
        if self.last_trade_time:
            seconds_since_last = (datetime.now() - self.last_trade_time).total_seconds()
            if seconds_since_last < self.min_trade_interval:
                return False, f"Zu kurze Zeit seit letztem Trade ({seconds_since_last:.0f}s < {self.min_trade_interval}s)"
        
        # 5. Prüfe aktuelle Position (falls trade_type und entry_price gesetzt sind)
        if self.last_trade_type and self.last_trade_price > 0:
            if signal > 0 and self.last_trade_type == 'BUY':
                # Will kaufen, aber bereits in Long-Position
                price_change = (current_price - self.last_trade_price) / self.last_trade_price
                
                if price_change > 0.01:  # +1% höher als letzter Kauf
                    return False, f"Preis {price_change*100:.1f}% höher als letzter Kauf, keine weitere Akkumulation"
        
        # 6. Selbstoptimierung bei Bedarf durchführen
        self.maybe_optimize_parameters()
        
        return True, f"Signal bestätigt (Stärke: {signal_strength:.2f})"
    
    def record_trade_result(self, trade_type, entry_price, exit_price=None, profit=None):
        """Zeichnet Handelsergebnisse auf für Optimierung und Tracking"""
        self.last_trade_time = datetime.now()
        self.last_trade_type = trade_type
        
        if trade_type == 'BUY':
            self.last_trade_price = entry_price
        
        # Wenn ein Trade geschlossen wurde (Verkauf oder Close)
        if exit_price and profit is not None:
            # Aktualisiere tägliche Performance
            profit_percent = profit / entry_price
            self.daily_profit += profit_percent
            self.daily_trades += 1
            
            # Speichere für Optimierungszwecke
            self.performance_history.append({
                'time': datetime.now(),
                'type': trade_type,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'profit': profit,
                'profit_percent': profit_percent,
                'parameters': {
                    'signal_threshold': self.signal_threshold,
                    'min_trade_interval': self.min_trade_interval,
                    'daily_profit_target': self.daily_profit_target,
                    'max_daily_loss': self.max_daily_loss
                }
            })
            
            # Begrenze die Historie auf die letzten 30 Trades
            if len(self.performance_history) > 30:
                self.performance_history = self.performance_history[-30:]
    
    def maybe_optimize_parameters(self):
        """Führt bei Bedarf eine Selbstoptimierung der Parameter durch"""
        if not self.optimization_active:
            return
            
        # Prüfe, ob es Zeit für eine Optimierung ist
        if (self.last_optimization is None or 
            (datetime.now() - self.last_optimization).total_seconds() > self.optimization_interval * 3600):
            
            # Benötigen mindestens 10 Trades für die Optimierung
            if len(self.performance_history) < 10:
                return
                
            print(f"{Fore.CYAN}[{datetime.now().strftime('%H:%M:%S')}] Starte Parameter-Selbstoptimierung...{Style.RESET_ALL}")
            
            # Berechne Performance mit aktuellen Parametern
            current_win_rate = self._calculate_win_rate()
            current_avg_profit = self._calculate_avg_profit()
            current_score = current_win_rate * 0.6 + current_avg_profit * 0.4
            
            best_params = None
            best_score = current_score
            
            # Teste verschiedene Parameterkombinationen (einfacher Grid-Search)
            for signal_threshold in self.param_ranges['signal_threshold']:
                for min_trade_interval in self.param_ranges['min_trade_interval']:
                    # Die anderen Parameter weniger häufig variieren, um Rechenzeit zu sparen
                    for daily_profit_target in [self.param_ranges['daily_profit_target'][1]]:
                        for max_daily_loss in [self.param_ranges['max_daily_loss'][1]]:
                            # Simuliere die Performance mit diesen Parametern
                            temp_win_rate = self._simulate_win_rate(signal_threshold, min_trade_interval)
                            temp_avg_profit = self._simulate_avg_profit(signal_threshold, min_trade_interval)
                            temp_score = temp_win_rate * 0.6 + temp_avg_profit * 0.4
                            
                            # Speichere, wenn besser
                            if temp_score > best_score:
                                best_score = temp_score
                                best_params = {
                                    'signal_threshold': signal_threshold,
                                    'min_trade_interval': min_trade_interval,
                                    'daily_profit_target': daily_profit_target,
                                    'max_daily_loss': max_daily_loss
                                }
            
            # Wende die besten Parameter an, wenn gefunden
            if best_params and best_score > current_score * 1.05:  # Mindestens 5% Verbesserung
                old_threshold = self.signal_threshold
                old_interval = self.min_trade_interval
                
                self.signal_threshold = best_params['signal_threshold']
                self.min_trade_interval = best_params['min_trade_interval']
                self.daily_profit_target = best_params['daily_profit_target']
                self.max_daily_loss = best_params['max_daily_loss']
                
                print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Parameter optimiert:"
                      f" Signalschwelle: {old_threshold:.2f} → {self.signal_threshold:.2f},"
                      f" Handelsintervall: {old_interval}s → {self.min_trade_interval}s{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Keine besseren Parameter gefunden.{Style.RESET_ALL}")
            
            self.last_optimization = datetime.now()
    
    def _calculate_win_rate(self):
        """Berechnet die aktuelle Win Rate aus der Handelshistorie"""
        if not self.performance_history:
            return 0.5  # Neutraler Wert, wenn keine Daten
        
        wins = sum(1 for trade in self.performance_history if trade['profit'] > 0)
        return wins / len(self.performance_history)
    
    def _calculate_avg_profit(self):
        """Berechnet den durchschnittlichen Gewinn aus der Handelshistorie"""
        if not self.performance_history:
            return 0
        
        total_profit = sum(trade['profit_percent'] for trade in self.performance_history)
        return total_profit / len(self.performance_history)
    
    def _simulate_win_rate(self, signal_threshold, min_trade_interval):
        """Simuliert Win Rate mit anderen Parametern"""
        if not self.performance_history:
            return 0.5
            
        # Einfache Simulation: Höhere Schwellen = weniger Trades, aber höhere Genauigkeit
        base_win_rate = self._calculate_win_rate()
        
        # Relative Änderung berechnen
        threshold_factor = signal_threshold / self.signal_threshold
        interval_factor = min_trade_interval / self.min_trade_interval
        
        # Annahmen:
        # - Höhere Schwellen verbessern die Win Rate, aber reduzieren die Anzahl der Trades
        # - Längere Intervalle tendieren zu besseren Trades (weniger Overtrading)
        adjustment = (threshold_factor - 1) * 0.2 + (interval_factor - 1) * 0.1
        
        # Anwenden mit Begrenzung
        simulated_win_rate = base_win_rate * (1 + adjustment)
        return min(0.95, max(0.3, simulated_win_rate))  # Begrenzen zwischen 30% und 95%
    
    def _simulate_avg_profit(self, signal_threshold, min_trade_interval):
        """Simuliert durchschnittlichen Gewinn mit anderen Parametern"""
        if not self.performance_history:
            return 0
            
        # Ähnlich wie bei Win Rate
        base_avg_profit = self._calculate_avg_profit()
        
        # Relative Änderung berechnen
        threshold_factor = signal_threshold / self.signal_threshold
        interval_factor = min_trade_interval / self.min_trade_interval
        
        # Annahmen wie oben
        adjustment = (threshold_factor - 1) * 0.3 + (interval_factor - 1) * 0.15
        
        # Anwenden mit Begrenzung
        simulated_avg_profit = base_avg_profit * (1 + adjustment)
        return simulated_avg_profit  # Hier ohne harte Grenzen
    
    def day_trader_strategy(self, df, actual_balance=None):
        """
        Hauptfunktion für die Day-Trader-Strategie.
        Kompatibel mit der bestehenden Strategie-Schnittstelle.
        """
        if df.empty or len(df) < 10:
            info = {
                'strategy': 'DAY_TRADER',
                'description': 'Optimierte Day-Trading-Strategie für kleine Kapitalbeträge',
                'signal_details': "Nicht genügend Daten für Signalgenerierung"
            }
            return 0, info
        
        try:
            # 1. Aktueller Preis
            current_price = df['close'].iloc[-1]
            
            # 2. Berechne Signal und Signalstärke
            signal_strength, signal_details = self.calculate_signal_strength(df)
            
            # 3. Konvertiere in binäres Signal
            if signal_strength > self.signal_threshold:
                signal = 1  # Kaufsignal
            elif signal_strength < -self.signal_threshold:
                signal = -1  # Verkaufssignal
            else:
                signal = 0  # Kein Signal
            
            # 4. Prüfe, ob der Trade ausgeführt werden soll
            execute_trade, execution_reason = self.should_execute_trade(
                signal, signal_strength, current_price, actual_balance
            )
            
            # Unterdrücke Signal, wenn nicht ausgeführt werden soll
            if not execute_trade:
                original_signal = signal
                signal = 0
                print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Signal ignoriert: {execution_reason}{Style.RESET_ALL}")
            
            # Signal-Farbe für Ausgabe
            signal_color = Fore.GREEN if signal > 0 else (Fore.RED if signal < 0 else Fore.YELLOW)
            signal_text = "KAUF" if signal > 0 else ("VERKAUF" if signal < 0 else "HALTEN")
            
            # 5. Zusammenstellen der Strategieinformationen
            info = {
                'strategy': 'DAY_TRADER',
                'description': 'Optimierte Day-Trading-Strategie für kleine Kapitalbeträge',
                'signal_details': f"{signal_color}{signal_text}: Signalstärke {signal_strength:.2f}{Style.RESET_ALL}",
                'parameters': f"Schwelle: {self.signal_threshold:.2f}, Min. Intervall: {self.min_trade_interval}s",
                'signal_strength': signal_strength,
                'execution_decision': execute_trade,
                'execution_reason': execution_reason,
                'raw_signal_details': signal_details,
                'analysis': f"Signalstärke: {signal_strength:.2f} | Trades heute: {self.daily_trades} | Tagesgewinn: {self.daily_profit*100:.1f}%"
            }
            
            return signal, info
            
        except Exception as e:
            print(f"{Fore.RED}Fehler in der Day-Trader-Strategie: {str(e)}{Style.RESET_ALL}")
            info = {
                'strategy': 'DAY_TRADER',
                'description': 'Optimierte Day-Trading-Strategie für kleine Kapitalbeträge',
                'signal_details': f"Fehler: {str(e)}"
            }
            return 0, info


# Globale Instanz der Day-Trader-Strategie
_day_trader_strategy_instance = None

def get_day_trader_strategy_instance():
    """Singleton-Zugriff auf die Day-Trader-Strategie-Instanz"""
    global _day_trader_strategy_instance
    if _day_trader_strategy_instance is None:
        _day_trader_strategy_instance = SimpleDayTraderStrategy()
    return _day_trader_strategy_instance

def day_trader_strategy(df):
    """
    Wrapper-Funktion, kompatibel mit dem vorhandenen Strategie-Interface.
    
    Parameters:
    df (pandas.DataFrame): DataFrame mit Marktdaten und Indikatoren
    
    Returns:
    tuple: (signal, info) mit Handelssignal und Informationen
    """
    strategy = get_day_trader_strategy_instance()
    return strategy.day_trader_strategy(df)
