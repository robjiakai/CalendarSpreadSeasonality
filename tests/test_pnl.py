"""Reproduce the HW p.3 example: buy 10 CL[G][H0], 5 Nov -> 8 Nov 2019."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pnl import daily_pnl, leg_positions, trade_pnl  # noqa: E402


def make_combo():
    return pd.DataFrame({
        'instance': 2020,
        'date': pd.to_datetime(['2019-11-05', '2019-11-06', '2019-11-07', '2019-11-08']),
        'l1_settlement': [57.15, 56.20, 56.93, 57.10],
        'l2_settlement': [56.84, 55.84, 56.54, 56.77],
        'l1_futcode': 1, 'l2_futcode': 2,
    })


def test_hw_example():
    combos = {'CL[G][H0]': make_combo()}
    trades = pd.DataFrame([{
        'combo': 'CL[G][H0]', 'instance': 2020, 'direction': +1, 'lots': 10,
        'entry_date': pd.Timestamp('2019-11-05'),
        'exit_date': pd.Timestamp('2019-11-08'), 'P': 1000.0}])
    legs = leg_positions(trades, combos)
    d = daily_pnl(legs)
    assert d['pnl'].round(2).tolist() == [0.0, 500.0, 300.0, -600.0]
    assert d['cost'].round(2).tolist() == [284.98, 0.0, 0.0, 284.68]
    # Exact value is -369.65; the HW rounds each cost to the cent first
    # (284.975 -> 284.98, 284.675 -> 284.68), giving -369.66.
    assert d['net'].sum() == pytest.approx(-369.66, abs=0.011)
    per = trade_pnl(legs)
    assert per['pnl'].iloc[0] == pytest.approx(200.0)
    assert per['cost'].iloc[0] == pytest.approx(569.66, abs=0.011)


def test_netting_two_overlapping_trades():
    """Long then short the same spread on overlapping days: costs net out."""
    combos = {'CL[G][H0]': make_combo()}
    base = dict(combo='CL[G][H0]', instance=2020, lots=10, P=1000.0,
                entry_date=pd.Timestamp('2019-11-05'),
                exit_date=pd.Timestamp('2019-11-08'))
    trades = pd.DataFrame([{**base, 'direction': +1}, {**base, 'direction': -1}])
    d = daily_pnl(leg_positions(trades, combos))
    assert d['pnl'].abs().sum() == 0 and d['cost'].sum() == 0
