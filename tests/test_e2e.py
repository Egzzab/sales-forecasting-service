"""Сквозной пользовательский сценарий API."""

import math

import pandas as pd
import pytest
import psycopg
from fastapi.testclient import TestClient
from uuid import uuid4

from apy import app
from config import get_var_db


@pytest.fixture
def sales_history_csv():
    days = range(120)
    history = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=120, freq="D"),
            "product_id": ["P001"] * 120,
            "category": ["food"] * 120,
            "price": [100.0 + day % 5 for day in days],
            "promo": [int(day % 10 == 0) for day in days],
            "sales": [20 + day % 7 + (day // 30) % 3 for day in days],
        }
    )

    return history.to_csv(index=False).encode("utf-8")


@pytest.mark.e2e
def test_user_scenario(sales_history_csv):
    client = TestClient(app)
    company_name = f"e2e_{uuid4().hex}"
    company_id = None
    db_config = get_var_db()
    email = f'alpak{uuid4().hex}@email.cm'
    user_data = {'email': email, 'password': 'qwerty123'}

    assert "test" in db_config["dbname"].lower()

    try:
        response = client.post("/register", json = user_data)
        assert response.status_code == 200

        response = client.post("/login", json = user_data)
        assert response.status_code == 200
        token = response.json()['access_token']

        response = client.post("/companies", json={"name": company_name}, headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        company_id = response.json()["id"]
        assert type(company_id) is int

        upload_response = client.post(
            f"/upload?company_id={company_id}",
            files={"file": ("sales.csv", sales_history_csv, "text/csv")},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert upload_response.status_code == 200
        assert upload_response.json() == {"status": "ready"}

        build_config_response = client.post(f"/build_config?company_id={company_id}", headers={"Authorization": f"Bearer {token}"})

        assert build_config_response.status_code == 200
        assert build_config_response.json() == {"status": "ready"}

        forecast_response = client.post(
            f"/forecast?company_id={company_id}",
            json={
                "price": {"P001": [100, 101, 102, 103, 104, 105, 106]},
                "promo": {"P001": [0, 0, 1, 0, 0, 1, 0]},
            }, headers={"Authorization": f"Bearer {token}"}
        )

        assert forecast_response.status_code == 200
        forecast = forecast_response.json()
        assert set(forecast) == {"P001"}
        assert isinstance(forecast["P001"], list)
        assert len(forecast["P001"]) == 7
        assert all(
            type(value) in (int, float) and math.isfinite(value)
            for value in forecast["P001"]
        )
    finally:
        with psycopg.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT company_id FROM companies WHERE company_name = %s",
                    (company_name,),
                )
                company_ids = {row[0] for row in cursor.fetchall()}
                if company_id is not None:
                    company_ids.add(company_id)

                for cleanup_company_id in company_ids:
                    cursor.execute(
                        "DELETE FROM model_configs WHERE company_id = %s",
                        (cleanup_company_id,),
                    )
                    cursor.execute(
                        "DELETE FROM sales_history WHERE company_id = %s",
                        (cleanup_company_id,),
                    )
                    cursor.execute(
                        "DELETE FROM companies WHERE company_id = %s",
                        (cleanup_company_id,),
                    )
                cursor.execute('DELETE FROM users_info WHERE email = %s', (email,))
