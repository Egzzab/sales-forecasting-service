from data import add_company, get_sales_history, save_sales_history, get_config, save_config, CompanyDataNotFoundError, ConfigNotFoundError
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
from pandas import Timestamp
import psycopg
from uuid import uuid4
from config import get_var_db

@pytest.fixture
def df():
    return pd.DataFrame({'date': [Timestamp('2024-01-01 00:00:00'),
    Timestamp('2024-01-01 00:00:00'),
    Timestamp('2024-01-02 00:00:00'),
    Timestamp('2024-01-02 00:00:00'),
    Timestamp('2024-01-03 00:00:00'),
    Timestamp('2024-01-03 00:00:00')],
    'product_id': ['P001', 'P002', 'P001', 'P002', 'P001', 'P002'],
    'category': ['food', 'cosmetics', 'food', 'cosmetics', 'food', 'cosmetics'],
    'price': [1293.17, 515.55, 1317.96, 511.6, 1300.03, 502.77],
    'promo': [False, False, False, False, False, False],
    'sales': [30, 11, 19, 13, 19, 11]}
    )


def test_add_company_get_save_history(df):
    company_id = add_company("test")
    try:
        save_sales_history(df, company_id)
        res_df, orig_date = get_sales_history(company_id)
        assert orig_date == df["date"].min()
        assert pd.api.types.is_datetime64_any_dtype(res_df["date"])
        assert pd.api.types.is_float_dtype(res_df["price"])
        res_df = res_df.sort_values(["date", 'product_id']).reset_index(drop=True).drop("company_id", axis = 1)
        pd.testing.assert_frame_equal(df, res_df, check_dtype=False)
        df.loc[1, "price"] = 19
        save_sales_history(df, company_id)
        res_df, _ = get_sales_history(company_id)
        res_df = res_df.sort_values(["date", 'product_id']).reset_index(drop=True).drop("company_id", axis = 1)
        pd.testing.assert_frame_equal(df, res_df, check_dtype=False)
    finally:
        with psycopg.connect(**get_var_db()) as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM sales_history WHERE company_id = %s", (company_id,))
                cursor.execute("DELETE FROM companies WHERE company_id = %s", (company_id,))


def test_save_and_get_config():
    company_id = add_company(f"test_config_{uuid4().hex}")
    try:
        conf_v1 = {
            "updated_at": "2026-08-31T10:00:00+00:00",
            "products": {"P001": {"model": "bl_lag1", "score": 1.0}},
        }
        save_config(company_id, conf_v1)
        assert get_config(company_id) == conf_v1

        conf_v2 = {
            "updated_at": "2026-08-31T11:00:00+00:00",
            "products": {"P001": {"model": "bl_lag7", "score": 0.8}},
        }
        save_config(company_id, conf_v2)
        assert get_config(company_id) == conf_v2
    finally:
        with psycopg.connect(**get_var_db()) as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM model_configs WHERE company_id = %s", (company_id,))
                cursor.execute("DELETE FROM companies WHERE company_id = %s", (company_id,))


def test_get_sales_history_empty_data():
    fake_connection = MagicMock()
    fake_cursor = MagicMock()
    with patch("data.psycopg.connect") as fake_connect:
        fake_connect.return_value.__enter__.return_value = fake_connection
        fake_connection.cursor.return_value.__enter__.return_value = fake_cursor
        fake_cursor.description = []
        fake_cursor.fetchall.return_value = []
        with pytest.raises(CompanyDataNotFoundError):
            get_sales_history(1)


def test_get_config_empty_data():
    fake_connection = MagicMock()
    fake_cursor = MagicMock()
    fake_cursor.fetchone.return_value = None
    with patch("data.psycopg.connect") as fake_connect:
        fake_connect.return_value.__enter__.return_value = fake_connection
        fake_connection.cursor.return_value.__enter__.return_value = fake_cursor
        with pytest.raises(ConfigNotFoundError):
            get_config(1)


