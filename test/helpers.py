from unittest.mock import call


def get_expected_report_calls():
    expected_call_strs = ['** REPORT **',
                      'Report: $9,844 out of potential $9,905: latham BTC_L5 <15m TP and TSL>. Median potential profit: 0.12%, mean potential profit: 0.02%, std dev 0.28. Median drawdown: -0.21%, std dev: 0.25. Leverage: 1. Trades: 6 since 07-06 05:23 UTC',
                      'Report: $9,856 out of potential $10,046: latham BTC_L3 <15m Tiny TP>. Median potential profit: 0.15%, mean potential profit: 0.11%, std dev 0.31. Median drawdown: -0.31%, std dev: 0.3. Leverage: 1. Trades: 7 since 07-06 05:23 UTC',
                      'Report: $9,911 out of potential $10,064: latham BTC_L4 <15m Split TPs>. Median potential profit: 0.27%, mean potential profit: 0.15%, std dev 0.29. Median drawdown: -0.3%, std dev: 0.29. Leverage: 1. Trades: 7 since 07-06 05:23 UTC',
                      'Report: $9,977 out of potential $10,019: malcolm BTC_M1 <A2A 15m>. Median potential profit: 0.32%, mean potential profit: 0.32%, std dev 0. Median drawdown: -0.23%, std dev: 0. Leverage: 1. Trades: 1 since 07-08 03:51 UTC',
                      'Report: $9,987 out of potential $10,025: latham BTC_L6 <15m TSL>. Median potential profit: 0.23%, mean potential profit: 0.12%, std dev 0.3. Median drawdown: -0.15%, std dev: 0.18. Leverage: 1. Trades: 5 since 07-06 05:23 UTC',
                      'Report: $10,000 out of potential $10,000: malcolm ETH_M1 <15m ETH Fo Shizzle on da A2A>. Median potential profit: 0%, mean potential profit: 0%, std dev 0. Median drawdown: 0%, std dev: 0. Leverage: 1. Trades: 0 since 07-08 18:23 UTC',
                      'Report: $10,000 out of potential $10,000: malcolm BTC_M2 <30m A2A HTSL>. Median potential profit: 0%, mean potential profit: 0%, std dev 0. Median drawdown: 0%, std dev: 0. Leverage: 1. Trades: 0 since 07-08 17:09 UTC',
                      'Report: $10,000 out of potential $10,000: latham BTC_L1 <1m Benchmark>. Median potential profit: 0%, mean potential profit: 0%, std dev 0. Median drawdown: 0%, std dev: 0. Leverage: 1. Trades: 0 since 07-06 05:23 UTC',
                      'Report: $10,000 out of potential $10,000: latham BTC_L2 <1m Split TP>. Median potential profit: 0%, mean potential profit: 0%, std dev 0. Median drawdown: 0%, std dev: 0. Leverage: 1. Trades: 0 since 07-06 05:23 UTC',
                      'Report: $10,000 out of potential $10,000: latham BTC_M3 <1h TSL/TP>. Median potential profit: 0%, mean potential profit: 0%, std dev 0. Median drawdown: 0%, std dev: 0. Leverage: 1. Trades: 0 since 07-08 18:27 UTC',
                      'Report: $10,000 out of potential $10,000: latham BTC_M4 < 5/15 A2A HTSL>. Median potential profit: 0%, mean potential profit: 0%, std dev 0. Median drawdown: 0%, std dev: 0. Leverage: 1. Trades: 0 since 07-08 18:27 UTC',
                      'Report: $10,000 out of potential $10,000: latham BTC_M5 <15m A2A HTSL>. Median potential profit: 0%, mean potential profit: 0%, std dev 0. Median drawdown: 0%, std dev: 0. Leverage: 1. Trades: 0 since 07-08 18:27 UTC',
    ]
    expected_calls = []
    for _str in expected_call_strs:
        expected_calls.append(call(_str))
    return expected_calls
