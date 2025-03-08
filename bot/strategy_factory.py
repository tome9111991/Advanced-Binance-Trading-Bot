# strategy_factory.py
import importlib

class StrategyFactory:
    """Factory-Klasse zur Verwaltung und Bereitstellung von Trading-Strategien"""
    
    _strategies = {}
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Initialisiert die verfügbaren Strategien"""
        if cls._initialized:
            return
            
        # Grundstrategien (direkt referenzierbar)
        from strategies import (
            sma_crossover_strategy,
            rsi_strategy,
            macd_strategy,
            bollinger_bands_strategy,
            multi_indicator_strategy,
            aggressive_test_strategy
        )
        
        cls._strategies.update({
            'SMA_CROSSOVER': sma_crossover_strategy,
            'RSI': rsi_strategy,
            'MACD': macd_strategy,
            'BOLLINGER_BANDS': bollinger_bands_strategy,
            'MULTI_INDICATOR': multi_indicator_strategy,
            'AGGRESSIVE_TEST': aggressive_test_strategy
        })
        
        # Füge Day Trader Strategie hinzu
        try:
            from day_trader_strategy import day_trader_strategy
            cls._strategies['DAY_TRADER'] = day_trader_strategy
            print("Day Trader Strategie erfolgreich geladen.")
        except ImportError:
            print("Day Trader Strategie nicht gefunden. Strategie nicht verfügbar.")
        
        cls._initialized = True
    
    @classmethod
    def get_strategy(cls, strategy_name):
        """Gibt die angeforderte Strategie zurück, lädt sie bei Bedarf dynamisch"""
        if not cls._initialized:
            cls.initialize()
            
        if strategy_name in cls._strategies:
            return cls._strategies[strategy_name]
            
        # Dynamisches Laden komplexerer Strategien, um zirkuläre Importe zu vermeiden
        if strategy_name == 'ADAPTIVE':
            if 'ADAPTIVE' not in cls._strategies:
                from adaptive_strategy import adaptive_strategy
                cls._strategies['ADAPTIVE'] = adaptive_strategy
            return cls._strategies['ADAPTIVE']
            
        elif strategy_name == 'ENHANCED_ADAPTIVE':
            if 'ENHANCED_ADAPTIVE' not in cls._strategies:
                from enhanced_adaptive_strategy import enhanced_adaptive_strategy
                cls._strategies['ENHANCED_ADAPTIVE'] = enhanced_adaptive_strategy
            return cls._strategies['ENHANCED_ADAPTIVE']
            
        elif strategy_name == 'SMALL_CAPITAL':
            if 'SMALL_CAPITAL' not in cls._strategies:
                from small_capital_strategy import small_capital_strategy
                cls._strategies['SMALL_CAPITAL'] = small_capital_strategy
            return cls._strategies['SMALL_CAPITAL']
        
        elif strategy_name == 'DAY_TRADER':
            if 'DAY_TRADER' not in cls._strategies:
                try:
                    from day_trader_strategy import day_trader_strategy
                    cls._strategies['DAY_TRADER'] = day_trader_strategy
                    return cls._strategies['DAY_TRADER']
                except ImportError:
                    print(f"Strategie DAY_TRADER nicht gefunden. Verwende MULTI_INDICATOR.")
                    return cls._strategies['MULTI_INDICATOR']
            
        # Fallback: Versuche Modul dynamisch zu laden
        try:
            module_name = f"{strategy_name.lower()}_strategy"
            module = importlib.import_module(module_name)
            strategy_func = getattr(module, f"{strategy_name.lower()}_strategy")
            cls._strategies[strategy_name] = strategy_func
            return strategy_func
        except (ImportError, AttributeError):
            # Wenn Strategie nicht gefunden, verwende Multi-Indikator als Standard
            print(f"Strategie {strategy_name} nicht gefunden. Verwende MULTI_INDICATOR.")
            return cls._strategies['MULTI_INDICATOR']