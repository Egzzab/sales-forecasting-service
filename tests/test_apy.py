from apy import RequestData, app, RegisterData
from fastapi.testclient import TestClient
from pydantic import ValidationError
from unittest.mock import patch, MagicMock
from upload import SalesDataValidationError
from data_base import CompanyDataNotFoundError, ConfigNotFoundError, EmailAlreadyExistsError
from history_validation import HistoryValidationError
import pandas as pd
import pytest
from jwt import InvalidTokenError


def test_valid_request_data():
    request = RequestData(
        price={"P001": [0, 100.5, 101, 99.9, 102, 103.5, 104]},
        promo={"P001": [0, 1, 0, 1, 0, 0, 1]},
    )

    assert request.price == {"P001": [0, 100.5, 101, 99.9, 102, 103.5, 104]}
    assert request.promo == {"P001": [False, True, False, True, False, False, True]}


@pytest.mark.parametrize(
    "price,promo",
    [
        ({"P001": [100, 100, 100, 100, 100, 100]}, {"P001": [0, 0, 0, 0, 0, 0, 0]}),
        ({"P001": [100, 100, -1, 100, 100, 100, 100]}, {"P001": [0, 0, 0, 0, 0, 0, 0]}),
        ({"P001": [100, 100, 100, 100, 100, 100, 100]}, {"P001": [0, 0, 2, 0, 0, 0, 0]}),
        ({"P001": [100, 100, 100, 100, 100, 100, 100]}, {"P002": [0, 0, 0, 0, 0, 0, 0]}),
    ],
)
def test_invalid_request_data(price, promo):
    with pytest.raises(ValidationError):
        RequestData(price=price, promo=promo)


def test_create_company():
    client = TestClient(app)

    with (
        patch("apy.add_company", return_value=15) as mock_add_company,
        patch("apy.decode_access_token", return_value = 2) as fake_decoder
    ):
        response = client.post("/companies", json={"name": "  Test company  "}, headers={"Authorization": "Bearer fake_token"})
        empty_name_response = client.post("/companies", json={"name": "   "}, headers={"Authorization": "Bearer fake_token"})
        long_name_response = client.post("/companies", json={"name": "a" * 151}, headers={"Authorization": "Bearer fake_token"})

    assert response.status_code == 200
    assert response.json() == {"id": 15}
    fake_decoder.assert_called_with("fake_token")
    assert mock_add_company.call_args.args == ("Test company", 2)
    assert mock_add_company.call_count == 1
    assert empty_name_response.status_code == 422
    assert long_name_response.status_code == 422


@pytest.mark.parametrize(
    "validation_error,expected_status,expected_body",
    [
        (None, 200, {"status": "ready"}),
        (SalesDataValidationError("Некорректные данные"), 422, {"detail": "Некорректные данные"}),
    ],
    ids=["success", "validation_error"],
)
def test_upload_sales_history(validation_error, expected_status, expected_body):
    client = TestClient(app)
    raw_df = object()
    prepared_df = object()

    with (
        patch("apy.to_df", return_value=raw_df),
        patch("apy.prepare_sales_df", return_value=prepared_df) as mock_prepare,
        patch("apy.save_sales_history") as mock_save,
        patch("apy.decode_access_token", return_value = 2),
        patch("apy.find_user_have_company", return_value = object())
    ):
        if validation_error is not None:
            mock_prepare.side_effect = validation_error

        response = client.post(
            "/upload?company_id=7",
            files={"file": ("sales.csv", b"sales data", "text/csv")},
            headers={"Authorization": "Bearer fake_token"}
        )

    assert response.status_code == expected_status
    assert response.json() == expected_body
    if validation_error is None:
        assert mock_save.call_args.args[:2] == (prepared_df, 7)
    else:
        mock_save.assert_not_called()


@pytest.mark.parametrize(
    "path,payload",
    [
        (
            "/forecast?company_id=7",
            {
                "price": {"P001": [100, 100, 100, 100, 100, 100, 100]},
                "promo": {"P001": [0, 0, 0, 0, 0, 0, 0]},
            },
        ),
        ("/build_config?company_id=7", None),
    ],
    ids=["forecast", "build_config"],
)
@pytest.mark.parametrize(
    "error_type,expected_status,expected_detail",
    [
        (
            "missing_history",
            409,
            "В системе отсутствует история продаж для этой компании",
        ),
        ("invalid_history", 422, "Некорректная история"),
    ],
    ids=["missing_history", "invalid_history"],
)
def test_history_errors(path, payload, error_type, expected_status, expected_detail):
    client = TestClient(app)

    with (
        patch("apy.get_sales_history") as mock_get_history,
        patch("apy.check_data") as mock_check_data,
        patch("apy.decode_access_token", return_value = 2),
        patch("apy.find_user_have_company", return_value = object())
    ):
        if error_type == "missing_history":
            mock_get_history.side_effect = CompanyDataNotFoundError
        else:
            mock_get_history.return_value = (object(), object())
            mock_check_data.side_effect = HistoryValidationError("Некорректная история")

        if payload is None:
            response = client.post(path, headers={"Authorization": "Bearer fake_token"})
        else:
            response = client.post(path, json=payload, headers={"Authorization": "Bearer fake_token"})

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


def test_forecast_success():
    client = TestClient(app)
    forecast_df = pd.DataFrame({"product_id": ["P001"]})
    expected_forecast = {"P001": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]}
    payload = {
        "price": {"P001": [100, 100, 100, 100, 100, 100, 100]},
        "promo": {"P001": [0, 0, 0, 0, 0, 0, 0]},
    }

    with (
        patch("apy.get_sales_history", return_value=(object(), object())),
        patch("apy.check_data", return_value=object()),
        patch("apy.f_ing", return_value=forecast_df),
        patch("apy.make_param", return_value={}),
        patch("apy.get_config", return_value={"products": {"P001": {}}}),
        patch("apy.make_forecast", return_value=expected_forecast),
        patch("apy.decode_access_token", return_value = 2),
        patch("apy.find_user_have_company", return_value = object())
    ):
        response = client.post("/forecast?company_id=7", json=payload,  headers={"Authorization": "Bearer fake_token"})

    assert response.status_code == 200
    assert response.json() == expected_forecast


@pytest.mark.parametrize(
    "error_type,config_products,request_product,expected_status,expected_detail",
    [
        (
            "missing_config",
            None,
            "P001",
            409,
            "Конфигурация для компании не найдена",
        ),
        (
            "stale_config",
            {"P002": {}},
            "P001",
            409,
            "Продукты в конфигурации и датафрейме не совпадают. Необходимо обновить конфигурацию",
        ),
        (
            "request_mismatch",
            {"P001": {}},
            "P002",
            400,
            "Набор продуктов не совпадает с ожидаемым",
        ),
    ],
    ids=["missing_config", "stale_config", "request_mismatch"],
)
def test_forecast_configuration_errors(
    error_type,
    config_products,
    request_product,
    expected_status,
    expected_detail,
):
    client = TestClient(app)
    forecast_df = pd.DataFrame({"product_id": ["P001"]})
    payload = {
        "price": {request_product: [100, 100, 100, 100, 100, 100, 100]},
        "promo": {request_product: [0, 0, 0, 0, 0, 0, 0]},
    }

    with (
        patch("apy.get_sales_history", return_value=(object(), object())),
        patch("apy.check_data", return_value=object()),
        patch("apy.f_ing", return_value=forecast_df),
        patch("apy.make_param", return_value={}),
        patch("apy.get_config") as mock_get_config,
        patch("apy.decode_access_token", return_value = 2),
        patch("apy.find_user_have_company", return_value = object())
    ):
        if error_type == "missing_config":
            mock_get_config.side_effect = ConfigNotFoundError
        else:
            mock_get_config.return_value = {"products": config_products}

        response = client.post("/forecast?company_id=7", json=payload,  headers={"Authorization": "Bearer fake_token"})

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


def test_build_config_success():
    client = TestClient(app)
    expected_config = {
        "updated_at": "2026-08-31T10:00:00+00:00",
        "products": {"P001": {"model": "bl_lag1", "score": 1.0}},
    }

    with (
        patch("apy.get_sales_history", return_value=(object(), object())),
        patch("apy.check_data", return_value=object()),
        patch("apy.f_ing", return_value=object()),
        patch("apy.make_param", return_value={}),
        patch("apy.make_test", return_value=expected_config),
        patch("apy.save_config") as mock_save_config,
        patch("apy.decode_access_token", return_value = 2),
        patch("apy.find_user_have_company", return_value = object())
    ):
        response = client.post("/build_config?company_id=7",  headers={"Authorization": "Bearer fake_token"})

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert mock_save_config.call_args.args[:2] == (7, expected_config)


def test_register():
    client = TestClient(app)
    fake_hash= object()
    with (
        patch("apy.hash_password", return_value = fake_hash) as fake_hash_func,
        patch("apy.add_user", return_value = 15) as fake_add_user
    ):
        response = client.post("/register", json = {"email": "alpak@email.cm", "password": "qwerty123"})
        assert response.status_code == 200
        assert response.json() == {'user_id': 15}
        assert fake_add_user.call_args.args == ("alpak@email.cm", fake_hash)
        fake_hash_func.assert_called_once_with("qwerty123")



@pytest.mark.parametrize(
        "email,password",
        [
            ("no email", "qwerty12345"),
            ("alpak@email.xzi", "qwerty")
        ]
)
def test_invalid_email_or_password(email, password):
    with pytest.raises(ValidationError):
        RegisterData(email=email, password=password)


def test_register_invalid_data():
    client = TestClient(app)
    with (
        patch("apy.hash_password", return_value = object()) as fake_hash_password,
        patch("apy.add_user", return_value = "15") as fake_add_user 
    ):
        response = client.post("/register", json={'email': "no email", "password": 'qwerty'})
        assert response.status_code == 422
        fake_hash_password.assert_not_called()
        fake_add_user.assert_not_called()


def test_register_email_exists():
    client = TestClient(app)
    with (
        patch("apy.hash_password", return_value = object()),
        patch("apy.add_user") as fake_add_user 
    ):
        fake_add_user.side_effect = EmailAlreadyExistsError
        response = client.post("/register", json={'email': "alpak@email.cm", "password": 'qwerty123'})
        assert response.status_code == 409
        fake_add_user.assert_called_once()


def test_login_success():
    client = TestClient(app)
    user = MagicMock()
    user.password_hash = "fake_hash"
    user.user_id = 2
    with (
        patch("apy.get_user", return_value = user) as fake_get_user,
        patch("apy.verify_password", return_value = True) as fake_verify_password,
        patch('apy.create_access_token', return_value = "fake_token") as fake_create_token
    ):
        response = client.post("/login", json = {'email': "alpak@email.cm", "password": 'qwerty123'})

        fake_get_user.assert_called_once_with("alpak@email.cm")
        fake_verify_password.assert_called_once_with('qwerty123', "fake_hash")
        fake_create_token.assert_called_once_with(2)
        assert response.status_code == 200
        assert response.json() == {'access_token': "fake_token", 'token_type': 'bearer'}
    


def test_login_but_user_doesnt_exist():
    client = TestClient(app)
    with (
        patch("apy.get_user", return_value = None) as fake_get_user,
        patch("apy.verify_password") as fake_verify_password
    ):
        response = client.post("/login", json = {'email': "alpak@email.cm", "password": 'qwerty123'})
        fake_get_user.assert_called_once_with("alpak@email.cm")
        assert response.status_code == 401
        fake_verify_password.assert_not_called()
        assert response.json() == {"detail": "Неверный email или пароль"}

def test_login_but_password_wrong():
    client = TestClient(app)
    user = MagicMock()
    user.password_hash = "fake_hash"
    with (
        patch("apy.get_user", return_value = user) as fake_get_user,
        patch("apy.verify_password", return_value = False) as fake_verify_password
    ):
        response = client.post("/login", json = {'email': "alpak@email.cm", "password": 'qwerty123'})
        fake_get_user.assert_called_once_with("alpak@email.cm")
        fake_verify_password.assert_called_once_with('qwerty123', "fake_hash")
        assert response.status_code == 401
        assert response.json() == {"detail": "Неверный email или пароль"}


def test_invalid_token():
    client = TestClient(app)
    with (
        patch("apy.add_company") as fake_add_company,
        patch("apy.decode_access_token") as fake_decoder
    ):
        fake_decoder.side_effect = InvalidTokenError
        response = client.post("/companies", json={"name": "  Test company  "}, headers={"Authorization": "Bearer fake_token"})   
        assert response.status_code == 401
        fake_add_company.assert_not_called()
        assert response.json() == {'detail': "Токен не действителен"} 

def test_no_token():
    client = TestClient(app)
    with (
        patch("apy.add_company") as fake_add_company,
        patch("apy.decode_access_token") as fake_decoder
    ):
        response = client.post("/companies", json={"name": "  Test company  "})   
        assert response.status_code == 401
        fake_add_company.assert_not_called()
        fake_decoder.assert_not_called()
        assert response.json() == {'detail': "Not authenticated"}

def test_userid_companyid_dont_match():
    client = TestClient(app)
    with (
        patch("apy.decode_access_token", return_value = 15),
        patch("apy.find_user_have_company", return_value = None) as fake_find_user,
        patch("apy.get_sales_history") as fake_get_sales
    ):
        response = client.post("/build_config?company_id=8", headers={"Authorization": "Bearer fake_token"})
        fake_find_user.assert_called_once_with(15, 8)
        fake_get_sales.assert_not_called()
        assert response.status_code == 404
        assert response.json() == {'detail': 'Ресурс не найден'}
        

    
