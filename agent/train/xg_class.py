import xg_learn as m

#train_dataset translation

q10= m.run_optimize_time_seriesPercentile(train_dataset, 0.1)
q50= m.run_optimize_time_seriesPercentile(train_dataset, 0.5)
q90= m.run_optimize_time_seriesPercentile(train_dataset, 0.9)

def predict_growth_probability(q10, q50, q90, price):
    
m.run_optimize(train_dataset)