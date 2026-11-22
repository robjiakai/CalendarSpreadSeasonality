"""End-to-end run on synthetic spreads with a planted seasonal drift."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.history import prepare  # noqa: E402
from src.metrics import perf_table  # noqa: E402
from src.pnl import daily_pnl, leg_positions, on_calendar, trade_pnl  # noqa: E402
from src.strategy import RuleParams, generate_trades  # noqa: E402


def fake_combo(code, ticker, month, seed):
    rng = np.random.default_rng(seed)
    parts = []
    for yr in range(2000, 2027):
        ltd = pd.Timestamp(yr, month, 15) - pd.offsets.BDay(0)
        dates = pd.bdate_range(ltd - pd.DateOffset(years=2), min(ltd, pd.Timestamp('2026-04-03')))
        n = len(dates)
        bd = -np.busday_count(dates.values.astype('datetime64[D]'), np.datetime64(ltd.date()))
        drift = np.where((bd >= -60) & (bd < -45), 0.02, 0.0)   # planted seasonal rise
        spread = 0.5 + np.cumsum(drift + rng.normal(0, 0.03, n))
        l2 = 60 + np.cumsum(rng.normal(0, 0.5, n))
        parts.append(pd.DataFrame({
            'instance': yr, 'combo': code, 'ticker': ticker, 'date': dates,
            'settlement': spread, 'l1_settlement': l2 + spread, 'l2_settlement': l2,
            'ltd': ltd, 'l1_futcode': yr * 100 + seed, 'l2_futcode': yr * 100 + seed + 50}))
    return pd.concat(parts, ignore_index=True)


def test_end_to_end():
    combos = {'CL[G][H0]': prepare(fake_combo('CL[G][H0]', 'CL', 2, 1)),
              'CL[J][K0]': prepare(fake_combo('CL[J][K0]', 'CL', 4, 2))}
    params = RuleParams(entry_offsets=(-80, -60, -40), hold=15, min_hit=0.6, edge_mult=1.0)
    start, end = pd.Timestamp('2021-01-01'), pd.Timestamp('2025-12-31')
    trades = generate_trades(combos, {'CL': 1000.0}, params, start, end)
    assert len(trades) > 0
    assert (trades['entry_off'] == -60).mean() > 0.5        # finds the planted window
    assert (trades['direction'] == 1).all()
    legs = leg_positions(trades, combos)
    per = trade_pnl(legs)
    trades = trades.join(per.rename(columns={'pnl': 'gross'}))
    cal = pd.bdate_range(start, end)
    daily = on_calendar(daily_pnl(legs), cal)
    assert np.isclose(daily['pnl'].sum(), trades['gross'].sum())
    tbl = perf_table(daily, trades, 10_000_000)
    print(trades[['combo', 'entry_date', 'exit_date', 'direction', 'lots', 'past_n',
                  'past_mean_usd', 'gross', 'cost']].head())
    print(tbl.round(4).to_string())
    assert tbl.shape[0] == 6
