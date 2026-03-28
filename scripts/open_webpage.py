"""
Tool: open_webpage — 打开网页并分析页面内容

用法:
    python scripts/open_webpage.py --url https://www.bilibili.com
    python scripts/open_webpage.py --url https://www.bilibili.com --no-analyze

stdout 输出:
    操作结果 + 页面类型 + 元素列表（含坐标）+ 页面描述
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
    parser.add_argument("--url", required=True)
    parser.add_argument("--no-analyze", action="store_true", help="仅截图，不调用VLM分析")
    args = parser.parse_args()

    disconnect, page = await connect_browser()
    try:
        await page.goto(args.url, wait_until="domcontentloaded")
        await asyncio.sleep(2.0)
        step = get_step_counter()
        state = await screenshot_and_analyze(page, step, no_analyze=args.no_analyze)
        print(f"操作: 已打开网页 {args.url}\n\n当前页面状态:\n{state}")
    except Exception as e:
        print(f"操作失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await disconnect()


if __name__ == "__main__":
    asyncio.run(main())
