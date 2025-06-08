# config.py
import json
import os

CONFIG_FILE = "config.json"

def load_config():
    """从配置文件中加载数据，如果不存在则返回空字典。"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(config_data):
    """将传入的配置数据保存到配置文件中"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)
