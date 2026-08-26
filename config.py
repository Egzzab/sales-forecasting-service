


dc_param = {
    'bl_lag1': [1],
    'bl_lag7': [1],
    'ridge_seq_mm': [
        {'alpha': 0.001},
        {'alpha': 0.01},
        {'alpha': 0.1},
        {'alpha': 1},
        {'alpha': 10},
        {'alpha': 100},
        {'alpha': 1000}
        ],
    'ridge_str_fd': [
        {'alpha': 0.001},
        {'alpha': 0.01},
        {'alpha': 0.1},
        {'alpha': 1},
        {'alpha': 10},
        {'alpha': 100},
        {'alpha': 1000}
        ],
    'cat_str_fd': [
        {'depth': 4, 'learning_rate': 0.05, 'iterations': 400, 'l2_leaf_reg': 5},
        {'depth': 6, 'learning_rate': 0.05, 'iterations': 400, 'l2_leaf_reg': 5},
        {'depth': 8, 'learning_rate': 0.05, 'iterations': 400, 'l2_leaf_reg': 5}
        ],
    'prph': [
        {'changepoint_prior_scale': 0.05, 'seasonality_prior_scale': 10.0, 'seasonality_mode': 'additive'}
        ]
}