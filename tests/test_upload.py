import pandas as pd
from upload import prepare_sales_df, NegativePriceError, InvalidPromoValueError, MissingRequiredColumnError, DuplicateSalesRecordError, EmptyStringValueError
import pytest




@pytest.fixture
def df():
    return pd.DataFrame({'date': ['2024-01-01 00:00:00',
  '2024-01-01 00:00:00',
  '2024-01-01 00:00:00',
  '2024-01-01 00:00:00',
  '2024-01-01 00:00:00'],
  'product_id': ['P001', 'P002', 'P003', 'P004', 'P005'],
  'category': ['food', 'cosmetics', 'food', 'cosmetics', 'food'],
  'price': ['1293.17',
  '515.55',
  '760.15',
  '994.74',
  '1106.33'],
 'promo': [False, False, False, False, False],
 'sales': [30, 11, 25, 26, 29]})




def test_valid_sales_data(df):

    df["product_id"] = df["product_id"] + " "
    df["category"] = df["category"] + " "
    res_df = prepare_sales_df(df)
    assert pd.api.types.is_datetime64_any_dtype(res_df["date"])
    assert pd.api.types.is_bool_dtype(res_df["promo"])
    assert pd.api.types.is_integer_dtype(res_df["sales"])
    assert (res_df["product_id"] == res_df["product_id"].str.strip()).all()
    assert (res_df["category"] == res_df["category"].str.strip()).all()





def test_neg_price_error(df):
    df.loc[1, "price"] = "-4"
    with pytest.raises(NegativePriceError):
        prepare_sales_df(df)


    

def test_invalid_value_promo(df):
    df["promo"] = df["promo"].astype(int)
    df.loc[1, "promo"] = 4
    with pytest.raises(InvalidPromoValueError):
        prepare_sales_df(df)





def test_missing_columns(df):
    df = df.drop("price", axis = 1)
    with pytest.raises(MissingRequiredColumnError):
        prepare_sales_df(df)    



def test_duplicated_row(df):
    df.iloc[3] = df.iloc[1]
    with pytest.raises(DuplicateSalesRecordError):
        prepare_sales_df(df)  



def test_empty_product(df):
    df.loc[1, "product_id"] = "   " 
    with pytest.raises(EmptyStringValueError):
        prepare_sales_df(df)  
















