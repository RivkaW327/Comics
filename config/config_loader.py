import json
import os

def load_config():
    config_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(config_dir, 'config.json')

    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    return config

config = load_config()