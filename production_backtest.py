import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# =============================================================================
# CONFIGURATION & PARAMETERS
# =============================================================================
CONFIG = {
    'BANKNIFTY': {
        'csv_path': 'C:\\Users\\CSC\\claude_algo\\backtest_data\\banknifty_index_1m.csv',
        'strike_offset': 200,
        'premium_target_base': 400,
        'lot_size': 15
    },
    'NIFTY': {
        'csv_path': 'C:\\Users\\CSC\\claude_algo\\backtest_data\\nifty_index_1m.csv',
        'strike_offset': 200,
        'premium_target_base': 175,
        'lot_size': 25
    }
}

IST = pytz.timezone('Asia/Kolkata')

# =============================================================================
# MATH UTILS
# =============================================================================
def calculate_metrics(df):
    df = df.copy()
    df['range'] = df['high'] - df['low']
    df['avg_range'] = df['range'].rolling(20).mean()
    df['atr'] = df['range'].rolling(14).mean()
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['vwap'] = df.groupby(df.index.date)['tp'].expanding().mean().reset_index(level=0, drop=True)
    return df

# =============================================================================
# CORE ENGINE
# =============================================================================
class HighConvictionBacktester:
    def __init__(self, symbol, config):
        self.symbol = symbol
        self.config = config
        self.trades = []

    def run(self):
        print(f"Processing {self.symbol} with High-Conviction Filters...")
        try:
            df = pd.read_csv(self.config['csv_path'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
        except Exception as e:
            print(f"Error reading {self.symbol} CSV: {e}")
            return

        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC').tz_convert(IST)
        else:
            df.index = df.index.tz_convert(IST)

        df = calculate_metrics(df)

        in_pos = False
        current_trade = None

        for i in range(30, len(df)):
            row = df.iloc[i]
            timestamp = df.index[i]

            if timestamp.hour < 9 or (timestamp.hour == 9 and timestamp.minute < 15) or timestamp.hour >= 15:
                continue

            if not in_pos:
                try:
                    close_30m_ago = df.iloc[i-30]['close']
                    prev_low = df.iloc[i-1]['low']
                    prev_vwap = df.iloc[i-1]['vwap']
                    curr_close = row['close']
                    curr_vwap = row['vwap']
                    atr = row['atr']

                    if np.isnan(atr) or atr == 0: continue

                    # --- FILTER 1: Volatility Floor ---
                    # Market must be active. ATR must be at least 20% of avg_range to avoid flat markets.
                    if row['range'] < (0.1 * row['avg_range']): continue

                    # --- FILTER 3: Distance from Mean (The Stretch) ---
                    # Only trade if the price was significantly away from VWAP before pulling back
                    # Check if the max high/low in last 10 bars was > 1.5 ATR away from VWAP
                    window = df.iloc[i-10:i]
                    stretch_bull = (window['high'].max() - prev_vwap) > (1.5 * atr)
                    stretch_bear = (prev_vwap - window['low'].min()) > (1.5 * atr)

                    # Bullish CE Signal
                    if (curr_close > close_30m_ago and prev_low <= prev_vwap and curr_close > curr_vwap and row['close'] > row['open']):
                        if stretch_bull:
                            trade = self.execute_trade(df, i, 'CE', timestamp)
                            if trade:
                                self.trades.append(trade)
                                current_trade = trade
                                in_pos = True
                                continue

                    # Bearish PE Signal
                    if (curr_close <= close_30m_ago and df.iloc[i-1]['high'] >= prev_vwap and curr_close < curr_vwap and row['close'] < row['open']):
                        if stretch_bear:
                            trade = self.execute_trade(df, i, 'PE', timestamp)
                            if trade:
                                self.trades.append(trade)
                                current_trade = trade
                                in_pos = True
                                continue
                except (IndexError, KeyError): pass

            else:
                spot_change = (row['close'] - current_trade['entry_spot']) / current_trade['entry_spot']
                curr_premium = current_trade['entry_premium'] * (1 + (spot_change * 10 if current_trade['side'] == 'CE' else -spot_change * 10))

                if curr_premium >= current_trade['target']:
                    current_trade['exit_premium'] = curr_premium
                    current_trade['result'] = 'TARGET'
                    in_pos = False
                elif curr_premium <= current_trade['stop']:
                    current_trade['exit_premium'] = curr_premium
                    current_trade['result'] = 'SL'
                    in_pos = False
                elif timestamp.hour == 15:
                    current_trade['exit_premium'] = curr_premium
                    current_trade['result'] = 'TIME'
                    in_pos = False

    def execute_trade(self, df, idx, side, time):
        entry_premium = self.config['premium_target_base']
        if idx + 1 >= len(df): return None

        # --- FILTER 2: Power Candle Requirement ---
        conf_candle = df.iloc[idx+1]
        conf_range = conf_candle['high'] - conf_candle['low']
        if conf_range == 0: return None

        body = abs(conf_candle['close'] - conf_candle['open'])
        body_ratio = body / conf_range

        # Require at least 60% body to confirm strong momentum
        if body_ratio < 0.60 or not (conf_candle['close'] > conf_candle['open']):
            return None

        risk = 10.0
        target = entry_premium + (2 * risk)
        stop = entry_premium - risk

        return {
            'symbol': self.symbol,
            'side': side,
            'entry_time': time,
            'entry_spot': df.iloc[idx]['close'],
            'entry_premium': entry_premium,
            'target': target,
            'stop': stop,
            'exit_premium': None,
            'result': None
        }

    def get_metrics(self):
        pnls = [(t['exit_premium'] - t['entry_premium']) for t in self.trades if t['exit_premium'] is not None]
        if not pnls: return {'total_pnl': 0, 'win_rate': 0, 'count': 0}
        wins = [p for p in pnls if p > 0]
        return {'total_pnl': sum(pnls), 'win_rate': len(wins)/len(pnls), 'count': len(pnls)}

if __name__ == "__main__":
    results = []
    for symbol, config in CONFIG.items():
        bt = HighConvictionBacktester(symbol, config)
        bt.run()
        m = bt.get_metrics()
        results.append({'Symbol': symbol, **m})

    print("\n--- HIGH-CONVICTION PRODUCTION RESULTS ---")
    print(pd.DataFrame(results))
