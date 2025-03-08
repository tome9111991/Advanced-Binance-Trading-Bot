# Advanced Binance Trading Bot

An advanced, feature-rich trading bot for Binance exchange that supports both Spot and Futures markets with real-time technical analysis, adaptive strategy selection, and comprehensive risk management.

![Bot Banner](https://i.imgur.com/placeholder.jpg)

## Features

- **Dual Trading Modes**: 
  - Futures Testnet Mode (practice without real money)
  - Spot Live Mode (trade with real assets)
  
- **Technical Analysis Engine**:
  - Real-time calculation of multiple technical indicators
  - Customizable parameters for all indicators
  - Visualization of indicator values and trends

- **Multiple Trading Strategies**:
  - Supports 8+ configurable trading strategies
  - Adaptive strategy switching based on market conditions
  - Specialized strategies for small capital accounts

- **Advanced Market Analysis**:
  - Market regime detection (trending, ranging, volatile markets)
  - Volume pressure analysis
  - Chart pattern recognition
  - Signal proximity analysis

- **Risk Management**:
  - Customizable risk per trade
  - Dynamic position sizing
  - Automated stop-loss and take-profit
  - Daily loss limits and maximum drawdown protection

- **Real-time Visualization**:
  - Console-based dashboard with colored indicators
  - Market data and position information
  - Strategy selection reasoning
  - Performance metrics

- **Performance Tracking**:
  - Trade history and win rate calculation
  - Profit/loss tracking
  - Strategy performance comparison
  - Exportable performance data

## Supported Trading Strategies

The bot includes the following trading strategies:

1. **SMA Crossover**: Trades based on Short/Long Simple Moving Average crossovers
2. **RSI**: Uses the Relative Strength Index for overbought/oversold conditions
3. **MACD**: Trades based on the Moving Average Convergence Divergence indicator
4. **Bollinger Bands**: Trades when price breaks out of or reverts to the bands
5. **Multi-Indicator**: Combines signals from multiple indicators with weighted scoring
6. **Adaptive**: Dynamically selects the best strategy based on recent performance
7. **Enhanced Adaptive**: Advanced version with market regime detection
8. **Small Capital**: Optimized for accounts with limited capital
9. **Day Trader**: Specialized for intraday trading with self-optimization

## Requirements

- Python 3.8+
- Binance account (with API keys)
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/tome9111991/Advanced-Binance-Trading-Bot.git
cd binance-trading-bot
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your settings in `config.py` (see Configuration section)

## Configuration

All bot settings are managed in the `config.py` file:

### API Configuration
```python
API_KEY = ""      # Your Binance API key
API_SECRET = ""   # Your Binance API secret
```

### Environment Settings
```python
USE_TESTNET = True  # True for Testnet, False for live trading
```

### Trading Configuration
```python
SYMBOL = 'SOL/USDC'   # Trading pair
TIMEFRAME = '15m'     # Candlestick timeframe
QUANTITY_TYPE = 'PERCENTAGE'  # 'ABSOLUTE' or 'PERCENTAGE'
QUANTITY = 0.2        # 20% of available balance or fixed quantity
```

### Strategy Selection
```python
ACTIVE_STRATEGY = 'MULTI_INDICATOR'  # Choose your strategy
```

### Risk Management
```python
MAX_RISK_PER_TRADE = 0.02   # 2% risk per trade
STOP_LOSS_PERCENT = 0.02    # 2% stop loss
TAKE_PROFIT_PERCENT = 0.04  # 4% take profit
```

## Usage

Run the bot with:

```bash
python main.py
```

For signal analysis reports:

```bash
python main.py --analyze-signals [day|week|month|all]
```

## How It Works

1. **Initialization**:
   - The bot connects to Binance using your API credentials
   - It loads configuration settings and initializes the selected strategy

2. **Data Collection**:
   - Historical market data is fetched from Binance
   - Technical indicators are calculated based on this data

3. **Signal Generation**:
   - The selected strategy analyzes market data and indicators
   - Trading signals (buy/sell/hold) are generated

4. **Risk Analysis**:
   - Risk management rules are applied to the signal
   - Position sizing is calculated based on account balance and risk parameters

5. **Trade Execution**:
   - If all conditions are met, the trade is executed
   - Stop-loss and take-profit are set if applicable

6. **Performance Tracking**:
   - Trade results are recorded and analyzed
   - Performance metrics are updated in real-time

## Warning and Disclaimer

**USE AT YOUR OWN RISK**. Trading cryptocurrencies involves substantial risk and is not suitable for all investors. The high degree of leverage can work against you as well as for you. Before deciding to trade cryptocurrencies you should carefully consider your investment objectives, level of experience, and risk appetite. The possibility exists that you could sustain a loss of some or all of your initial investment and therefore you should not invest money that you cannot afford to lose.

This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages or other liability, whether in an action of contract, tort or otherwise, arising from, out of or in connection with the software or the use or other dealings in the software.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
