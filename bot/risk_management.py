import pandas as pd
import numpy as np
from datetime import datetime
from colorama import Fore, Style
import utils
import config

class PositionSizing:
    """Methoden für die Berechnung der optimalen Positionsgröße"""
    
    @staticmethod
    def fixed_size(quantity=None):
        """Feste Positionsgröße"""
        if quantity is None:
            return config.QUANTITY
        return quantity
    
    @staticmethod
    def percent_of_balance(balance, current_price, percent=0.1):
        """Berechnet die Positionsgröße als Prozentsatz des Kontostands"""
        position_value = balance * percent
        return position_value / current_price
    
    @staticmethod
    def kelly_criterion(balance, win_rate, risk_reward_ratio):
        """Berechnet die optimale Positionsgröße nach dem Kelly-Kriterium"""
        kelly_percent = win_rate - ((1 - win_rate) / risk_reward_ratio)
        # Begrenze auf maximal 25% des Kontostands
        kelly_percent = min(max(0, kelly_percent), 0.25)
        return kelly_percent * balance
    
    @staticmethod
    def risk_based(balance, current_price, stop_loss_price, risk_percent=0.02):
        """Berechnet die Positionsgröße basierend auf dem Risiko"""
        if stop_loss_price <= 0 or current_price <= 0:
            return config.QUANTITY
        
        # Maximaler Verlust in der Quote-Währung
        max_loss = balance * risk_percent
        
        # Verlust pro Einheit
        price_diff = abs(current_price - stop_loss_price)
        
        # Berechne Positionsgröße
        if price_diff > 0:
            position_size = max_loss / price_diff
            return position_size
        else:
            return config.QUANTITY

def calculate_position_size(balance, current_price, default_quantity=None):
    """Berechnet die optimale Positionsgröße basierend auf der Konfiguration"""
    try:
        base_currency = config.get_base_currency()
        quote_currency = config.get_quote_currency()
        risk_percent = config.MAX_RISK_PER_TRADE
        stop_loss_percent = config.STOP_LOSS_PERCENT
        stop_loss_price = current_price * (1 - stop_loss_percent)
        
        # Bei prozentualer Positionsgröße
        if config.QUANTITY_TYPE == 'PERCENTAGE':
            size = PositionSizing.percent_of_balance(
                balance=balance,
                current_price=current_price,
                percent=config.QUANTITY
            )
            
            # Begrenze die Positionsgröße auf maximal 50% des Kontostands
            max_size = PositionSizing.percent_of_balance(balance, current_price, 0.5)
            size = min(size, max_size)
        else:
            # Verwende risikobasierte Positionsgröße
            size = PositionSizing.risk_based(
                balance=balance,
                current_price=current_price,
                stop_loss_price=stop_loss_price,
                risk_percent=risk_percent
            )
            
            # Begrenze die Positionsgröße
            max_size = PositionSizing.percent_of_balance(balance, current_price, 0.5)  # Maximal 50% des Kontostands
            size = min(size, max_size)
        
        # Minimale Positionsgröße (angepasst für unterschiedliche Assets)
        min_size = 0.001 if base_currency == 'BTC' else 0.01  # 0.001 für BTC, 0.01 für andere
        if size < min_size:
            size = min_size
        
        # Rundungsgenauigkeit abhängig vom Asset
        precision = 5 if base_currency == 'BTC' else 3  # 5 Dezimalstellen für BTC, 3 für andere
        size = round(size, precision)
        
        print(f"{Fore.CYAN}[{datetime.now().strftime('%H:%M:%S')}] Berechnete Positionsgröße: {size} {base_currency} (Risiko: {risk_percent*100}%){Style.RESET_ALL}")
        return size
    except Exception as e:
        utils.log_error(e, "Fehler bei der Berechnung der Positionsgröße")
        return default_quantity if default_quantity is not None else config.QUANTITY

def calculate_stop_loss(entry_price, position_type, atr=None):
    """Berechnet den Stop-Loss-Preis"""
    try:
        stop_loss_percent = config.STOP_LOSS_PERCENT
        
        if position_type == 'LONG':
            # Für Long-Positionen: Stop-Loss unterhalb des Einstiegspreises
            stop_loss = entry_price * (1 - stop_loss_percent)
        else:
            # Für Short-Positionen: Stop-Loss oberhalb des Einstiegspreises
            stop_loss = entry_price * (1 + stop_loss_percent)
        
        # Wenn ATR verfügbar ist, passen wir den Stop-Loss an die Volatilität an
        if atr is not None and atr > 0:
            atr_multiplier = 2  # Anpassbarer Faktor
            if position_type == 'LONG':
                stop_loss = min(stop_loss, entry_price - (atr * atr_multiplier))
            else:
                stop_loss = max(stop_loss, entry_price + (atr * atr_multiplier))
        
        return stop_loss
    except Exception as e:
        utils.log_error(e, "Fehler bei der Berechnung des Stop-Loss")
        # Fallback auf einfachen prozentualen Stop-Loss
        if position_type == 'LONG':
            return entry_price * (1 - config.STOP_LOSS_PERCENT)
        else:
            return entry_price * (1 + config.STOP_LOSS_PERCENT)

def calculate_take_profit(entry_price, position_type):
    """Berechnet den Take-Profit-Preis"""
    try:
        take_profit_percent = config.TAKE_PROFIT_PERCENT
        
        if position_type == 'LONG':
            # Für Long-Positionen: Take-Profit oberhalb des Einstiegspreises
            take_profit = entry_price * (1 + take_profit_percent)
        else:
            # Für Short-Positionen: Take-Profit unterhalb des Einstiegspreises
            take_profit = entry_price * (1 - take_profit_percent)
        
        return take_profit
    except Exception as e:
        utils.log_error(e, "Fehler bei der Berechnung des Take-Profit")
        # Fallback auf einfachen prozentualen Take-Profit
        if position_type == 'LONG':
            return entry_price * (1 + config.TAKE_PROFIT_PERCENT)
        else:
            return entry_price * (1 - config.TAKE_PROFIT_PERCENT)

def check_stop_loss_hit(current_price, stop_loss, position_type):
    """Prüft, ob der Stop-Loss getroffen wurde"""
    if position_type == 'LONG':
        return current_price <= stop_loss
    else:
        return current_price >= stop_loss

def check_take_profit_hit(current_price, take_profit, position_type):
    """Prüft, ob der Take-Profit getroffen wurde"""
    if position_type == 'LONG':
        return current_price >= take_profit
    else:
        return current_price <= take_profit

def check_trailing_stop(current_price, highest_price, trailing_stop_percent, position_type):
    """Prüft und berechnet den Trailing-Stop"""
    if position_type == 'LONG':
        # Für Long-Positionen: Trail-Stop unter dem höchsten Preis
        trailing_stop = highest_price * (1 - trailing_stop_percent)
        return current_price <= trailing_stop, trailing_stop
    else:
        # Für Short-Positionen: Trail-Stop über dem niedrigsten Preis
        trailing_stop = highest_price * (1 + trailing_stop_percent)
        return current_price >= trailing_stop, trailing_stop

def check_risk(df, current_position, current_price, entry_price, balance):
    """Überprüft verschiedene Risikofaktoren und entscheidet, ob ein Trade erlaubt ist"""
    
    print(f"{Fore.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] Führe Risikoanalyse durch...{Style.RESET_ALL}")
    
    # Holen der Währungskonfiguration
    base_currency = config.get_base_currency()
    quote_currency = config.get_quote_currency()
    
    # Im Testmodus mit aggressiver Strategie immer erlauben
    if config.ACTIVE_STRATEGY == 'AGGRESSIVE_TEST':
        result = {
            'allow_trade': True,
            'reason': 'Risikomanagement für Testzwecke deaktiviert',
            'risk_level': 'Test',
            'stop_loss': None,
            'take_profit': None
        }
        print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Risikoanalyse: Trade erlaubt (Testmodus){Style.RESET_ALL}")
        return result
    
    # Initialisiere das Ergebnis
    result = {
        'allow_trade': True,
        'reason': None,
        'risk_level': 'Niedrig',
        'stop_loss': None,
        'take_profit': None
    }
    
    try:
        # Berechne ATR, falls verfügbar
        atr = df['atr'].iloc[-1] if 'atr' in df.columns else None
        
        # 1. Überprüfe Volatilität
        if atr is not None:
            volatility = atr / current_price * 100  # Volatilität in Prozent
            if volatility > 5:  # Hohe Volatilität
                result['risk_level'] = 'Hoch'
                result['allow_trade'] = False
                result['reason'] = f"Hohe Volatilität: {volatility:.2f}%"
                return result
        
        # 2. Prüfe auf extreme RSI-Werte
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            if (rsi < 10 or rsi > 90) and current_position == 0:
                result['risk_level'] = 'Hoch'
                result['allow_trade'] = False
                result['reason'] = f"Extremer RSI-Wert: {rsi:.2f}"
                return result
        
        # 3. Prüfe Bollinger Band Squeeze (enge Bänder)
        if 'bb_width' in df.columns:
            bb_width = df['bb_width'].iloc[-1]
            if bb_width < 0.01:  # Sehr enge Bänder
                result['risk_level'] = 'Mittel'
                result['allow_trade'] = False
                result['reason'] = f"Bollinger Band Squeeze: {bb_width:.4f}"
                return result
        
        # 4. Maximum Drawdown Check
        # TODO: Implementiere Historie der Handelsergebnisse
        
        # 5. Tägliches Verlustlimit
        # TODO: Implementiere tägliche P&L-Tracking
        
        # 6. Aktuelles Risiko berechnen
        if current_position != 0:
            position_type = 'LONG' if current_position > 0 else 'SHORT'
            
            # Berechne Stop-Loss und Take-Profit
            stop_loss = calculate_stop_loss(entry_price, position_type, atr)
            take_profit = calculate_take_profit(entry_price, position_type)
            
            # Füge sie zum Ergebnis hinzu
            result['stop_loss'] = stop_loss
            result['take_profit'] = take_profit
            
            # Berechne potentiellen Verlust
            potential_loss = abs(entry_price - stop_loss) * abs(current_position)
            loss_percent = potential_loss / balance * 100
            
            if loss_percent > config.MAX_RISK_PER_TRADE * 100:
                result['risk_level'] = 'Hoch'
                result['allow_trade'] = False
                result['reason'] = f"Potenzieller Verlust zu hoch: {loss_percent:.2f}%"
                return result
        
        # Wenn wir hier ankommen, ist der Trade erlaubt
        print(f"{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Risikoanalyse: Trade erlaubt (Risikolevel: {result['risk_level']}){Style.RESET_ALL}")
        
        return result
    
    except Exception as e:
        utils.log_error(e, "Fehler bei der Risikoanalyse")
        # Im Fehlerfall erlauben wir den Trade, um keine potenziellen Gewinne zu verpassen
        result['allow_trade'] = True
        result['reason'] = f"Fehler bei der Risikoanalyse: {str(e)}"
        return result