Good Vibe Quantitative Trading Framework 📈

Welcome to the Good Vibe Traders open-source quantitative research project. This framework is a specialized engine designed to identify and exploit high-probability "Volatility Bursts" within the Indian equity derivatives market, specifically targeting NIFTY, BANKNIFTY, and SENSEX.

🚀 Project Vision

The Good Vibe Framework moves away from lagging indicators and subjective chart patterns. Our objective is to implement a purely deterministic, math-based approach to option buying. By identifying the exact moment the market shifts from a low-volatility state to a high-momentum burst, we aim to capture rapid premium expansions while strictly limiting risk.

🛠️ Technical Architecture

The framework utilizes a multi-stage filtration process to ensure only high-conviction trades are executed:

1. The Volatility Floor (Noise Filter)

To avoid "choppy" markets, the algo monitors the Average True Range (ATR). It only activates when the current range is significantly below the average, signaling a compression phase that typically precedes a violent breakout.

2. The Compass Bias (Trend Alignment)

No trade is taken in isolation. The system requires strict alignment across three time-layers:
- Price Action $\rightarrow$ 15m EMA $\rightarrow$ Daily VWAP.
- Entries are only permitted when the price is trending in the same direction as the medium-term EMA and the daily volume-weighted average.

3. The Sling-Shot Trigger (Institutional Momentum)

The entry is triggered by a "Power Candle" breakout:
- Micro-Range Breakout: Price must break a 5-candle consolidation range.
- Body-to-Wick Ratio: The trigger candle must have a body-to-range ratio of $\ge 80%$, signaling institutional aggression rather than retail noise.

4. Risk Management & Exit Logic

- Dynamic 1:2 RR: Every trade is entered with a mathematically calculated Stop Loss and a Target of exactly double the risk.
- Profit Protector: A breakeven trigger moves the stop to the entry price once the trade reaches a +10 point threshold.
- Time-Based Exit: All positions are hard-closed at 15:00 IST to eliminate overnight gap risk.

📊 Backtesting & Validation

The framework includes a high-precision backtesting suite that:
- Processes 1-minute tick data for professional-grade accuracy.
- Simulates Synthetic Option Premiums based on the 1:10 Spot-to-Premium Delta ratio.
- Validates results across multiple indices to ensure the logic is not index-specific.

🎯 Objective

Our mission is to provide a scalable, transparent, and verifiable open-source infrastructure for traders to validate quantitative hypotheses and automate high-conviction entries in the Indian markets.

---
Disclaimer: This project is for research and educational purposes only. Trading in derivatives involves significant risk.
