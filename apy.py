from fastapi import FastAPI,  HTTPException, UploadFile, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator, model_validator, EmailStr, Field
from forecast import make_forecast
from data_base import get_sales_history, save_sales_history, add_company, get_config, save_config, ConfigNotFoundError, CompanyDataNotFoundError, add_user, EmailAlreadyExistsError, get_user, find_user_have_company
from feature_engineering import f_ing
from param import make_param
from upload import to_df, prepare_sales_df, SalesDataValidationError
from make_test import make_test
from history_validation import check_data, HistoryValidationError
from auth_layer import hash_password, verify_password, create_access_token, decode_access_token
from jwt import InvalidTokenError


class RequestData(BaseModel):
    price: dict[str, list[float]]
    promo: dict[str, list[int]]

    @field_validator("price", "promo")
    @classmethod
    def check_length(cls, value):
        if not all([len(v) == 7 for v in value.values()]):
            raise ValueError('Для каждого продукта нужно 7 значений')
        return value

    @field_validator("price")
    @classmethod
    def check_price(cls, value):
        if not all([all([pr>= 0 for pr in v]) for v in value.values()]):
            raise ValueError('Цена не может быть отрицательной')
        return value

    @field_validator("promo")
    @classmethod
    def check_promo(cls, value):
        if not all([all([prom in (0, 1) for prom in v]) for v in value.values()]):
            raise ValueError('Promo не является корректным')
        value = {prod: [bool(v) for v in list_promo] for prod, list_promo in value.items()}
        return value

    @model_validator(mode = "after")
    def check_products(self):
        if set(self.price) !=  set(self.promo):
            raise ValueError("Ключи price и promo должны совпадать")
        return self


class CompanyCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def check_name(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Название компании не может быть пустым")
        elif len(value) > 150: 
            raise ValueError("Название компании слишком длинное")
        
        return value

class RegisterData(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginUser(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)



security = HTTPBearer()


def get_user_id(
        credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    try:
        user_id = decode_access_token(token)
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Токен не действителен")
    return user_id




def get_company_access(company_id: int, user_id: int = Depends(get_user_id)):
    if find_user_have_company(user_id, company_id) is None:
        raise HTTPException(status_code=404, detail="Ресурс не найден")
    return company_id





app = FastAPI()


@app.post("/forecast", response_model = dict[str, list[float]])
def forecast(data: RequestData, company_id: int = Depends(get_company_access)):
    try:
        df, orig_date = get_sales_history(company_id)
    except CompanyDataNotFoundError:
        raise HTTPException(status_code=409, detail="В системе отсутствует история продаж для этой компании")

    try:
        df = check_data(df)
    except HistoryValidationError as err:
        raise HTTPException(status_code=422, detail=str(err))

    
    df = f_ing(df, orig_date)
    other = make_param(orig_date)
    try:
        dc = get_config(company_id)
    except ConfigNotFoundError:
        raise HTTPException(status_code = 409, detail = "Конфигурация для компании не найдена")
        
    if set(dc["products"]) != set(df["product_id"]):
        raise HTTPException(status_code=409, detail="Продукты в конфигурации и датафрейме не совпадают. Необходимо обновить конфигурацию")
    elif set(data.price) != set(df["product_id"]):
        raise HTTPException(status_code=400, detail="Набор продуктов не совпадает с ожидаемым")
        
    return make_forecast(df, dc, data.price, data.promo, **other)





@app.post("/upload")
def load_sales_history(file: UploadFile, company_id: int = Depends(get_company_access)):
    try:
        df=prepare_sales_df(to_df(file))
    except SalesDataValidationError as err:
        raise HTTPException(status_code=422, detail = str(err))
    
    save_sales_history(df, company_id)
    return {"status": "ready"}




@app.post("/companies")
def make_company(company: CompanyCreate, user_id: int = Depends(get_user_id)):
    company_id = add_company(company.name, user_id)
    return {"id": company_id}



@app.post("/build_config")
def build_model_config(company_id: int = Depends(get_company_access)):
    try:
        df, orig_date = get_sales_history(company_id)
    except CompanyDataNotFoundError:
        raise HTTPException(status_code=409, detail="В системе отсутствует история продаж для этой компании")
        
    try:
        df = check_data(df)
    except HistoryValidationError as err:
        raise HTTPException(status_code=422, detail=str(err))
        
    df = f_ing(df, orig_date)
    other = make_param(orig_date)
    conf = make_test(df, **other)
    save_config(company_id, conf)
    return {"status": "ready"}
    

@app.post("/register")
def register_user(info_user: RegisterData): 
    password_hash = hash_password(info_user.password)
    try:
        user_id = add_user(info_user.email, password_hash)
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже существует")
    return {'user_id': user_id}
    


@app.post("/login")
def login_user(info_user: LoginUser):
    user = get_user(info_user.email)
    if user is None:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    if not verify_password(info_user.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    token = create_access_token(user.user_id)
    return {
        'access_token': token,
        'token_type': 'bearer'
    }
    


    
