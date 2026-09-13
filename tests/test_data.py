from data_base import add_company, get_sales_history, save_sales_history, get_config, save_config, CompanyDataNotFoundError, ConfigNotFoundError, make_engine, SalesHistory, Company, ModelConfigs, add_user, get_user, User, EmailAlreadyExistsError
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
from pandas import Timestamp
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import delete
from auth_layer import hash_password, verify_password

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
    email = f"alpak_{uuid4().hex}@xz.i"
    password = "oralcamp1"
    password_hash = hash_password(password)
    company_id = None
    try:
        user_id = add_user(email, password_hash)
        company_id = add_company(f"test_{uuid4().hex}", user_id)
        save_sales_history(df, company_id)
        res_df, orig_date = get_sales_history(company_id)
        assert orig_date == df["date"].min()
        assert pd.api.types.is_datetime64_any_dtype(res_df["date"])
        assert pd.api.types.is_float_dtype(res_df["price"])
        res_df = res_df.sort_values(["date", 'product_id']).reset_index(drop=True)      #.drop("company_id", axis = 1)
        pd.testing.assert_frame_equal(df, res_df, check_dtype=False)
        df.loc[1, "price"] = 19
        save_sales_history(df, company_id)
        res_df, _ = get_sales_history(company_id)
        res_df = res_df.sort_values(["date", 'product_id']).reset_index(drop=True)            #.drop("company_id", axis = 1)
        pd.testing.assert_frame_equal(df, res_df, check_dtype=False)
    finally:
        with Session(make_engine()) as session:
            stmt = delete(SalesHistory).where(SalesHistory.company_id == company_id)
            session.execute(stmt)
            stmt = delete(Company).where(Company.company_id == company_id)
            session.execute(stmt)
            stmt = delete(User).where(User.email == email)
            session.execute(stmt)
            session.commit()



def test_save_and_get_config():
    email = f"alpak_{uuid4().hex}@xz.i"
    password = "oralcamp1"
    password_hash = hash_password(password)
    company_id = None
    try:
        user_id = add_user(email, password_hash)
        company_id = add_company(f"test_config_{uuid4().hex}", user_id)
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
        with Session(make_engine()) as session:
            stmt = delete(ModelConfigs).where(ModelConfigs.company_id == company_id)
            session.execute(stmt)
            stmt = delete(Company).where(Company.company_id == company_id)
            session.execute(stmt)
            stmt = delete(User).where(User.email == email)
            session.execute(stmt)
            session.commit()



def test_get_sales_history_empty_data():
    fake_session = MagicMock()
    with patch("data_base.Session") as fake_Session:
        fake_Session.return_value.__enter__.return_value = fake_session
        fake_session.execute.return_value.all.return_value = []
        with pytest.raises(CompanyDataNotFoundError):
            get_sales_history(1)


def test_get_config_empty_data():
    fake_session = MagicMock()
    with patch("data_base.Session") as fake_Session:
        fake_Session.return_value.__enter__.return_value = fake_session
        fake_session.scalars.return_value.one_or_none.return_value = None
        with pytest.raises(ConfigNotFoundError):
            get_config(1)


def test_add_get_user():
    email = f"alpak_{uuid4().hex}@xz.i"
    password = "oralcamp1"
    password_hash = hash_password(password)
    try:
        user_id = add_user(email, password_hash)
        user = get_user(email)
    finally:
        with Session(make_engine()) as session:
            stmt = delete(User).where(User.email == email)
            session.execute(stmt)
            session.commit()

    assert user.user_id == user_id
    assert user.email == email
    assert user.password_hash != password
    assert user.password_hash == password_hash
    assert verify_password(password, user.password_hash)

def test_add_user_email_exists_error():
    email = f"alpak_{uuid4().hex}@xz.i"
    password = "oralcamp1"
    password_hash = hash_password(password)
    try:
        add_user(email, password_hash)
        with pytest.raises(EmailAlreadyExistsError):
            add_user(email, password_hash)
    finally:
        with Session(make_engine()) as session:
            stmt = delete(User).where(User.email == email)
            session.execute(stmt)
            session.commit()      

def test_get_user_no_exists():
    res = get_user(f"alpak_{uuid4().hex}@xz.i")
    assert res is None
    
