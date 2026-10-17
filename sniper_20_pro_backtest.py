import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# =============================================================================
# CONFIGURATION (THE "SNIPER-20 PRO" MANDATE)
# =============================================================================
CONFIG = {
    'BANKNIFTY': {
        'csv_path': 'C:\\Users\\CSC\\claude_algo\\backtest_data\\banknifty_index_1m.csv',
        'premium_base': 400,
    },
    'NIFTY': {
        'csv_path': 'C:\\Users\\CSC\\claude_algo\\backtest_data\\nifty_index_1m.csv',
        'premium_base': 175,
    }
}

IST = pytz.timezone('Asia/Kolkata')
TARGET_POINTS = 20.0
STOP_LOSS_POINTS = 10.0
BREAKEVEN_TRIGGER = 10.0 # Move SL to entry after +10 points

def calculate_indicators(df):
    df = df.copy()
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['vwap'] = df.groupby(df.index.date)['tp'].expanding().mean().reset_index(level=0, drop=True)
    df['ema15'] = df['close'].ewm(span=60, adjust=False).mean()
    df['range'] = df['high'] - df['low']
    df['atr'] = df['range'].rolling(14).mean()
    return df

class Sniper20ProBacktester:
    def __init__(self, symbol, config):
        self.symbol = symbol
        self.config = config
        self.trades = []

    def run(self):
        print(f"Running Sniper-20 PRO on {self.symbol}...")
        try:
            df = pd.read_csv(self.config['csv_path'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
        except Exception as e:
            print(f"Error reading {self.symbol}: {e}")
            return

        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC').tz_convert(IST)
        else:
            df.index = df.index.tz_convert(IST)

        df = calculate_indicators(df)

        daily_trade_count = {}
        in_pos = False
        current_trade = None

        for i in range(60, len(df)):
            row = df.iloc[i]
            timestamp = df.index[i]
            date = timestamp.date()

            if date not in daily_trade_count:
                daily_trade_count[date] = 0

            if daily_trade_count[date] >= 1 and not in_pos:
                continue

            is_window1 = (timestamp.hour == 9 and timestamp.minute >= 45) or (timestamp.hour == 10)
            is_window2 = (timestamp.hour == 13 and timestamp.minute >= 30) or (timestamp.hour == 14 and timestamp.minute <= 30)

            if not (is_window1 or is_window2) and not in_pos:
                continue

            if not in_pos:
                bullish_bias = (row['close'] > row['ema15']) and (row['ema15'] > row['vwap'])
                bearish_bias = (row['close'] < row['ema15']) and (row['ema15'] < row['vwap'])

                window = df.iloc[i-5:i]
                range_high = window['high'].max()
                range_low = window['low'].min()

                candle_range = row['high'] - row['low']
                if candle_range == 0: continue
                body = abs(row['close'] - row['open'])
                is_power_candle = (body / candle_range) >= 0.8

                if bullish_bias and row['close'] > range_high and is_power_candle and row['close'] > row['open']:
                    in_pos = True
                    current_trade = {
                        'symbol': self.symbol, 'side': 'CE', 'entry_time': timestamp,
                        'entry_spot': row['close'], 'entry_premium': self.config['premium_base'],
                        'target': self.config['premium_base'] + TARGET_POINTS,
                        'stop': self.config['premium_base'] - STOP_LOSS_POINTS,
                        'exit_premium': None, 'result': None, 'date': date,
                        'breakeven_hit': False
                    }
                    self.trades.append(current_trade)
                    continue

                if bearish_bias and row['close'] < range_low and is_power_candle and row['close'] < row['open']:
                    in_pos = True
                    current_trade = {
                        'symbol': self.symbol, 'side': 'PE', 'entry_time': timestamp,
                        'entry_spot': row['close'], 'entry_premium': self.config['premium_base'],
                        'target': self.config['premium_base'] + TARGET_POINTS,
                        'stop': self.config['premium_base'] - STOP_LOSS_POINTS,
                        'exit_premium': None, 'result': None, 'date': date,
                        'breakeven_hit': False
                    }
                    self.trades.append(current_trade)
                    continue
            else:
                spot_change = (row['close'] - current_trade['entry_spot']) / current_trade['entry_spot']
                curr_premium = current_trade['entry_premium'] * (1 + (spot_change * 10 if current_trade['side'] == 'CE' else -spot_change * 10))

                # --- PROFIT PROTECTOR: BREAKEVEN LOGIC ---
                if not current_trade['breakeven_hit']:
                    if abs(curr_premium - current_trade['entry_premium']) >= BREAKEVEN_TRIGGER:
                        current_trade['stop'] = current_trade['entry_premium']
                        current_trade['breakeven_hit'] = True

                if curr_premium >= current_trade['target']:
                    current_trade['exit_premium'] = curr_premium
                    current_trade['result'] = 'TARGET'
                    in_pos = False
                    daily_trade_count[date] += 1
                elif curr_premium <= current_trade['stop']:
                    current_trade['exit_premium'] = curr_premium
                    current_trade['result'] = 'SL'
                    in_pos = False
                    daily_trade_count[date] += 1
                elif timestamp.hour == 15:
                    current_trade['exit_premium'] = curr_premium
                    current_trade['result'] = 'TIME'
                    in_pos = False
                    daily_trade_count[date] += 1

    def get_detailed_results(self):
        data = []
        for t in self.trades:
            if t['exit_premium'] is not None:
                pnl = t['exit_premium'] - t['entry_premium']
                data.append({
                    'Date': pd.to_datetime(t['date']),
                    'Symbol': t['symbol'],
                    'Result': t['result'],
                    'P&L': pnl
                })
        return pd.DataFrame(data)

if __name__ == "__main__":
    all_data = []
    for symbol, config in CONFIG.items():
        bt = Sniper20ProBacktester(symbol, config)
        bt.run()
        all_data.append(bt.get_detailed_results())

    full_df = pd.concat(all_data)
    full_df['Month'] = full_df['Date'].dt.to_period('M')
    monthly_summary = full_df.groupby(['Month', 'Symbol'])['P&L'].sum().unstack().fillna(0)

    print("\n--- SNIPER-20 PRO MONTHLY P&L (POINTS) ---")
    print(monthly_summary)
    print("\n--- OVERALL SUMMARY ---")
    print(f"Total Portfolio P&L: {full_df['P&L'].sum():.2f} points")
    print(f"Average Monthly P&L: {full_df['P&L'].sum() / 12:.2f} points")
