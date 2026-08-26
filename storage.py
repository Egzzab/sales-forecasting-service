from json import dump, load

def save_to_json(config_dict):
    with open("config.json", "w") as file:
        dump(config_dict, file, indent=4)

def load_json(link):
    with open(link) as file:
        config_dict = load(file)
    return config_dict

