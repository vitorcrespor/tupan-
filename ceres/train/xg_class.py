from scipy.stats import norm
from train import analytics as a
import numpy as np

#train_dataset translation

def tendency_prediction(real_estate, time_span):
    log_q10= a.analyze_tendency(real_estate, 0.1, time_span)
    log_q50= a.analyze_tendency(real_estate, 0.5, time_span)
    log_q90= a.analyze_tendency(real_estate, 0.9, time_span)
    _mean= log_q50
    _stdDev= (log_q90 - log_q10)/(2 * 1.2815)

    target_growth_pct= 1- np.expm1(log_q50)/real_estate.price
    target_prices= real_estate * (1.0 + target_growth_pct / 100.0)
    target_log_threshold= np.log1p(target_prices)

    z_scores= (target_log_threshold - _mean) / _stdDev
    certainty_pct= (1.0 - norm.cdf(z_scores)) * 100.0
    interval= [np.expm1(log_q10), np.expm1(log_q50), np.expm1(log_q90)]

    return certainty_pct, interval

