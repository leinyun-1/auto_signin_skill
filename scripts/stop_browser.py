"""
关闭持久浏览器进程。

用法:
    python scripts/stop_browser.py
"""
import json
import os
import sys
import signal

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
            os.kill(pid, signal.SIGTERM)
            print(f"已发送终止信号给浏览器进程 (PID: {pid})")
        except ProcessLookupError:
            print(f"浏览器进程 (PID: {pid}) 已不存在")
        except Exception as e:
            print(f"关闭浏览器失败: {e}", file=sys.stderr)

    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print("状态文件已清理")


if __name__ == "__main__":
    main()
