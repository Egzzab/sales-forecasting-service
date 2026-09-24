import streamlit as st

import requests
import pandas as pd
import os
from io import BytesIO
from upload import excel_to_df, FileReadError
import matplotlib.pyplot as plt
from streamlit_local_storage import LocalStorage
import time

api_url = os.getenv("API_URL", 'http://127.0.0.1:8000')

def get_error_message(response):
    try:
        detail =  response.json()["detail"]
    except Exception:
        return "Ошибка сервера"
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return "; ".join(
            error.get("msg", "Ошибка валидации")
            for error in detail
        )

    return "Ошибка сервера"

ls = LocalStorage()

if "token" not in st.session_state:
    st.session_state.token = None

if "company_id" not in st.session_state:
    st.session_state.company_id = None

if "cnt_load" not in st.session_state:
    st.session_state.cnt_load = 0


if "cnt_make_new_company" not in st.session_state:
    st.session_state.cnt_make_new_company = 0

if "pred_for_user" not in st.session_state:
    st.session_state.pred_for_user = {}

if st.session_state.token is None:
    st.session_state.token = ls.getItem("token")

if st.session_state.token is None:
    act = st.radio("", ["sign in", 'sign up'], horizontal=True)
    if act == 'sign in':
        with st.form("login_form"):
            st.header("login")
            login = st.text_input("Ваша почта")
            password = st.text_input("Ваш пароль", type='password')
            if st.form_submit_button("Отправить"):
                try:
                    response = requests.post(f"{api_url}/login", json={'email': login, 'password': password}, timeout=(3, 10))
                except requests.RequestException:
                    st.error("Что то пошло не так")
                    st.stop()
                if response.status_code == 200:
                    st.session_state.token = response.json()['access_token']
                    ls.setItem("token", st.session_state.token)
                    time.sleep(1.5)
                    st.rerun()
                elif response.status_code == 401:
                    st.error("Неверный логин или пароль")
                else: 
                    st.error(get_error_message(response))

    elif act == 'sign up':
        with st.form("signup_form"):
            st.header("sign up")
            login = st.text_input("Введите почту")
            password = st.text_input("Введите пароль", type='password')
            if st.form_submit_button("Отправить"):
                try:
                    response = requests.post(f"{api_url}/register", json={'email': login, 'password': password}, timeout=(3, 10))
                except requests.RequestException:
                    st.error("Что то пошло не так")
                    st.stop()                
                if response.status_code == 200:
                    st.success("Регистрация успешна")
                elif response.status_code == 409:
                    st.error("Аккаунт с таким email уже существует")
                else:
                    st.error(get_error_message(response))
elif st.session_state.token is not None:
    st.title("Прогнозирование продаж")
    headers = {
        "Authorization": f"Bearer {st.session_state.token}"
    }
    with st.sidebar:
        if st.button("Выйти"):
            st.session_state.token = None
            st.session_state.company_id = None
            st.session_state.pred_for_user = {}
            ls.deleteItem("token")
            time.sleep(1.5)
            st.rerun()
        try:
            response = requests.get(f"{api_url}/companies", headers = headers, timeout=(3, 10))
        except requests.RequestException:
            st.error("Что то пошло не так")
            st.stop()
        if response.status_code == 200:
            companies_user = response.json()
        elif response.status_code == 401:
            st.session_state.token = None
            st.session_state.company_id = None
            st.session_state.pred_for_user = {}
            ls.deleteItem("token")
            time.sleep(1.5)
            st.rerun()
        else:
            st.error(get_error_message(response))
            st.stop()
        companies_dict = {name: id for id, name in companies_user['companies']}
        if companies_dict:
            company_user = st.selectbox("Выберите компанию", options=companies_dict.keys())
            st.session_state.company_id = companies_dict[company_user]
        new_org = st.text_input("Создать новую организацию", key=f"make_new_company_{st.session_state.cnt_make_new_company}")
        if st.button('Добавить'):
            try:
                response = requests.post(f"{api_url}/companies", headers=headers, json={'name': new_org}, timeout=(3, 10))
            except requests.RequestException:
                    st.error("Что то пошло не так")
                    st.stop()
            if response.status_code == 200:
                st.session_state.cnt_make_new_company += 1 
                st.rerun()
            elif response.status_code == 409:
                st.error("Такая компания уже существует")
            else:
                st.error(get_error_message(response))
    if st.session_state.company_id is None:
        st.info("Создайте компанию в боковой панели, чтобы начать работу")



    if st.session_state.company_id is not None:
        st.subheader("История продаж")
        with st.form(f"upload_form_{st.session_state.cnt_load}"):
            file = st.file_uploader("Добавить историю продаж", type=["csv", "xlsx"])
            but_loader = st.form_submit_button("Загрузить")
            if file is not None and but_loader:
                try:
                    response = requests.post(f'{api_url}/upload?company_id={st.session_state.company_id}', files={"file": (file.name, file, file.type)}, headers=headers, timeout=(3, 30))
                except requests.RequestException:
                        st.error("Что то пошло не так")
                        st.stop()
                if response.status_code == 200:
                    st.success("Файл загружен")
                    st.session_state.cnt_load += 1
                    st.session_state.pred_for_user.pop(st.session_state.company_id, None)
                else:
                    st.error(get_error_message(response))

        st.subheader("Конфигурация модели")
        if st.button("Создать или обновить конфигурацию"):
            try:
                with st.spinner("Создаем конфигурацию"):
                    response = requests.post(f'{api_url}/build_config?company_id={st.session_state.company_id}', headers=headers, timeout=(3, 600))
            except requests.RequestException:
                    st.error("Что то пошло не так")
                    st.stop()
            if response.status_code == 200:
                st.success("Успешно")
                st.session_state.pred_for_user.pop(st.session_state.company_id, None)
            else:
                st.error(get_error_message(response))

        try:
            response = requests.get(f'{api_url}/last_price?company_id={st.session_state.company_id}', headers=headers, timeout=(3, 15))
        except requests.RequestException:
            st.error("Что то пошло не так")
            st.stop()
        if response.status_code ==200:
            dict_df = response.json()
        else:
            st.error(get_error_message(response))
            st.stop()

        st.subheader("Параметры прогноза")
        regim = st.radio("Выберите режим", options=['загрузить файл', "ручной ввод"], horizontal=True)
        user_price, user_promo, new_user_price, new_user_promo = (None, None, None, None)
        df = pd.DataFrame(dict_df)
        curr_date = pd.to_datetime(df["date"].iloc[0])
        dict_of_price ={}
        for prod in df["product_id"].unique():
            price_prod = df[df["product_id"]== prod].iloc[0, 1]
            price_prod_week = [price_prod]*7
            dict_of_price[prod] = price_prod_week
        df = pd.DataFrame(dict_of_price).transpose().reset_index()
        df.columns = ["products"] + pd.date_range(curr_date + pd.Timedelta(days=1), periods=7).to_list()
        df_for_promo = df.copy()
        df_for_promo.iloc[:, 1:] = 0
        if regim  == "загрузить файл":
            bytes_io = BytesIO()
            with pd.ExcelWriter(bytes_io) as writter:
                df.to_excel(writter, sheet_name="price", index=False)
                df_for_promo.to_excel(writter, sheet_name="promo", index=False)
            bytes_io.seek(0)
            st.download_button("Скачать шаблон", bytes_io, file_name="forecast_template.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        with st.form("make_forecast"):
            if regim == "ручной ввод":
                st.write("Введите информацию о ценах и акциях на продукты на следующие 7 дней")
                st.write("Цены")
                user_price = st.data_editor(df, hide_index=True, disabled=["products"])
                st.write("Будет ли промо в конкретный день")
                user_promo = st.data_editor(df_for_promo, hide_index=True, disabled=["products"])
            elif regim == "загрузить файл":
                exl_price_promo = st.file_uploader("Загрузите заполненый шаблон", type="xlsx", key=f"uploader_for_{st.session_state.company_id}")
                if exl_price_promo is not None:
                    try:
                        new_user_price, new_user_promo = excel_to_df(exl_price_promo)
                    except FileReadError as err:
                        st.error(str(err))
            make_forecast = st.form_submit_button("Сделать прогноз")
            if make_forecast:
                if user_price is not None and user_promo is not None:
                    dict_of_price = user_price.set_index("products").transpose().to_dict(orient="list")
                    dict_of_promo = user_promo.set_index("products").transpose().to_dict(orient="list")
                elif new_user_promo is not None and new_user_price is not None:
                    dict_of_price = new_user_price.set_index("products").transpose().to_dict(orient="list")
                    dict_of_promo = new_user_promo.set_index("products").transpose().to_dict(orient="list")
                else:
                    st.error("Загрузите корректно заполненный шаблон")
                    st.stop()
                try:
                    with st.spinner("Делаем прогноз"):
                        response = requests.post(f'{api_url}/forecast?company_id={st.session_state.company_id}', headers=headers, json={"price": dict_of_price, "promo": dict_of_promo}, timeout=(3, 300))        
                except requests.RequestException:
                        st.error("Что то пошло не так")
                        st.stop()
                if response.status_code == 200:
                    st.success("Успех")
                    pred = pd.DataFrame(response.json(), index=pd.date_range(curr_date + pd.Timedelta(days=1), periods=7)).transpose()
                    st.session_state.pred_for_user[st.session_state.company_id] = pred
                else:
                    st.error(get_error_message(response))

        if st.session_state.company_id in st.session_state.pred_for_user:
            pred = st.session_state.pred_for_user[st.session_state.company_id]
            st.subheader("Результат прогноза")
            sums_of_sales = pred.sum(axis = 0)
            fig, axes = plt.subplots(figsize=(10, 5))
            axes.plot(sums_of_sales.index, sums_of_sales.values)
            axes.set_title("График продаж")
            axes.set_xlabel("Дата")
            axes.set_ylabel("Продажи")
            axes.grid(True)
            st.pyplot(fig)
            plt.close(fig)
            prod_for_graph = st.selectbox("Выберите продукт", pred.index)
            fig, axes = plt.subplots(figsize=(10, 5))
            axes.plot(pred.columns, pred.loc[prod_for_graph].values)
            axes.set_title("График продаж")
            axes.set_xlabel("Дата")
            axes.set_ylabel("Продажи")
            axes.grid(True)
            st.pyplot(fig)
            plt.close(fig)
            st.dataframe(pred)



     


