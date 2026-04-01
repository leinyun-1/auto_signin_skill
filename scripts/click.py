"""
Tool: click — 点击指定坐标，然后分析新页面

支持两种坐标格式（自动检测）：
  归一化坐标（0~1）: python scripts/click.py --x 0.5 --y 0.59
  绝对像素坐标:       python scripts/click.py --x 640 --y 472

用法:
    python scripts/click.py --x 0.5 --y 0.59
    python scripts/click.py --x 640 --y 400 --no-analyze

stdout 输出:
    操作结果 + 当前页面状态
    --no-analyze 模式: 操作结果 + 截图路径 + URL
"""
import argparse
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _shared import connect_browser, screenshot_and_analyze, get_step_counter, load_config


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--x", type=float, required=True)
    parser.add_argument("--y", type=float, required=True)
    parser.add_argument("--no-analyze", action="store_true", help="仅截图，不调用VLM分析")
    args = parser.parse_args()

    # 检测坐标类型：x 和 y 都 <=1.0 视为归一化坐标，否则视为绝对像素坐标
    if args.x <= 1.0 and args.y <= 1.0:
        config = load_config()
        vw = config["browser"].get("viewport_width", 1280)
        vh = config["browser"].get("viewport_height", 800)
        px = int(args.x * vw)
        py = int(args.y * vh)
    else:
        px = int(args.x)
        py = int(args.y)

    disconnect, page = await connect_browser()
    try:
        await page.mouse.click(px, py)
        await asyncio.sleep(2.0)
        step = get_step_counter()
        state = await screenshot_and_analyze(page, step, no_analyze=args.no_analyze)
        print(f"操作: 点击坐标({args.x},{args.y})成功\n\n当前页面状态:\n{state}")
    except Exception as e:
        print(f"操作失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await disconnect()


if __name__ == "__main__":
    asyncio.run(main())
