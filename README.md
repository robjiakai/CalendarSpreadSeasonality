# Calendar Spread Seasonality

A rule-based backtest of seasonal trading in futures calendar spreads. Many
commodities have a yearly cycle (natural gas storage, the summer gasoline
switch, hog supply, harvest), and calendar spreads (long one delivery month,
short another) isolate that cycle from the overall price level. The project
asks whether those seasonal moves are consistent enough to trade after
transaction costs, using an honest, lookahead-free backtest.

## Project

**1. Strategy design (data through 2020)**
Nine spreads, one per series, chosen for a known seasonal driver:

| Sector | Spreads | Driver |
|---|---|---|
| Energy | `NG[H][J0]`, `RB[H][J0]`, `HO[V][F0]` | Storage cycle, gasoline spec switch, heating demand |
| Livestock | `HE[J][M0]`, `LE[J][M0]` | Seasonal supply and demand |
| Crops | `ZC[N][Z0]`, `ZS[N][X0]`, `ZW[N][Z0]`, `CT[N][Z0]` | Old crop vs. new crop |

For each spread and a fixed window before the front contract's expiry, the
rule looks at the spread's move over the same window in every earlier year and
trades in the direction of the average move when its t-statistic exceeds 2 and
the move is larger than the round-trip cost. Five candidate rules were compared
by walk-forward backtest on 2006–2020, and the rule was then frozen.

**2. Out-of-sample performance (2021–2025)**
The frozen rule run once on 2021–2025, with $10M capital, fills at daily
settlements, and a cost of 2.5 bp of notional per leg on entry and exit.
Reports annualized return, volatility, Sharpe ratio and maximum drawdown,
gross and net of costs, by year and overall, plus cumulative P&L.

**3. Heavy tails**
Measures the kurtosis of daily spread changes for `NG[H][J0]`, `CL[F][G0]`
and `HE[J][M0]`. All three are far above the normal value of 3, so standard
deviation alone understates spread risk.

## Lookahead safeguards

- Each decision uses only past years whose trade window ended before the decision day.
- Decisions are made on day t−1 and filled at the settlement on day t.
- Days to expiry are counted from each contract's last trading day, not from the last bar in the data.
- Exits are fixed in advance, at least 3 business days before expiry, with no stops or resizing.

## Repository layout

```
CalendarSpreadSeasonality/
├── notebooks/
│   ├── data_exploration.ipynb   # data coverage checks
│   ├── q1_strategy.ipynb        # rule comparison on 2006–2020, 2021 trade list
│   ├── q2_performance.ipynb     # 2021–2025 run, performance table, P&L chart
│   └── q3_kurtosis.ipynb        # kurtosis of daily spread changes
├── src/
│   ├── backtest.py              # spread list, expiry axis, windows, backtest loop
│   ├── strategies.py            # candidate trading rules
│   └── metrics.py               # daily P&L, costs, performance statistics
├── results/
│   ├── trades_2021.csv
│   ├── q2_table.csv
│   └── q2_cum_pnl.png
└── tests/
```

## Data

Daily settlements come from WRDS (Refinitiv/Datastream futures) through the
[`futspread`](https://github.com/DataDrivenMethods/futspread) package, which
builds each calendar spread from its two legs. Data is not included in this
repository; set `FUTSPREAD_ROOT` to a local data store before running the
notebooks.