from apy import RequestData, app
from fastapi.testclient import TestClient
from pydantic import ValidationError
from unittest.mock import patch
from upload import SalesDataValidationError
from data_base import CompanyDataNotFoundError, ConfigNotFoundError
from history_validation import HistoryValidationError
import pandas as pd
import pytest


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

    with patch("apy.add_company", return_value=15) as mock_add_company:
        response = client.post("/companies", json={"name": "  Test company  "})
        empty_name_response = client.post("/companies", json={"name": "   "})
        long_name_response = client.post("/companies", json={"name": "a" * 151})

    assert response.status_code == 200
    assert response.json() == {"id": 15}
    assert mock_add_company.call_args.args[0] == "Test company"
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
    ):
        if validation_error is not None:
            mock_prepare.side_effect = validation_error

        response = client.post(
            "/upload?company_id=7",
            files={"file": ("sales.csv", b"sales data", "text/csv")},
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
    ):
        if error_type == "missing_history":
            mock_get_history.side_effect = CompanyDataNotFoundError
        else:
            mock_get_history.return_value = (object(), object())
            mock_check_data.side_effect = HistoryValidationError("Некорректная история")

        if payload is None:
            response = client.post(path)
        else:
            response = client.post(path, json=payload)

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
    ):
        response = client.post("/forecast?company_id=7", json=payload)

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
    ):
        if error_type == "missing_config":
            mock_get_config.side_effect = ConfigNotFoundError
        else:
            mock_get_config.return_value = {"products": config_products}

        response = client.post("/forecast?company_id=7", json=payload)

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
    ):
        response = client.post("/build_config?company_id=7")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert mock_save_config.call_args.args[:2] == (7, expected_config)
