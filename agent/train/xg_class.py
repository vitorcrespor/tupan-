import xg_learn as m
from scipy.stats import norm
import analytics as a

#train_dataset translation

def predict_growth_probability(real_estate):
    log_q10= a.analyze_tendency(real_estate, 0.1)
    log_q50= a.analyze_tendency(real_estate, 0.5)
    log_q90= a.analyze_tendency(real_estate, 0.9)
    _mean= log_q50
    _stdDev= (log_q90 - log_q10)/(2 * 1.2815)
    growth_probability = 1.0 - norm.cdf(real_estate.suggested_price, loc=_mean,
                                        scale=max(_stdDev, 1e-6))

    return float(growth_probability)

m.run_optimize(train_dataset)