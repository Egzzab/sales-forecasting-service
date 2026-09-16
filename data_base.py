from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy import create_engine, URL,  Text, select,  Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import insert, JSONB
from config import get_var_db
from datetime import date as dt
from decimal import Decimal
import pandas as pd
from functools import lru_cache
from sqlalchemy.exc import IntegrityError


class CompanyDataNotFoundError(Exception):
    pass

class ConfigNotFoundError(Exception):
    pass

class EmailAlreadyExistsError(Exception):
    pass


class Base(DeclarativeBase):
    pass



class User(Base):
    __tablename__ = "users_info"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] =mapped_column(Text)


class Company(Base):
    __tablename__ = "companies"

    company_id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(ForeignKey("users_info.user_id"))



class SalesHistory(Base):
    __tablename__ = "sales_history"

    date: Mapped[dt] = mapped_column(primary_key=True)
    product_id: Mapped[str] = mapped_column(Text, primary_key=True)
    category: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12,2))
    promo: Mapped[bool | None] = mapped_column()
    sales: Mapped[int | None] = mapped_column()
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.company_id"), primary_key=True)


class ModelConfigs(Base):
    __tablename__ = "model_configs"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.company_id"), primary_key=True)
    config: Mapped[dict | None] = mapped_column(JSONB)
    update_at: Mapped[dt | None] = mapped_column()





@lru_cache
def make_engine():

    var_env = get_var_db()

    url = URL.create(
        drivername = "postgresql+psycopg",
        username = var_env["user"],
        password = var_env["password"],
        host = var_env["host"],
        port = var_env["port"],
        database = var_env["dbname"]
    )

    engine = create_engine(url)
    return engine









def add_company(company_name, user_id):
    with Session(make_engine()) as session:
        companyn = Company(company_name = company_name, user_id= user_id)
        session.add(companyn)
        session.commit()
        return companyn.company_id





def get_sales_history(company_id):
    with Session(make_engine()) as session:
        stmt = select(
            SalesHistory.date, 
            SalesHistory.product_id, 
            SalesHistory.category, 
            SalesHistory.price,
            SalesHistory.promo,
            SalesHistory.sales
            ).where(SalesHistory.company_id == company_id)
        res = session.execute(stmt).all()
        df = pd.DataFrame(res, columns=['date', 'product_id', 'category', 'price', 'promo', 'sales'])

    if df.empty:
        raise CompanyDataNotFoundError
            
    df["date"] = pd.to_datetime(df["date"])
    df["price"] = df["price"].astype(float)
    orig_date = df["date"].min()
    return df, orig_date




def save_sales_history(df, company_id):
    df = df.copy()
    df["company_id"] = company_id
    with Session(make_engine()) as session:
        records = df.to_dict("records")
        stmt = insert(SalesHistory).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements= [SalesHistory.company_id, SalesHistory.date, SalesHistory.product_id],
            set_= {SalesHistory.category: stmt.excluded.category,
                   SalesHistory.price: stmt.excluded.price,
                   SalesHistory.promo: stmt.excluded.promo,
                   SalesHistory.sales: stmt.excluded.sales}
        )
        session.execute(stmt)
        session.commit()




def get_config(company_id):
    with Session(make_engine()) as session:
        stmt = select(ModelConfigs.config).where(ModelConfigs.company_id == company_id)
        config = session.scalars(stmt).one_or_none()
        if config is None:
            raise ConfigNotFoundError
        return config




def save_config(company_id, conf):
    update_at = pd.to_datetime(conf["updated_at"]).date()
    with Session(make_engine()) as session:
        stmt = insert(ModelConfigs).values(
            company_id=company_id,
            config=conf,
            update_at=update_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[ModelConfigs.company_id],
            set_={
                ModelConfigs.config: stmt.excluded.config,
                ModelConfigs.update_at: stmt.excluded.update_at,
            },
        )
        session.execute(stmt)
        session.commit()


def add_user(email, password_hash):
    with Session(make_engine()) as session:
        person = User(email = email, password_hash = password_hash)
        try:
            session.add(person)
            session.commit()
        except IntegrityError:
            session.rollback()
            raise EmailAlreadyExistsError
        return person.user_id

def get_user(email):
    with Session(make_engine()) as session:
        stmt = select(User).where(User.email == email)
        user = session.scalars(stmt).one_or_none()
        return user

def find_user_have_company(user_id, company_id):
    with Session(make_engine()) as session:
        stmt = select(Company).where(Company.company_id == company_id, Company.user_id == user_id)
        return session.scalar(stmt)