import numpy as np
import pandas as pd
from futspread.universe import POINT_VALUE

from .backtest import C

CAPITAL = 10_000_000

def daily_pnl(trades, combos):
    """Gross P&L and cost per day, summed over all trades."""
    rows = []
    for t in trades.itertuples():
        df = combos[t.combo]
        P = POINT_VALUE[df['ticker'].iloc[0]]
        d = df[(df['instance'] == t.year) & (df['date'] >= t.entry) & (df['date'] <= t.exit)]
        # P&L: change in the spread since yesterday; 0 on the entry day
        gross = t.dir * t.lots * d['settlement'].diff().fillna(0) * P
        # Cost: both legs' notional, charged on the entry day and the exit day only
        notional = t.lots * P * (d['l1_settlement'].abs() + d['l2_settlement'].abs())
        cost = notional * 0
        cost.iloc[[0, -1]] = C * notional.iloc[[0, -1]]
        rows.append(pd.DataFrame({'date': d['date'], 'gross': gross, 'cost': cost}))
    daily = pd.concat(rows).groupby('date').sum()

    # Days with no trade still count (as 0) in the mean and the volatility
    cal = pd.concat([df['date'] for df in combos.values()]).drop_duplicates().sort_values()
    cal = cal[(cal >= '2021-01-01') & (cal <= '2025-12-31')]
    daily = daily.reindex(cal).fillna(0)
    daily['net'] = daily['gross'] - daily['cost']
    return daily

def stats(x):
    r = x / CAPITAL
    ret = r.mean() * 252
    vol = r.std() * np.sqrt(252)
    cum = x.cumsum()
    max_dd = (cum - cum.cummax().clip(lower=0)).min() / CAPITAL   # starting 0 counts as a peak
    return [ret, vol, ret / vol, max_dd]

def q2_table(daily, trades):
    periods = {str(y): (f'{y}-01-01', f'{y}-12-31') for y in range(2021, 2026)}
    periods['2021–2025'] = ('2021-01-01', '2025-12-31')
    rows = {}
    for name, (a, b) in periods.items():
        d = daily.loc[a:b]                                     # each period restarts at 0
        t = trades[(trades['entry'] >= a) & (trades['entry'] <= b)]   # trades counted by entry year
        rows[name] = (stats(d['gross']) + stats(d['net'])
                      + [len(t), (t['gross'] > 0).mean(), d['cost'].sum() / d['gross'].sum()])
    cols = ['G Return', 'G Vol', 'G Sharpe', 'G MaxDD',
            'N Return', 'N Vol', 'N Sharpe', 'N MaxDD', 'Trades', 'Won', 'Cost/gross']
    return pd.DataFrame(rows, index=cols).T