import pandas as pd
from pandas._libs.tslibs.parsing import DateParseError
from pandas.errors import EmptyDataError
import numpy as np

class SalesDataValidationError(Exception):
    pass

class UnsupportedFileFormatError(SalesDataValidationError):
    pass

class MissingRequiredColumnError(SalesDataValidationError):
    pass

class MissingValueError(SalesDataValidationError):
    pass

class NegativePriceError(SalesDataValidationError):
    pass

class NegativeSalesError(SalesDataValidationError):
    pass
    
class InvalidPromoValueError(SalesDataValidationError):
    pass

class DuplicateSalesRecordError(SalesDataValidationError):
    pass

class InvalidDateFormatError(SalesDataValidationError):
    pass

class InvalidPriceFormatError(SalesDataValidationError):
    pass

class InvalidPromoFormatError(SalesDataValidationError):
    pass

class InvalidSalesFormatError(SalesDataValidationError):
    pass

class FileReadError(SalesDataValidationError):
    pass

class EmptyFileError(SalesDataValidationError):
    pass

class InvalidNumericValueError(SalesDataValidationError):
    pass

class EmptyStringValueError(SalesDataValidationError):
    pass

def to_df(file):
    name = file.filename.lower()
    extension = name.split(".")[-1]
    if extension == "csv":
        try:
            df= pd.read_csv(file.file)
        except EmptyDataError:
            raise EmptyFileError("В файле нет данных")
        except Exception:
            raise FileReadError("Не удалось прочитать файл")
            
    elif extension == "xlsx":
        try:
            df = pd.read_excel(file.file)
        except Exception:
            raise FileReadError("Не удалось прочитать файл")
    else:
        raise UnsupportedFileFormatError('Неподдерживаемый формат файла')
        
    if df.empty:
        raise EmptyFileError("В файле нет данных")
        
    return df

def prepare_sales_df(df):
    try:
        df= df[['date', 'product_id', 'category', 'price', 'promo', 'sales']].copy()
    except KeyError:
        raise MissingRequiredColumnError("Отсутствует необходимая колонка")
        
    if df.isnull().any().any():
            raise MissingValueError("В данных присутствуют null значения")
        
    try:
        df["date"] = pd.to_datetime(df["date"])
    except (DateParseError, ValueError):
        raise InvalidDateFormatError("Не удалось спарсить дату. Возможно неверый формат")
    df["date"] = df["date"].dt.normalize()
     
    df["product_id"] = df["product_id"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()

    if (df["product_id"] == '').any() or (df["category"] == '').any():
        raise EmptyStringValueError('В колонке продуктов или в колонке категорий присутствует пустая строка')

    

    
    try:
        df["price"] = df["price"].astype(float)
    except ValueError:
        raise InvalidPriceFormatError("Неверный формат цены")

    try:
        df["promo"] = df["promo"].astype(float)
    except ValueError:
        raise InvalidPromoFormatError("Неверный формат промо")

    try:
        df["sales"] = df["sales"].astype(float)
    except ValueError:
        raise InvalidSalesFormatError("Неверный формат продаж")

    if not np.isfinite(df[["price", "promo", "sales"]]).all().all():
        raise InvalidNumericValueError("В числовых данных есть NaN или бесконечные значения")
    

    if (df["price"]<0).any():
        raise NegativePriceError("Цена не может быть отрицательной")

    if (df["sales"]<0).any():
        raise NegativeSalesError("Продажи не могут быть отрицательными")
    elif not (df["sales"] == df["sales"].astype(int)).all():
        raise InvalidSalesFormatError("Продажи могут быть только целым числом")

    df["sales"] = df["sales"].astype(int)

    if not df["promo"].isin([0.0, 1.0]).all():
        raise InvalidPromoValueError("Некорректное промо, пока допустимы значения 0 - нет, 1 - да")

    df["promo"] = df["promo"].astype(bool)

    if (df.groupby(['date', 'product_id'])["sales"].count() != 1).any():
        raise DuplicateSalesRecordError("В данных есть дубликаты")

    return df
    








    