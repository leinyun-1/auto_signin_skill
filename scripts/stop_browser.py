"""
关闭浏览器。

用法:
    python scripts/stop_browser.py
"""
import json
import os
import sys
import subprocess

_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(_SKILL_DIR, "state.json")


def main():
    if not os.path.exists(STATE_FILE):
        print("浏览器未在运行")
        return

    with open(STATE_FILE, "r") as f:
        state = json.load(f)

    pid = state.get("pid")
    if pid:
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                import signal
                os.kill(pid, signal.SIGTERM)
            print(f"浏览器已关闭 (PID: {pid})")
        except ProcessLookupError:
            print("浏览器进程已不存在")
        except Exception as e:
            print(f"关闭失败: {e}", file=sys.stderr)

    os.remove(STATE_FILE)


if __name__ == "__main__":
    main()
