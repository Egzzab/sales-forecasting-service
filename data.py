import pandas as pd
import psycopg 


class ConfigNotFoundError(Exception):
    pass

class CompanyDataNotFoundError(Exception):
    pass

def get_sales_history(company_id, dbname, user, password, host, port):
    with psycopg.connect(
         dbname = dbname,        
         user =  user,            
         password = password,    
         host = host,           
         port = port             
     ) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM sales_history WHERE company_id = %s", (company_id,))
            col = [col.name for col in cursor.description]
            df = pd.DataFrame(cursor.fetchall(), columns=col)

    if df.empty:
        raise CompanyDataNotFoundError
        
    df["date"] = pd.to_datetime(df["date"])
    df["price"] = df["price"].astype(float)
    orig_date = df["date"].min()
    return df, orig_date



def save_sales_history(df, company_id, dbname, user, password, host, port):
    df = df.copy()
    df["company_id"] = company_id
    with psycopg.connect(
        dbname = dbname,        #"forecast_sales",
        user =  user,           #"postgres", 
        password = password,    #"egor",
        host = host,            #"localhost",
        port = port             #"5432"
     ) as conn:
        with conn.cursor() as cursor:
            cursor.executemany("""INSERT INTO sales_history(company_id, date, product_id, category, price, promo, sales)
                                VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (company_id, date, product_id)
                                DO UPDATE SET
                                	category = EXCLUDED.category,
                                	price= EXCLUDED.price,
                                	promo = EXCLUDED.promo,
                                	sales = EXCLUDED.sales;""", list(df[['company_id', 'date', 'product_id', 'category', 'price', 'promo', 'sales']].itertuples(False, None)))



def add_company(company_name, dbname, user, password, host, port):
    with psycopg.connect(
        dbname = dbname,        
        user =  user,          
        password = password,   
        host = host,          
        port = port           
     ) as conn:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO companies(company_name) VALUES (%s) RETURNING company_id", (company_name,))
            return cursor.fetchone()[0]


def get_config(company_id, dbname, user, password, host, port):
    with psycopg.connect(
        dbname = dbname,        
        user =  user,           
        password = password,   
        host = host,            
        port = port            
     ) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT config FROM model_configs WHERE company_id = %s", (company_id,))
            conf= cursor.fetchone()
            if conf is None:
                raise ConfigNotFoundError
            return conf[0]
                
     
def save_config(company_id, conf, dbname, user, password, host, port):
    update_at = conf["updated_at"]
    with psycopg.connect(
        dbname = dbname,        
        user =  user,           
        password = password,    
        host = host,           
        port = port             
     ) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""INSERT INTO model_configs(company_id, config, update_at) VALUES (%s,%s,%s) ON CONFLICT (company_id)
                            DO UPDATE SET config = EXCLUDED.config, update_at = EXCLUDED.update_at""", (company_id, psycopg.types.json.Jsonb(conf), update_at))
        
     



    

