"""
Tool: type_text — 在当前焦点输入框输入文字，然后分析页面

用法:
    python scripts/type_text.py --text "my_username"
    python scripts/type_text.py --text "my_username" --no-analyze

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
    parser.add_argument("--text", required=True)
    parser.add_argument("--no-analyze", action="store_true", help="仅截图，不调用VLM分析")
    args = parser.parse_args()

    disconnect, page = await connect_browser()
    try:
        await page.keyboard.type(args.text, delay=50)
        await asyncio.sleep(1.0)
        step = get_step_counter()
        state = await screenshot_and_analyze(page, step, no_analyze=args.no_analyze)
        display = args.text[:20] + "..." if len(args.text) > 20 else args.text
        print(f"操作: 输入文字\"{display}\"成功\n\n当前页面状态:\n{state}")
    except Exception as e:
        print(f"操作失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await disconnect()


if __name__ == "__main__":
    asyncio.run(main())
