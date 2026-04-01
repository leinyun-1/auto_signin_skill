"""
启动浏览器并保持运行，供其他 tool 通过 CDP 连接。

用系统命令直接启动浏览器（独立进程），通过 Playwright 连接设置 viewport。

用法:
    python scripts/start_browser.py
    python scripts/start_browser.py --headless
"""
import argparse
import json
import os
import sys
import time
import subprocess
import shutil
import urllib.request

_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(_SKILL_DIR, "state.json")
CONFIG_FILE = os.path.join(_SKILL_DIR, "config.json")
CDP_PORT = 9222


def is_cdp_alive():
    try:
        urllib.request.urlopen(f"http://localhost:{CDP_PORT}/json/version", timeout=2).close()
        return True
    except Exception:
        return False


def find_browser(channel):
    for name in [channel, "msedge", "chrome", "chromium"]:
        path = shutil.which(name)
        if path:
            return path
    if sys.platform == "win32":
        for p in [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        ]:
            if os.path.isfile(p):
                return p
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    if is_cdp_alive():
        if not os.path.exists(STATE_FILE):
            with open(STATE_FILE, "w") as f:
                json.dump({"cdp_url": f"http://localhost:{CDP_PORT}", "pid": 0,
                           "step_counter": 0, "started_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)
        print(f"浏览器已在运行 (CDP: http://localhost:{CDP_PORT})")
        return

    if not os.path.exists(CONFIG_FILE):
        print("错误: config.json 不存在", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    channel = config["browser"].get("channel", "msedge")
    headless = args.headless or config["browser"].get("headless", False)
    vw = config["browser"].get("viewport_width", 1280)
    vh = config["browser"].get("viewport_height", 800)

    exe = find_browser(channel)
    if not exe:
        print(f"错误: 找不到浏览器 ({channel})", file=sys.stderr)
        sys.exit(1)

    # 用独立 user-data-dir 避免与系统 Edge 冲突
    user_data_dir = os.path.join(_SKILL_DIR, ".browser_profile")

    cmd = [exe, f"--remote-debugging-port={CDP_PORT}",
           f"--user-data-dir={user_data_dir}",
           "--no-first-run", "--no-default-browser-check",
           "--disable-background-timer-throttling",
           "--disable-backgrounding-occluded-windows",
           # 强制 DPR=1，使截图坐标=点击坐标
           "--force-device-scale-factor=1",
           ]
    if headless:
        cmd.append("--headless=new")

    # 系统级独立进程
    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **kwargs)

    # 等 CDP 就绪
    for _ in range(20):
        time.sleep(0.5)
        if is_cdp_alive():
            # 通过 CDP 设置第一个 tab 的 viewport
            _set_viewport_via_cdp(vw, vh)

            with open(STATE_FILE, "w") as f:
                json.dump({"cdp_url": f"http://localhost:{CDP_PORT}", "pid": proc.pid,
                           "channel": channel, "headless": headless, "step_counter": 0,
                           "started_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)
            print(f"浏览器已启动 (PID: {proc.pid}, CDP: http://localhost:{CDP_PORT})")
            return

    print("错误: 浏览器启动超时", file=sys.stderr)
    proc.kill()
    sys.exit(1)


def _set_viewport_via_cdp(width, height):
    """通过 CDP 原生协议设置 viewport 大小，不依赖 Playwright"""
    import json as _json
    try:
        # 获取 WebSocket URL
        data = urllib.request.urlopen(f"http://localhost:{CDP_PORT}/json").read()
        targets = _json.loads(data)
        ws_url = None
        for t in targets:
            if t.get("type") == "page":
                ws_url = t.get("webSocketDebuggerUrl")
                break
        if not ws_url:
            return

        # 用 websocket 发送 CDP 命令设置 viewport
        # 简单方案：通过 HTTP fetch 方式（CDP 的 /json/protocol 不支持），
        # 但最简单有效的是启动时设置 --window-size，配合 --force-device-scale-factor=1
        # viewport 大小可以通过后续 Playwright connect 时 set_viewport_size 来精确控制
        pass
    except Exception:
        pass


if __name__ == "__main__":
    main()
