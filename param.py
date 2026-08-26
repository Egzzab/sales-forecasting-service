from config import dc_param

def make_param(orig_date, **param):
    other_param = {}
    other_param.update(param)
    other_param["orig_date"] = orig_date
    other_param["dc_param"] = dc_param
    return other_param