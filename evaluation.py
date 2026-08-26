import numpy as np
import pandas as pd
from registry import model_name
from datetime import datetime, UTC
# метрики



# метрика wape
#def wape(y_true, y_pred):
    #return np.sum(np.abs(y_true - y_pred))/np.sum(np.abs(y_true))*100


# функция оценки
def score_met(pred_df, X_test):
    #score= {}
    wp_for_prod = {}
    for prod in pred_df.columns:
        #fst_week=Xy_val["date"].min()+ pd.Timedelta(weeks=1)
        pred_week = pred_df[prod].values
        #true_week = Xy_val[(Xy_val["date"]<fst_week) & (Xy_val["product_id"] == prod)]["sales"].values
        true_week = X_test[X_test["product_id"] == prod]["sales"].values
        #mae= mean_absolute_error(true_week, pred_week)
        #rmse= root_mean_squared_error(true_week, pred_week)
        #wap = wape(true_week, pred_week)
        sum_of_err = np.sum(np.abs(true_week - pred_week))
        val_sales = np.sum(np.abs(true_week))
        #score[prod] = [mae, rmse, wap]
        wp_for_prod[prod] = [sum_of_err, val_sales]
    #true_all_sales = Xy_val[(Xy_val["date"]<fst_week)].sort_values("product_id")["sales"].values
    #true_all_sales = X_test.sort_values("product_id")["sales"].values
    #pred_all_sales = pred_df.values.transpose().reshape(-1)
    #score["all"]=[mean_absolute_error(true_all_sales, pred_all_sales), root_mean_squared_error(true_all_sales, pred_all_sales), wape(true_all_sales, pred_all_sales)]
    return pd.DataFrame(wp_for_prod, index= ["sum_of_err", "val_sales"] )  #pd.DataFrame(score, index= ["mae", "rmse", "wape"] ), 


def tcv(model, X, param, cv = 4, **other_param):
    #cv_score = []
    met_for_gs= []
    time = X["date"].max()
    for week in range(cv, 0, -1):
        fin_train = time- pd.Timedelta(weeks = week)
        fin_test = fin_train + pd.Timedelta(weeks = 1)
        X_train = X[X["date"]<= fin_train]
        X_test = X[(X["date"]> fin_train) & (X["date"] <= fin_test)]
        price_for_week = {}
        promo_for_week = {}
        for prod in X["product_id"].unique():
            df_prod = X_test[X_test["product_id"] == prod]
            price_for_week[prod] = df_prod["price"].to_numpy()
            promo_for_week[prod] = df_prod["promo"].to_numpy()
        res = model(X_train, price_for_week, promo_for_week, param, **other_param) # адаптировать
        wp_for_prod = score_met(res, X_test) #score,
        #cv_score.append(score)
        met_for_gs.append(wp_for_prod)
    #score_for_model = pd.DataFrame(np.sum(cv_score, axis=0)/cv, index = ["mae", "rmse", "wape"], columns = (*X["product_id"].unique(), "all"))    
    sum_err_vol = np.sum(met_for_gs, axis= 0)

    sum_err = sum_err_vol[0].astype(float)
    val_sales = sum_err_vol[1]
    
    
    
    wape = np.divide(
        sum_err*100,
        val_sales,
        where = val_sales>0,
        out = sum_err
    )
        
    
    pooled_wape_for_prod = pd.DataFrame([wape, val_sales], columns= X["product_id"].unique(), index = ["Pooled_wape", "val_sales"])
    return pooled_wape_for_prod


def fin_test(X, prod_score_param, **other_param):
    fin = {}
    res_glob_cat = None
    being_cat= False
    for prod in prod_score_param:
        modeln = prod_score_param[prod][1]
        if being_cat and modeln == "cat_str_fd":
            fin[prod] = res_glob_cat[prod]          #.loc["Pooled_wape"]
            continue
        model = model_name[modeln]
        df_learn = X[X["product_id"] == prod] if modeln != "cat_str_fd" else X
        res = tcv(model, df_learn, prod_score_param[prod][2], **other_param)#
        if modeln == "cat_str_fd":
            res_glob_cat = res
            being_cat = True
        fin[prod] = res[prod]       #.loc["Pooled_wape"]   
    # делаем словарь для сиреализации
    config_dict = {}
    config_dict["updated_at"] = datetime.now(UTC).isoformat()
    products = {}
    for prod in prod_score_param:
        model_for_prod = prod_score_param[prod][1]
        parametrs = prod_score_param[prod][2]
        wape_prod= fin[prod].loc["Pooled_wape"]   
        metric = "WAPE" if (fin[prod].loc["val_sales"])>0 else "SAE"
        prod_info = {"model": model_for_prod, "parameters": parametrs, "score": wape_prod, "metric": metric}
        products[prod] = prod_info
    config_dict["products"] = products
    return config_dict 
    

def train_test(df):
    fin_val=df['date'].max()-pd.Timedelta(weeks=4)
    #fin_train=fin_val-pd.Timedelta(weeks=4)
    Xy_test=df[df["date"]>fin_val]
    Xy_train= df[df['date']<=fin_val] # fin_train
    return Xy_train, Xy_test

    