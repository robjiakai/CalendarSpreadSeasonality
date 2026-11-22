import numpy as np
import pandas as pd

from .backtest import C


def mean_vs_cost(past, cost, k=2, n=8):     # 1. average move beats k × cost
    if len(past) < n: return 0
    m = past.mean()
    return int(np.sign(m)) if abs(m) > k * cost else 0

def hit_rate(past, cost, h=0.7, n=8):        # 2. consistent direction
    if len(past) < n: return 0
    up = (past > 0).mean()
    if up >= h and past.mean() > cost: return 1
    if up <= 1 - h and -past.mean() > cost: return -1
    return 0

def t_stat(past, cost, z=2, n=8):            # 3. mean is significant
    if len(past) < n: return 0
    t = past.mean() / (past.std() / np.sqrt(len(past)))
    return int(np.sign(t)) if abs(t) > z and abs(past.mean()) > cost else 0

def median_vs_cost(past, cost, k=2, n=8):    # 4. robust to one huge year (heavy tails, Q3)
    if len(past) < n: return 0
    m = past.median()
    return int(np.sign(m)) if abs(m) > k * cost else 0

def recent(past, cost, last=10):             # 5. only the last 10 years
    return mean_vs_cost(past.iloc[-last:], cost, n=min(8, last))