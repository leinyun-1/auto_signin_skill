"""
启动持久浏览器进程（后台运行），供其他 tool 脚本通过 CDP 连接复用。

用法:
    python scripts/start_browser.py
    python scripts/start_browser.py --headless

浏览器信息保存在 state.json 中。使用完毕后运行 stop_browser.py 关闭。
"""
import argparse
import asyncio
import json
import os
import sys
import signal
import time

_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(_SKILL_DIR, "state.json")
CONFIG_FILE = os.path.join(_SKILL_DIR, "config.json")


async def main():
    parser = argparse.ArgumentParser(description="启动持久浏览器")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    args = parser.parse_args()

    # 检查配置
    if not os.path.exists(CONFIG_FILE):
        print("错误: 请先运行 python scripts/setup.py 完成配置", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    from playwright.async_api import async_playwright

    pw = await async_playwright().start()

    headless = args.headless or config["browser"].get("headless", False)
    channel = config["browser"].get("channel", "msedge")
    cdp_port = 9222

    browser = await pw.chromium.launch(
        channel=channel,
        headless=headless,
        args=[
            f"--remote-debugging-port={cdp_port}",
            "--disable-gpu",
            "--disable-gpu-compositing",
        ],
    )

    # 创建带正确 viewport 的 page
    context = await browser.new_context(
        viewport={
            "width": config["browser"].get("viewport_width", 1280),
            "height": config["browser"].get("viewport_height", 800),
        },
        device_scale_factor=1,
    )
    page = await context.new_page()

    # 保存状态
    state = {
        "cdp_url": f"http://localhost:{cdp_port}",
        "pid": os.getpid(),
        "channel": channel,
        "headless": headless,
        "step_counter": 0,
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    print(f"浏览器已启动 (channel={channel}, headless={headless})")
    print(f"CDP 端口: {cdp_port}")
    print(f"PID: {os.getpid()}")
    print(f"状态文件: {STATE_FILE}")
    print("按 Ctrl+C 关闭，或运行 python scripts/stop_browser.py")

    # 保持进程运行
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\n正在关闭浏览器...")
    finally:
        await browser.close()
        await pw.stop()
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        print("浏览器已关闭")


if __name__ == "__main__":
    asyncio.run(main())
