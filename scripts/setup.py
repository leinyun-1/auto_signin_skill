"""
首次环境准备：检查并安装依赖、配置 API Key。

用法:
    python scripts/setup.py
    python scripts/setup.py --api-key sk-xxx --api-base https://api.moonshot.cn/v1 --model kimi-k2.5
"""
import argparse
import json
import os
import sys
import subprocess

_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(_SKILL_DIR, "config.json")

REQUIRED_PACKAGES = [
    ("playwright", "playwright"),
    ("Pillow", "PIL"),
    ("pyyaml", "yaml"),
    ("httpx", "httpx"),
]


def check_and_install_packages():
    missing = []
    for pip_name, import_name in REQUIRED_PACKAGES:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)
    if missing:
        print(f"[Setup] 正在安装: {', '.join(missing)}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install"] + missing,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        print("[Setup] 依赖安装完成")
    else:
        print("[Setup] Python 依赖已就绪")


def check_and_install_browser(channel="msedge"):
    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        try:
            b = pw.chromium.launch(channel=channel, headless=True)
            b.close()
            print("[Setup] 浏览器驱动已就绪")
        except Exception:
            print(f"[Setup] 正在安装浏览器驱动 ({channel})...")
            subprocess.run([sys.executable, "-m", "playwright", "install", channel], check=False)
            print("[Setup] 浏览器驱动安装完成")
        finally:
            pw.stop()
    except ImportError:
        print("[Setup] playwright 未安装，请先运行 setup")


def configure(args):
    # 加载已有配置或创建默认配置
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {
            "llm": {
                "provider": "kimi",
                "api_key": "",
                "api_base": "https://api.moonshot.cn/v1",
                "model": "kimi-k2.5",
                "temperature": 1.0,
                "max_tokens": 8192,
                "thinking": False,
                "min_request_interval": 4,
            },
            "browser": {
                "channel": "msedge",
                "headless": False,
                "viewport_width": 1280,
                "viewport_height": 800,
                "default_timeout": 30000,
                "screenshot_dir": os.path.join(_SKILL_DIR, "screenshots"),
            },
        }

    # 命令行参数覆盖
    if args.api_key:
        config["llm"]["api_key"] = args.api_key
    if args.api_base:
        config["llm"]["api_base"] = args.api_base
    if args.model:
        config["llm"]["model"] = args.model
    if args.channel:
        config["browser"]["channel"] = args.channel

    # 交互式补全 API Key
    if not config["llm"]["api_key"] or config["llm"]["api_key"].startswith("your"):
        print("\n" + "-" * 50)
        print("需要配置 VLM API Key")
        print(f"API 地址: {config['llm']['api_base']}")
        print(f"模型: {config['llm']['model']}")
        print("-" * 50)
        key = input("请输入 API Key: ").strip()
        if not key:
            print("错误: API Key 不能为空")
            sys.exit(1)
        config["llm"]["api_key"] = key

    # 保存配置
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"[Setup] 配置已保存到 {CONFIG_FILE}")

    return config


def main():
    parser = argparse.ArgumentParser(description="Auto Sign Skill 环境准备")
    parser.add_argument("--api-key", help="VLM API Key")
    parser.add_argument("--api-base", help="API 地址")
    parser.add_argument("--model", help="模型名称")
    parser.add_argument("--channel", help="浏览器类型 (msedge/chromium)", default=None)
    args = parser.parse_args()

    print("=" * 50)
    print("Auto Sign Skill Setup")
    print("=" * 50 + "\n")

    # 1. 安装 Python 依赖
    check_and_install_packages()

    # 2. 配置
    config = configure(args)

    # 3. 安装浏览器驱动
    check_and_install_browser(config["browser"]["channel"])

    print("\n[Setup] 完成! 现在可以使用以下命令:")
    print(f"  python {os.path.join('scripts', 'open_webpage.py')} --url https://example.com")


if __name__ == "__main__":
    main()
