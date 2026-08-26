from models import bl_lag1, bl_lag7, ridge_seq_mm, ridge_str_fd, cat_str_fd, prph

model_name = {
    "bl_lag1": bl_lag1, 
    "bl_lag7": bl_lag7, 
    "ridge_seq_mm": ridge_seq_mm, 
    "ridge_str_fd": ridge_str_fd, 
    "cat_str_fd": cat_str_fd, 
    "prph": prph
}

model_weight = {
    "bl_lag1": 0,
    "bl_lag7": 1,
    "ridge_str_fd": 2,
    "ridge_seq_mm": 3,
    "prph": 4,
    "cat_str_fd": 5,
}