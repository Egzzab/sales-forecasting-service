from registry import model_name
import pandas as pd
def make_forecast(X, config_dict, price_for_week, promo_for_week, **other_param):
    fin_pred = {}
    res_glob_cat = None
    being_cat= False
    for prod, info in config_dict["products"].items():
        modeln = info["model"]
        if being_cat and modeln == "cat_str_fd":
            fin_pred[prod] = res_glob_cat[prod].tolist()
            continue    
        model = model_name[modeln]
        df_learn = X[X["product_id"] == prod] if modeln != "cat_str_fd" else X
        param = info["parameters"]
        pred_prod = model(df_learn, price_for_week, promo_for_week, param, **other_param)############
        fin_pred[prod] = pred_prod[prod].tolist()
        if modeln == "cat_str_fd":
            res_glob_cat = pred_prod
            being_cat = True
    return fin_pred