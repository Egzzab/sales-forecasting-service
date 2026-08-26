from evaluation import tcv
import numpy as np
import pandas as pd
from registry import model_name, model_weight





def grid(model, X, cv =4, **other_param):
    dc_param = other_param["dc_param"]
    param_for_model = dc_param[model.__name__]
    param_res = []
    val_prod = None
    for param in param_for_model:
        res=tcv(model, X, param, cv= cv, **other_param)
        if val_prod is None:
            val_prod = res.loc["val_sales"].to_numpy()
        param_res.append(res.loc["Pooled_wape"].to_numpy())    
    df_param_res = pd.DataFrame(param_res, columns = X["product_id"].unique())
    res = {}
    if model.__name__ != 'cat_str_fd':
        for prod in df_param_res.columns:
            score_prod = df_param_res[prod]
            nparam = score_prod.idxmin()
            score = score_prod.loc[nparam]
            param = param_for_model[nparam]
            res[prod] = [score, param]
    elif model.__name__ == 'cat_str_fd':
        if (val_prod>0).any():
            score_prods = df_param_res[df_param_res.columns[val_prod>0]].mean(axis = 1)
        else:
            score_prods = df_param_res.mean(axis = 1)
        best_nparam = score_prods.idxmin()
        param = param_for_model[best_nparam]
        for prod in df_param_res.columns:
            score_prod = df_param_res[prod].loc[best_nparam]
            res[prod] = [score_prod, param]

    metrics = np.where(
        val_prod>0,
        "WAPE",
        "SAE"
    )

    for k, prod in enumerate(res):
        res[prod].append(metrics[k])
    
    return res



def all_grid(Xy_train, **other_param):
    sp_model = model_name.values()  
    res = {}
    for model in sp_model:
        res[model.__name__] = grid(model, Xy_train, **other_param)
    prod_score_param = {}
    for prod in Xy_train["product_id"].unique():
        best_score_in_model = []
        for model, info in res.items():
            score, param, metric = info[prod]
            best_score_in_model.append((score, model_weight[model], model, param, metric))
        best_score_prod = min(best_score_in_model)
        prod_score_param[prod] = [best_score_prod[0], *best_score_prod[2:]]       
    return prod_score_param



    