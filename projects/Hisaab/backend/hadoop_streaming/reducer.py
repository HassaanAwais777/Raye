#!/usr/bin/env python3
"""Hadoop Streaming REDUCER for Hisaab.

Input (sorted by key):  platform \t impressions,clicks,spend,conversions,revenue,count
Output:                 platform \t final sums (same field order)
"""
import sys

current = None
acc = (0, 0, 0.0, 0, 0.0, 0)

for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    key, _, payload = line.partition("\t")
    try:
        imp, clk, spend, conv, rev, n = payload.split(",")
        vals = (int(imp), int(clk), float(spend), int(conv), float(rev), int(n))
    except ValueError:
        continue
    if current is not None and key != current:
        print(f"{current}\t{acc[0]},{acc[1]},{acc[2]:.4f},{acc[3]},{acc[4]:.4f},{acc[5]}")
        acc = (0, 0, 0.0, 0, 0.0, 0)
    current = key
    acc = (acc[0] + vals[0], acc[1] + vals[1], acc[2] + vals[2],
           acc[3] + vals[3], acc[4] + vals[4], acc[5] + vals[5])

if current is not None:
    print(f"{current}\t{acc[0]},{acc[1]},{acc[2]:.4f},{acc[3]},{acc[4]:.4f},{acc[5]}")
