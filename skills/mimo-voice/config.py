#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置解析 —— 密钥与网关的统一读取（本文件不含任何密钥）

解析优先级：
    API Key : 环境变量 MIMO_API_KEY
              > ~/.config/mimo-tts/config.json 的 api_key
              > ~/.config/mimo-tts/mimo_key.txt（纯文本，仅本机）
    网关地址: 环境变量 MIMO_API_BASE
              > config.json 的 api_base
              > https://api.xiaomimimo.com/v1（官方默认）

首次使用请运行同目录的 setup.py 完成配置。
"""
import json
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CONFIG_DIR = os.path.expanduser("~/.config/mimo-tts")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
KEY_FILE = os.path.join(CONFIG_DIR, "mimo_key.txt")
DEFAULT_API_BASE = "https://api.xiaomimimo.com/v1"


class ConfigError(Exception):
    pass


def _load_config_file():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def get_api_key():
    key = os.environ.get("MIMO_API_KEY", "").strip()
    if key:
        return key
    cfg = _load_config_file()
    if cfg.get("api_key", "").strip():
        return cfg["api_key"].strip()
    try:
        with open(KEY_FILE, encoding="utf-8") as f:
            key = f.read().strip()
        if key:
            return key
    except OSError:
        pass
    raise ConfigError(
        "❌ 找不到 API Key。\n"
        "   首次使用请运行 setup.py 完成配置，或设置环境变量 MIMO_API_KEY。"
    )


def get_api_base():
    base = os.environ.get("MIMO_API_BASE", "").strip()
    if base:
        return base.rstrip("/")
    cfg = _load_config_file()
    if cfg.get("api_base", "").strip():
        return cfg["api_base"].strip().rstrip("/")
    return DEFAULT_API_BASE


def get_pref(name, default=None):
    return _load_config_file().get(name, default)
