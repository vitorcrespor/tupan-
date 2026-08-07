import xg_learn as m

#train_dataset translation

log_q10= m.run_optimize_time_seriesPercentile(train_dataset, 0.1)
log_q50= m.run_optimize_time_seriesPercentile(train_dataset, 0.5)
log_q90= m.run_optimize_time_seriesPercentile(train_dataset, 0.9)

def predict_growth_probability(log_q10, log_q50, log_q90):
    _mean= log_q50
    _stdDev= (log_q90 - log_q10)/(2 * 1.2815)

m.run_optimize(train_dataset)