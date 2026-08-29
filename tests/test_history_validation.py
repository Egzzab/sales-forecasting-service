import pandas as pd
from history_validation import check_data, DifferentLastDateError, MissingDateError, HistoryTooShortError
import pytest


@pytest.fixture
def df():
    dates = pd.date_range("2026-01-01", periods=100)
    fdf = pd.DataFrame({"date":dates, "product_id": "prod_1"})
    sdf = pd.DataFrame({"date":dates, "product_id": "prod_2"})
    return pd.concat([fdf, sdf], ignore_index=True)


def test_valid_history(df):
    check_data(df)

def test_diff_last_date(df):
    idx_date = df["date"].idxmax()
    df = df.drop(idx_date)
    with pytest.raises(DifferentLastDateError):
        check_data(df)

def test_missed_date(df):
    df = df.drop(10)
    with pytest.raises(MissingDateError):
        check_data(df)

def test_history_too_short(df):
    df = df.iloc[30:]
    with pytest.raises(HistoryTooShortError):
        check_data(df)
        



