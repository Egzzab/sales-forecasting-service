CREATE TABLE IF NOT EXISTS public.companies
(
    company_id integer NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 ),
    company_name text COLLATE pg_catalog."default",
    CONSTRAINT companies_pkey PRIMARY KEY (company_id)
)
;


CREATE TABLE IF NOT EXISTS public.model_configs
(
    company_id integer NOT NULL,
    config jsonb,
    update_at date,
    CONSTRAINT model_configs_pkey PRIMARY KEY (company_id),
    CONSTRAINT fk_model_configs_company FOREIGN KEY (company_id)
    REFERENCES public.companies (company_id)
        MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

;

CREATE TABLE IF NOT EXISTS public.sales_history
(
    date date NOT NULL,
    product_id text COLLATE pg_catalog."default" NOT NULL,
    category text COLLATE pg_catalog."default",
    price numeric(12,2),
    promo boolean,
    sales integer,
    company_id integer NOT NULL,
    CONSTRAINT sales_history_pkey PRIMARY KEY (company_id, date, product_id),
    CONSTRAINT fk_sales_history_company FOREIGN KEY (company_id)
    REFERENCES public.companies (company_id)
        MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)


