"""ReflexiveTrader Pro — 配置管理"""

import os
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    # 优先从 Streamlit Secrets 读取 (云端部署)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "notion" in st.secrets:
            notion_secrets = st.secrets["notion"]
            return {
                "notion": {
                    "api_key": str(notion_secrets["api_key"]).strip(),
                    "database_id": str(notion_secrets.get("database_id", "")).strip(),
                    "parent_page_id": str(notion_secrets.get("parent_page_id", "")).strip(),
                },
                "account": dict(st.secrets.get("account", {
                    "equity": 100000, "max_risk_per_trade": 0.02, "max_total_heat": 0.06
                })),
                "reports": dict(st.secrets.get("reports", {"output_dir": "./reports"})),
            }
    except Exception:
        pass

    # 本地: 从 config.yaml 读取
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)


def get_notion_api_key(cfg: dict) -> str:
    key = os.environ.get("NOTION_API_KEY") or cfg.get("notion", {}).get("api_key", "")
    if not key or key == "secret_xxx":
        raise ValueError("请在 config.yaml 或环境变量 NOTION_API_KEY 中设置 Notion API Key")
    return key
