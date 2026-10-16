# DO integration and residual screen

## Outcome

Official annual-report DO minima were integrated as annual features without altering the daily environmental master. Seven years have verified annual minima (2014, 2016, 2019–2023). Only six years have both DO and an accumulated-temperature residual because the 2020 surface-temperature series needed for that residual is absent.

No multivariable mortality model was fitted to the DO subset. Six complete years are insufficient for a stable Heat + DO or interaction model; the correlations below are screening statistics only.

## Verified DO definition

- Variable: annual minimum of the annual report's survey-date spatial mean DO, mg/L.
- Depths: 0 m, 2 m, 5 m, 10 m, and bottom minus 1 m.
- Station set: Tsukune, Ninoshima Gakuen, and Eba (three-station mean).
- Important mismatch: temperature and salinity city means use a five-station set. DO is therefore a related Hiroshima Bay indicator, not a co-located measurement.
- 2015: unavailable because the H27 report states that DO was missing owing to instrument malfunction.

## Exploratory screen

Complete-case n = 6. The largest absolute descriptive relationships were:

- do_5m_annual_min_mg_L vs residual_pct_points: r=0.685 (n=6)
- do_b1m_annual_min_mg_L vs mortality_oct_dec_mean_pct: r=-0.608 (n=6)
- do_5m_annual_min_mg_L vs mortality_oct_dec_mean_pct: r=0.448 (n=6)
- do_0m_annual_min_mg_L vs residual_pct_points: r=0.425 (n=6)
- do_2m_annual_min_mg_L vs residual_pct_points: r=0.341 (n=6)

These values must not be treated as inferential evidence. In particular, depth-specific signs can be unstable at n=6 and annual minima do not encode the duration or timing of low-DO exposure.

## Research implications

1. The verified annual DO minima are suitable for year-level fingerprinting and prioritizing residual years.
2. They are not suitable for daily lag analysis or for identifying whether low DO preceded mortality.
3. The next defensible step is to extract survey-date × depth DO observations from the annual tables for additional years, retain the three-station definition, and derive mechanism-aligned features such as Jul–Sep minimum, days/observations below 4 and 2 mg/L, and pre-mortality 14/30/60-day summaries.
4. The 2023 heat-model residual is −4.10 percentage points, so the current accumulated-temperature model modestly overpredicts mortality; annual minimum DO alone cannot explain this with adequate sample size.

## Files

- `annual_environment_mortality_do_features.csv`: one row per year with outcome, accumulated-temperature feature, model residual, and verified DO minima.
- `do_exploratory_correlations.csv`: descriptive correlations only.
- `do_integration_validation.csv`: join, range, row-count, and non-imputation checks.
- `do_integration_summary.json`: machine-readable summary.
