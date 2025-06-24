# backend/config_store.py

ORACLE_CONFIG = {}

def update_db_config(new_config):
    global ORACLE_CONFIG
    ORACLE_CONFIG = new_config

def get_current_db_config():
    if not ORACLE_CONFIG:
        raise Exception("DB config not set. Use /api/set-db-config")
    return ORACLE_CONFIG
