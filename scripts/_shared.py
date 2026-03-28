"""
共享工具：浏览器 CDP 连接、VLM 分析、配置加载。

所有 tool 脚本共用此模块。浏览器通过 CDP 端口跨脚本复用。
"""
import json
import os
import sys
import asyncio

_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SKILL_DIR)

STATE_FILE = os.path.join(_SKILL_DIR, "state.json")
CONFIG_FILE = os.path.join(_SKILL_DIR, "config.json")


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    print("错误: 配置文件不存在，请先运行 python scripts/setup.py", file=sys.stderr)
    sys.exit(1)


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    print("错误: 浏览器未启动，请先运行 python scripts/start_browser.py", file=sys.stderr)
    sys.exit(1)


async def connect_browser():
    """
    通过 CDP 连接到已启动的浏览器，返回 (disconnect, page)。

    disconnect: 异步函数，脚本结束时调用，仅断开CDP连接，不影响浏览器本身。
    page: Playwright Page 对象。
    """
    from playwright.async_api import async_playwright

    state = load_state()
    cdp_url = state["cdp_url"]

    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(cdp_url)

    config = load_config()
    vw = config["browser"].get("viewport_width", 1280)
    vh = config["browser"].get("viewport_height", 800)

    # 获取已有的 page，或创建新的
    contexts = browser.contexts
    if contexts and contexts[0].pages:
        page = contexts[0].pages[0]
        await page.set_viewport_size({"width": vw, "height": vh})
    else:
        context = await browser.new_context(
            viewport={"width": vw, "height": vh},
            device_scale_factor=1,
        )
        page = await context.new_page()

    async def disconnect():
        """仅断开 CDP 连接，不关闭浏览器"""
        try:
            await browser.close()
        except Exception:
            pass
        try:
            await pw.stop()
        except Exception:
            pass

    return disconnect, page


async def take_screenshot(page, step_hint: int = 0) -> str:
    """仅截图，返回截图文件的绝对路径"""
    config = load_config()
    screenshot_dir = config["browser"].get("screenshot_dir", os.path.join(_SKILL_DIR, "screenshots"))
    os.makedirs(screenshot_dir, exist_ok=True)

    screenshot_path = os.path.join(screenshot_dir, f"step_{step_hint:03d}.png")
    await page.screenshot(path=screenshot_path, full_page=False)
    return os.path.abspath(screenshot_path)


async def screenshot_and_analyze(page, step_hint: int = 0, no_analyze: bool = False) -> str:
    """
    截图，可选 VLM 分析。

    Args:
        page: Playwright page 对象
        step_hint: 步数编号
        no_analyze: True=仅截图返回路径和URL，False=截图+VLM分析返回完整页面状态

    Returns:
        no_analyze=True:  "截图: <path>\nURL: <url>"
        no_analyze=False: VLM 分析的页面状态文本
    """
    screenshot_path = await take_screenshot(page, step_hint)
    current_url = page.url

    if no_analyze:
        return f"截图: {screenshot_path}\nURL: {current_url}"

    from llm_client import LLMClient
    from vision_analyzer import VisionAnalyzer

    config = load_config()
    llm_client = LLMClient(config["llm"])
    prompts_dir = os.path.join(_SKILL_DIR, "prompts")
    vision = VisionAnalyzer(llm_client, prompts_dir)

    page_state = await vision.analyze(screenshot_path, current_url)
    await llm_client.close()

    return page_state.to_text_summary()


def get_step_counter() -> int:
    """从 state 中读取并递增步数计数器"""
    state = load_state()
    step = state.get("step_counter", 0) + 1
    state["step_counter"] = step
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)
    return step
