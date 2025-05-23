import json

with open("secret.json") as config_file:
    config = json.load(config_file)
    globals().update(config)

with open("categories.json") as categories_file:
    CATEGORIES = json.load(categories_file)
