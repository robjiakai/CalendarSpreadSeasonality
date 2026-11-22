import numpy as np
import pandas as pd
from futspread import load_combo
from futspread.universe import POINT_VALUE

C = 2.5e-4

windows = [(-80, -60), (-60, -40), (-40, -20)]

SPREADS = [
    # Energy: weather related
    'NG[H][J0]',   # Nat gas: "widow maker", end of winter withdrawals vs start of injections
    'RB[H][J0]',   # Gasoline: winter-grade March vs summer-grade April (the spring spec switch)
    'HO[V][F0]',   # Heating oil: October vs January, into peak heating demand
    # Livestock
    'HE[J][M0]',   # Lean hogs: April vs June, into the summer supply squeeze
    'LE[J][M0]',   # Live cattle: April vs June, spring grilling demand
    # Grains and fibre: old crop vs new crop
    'ZC[N][Z0]',   # Corn: July vs December
    'ZS[N][X0]',   # Soybeans: July vs November
    'ZW[N][Z0]',   # Wheat: July (harvest) vs December
    'CT[N][Z0]',   # Cotton: July vs December
]

def add_dte(df):
    """Sort, add business days to expiry, and the previous day's values."""
    df = df.sort_values(['instance', 'date']).reset_index(drop=True)
    df['dte'] = -np.busday_count(df['date'].values.astype('datetime64[D]'),
                                 df['ltd'].values.astype('datetime64[D]'))
    g = df.groupby('instance')          # shift WITHIN each year, not across years
    df['prev_date'] = g['date'].shift(1)
    df['l1_prev'] = g['l1_settlement'].shift(1)
    df['l2_prev'] = g['l2_settlement'].shift(1)
    return df

def build_combos():
    combos = {}
    for code in SPREADS:
        try:
            df = load_combo(code)
        except FileNotFoundError:
            df = build_combo(code)
        combos[code] = add_dte(df)
    return combos

def window(df, entry, exit, max_slip=3):
    """One row per year: prices on the first day at/after each offset."""
    cols = ['date', 'dte', 'settlement', 'l1_settlement', 'l2_settlement']
    a = df[df['dte'] >= entry].drop_duplicates('instance').set_index('instance')
    b = df[df['dte'] >= exit].drop_duplicates('instance').set_index('instance')
    w = a[cols + ['prev_date', 'l1_prev', 'l2_prev']].join(
        b[cols], lsuffix='_in', rsuffix='_out', how='inner')
    w = w[(w['dte_in'] - entry <= max_slip) & (w['dte_out'] - exit <= max_slip)]
    w = w[w['dte_out'] <= -3]          # R5, with 1 day spare because busday_count ignores holidays
    w['move'] = w['settlement_out'] - w['settlement_in']
    return w

def backtest(combos, rule, windows, start, end, notional=1_000_000):
    """combos: {code: add_dte(load_combo(code))}; windows: [(entry, exit), ...]
    rule(past_moves, cost_pts) -> +1, -1 or 0."""
    trades = []
    for code, df in combos.items():
        P = POINT_VALUE[df['ticker'].iloc[0]]
        for entry, exit in windows:
            w = window(df, entry, exit)
            now = w[(w['date_in'] >= start) & (w['date_out'] <= end)]
            for yr, r in now.iterrows():
                past = w.loc[w['date_out'] < r['prev_date'], 'move']   # R6
                legs_prev = abs(r['l1_prev']) + abs(r['l2_prev'])
                d = rule(past, 2 * C * legs_prev)   # cost known on decision day
                if d == 0:
                    continue
                lots = notional / (legs_prev * P)   # same notional every trade
                gross = d * lots * r['move'] * P
                cost = C * lots * P * (abs(r['l1_settlement_in']) + abs(r['l2_settlement_in'])
                                       + abs(r['l1_settlement_out']) + abs(r['l2_settlement_out']))
                trades.append(dict(combo=code, year=yr, entry=r['date_in'],
                                   exit=r['date_out'], dir=d, lots=lots,
                                   past_mean_usd=past.mean() * P,
                                   gross=gross, cost=cost))
    t = pd.DataFrame(trades)
    t = t.sort_values('entry').drop_duplicates(['combo', 'year'], keep='first')
    t['net'] = t['gross'] - t['cost']
    return t

def summarise(t):
    return pd.Series({'trades': len(t), 'won': (t['gross'] > 0).mean(),
                      'gross': t['gross'].sum(), 'cost': t['cost'].sum(),
                      'net': t['net'].sum(), 'net_per_trade': t['net'].mean()})