# Forex_System0_Backtest
Deterministic FX backtesting toolkit built around the production decision pipeline. This repository focuses on realistic execution mechanics (spread, slippage, commission), regime-aware filtering, and robustness tooling (walk-forward, Monte Carlo).

## What This Is
- Market: EURUSD
- Timeframe: 2-minute bars via MT5 in backtest (`back_test.py`)
- Core idea: A hierarchical veto pipeline: data -> regime -> strategy -> psychology -> costs -> risk -> execution
- Backtest goal: Realistic, conservative simulation for small-account systems

## Project Layout (Current)
- `back_test.py` - deterministic simulator + reporting
- `backtest_config.py` - backtest parameters (risk, execution, microstructure, session controls)
- `config.py` - live config defaults (risk, indicators, thresholds)
- `regime.py` - volatility/structure classification (returns bias + risk multiplier)
- `strategy.py` - trend + mean-reversion signals
- `psychology.py` - behavioral filters (cooldowns, max trades, etc.)
- `costs.py` - spread/slippage filters + rollover window checks (timestamp-aware)
- `risk.py` - position sizing (price-distance stops converted to pips)
- `session.py` - time-of-day trade gate (UTC blocked hours)
- `microstructure.py` - session + volatility multipliers for spread/slippage
- `performance.py` - report generation
- `calibration.py` - MT5 history calibration for spread/slippage stats
- `walk_forward.py` - rolling window backtests
- `monte_carlo.py` - resampled equity outcomes
- `risk_validation.py` - realized R vs configured risk

## Quick Start
1. Ensure MT5 is installed and configured.
2. Run the backtest:
   ```powershell
   python back_test.py
   ```
3. Optional tools:
   ```powershell
   python calibration.py
   python walk_forward.py
   python monte_carlo.py
   python risk_validation.py
   ```

## Key Backtest Features
- Realistic execution:
  - Bid/ask spread modeled in price
  - Slippage applied on entry and exit
  - Commission per lot (configurable)
- Regime-aware filters:
  - Volatility: compression / normal / expansion / extreme
  - Structure: trend / range
  - Returns `strategy_bias` and `risk_multiplier`
- Session filter:
  - UTC blocked hours (default: 3, 5, 10, 11, 12)
- Breakeven moves:
  - Move SL to entry after `BE_TRIGGER_R_MULT * stop_distance`
- Swap modeling:
  - Per-lot per-rollover swap cost (off by default)
- Robustness:
  - Walk-forward tests
  - Monte Carlo resampling

## Live Alignment Notes
- Session filter, rollover-aware costs, and regime risk scaling are applied in `main.py`.
- `main.py` runs calibration and a backtest before entering the live loop.
- `data.get_mock_bar()` is still the default in `main.py` unless switched to `data.get_processed_bar()`.

## Configuration (Most Used)
In `backtest_config.py`:
- `BT_START_DATE`, `BT_END_DATE`
- `BT_INITIAL_BALANCE`
- `FIXED_SPREAD_PIPS`, `FIXED_SLIPPAGE_PIPS`, `COMMISSION_PER_LOT`
- `BT_MEAN_REVERSION_ONLY` (disable trend-following)
- `BE_TRIGGER_R_MULT`, `BE_OFFSET_PIPS`
- `MS_ENABLE` and session/volatility multipliers
- `SWAP_LONG_PER_LOT`, `SWAP_SHORT_PER_LOT`

In `config.py`:
- `RISK_PER_TRADE`, `MAX_EFFECTIVE_LEVERAGE`
- `ATR_STOP_MULTIPLIER`, `RR_MIN`, `EXTENDED_MULTIPLIER`
- `VOL_Z_COMPRESSION`, `VOL_Z_EXPANSION`, `ADX_TREND_THRESHOLD`

## Running in Silence
The backtest suppresses verbose strategy prints by default to avoid console overflow. You can change this by calling:
```python
run_simulation(verbose=True)
```

## What's Next
- Calibrate `FIXED_SPREAD_PIPS`, `FIXED_SLIPPAGE_PIPS`, and `COMMISSION_PER_LOT` using `calibration.py`
- Adjust session blocked hours based on updated loss breakdowns
- Run walk-forward + Monte Carlo after parameter changes
