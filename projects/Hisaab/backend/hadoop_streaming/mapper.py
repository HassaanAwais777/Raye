#!/usr/bin/env python3
"""Hadoop Streaming MAPPER for Hisaab.

Run on a real cluster:
  hadoop jar hadoop-streaming.jar \
    -input /data/campaign_10m.csv -output /data/out \
    -file mapper.py -mapper "python3 mapper.py" \
    -file reducer.py -reducer "python3 reducer.py" \
    -combiner "python3 mapper.py"

Emits:  platform \t impressions,clicks,spend,conversions,revenue,1
As a combiner it also folds its own stdin (identical output format).
"""
import csv
import sys

COL = {"platform": 2, "impressions": 3, "clicks": 4, "spend": 5, "conversions": 6, "revenue": 7}

acc = {}
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    row = next(csv.reader([line]))
    try:
        key = row[COL["platform"]]
        vals = (int(row[COL["impressions"]]), int(row[COL["clicks"]]),
                float(row[COL["spend"]]), int(row[COL["conversions"]]),
                float(row[COL["revenue"]]), 1)
    except (ValueError, IndexError):
        continue                                  # header / malformed line
    a = acc.setdefault(key, (0, 0, 0.0, 0, 0.0, 0))
    acc[key] = (a[0] + vals[0], a[1] + vals[1], a[2] + vals[2],
                a[3] + vals[3], a[4] + vals[4], a[5] + vals[5])

for key, v in acc.items():
    print(f"{key}\t{v[0]},{v[1]},{v[2]:.4f},{v[3]},{v[4]:.4f},{v[5]}")
