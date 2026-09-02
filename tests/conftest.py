import os

import pytest
from dotenv import load_dotenv


load_dotenv()


@pytest.fixture(autouse=True)
def use_test_db(monkeypatch):
    db_name = os.getenv("DB_NAME")
    test_db_name = os.getenv("DB_NAME_TEST")

    if db_name is None:
        pytest.fail("Не задана переменная DB_NAME")
    if test_db_name is None:
        pytest.fail("Не задана переменная DB_NAME_TEST")
    if "test" not in test_db_name.lower():
        pytest.fail("DB_NAME_TEST должна указывать на тестовую БД")
    if test_db_name == db_name:
        pytest.fail("Рабочая и тестовая БД не должны совпадать")

    monkeypatch.setenv("DB_NAME", test_db_name)
