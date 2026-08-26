import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import Ridge
from feature_engineering import f_ing
import numpy as np
from sklearn.preprocessing import FunctionTransformer
from catboost import CatBoostRegressor
import prophet_setup
from prophet import Prophet


def bl_lag1(X, *arg, **other_param):
    pas=X[X["date"]==X["date"].max()][["product_id", "sales"]]
    pas=pas.set_index("product_id")
    sl_pred={prod: [pas["sales"].loc[prod]]*7 for prod in pas.index}
    return pd.DataFrame(sl_pred, index=[i for i in range(1, 8)])

def bl_lag7(X, *arg, **other_param):
    point = X['date'].max()
    sl_pred = {}
    for i in range(1, 8):
        point=point + pd.Timedelta(days=1)
        lag = point - pd.Timedelta(weeks=1)
        pas = X[X['date'] == lag].set_index("product_id")["sales"]
        sl_pred[i] = pas

    pred_dt = pd.DataFrame(sl_pred).transpose()
    pred_dt.columns.name= None
    return pred_dt

def ridge_seq_mm(X, price_for_week, promo_for_week, param, **other_param):
    categorical_nominal = ["product_id", "category", "month", "day_of_week"]
    numeric = ["price", "lag_1", "lag_7", "roll_mean_7", "roll_std_7", "idx_time", 'diff_1', 'diff_7']
    binary = ['promo', "start_month", "end_month", "is_weekend"]
    col_trans = ColumnTransformer([
    ("numeric", StandardScaler(), numeric),
    ("categorical_nominal", OneHotEncoder(handle_unknown='ignore'), categorical_nominal),
    ("binary", "passthrough", binary)
])
    model = Pipeline([("preprocessor", col_trans), ("model", Ridge(**param))])
    return seq_pred_2(X, model, price_for_week, promo_for_week, **other_param)

def seq_pred_2(X, model, price_for_week, promo_for_week, **other_param):
    orig_date = other_param["orig_date"]
    X_train = X
    y_train = X["sales"]
    point = X_train["date"].max()
    fin = {}
    for prod in X_train["product_id"].unique():
        X_train_prod = X_train[X_train["product_id"] == prod]
        y_train_prod = y_train[X_train["product_id"] == prod]
        model.fit(X_train_prod, y_train_prod)
        prepr = X_train_prod[['date', 'product_id', 'category', 'price', 'promo', 'sales']].copy()
        new_day = prepr[prepr["date"] == point].copy()
        res_prod = []
        price_prod= price_for_week[prod]
        promo_prod= promo_for_week[prod]
        for day in range(1, 8):
            price_day = price_prod[day-1]
            promo_day = promo_prod[day-1]
            new_day["date"] = new_day["date"] + pd.Timedelta(days=1)
            new_day["price"] = price_day
            new_day["promo"] = promo_day
            new_X = pd.concat([prepr, new_day])
            new_df = f_ing(new_X, orig_date) 
            one_day=new_df[new_df["date"] == new_day["date"].max()]
            res = model.predict(one_day)[0]
            res = 0 if res< 0 else res
            res_prod.append(res)
            new_day["sales"] = res
            prepr = pd.concat([prepr, new_day])
        fin[prod] = res_prod    
    return pd.DataFrame(fin, index=range(1, 8))


def ridge_str_fd(X, price_for_week, promo_for_week, param, **other_param):
    categorical_nominal = ["product_id", "category", "month", "day_of_week", "horizont"]
    numeric = ["price", "lag_1", "lag_7", "roll_mean_7", "roll_std_7", "idx_time", 'diff_1', 'diff_7', "curr_sales"]
    binary = ['promo', "start_month", "end_month", "is_weekend"]
    col_trans = ColumnTransformer([
    ("numeric", StandardScaler(), numeric),
    ("categorical_nominal", OneHotEncoder(handle_unknown='ignore'), categorical_nominal),
    ("binary", "passthrough", binary)
])
    model = Pipeline([("preprocessor", col_trans), ("model", Ridge(**param))])
    return str_pred_fst(X, model, price_for_week, promo_for_week, **other_param)



def str_pred_fst(X, model, price_for_week, promo_for_week, **other_param):
    orig_date = other_param['orig_date']
    last_date = X["date"].max()
    last_day = X[X["date"] == X["date"].max()]
    sales_ld= last_day["sales"]
    fin = {}
    dfs = []
    ld = []
    for hor in range(1, 8):
        curr_sales = X["sales"]
        sales_hor = X.groupby("product_id")["sales"].shift(-hor)
        month = X.groupby("product_id")["month"].shift(-hor)
        day_of_week = X.groupby("product_id")["day_of_week"].shift(-hor)
        price = X.groupby("product_id")["price"].shift(-hor)
        idx_time = X.groupby("product_id")["idx_time"].shift(-hor)
        promo = X.groupby("product_id")["promo"].shift(-hor)
        start_month = X.groupby("product_id")["start_month"].shift(-hor)
        end_month = X.groupby("product_id")["end_month"].shift(-hor)
        is_weekend = X.groupby("product_id")["is_weekend"].shift(-hor)
        X_train = X.copy()
        X_train["curr_sales"] = curr_sales
        X_train["month"] = month
        X_train["day_of_week"] = day_of_week
        X_train["price"] = price
        X_train["idx_time"] = idx_time
        X_train["promo"] = promo
        X_train["start_month"] = start_month
        X_train["end_month"] = end_month
        X_train["is_weekend"] = is_weekend
        X_train["horizont"] = hor
        X_train = X_train[sales_hor.notnull()]
        X_train["y_train"] = sales_hor.dropna()
        dfs.append(X_train)
        ld_hor = last_day.copy()
        cur_date = last_date + pd.Timedelta(days= hor)
        ld_hor["curr_sales"] = sales_ld
        ld_hor["month"] = cur_date.month
        ld_hor["day_of_week"] = cur_date.dayofweek
        ld_hor["idx_time"] = (cur_date - orig_date).days
        ld_hor["start_month"] = int(cur_date.day<=5)
        ld_hor["end_month"] = int(cur_date.day>26)
        ld_hor["is_weekend"] = int(cur_date.dayofweek in [5,6])
        ld_hor["horizont"] = hor
        ld.append(ld_hor)
    test = pd.concat(ld, ignore_index = True)
    all_df = pd.concat(dfs, ignore_index=True)
    for prod in X["product_id"].unique():
        price_prod= price_for_week[prod]
        promo_prod= promo_for_week[prod]
        prod_df = all_df[all_df["product_id"] == prod]
        model.fit(prod_df, prod_df["y_train"])
        df_for_pred = test[test["product_id"] == prod].copy()
        df_for_pred["price"] = price_prod
        df_for_pred["promo"] = promo_prod
        y_pred = model.predict(df_for_pred)
        y_pred = np.maximum(y_pred, 0)
        fin[prod] = y_pred
    return pd.DataFrame(fin, index=range(1, 8))

def cat_str_fd(X, price_for_week, promo_for_week, param, **other_param):
    categorical_nominal = ["product_id", "category", "month", "day_of_week"]
    numeric = ["price", "lag_1", "lag_7", "roll_mean_7", "roll_std_7", "idx_time", 'diff_1', 'diff_7', "horizont", "curr_sales"]
    binary = ['promo', "start_month", "end_month", "is_weekend"]
    col_for_cat = categorical_nominal+numeric+binary
    selector = FunctionTransformer(func= lambda df: df[col_for_cat])
    model = Pipeline([("preprocessor", selector), ("model", CatBoostRegressor(cat_features= categorical_nominal, verbose=False, thread_count=-1, **param))])
    return str_pred_fst_cat(X, model, price_for_week, promo_for_week, **other_param)

def str_pred_fst_cat(X, model, price_for_week, promo_for_week, **other_param):
    orig_date = other_param['orig_date']    
    last_date = X["date"].max()
    last_day = X[X["date"] == X["date"].max()]
    sales_ld= last_day["sales"]
    dfs = []
    ld = []
    for hor in range(1, 8):
        curr_sales = X["sales"]
        sales_hor = X.groupby("product_id")["sales"].shift(-hor)
        month = X.groupby("product_id")["month"].shift(-hor)
        day_of_week = X.groupby("product_id")["day_of_week"].shift(-hor)
        price = X.groupby("product_id")["price"].shift(-hor)
        idx_time = X.groupby("product_id")["idx_time"].shift(-hor)
        promo = X.groupby("product_id")["promo"].shift(-hor)
        start_month = X.groupby("product_id")["start_month"].shift(-hor)
        end_month = X.groupby("product_id")["end_month"].shift(-hor)
        is_weekend = X.groupby("product_id")["is_weekend"].shift(-hor)
        X_train = X.copy()
        X_train["curr_sales"] = curr_sales
        X_train["month"] = month
        X_train["day_of_week"] = day_of_week
        X_train["price"] = price
        X_train["idx_time"] = idx_time
        X_train["promo"] = promo
        X_train["start_month"] = start_month
        X_train["end_month"] = end_month
        X_train["is_weekend"] = is_weekend
        X_train["horizont"] = hor
        X_train = X_train[sales_hor.notnull()]
        X_train["y_train"] = sales_hor.dropna()
        dfs.append(X_train)
        # далее дф для прогноза
        ld_hor = last_day.copy()
        cur_date = last_date + pd.Timedelta(days= hor)
        ld_hor["curr_sales"] = sales_ld
        ld_hor["month"] = cur_date.month
        ld_hor["day_of_week"] = cur_date.dayofweek
        ld_hor["idx_time"] = (cur_date - orig_date).days
        ld_hor["start_month"] = int(cur_date.day<=5)
        ld_hor["end_month"] = int(cur_date.day>26)
        ld_hor["is_weekend"] = int(cur_date.dayofweek in [5,6])
        ld_hor["horizont"] = hor
        ld.append(ld_hor)
    test = pd.concat(ld, ignore_index = True)
    all_df = pd.concat(dfs, ignore_index=True)
    all_df["month"] = all_df["month"].astype(int)
    all_df["day_of_week"] = all_df["day_of_week"].astype(int)
    test["month"] = test["month"].astype(int)
    test["day_of_week"] = test["day_of_week"].astype(int)
    y_train = all_df["y_train"]
    model.fit(all_df, y_train)
    test = test.sort_values(["product_id", "horizont"]).reset_index(drop= True)
    for prod in test["product_id"].unique():
        mask = test["product_id"] == prod
        test.loc[mask, "price"] = price_for_week[prod]
        test.loc[mask, "promo"] = promo_for_week[prod]
    y_pred = model.predict(test)
    y_pred = np.maximum(y_pred, 0).reshape(-1, 7).transpose()
    return pd.DataFrame(y_pred, columns= test["product_id"].unique(), index= range(1, 8))

def prph(X, price_for_week, promo_for_week, param, **other_param):
    prph_df = X[["date","product_id", "sales", "price", "promo"]].rename({"date":"ds", "sales":"y"}, axis=1)
    res ={}
    for prod in X["product_id"].unique():
        prod_df = prph_df[prph_df["product_id"] == prod].drop("product_id", axis = 1)
        model= Prophet(**param)
        model.add_seasonality(name="monthly", period=30.5, fourier_order=5)
        model.add_regressor("price")
        model.add_regressor("promo")
        model.fit(prod_df)
        pred_df = model.make_future_dataframe(periods= 7, freq="D", include_history=False)
        price_prod = price_for_week[prod]
        promo_prod = promo_for_week[prod]
        pred_df["price"] = price_prod
        pred_df["promo"]= promo_prod
        forecast = model.predict(pred_df)
        y_pred = forecast["yhat"].apply(lambda x: 0 if x<0 else x)
        res[prod]= y_pred.to_numpy()
    return pd.DataFrame(res, index = range(1, 8)) 

