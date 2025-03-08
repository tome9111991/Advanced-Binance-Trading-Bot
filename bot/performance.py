import pandas as pd
import numpy as np
from datetime import datetime
import os
from colorama import Fore, Style
import utils
import config

class PerformanceTracker:
    """Klasse zum Verfolgen der Performance des Trading-Bots"""
    
    def __init__(self):
        self.trades = []
        self.daily_pnl = {}
        self.start_time = datetime.now()
        self.initial_balance = None
        self.current_balance = None
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Performance-Metriken
        self.total_profit = 0
        self.max_drawdown = 0
        self.win_rate = 0
        self.profit_factor = 0
        self.avg_win = 0
        self.avg_loss = 0
        self.largest_win = 0
        self.largest_loss = 0
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.max_consecutive_wins = 0
        self.max_consecutive_losses = 0
        
        # Währungsinformationen
        self.quote_currency = config.get_quote_currency()
    
    def set_initial_balance(self, balance):
        """Setzt den initialen Kontostand"""
        self.initial_balance = balance
        self.current_balance = balance
    
    def update_balance(self, balance):
        """Aktualisiert den aktuellen Kontostand"""
        self.current_balance = balance
        
        # Berechne aktuellen Drawdown
        if self.initial_balance is not None and self.initial_balance > 0:
            drawdown = (self.initial_balance - self.current_balance) / self.initial_balance
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
    
    def add_trade(self, trade_type, entry_price, exit_price, position_size, profit):
        """Fügt einen abgeschlossenen Trade hinzu"""
        trade_time = datetime.now()
        trade_date = trade_time.date()
        
        # Aktualisiere die Quote-Währung für den Fall, dass sich die Konfiguration geändert hat
        self.quote_currency = config.get_quote_currency()
        base_currency = config.get_base_currency()
        
        # Trade-Informationen
        trade = {
            'time': trade_time,
            'type': trade_type,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'position_size': position_size,
            'profit': profit,
            'profit_percent': (profit / (entry_price * position_size)) * 100 if entry_price * position_size != 0 else 0,
            'quote_currency': self.quote_currency,
            'base_currency': base_currency
        }
        
        self.trades.append(trade)
        self.total_trades += 1
        
        # Aktualisiere täglichen P&L
        if trade_date not in self.daily_pnl:
            self.daily_pnl[trade_date] = 0
        self.daily_pnl[trade_date] += profit
        
        # Aktualisiere Gewinn/Verlust-Statistiken
        self.total_profit += profit
        
        if profit > 0:
            self.winning_trades += 1
            self.avg_win = (self.avg_win * (self.winning_trades - 1) + profit) / self.winning_trades if self.winning_trades > 0 else 0
            if profit > self.largest_win:
                self.largest_win = profit
            
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            if self.consecutive_wins > self.max_consecutive_wins:
                self.max_consecutive_wins = self.consecutive_wins
        
        elif profit < 0:
            self.losing_trades += 1
            self.avg_loss = (self.avg_loss * (self.losing_trades - 1) + abs(profit)) / self.losing_trades if self.losing_trades > 0 else 0
            if abs(profit) > self.largest_loss:
                self.largest_loss = abs(profit)
            
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            if self.consecutive_losses > self.max_consecutive_losses:
                self.max_consecutive_losses = self.consecutive_losses
        
        # Aktualisiere Performance-Metriken
        if self.total_trades > 0:
            self.win_rate = self.winning_trades / self.total_trades
        
        total_wins = sum(trade['profit'] for trade in self.trades if trade['profit'] > 0)
        total_losses = sum(abs(trade['profit']) for trade in self.trades if trade['profit'] < 0)
        
        if total_losses > 0:
            self.profit_factor = total_wins / total_losses
        
        # Speichere Daten, wenn konfiguriert
        if config.SAVE_PERFORMANCE_DATA:
            self.save_to_csv()
        
        # Ausgabe der Trade-Informationen
        trade_info = f"Trade: {trade_type} | Einstieg: {entry_price:.2f} | Ausstieg: {exit_price:.2f} | Gewinn/Verlust: "
        if profit > 0:
            print(f"{Fore.GREEN}{trade_info}{profit:.2f} {self.quote_currency}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}{trade_info}{profit:.2f} {self.quote_currency}{Style.RESET_ALL}")
    
    def save_to_csv(self):
        """Speichert die Performance-Daten in eine CSV-Datei"""
        try:
            # Trades als DataFrame konvertieren
            trades_df = pd.DataFrame(self.trades)
            
            # Speichere in CSV
            trades_df.to_csv(config.PERFORMANCE_FILE, index=False)
        except Exception as e:
            utils.log_error(e, "Fehler beim Speichern der Performance-Daten")
    
    def load_from_csv(self):
        """Lädt Performance-Daten aus einer CSV-Datei"""
        try:
            if os.path.exists(config.PERFORMANCE_FILE):
                trades_df = pd.read_csv(config.PERFORMANCE_FILE)
                
                # Konvertiere zu Liste von Dictionaries
                self.trades = trades_df.to_dict('records')
                
                # Aktualisiere Statistiken
                self.total_trades = len(self.trades)
                self.winning_trades = sum(1 for trade in self.trades if trade['profit'] > 0)
                self.losing_trades = sum(1 for trade in self.trades if trade['profit'] < 0)
                
                # Berechne Metriken neu
                self.calculate_metrics()
        except Exception as e:
            utils.log_error(e, "Fehler beim Laden der Performance-Daten")
    
    def calculate_metrics(self):
        """Berechnet Performance-Metriken basierend auf den gespeicherten Trades"""
        if not self.trades:
            return
        
        # Aktualisiere Währungsinformationen
        self.quote_currency = config.get_quote_currency()
        
        # Total Profit
        self.total_profit = sum(trade['profit'] for trade in self.trades)
        
        # Win Rate
        if self.total_trades > 0:
            self.win_rate = self.winning_trades / self.total_trades
        
        # Profit Factor
        total_wins = sum(trade['profit'] for trade in self.trades if trade['profit'] > 0)
        total_losses = sum(abs(trade['profit']) for trade in self.trades if trade['profit'] < 0)
        
        if total_losses > 0:
            self.profit_factor = total_wins / total_losses
        
        # Average Win/Loss
        if self.winning_trades > 0:
            self.avg_win = total_wins / self.winning_trades
        
        if self.losing_trades > 0:
            self.avg_loss = total_losses / self.losing_trades
        
        # Largest Win/Loss
        if self.winning_trades > 0:
            self.largest_win = max(trade['profit'] for trade in self.trades if trade['profit'] > 0)
        
        if self.losing_trades > 0:
            self.largest_loss = max(abs(trade['profit']) for trade in self.trades if trade['profit'] < 0)
        
        # Berechne täglichen P&L
        self.daily_pnl = {}
        for trade in self.trades:
            trade_date = pd.to_datetime(trade['time']).date() if isinstance(trade['time'], str) else trade['time'].date()
            if trade_date not in self.daily_pnl:
                self.daily_pnl[trade_date] = 0
            self.daily_pnl[trade_date] += trade['profit']
        
        # Berechne maximale aufeinanderfolgende Gewinne/Verluste
        self.calculate_consecutive_wins_losses()
    
    def calculate_consecutive_wins_losses(self):
        """Berechnet die maximale Anzahl aufeinanderfolgender Gewinne und Verluste"""
        if not self.trades:
            return
        
        # Sortiere Trades nach Zeit
        sorted_trades = sorted(self.trades, key=lambda x: x['time'])
        
        current_wins = 0
        current_losses = 0
        
        for trade in sorted_trades:
            if trade['profit'] > 0:
                current_wins += 1
                current_losses = 0
                if current_wins > self.max_consecutive_wins:
                    self.max_consecutive_wins = current_wins
            elif trade['profit'] < 0:
                current_losses += 1
                current_wins = 0
                if current_losses > self.max_consecutive_losses:
                    self.max_consecutive_losses = current_losses
    
    def print_summary(self):
        """Gibt eine Zusammenfassung der Performance aus"""
        print(f"\n{Fore.CYAN}=== Performance-Zusammenfassung ==={Style.RESET_ALL}")
        
        # Währungsinformationen aktualisieren
        self.quote_currency = config.get_quote_currency()
        
        # Laufzeit
        runtime = datetime.now() - self.start_time
        days, remainder = divmod(runtime.total_seconds(), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        print(f"Laufzeit: {int(days)} Tage, {int(hours)} Stunden, {int(minutes)} Minuten")
        
        # Balance und Profit
        if self.initial_balance is not None:
            profit_percent = (self.total_profit / self.initial_balance) * 100 if self.initial_balance > 0 else 0
            print(f"Initialer Kontostand: {self.initial_balance:.2f} {self.quote_currency}")
            print(f"Aktueller Kontostand: {self.current_balance:.2f} {self.quote_currency}")
            print(f"Gesamtgewinn/-verlust: {self.total_profit:.2f} {self.quote_currency} ({profit_percent:.2f}%)")
        else:
            print(f"Gesamtgewinn/-verlust: {self.total_profit:.2f} {self.quote_currency}")
        
        # Trade-Statistiken
        print(f"\nAnzahl Trades: {self.total_trades}")
        if self.total_trades > 0:
            print(f"Gewinnende Trades: {self.winning_trades} ({self.win_rate*100:.2f}%)")
            print(f"Verlierende Trades: {self.losing_trades} ({(1-self.win_rate)*100:.2f}%)")
        
        # Profit-Statistiken
        print(f"\nProfit-Faktor: {self.profit_factor:.2f}")
        print(f"Durchschnittlicher Gewinn: {self.avg_win:.2f} {self.quote_currency}")
        print(f"Durchschnittlicher Verlust: {self.avg_loss:.2f} {self.quote_currency}")
        print(f"Größter Gewinn: {self.largest_win:.2f} {self.quote_currency}")
        print(f"Größter Verlust: {self.largest_loss:.2f} {self.quote_currency}")
        
        # Consecutive Wins/Losses
        print(f"\nMaximale aufeinanderfolgende Gewinne: {self.max_consecutive_wins}")
        print(f"Maximale aufeinanderfolgende Verluste: {self.max_consecutive_losses}")
        print(f"Aktuelle aufeinanderfolgende Gewinne: {self.consecutive_wins}")
        print(f"Aktuelle aufeinanderfolgende Verluste: {self.consecutive_losses}")
        
        # Drawdown
        print(f"\nMaximaler Drawdown: {self.max_drawdown*100:.2f}%")
        
        print(f"\n{Fore.CYAN}======================================{Style.RESET_ALL}")