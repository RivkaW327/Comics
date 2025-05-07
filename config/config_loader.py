import json
import os

def load_config():
    # Get the directory of the current file
    config_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the full path to config.json
    config_path = os.path.join(config_dir, 'config.json')

    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    return config

config = load_config()