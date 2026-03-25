import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "active_model": "DeepSeek",
    "api_keys": {
        "DeepSeek": "",
        "Qwen": "",
        "Gemini": ""
    }
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return DEFAULT_CONFIG

def save_config(config_data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)