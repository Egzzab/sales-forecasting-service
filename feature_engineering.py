import numpy as np
import pandas as pd
#функция обработки данных -- создание признаков
def f_ing(df, orig_date):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values(["product_id", "date"], inplace = True)
    lag_1=df.groupby("product_id")["sales"].shift(1)
    df["lag_1"]= lag_1
    lag_7=df.groupby("product_id")["sales"].shift(7)
    df["lag_7"]= lag_7
    roll_mean= df.groupby("product_id")["sales"].transform(lambda x: x.shift(1).rolling(7).mean())
    df["roll_mean_7"]= roll_mean
    roll_std= df.groupby("product_id")["sales"].transform(lambda x: x.shift(1).rolling(7).std())
    df["roll_std_7"]= roll_std
    df["day"]=df["date"].dt.day
    df["month"]=df["date"].dt.month
    df["day_of_week"]= df['date'].dt.dayofweek
    df["is_weekend"]= (df["day_of_week"].isin([5,6])).astype(int)
    df["idx_time"]=(df["date"]-orig_date).dt.days
    df["diff_1"]= df.groupby("product_id")["sales"].transform(lambda x: x.diff().shift(1))
    df["diff_7"]= df.groupby("product_id")["sales"].transform(lambda x: x.diff(7).shift(1))
    df["start_month"] = (df["date"].dt.day<=5).astype(int)
    df["end_month"] = (df["date"].dt.day>26).astype(int)
    df["sin_month"] = np.sin(2 * np.pi * (df['month']-1)/12)
    df["cos_month"] = np.cos(2 * np.pi * (df['month']-1)/12)
    df["sin_dw"] = np.sin(2 * np.pi * df['day_of_week']/7)
    df["cos_dw"] = np.cos(2 * np.pi * df['day_of_week']/7)
    df["sin_day"] = np.sin(2 * np.pi * (df['day']-1)/df["date"].dt.days_in_month)
    df["cos_day"] = np.cos(2 * np.pi * (df['day']-1)/df["date"].dt.days_in_month)
    df = df.dropna()
    return df