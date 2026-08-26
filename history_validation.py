import pandas as pd


class HistoryValidationError(Exception):
    pass

class DifferentLastDateError(HistoryValidationError):
    pass

class MissingDateError(HistoryValidationError):
    pass

class HistoryTooShortError(HistoryValidationError):
    pass


def check_data(df):
    df = df.sort_values(["product_id", "date"])
    if df.groupby("product_id")["date"].max().nunique() != 1:
        raise DifferentLastDateError("У товаров разные последние даты в истории продаж")

    if (df.groupby("product_id")["date"].diff().dropna() != pd.Timedelta(days = 1)).any():
        raise MissingDateError("В истории продаж есть пропущеные дни")

    if not (df.groupby("product_id").size() >= 90).all():
        raise HistoryTooShortError("Для каждого товара требуется минимум 90 записей")
    return df


