"""
Tool: scroll — 滚动页面，然后分析新的可视区域

用法:
    python scripts/scroll.py --direction down
    python scripts/scroll.py --direction up --amount 500
    python scripts/scroll.py --direction down --no-analyze

stdout 输出:
    操作结果 + 当前页面状态
    --no-analyze 模式: 操作结果 + 截图路径 + URL
"""
import argparse
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _shared import connect_browser, screenshot_and_analyze, get_step_counter


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--direction", required=True, choices=["up", "down"])
    parser.add_argument("--amount", type=int, default=300)
    parser.add_argument("--no-analyze", action="store_true", help="仅截图，不调用VLM分析")
    args = parser.parse_args()

    disconnect, page = await connect_browser()
    try:
        delta_y = args.amount if args.direction == "down" else -args.amount
        await page.mouse.wheel(0, delta_y)
        await asyncio.sleep(1.0)
        step = get_step_counter()
        state = await screenshot_and_analyze(page, step, no_analyze=args.no_analyze)
        d = "下" if args.direction == "down" else "上"
        print(f"操作: 向{d}滚动{args.amount}px成功\n\n当前页面状态:\n{state}")
    except Exception as e:
        print(f"操作失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await disconnect()


if __name__ == "__main__":
    asyncio.run(main())
