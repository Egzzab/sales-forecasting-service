from optimization import all_grid
from evaluation import fin_test, train_test


def make_test(df, **other_param):
    Xy_train, _ = train_test(df)
    prod_score_param = all_grid(Xy_train, **other_param)
    return fin_test(df, prod_score_param, **other_param)

    