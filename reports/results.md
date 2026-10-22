# Backtest results

Rolling-origin, expanding window. 12 fold origins (2022Q2 to 2025Q1), horizons h=1..4, 10 companies. Metrics are computed per (company, fold) over the 4 horizons, then averaged. Common data end: 2026Q1. ETS fell back to seasonal naive 0 time(s).

## Aggregate

| model | MAPE | sMAPE | MASE | MASE median | fold MAPE std | fold MAPE var | # companies best | cells |
|---|---|---|---|---|---|---|---|---|
| Naive | 8.176 | 8.343 | 1.560 | 1.417 | 3.064 | 11.784 | 1 | 120 |
| Seasonal naive | 6.266 | 6.520 | 1.171 | 0.907 | 1.872 | 4.445 | 3 | 120 |
| ETS (damped, log) | 4.405 | 4.365 | 0.802 | 0.689 | 2.043 | 5.180 | 3 | 120 |
| LightGBM (revenue features) | 4.324 | 4.303 | 0.787 | 0.720 | 1.851 | 4.117 | 2 | 120 |
| LightGBM + macro | 4.423 | 4.398 | 0.811 | 0.730 | 1.772 | 3.624 | 1 | 120 |

Stability = per company, the std (and variance) of fold-level MAPE across folds, averaged over companies. Lower is more stable.

## MASE by company

| ticker | naive | seasonal_naive | ets | lgbm | lgbm_macro |
|---|---|---|---|---|---|
| AAPL | 2.060 | 0.690 | 0.928 | 0.609 | 0.649 |
| AMZN | 1.826 | 1.693 | 0.527 | 0.681 | 0.678 |
| GOOGL | 1.059 | 1.316 | 0.400 | 0.601 | 0.596 |
| HD | 1.862 | 0.992 | 1.113 | 1.354 | 1.357 |
| KO | 0.749 | 0.502 | 0.390 | 0.342 | 0.342 |
| MSFT | 1.631 | 2.315 | 0.854 | 1.012 | 0.970 |
| NKE | 0.819 | 0.980 | 1.549 | 1.195 | 1.288 |
| PG | 1.043 | 0.575 | 0.729 | 0.631 | 0.642 |
| TGT | 2.687 | 0.634 | 0.920 | 0.948 | 0.948 |
| WMT | 1.866 | 2.016 | 0.610 | 0.494 | 0.639 |

## MAPE % by company

| ticker | naive | seasonal_naive | ets | lgbm | lgbm_macro |
|---|---|---|---|---|---|
| AAPL | 14.93 | 4.92 | 6.67 | 4.59 | 4.94 |
| AMZN | 10.90 | 10.39 | 3.38 | 4.14 | 4.12 |
| GOOGL | 8.42 | 10.54 | 3.44 | 5.09 | 5.00 |
| HD | 8.34 | 4.41 | 5.00 | 6.15 | 6.18 |
| KO | 6.33 | 4.31 | 3.30 | 2.88 | 2.88 |
| MSFT | 8.37 | 12.04 | 4.42 | 5.33 | 5.10 |
| NKE | 4.99 | 5.97 | 9.52 | 7.25 | 7.80 |
| PG | 4.37 | 2.42 | 3.06 | 2.69 | 2.74 |
| TGT | 10.39 | 2.55 | 3.71 | 3.86 | 3.85 |
| WMT | 4.72 | 5.12 | 1.55 | 1.27 | 1.62 |

## Fold-to-fold std of MAPE by company

| ticker | naive | seasonal_naive | ets | lgbm | lgbm_macro |
|---|---|---|---|---|---|
| AAPL | 6.31 | 2.71 | 2.35 | 2.81 | 2.71 |
| AMZN | 2.33 | 0.90 | 1.92 | 1.97 | 1.78 |
| GOOGL | 2.87 | 3.27 | 2.72 | 3.38 | 2.91 |
| HD | 3.40 | 2.02 | 1.60 | 2.15 | 2.05 |
| KO | 2.15 | 1.47 | 1.72 | 0.90 | 0.74 |
| MSFT | 2.38 | 2.80 | 1.44 | 1.64 | 1.55 |
| NKE | 2.31 | 3.03 | 4.62 | 2.36 | 2.31 |
| PG | 1.57 | 1.14 | 1.54 | 1.07 | 1.22 |
| TGT | 5.65 | 0.50 | 1.85 | 1.70 | 1.60 |
| WMT | 1.68 | 0.87 | 0.67 | 0.55 | 0.87 |

## MAPE % by horizon

| model | MAPE_h1 | MAPE_h2 | MAPE_h3 | MAPE_h4 |
|---|---|---|---|---|
| ets | 3.58 | 4.55 | 4.55 | 4.93 |
| lgbm | 3.35 | 4.28 | 4.58 | 5.09 |
| lgbm_macro | 3.43 | 4.35 | 4.68 | 5.23 |
| naive | 8.02 | 9.06 | 8.98 | 6.64 |
| seasonal_naive | 6.07 | 6.08 | 6.27 | 6.64 |

## Bootstrap 95% CIs: mean MASE difference (LightGBM minus comparator; negative = LightGBM better)

`cells` resamples (company, fold) pairs; `companies` resamples whole companies (respects correlation between overlapping folds of the same company, so it is the more conservative interval).

| model | vs | resample | mean_diff | ci_low | ci_high | significant (CI excludes 0) |
|---|---|---|---|---|---|---|
| lgbm | naive | cells | -0.774 | -0.934 | -0.616 | yes |
| lgbm | naive | companies | -0.774 | -1.157 | -0.398 | yes |
| lgbm | seasonal_naive | cells | -0.385 | -0.533 | -0.238 | yes |
| lgbm | seasonal_naive | companies | -0.385 | -0.804 | -0.004 | yes |
| lgbm | ets | cells | -0.015 | -0.098 | +0.063 | no |
| lgbm | ets | companies | -0.015 | -0.139 | +0.104 | no |
| lgbm | lgbm_macro | cells | -0.024 | -0.060 | +0.009 | no |
| lgbm | lgbm_macro | companies | -0.024 | -0.060 | +0.004 | no |
| lgbm_macro | naive | cells | -0.749 | -0.910 | -0.593 | yes |
| lgbm_macro | naive | companies | -0.749 | -1.125 | -0.370 | yes |
| lgbm_macro | seasonal_naive | cells | -0.360 | -0.503 | -0.217 | yes |
| lgbm_macro | seasonal_naive | companies | -0.360 | -0.765 | +0.025 | no |
| lgbm_macro | ets | cells | +0.009 | -0.073 | +0.089 | no |
| lgbm_macro | ets | companies | +0.009 | -0.096 | +0.112 | no |
| lgbm_macro | lgbm | cells | +0.024 | -0.009 | +0.060 | no |
| lgbm_macro | lgbm | companies | +0.024 | -0.004 | +0.060 | no |

