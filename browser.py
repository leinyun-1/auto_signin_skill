"""Playwright 浏览器控制工具"""
import asyncio
import os
from playwright.async_api import async_playwright, Browser, Page, Playwright


class BrowserTool:
    """封装所有浏览器操作：导航、截图、点击、输入、滚动等"""

    def __init__(self, config: dict):
        """
        Args:
            config: browser 配置段
                {headless, viewport_width, viewport_height, default_timeout, screenshot_dir}
        """
        self.config = config
        self._playwright: Playwright = None
        self._browser: Browser = None
        self._page: Page = None

    async def start(self) -> None:
        """启动 Playwright → Edge 浏览器 → 创建新页面"""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            channel=self.config.get("channel", "msedge"),
            headless=self.config.get("headless", False),
            args=[
                "--disable-gpu",                    # 禁用 GPU 加速，防止 Win11 桌面黑屏
                "--disable-gpu-compositing",        # 禁用 GPU 合成
                "--disable-software-rasterizer",    # 禁用软件光栅化后备
            ],
        )
        # 强制 device_scale_factor=1，确保截图像素坐标 = CSS 坐标 = mouse.click 坐标
        # 否则 Windows 150% 缩放下截图会是 1920x1200 但 click 坐标系是 1280x800
        self._page = await self._browser.new_page(
            viewport={
                "width": self.config.get("viewport_width", 1280),
                "height": self.config.get("viewport_height", 800),
            },
            device_scale_factor=1,
        )
        self._page.set_default_timeout(self.config.get("default_timeout", 30000))
        print(f"[DEBUG] viewport: {self.config.get('viewport_width', 1280)}x{self.config.get('viewport_height', 800)}, device_scale_factor=1")

    async def close(self) -> None:
        """关闭浏览器和 Playwright"""
        if self._page:
            await self._page.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def navigate(self, url: str) -> None:
        """导航到指定 URL"""
        await self._page.goto(url, wait_until="domcontentloaded")

    async def screenshot(self, save_path: str) -> str:
        """
        viewport 截图，保证截图尺寸 = viewport 尺寸 = click 坐标系。
        """
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        await self._page.screenshot(path=save_path, full_page=False)
        # 验证截图尺寸
        from PIL import Image
        img = Image.open(save_path)
        vw = self.config.get("viewport_width", 1280)
        vh = self.config.get("viewport_height", 800)
        if img.size != (vw, vh):
            print(f"[WARNING] 截图尺寸 {img.size} ≠ viewport ({vw}x{vh})，坐标可能不匹配！")
        else:
            print(f"[DEBUG] 截图尺寸 {img.size} ✓")
        return os.path.abspath(save_path)

    async def click(self, x: int, y: int) -> None:
        """在像素坐标 (x, y) 处模拟鼠标点击"""
        await self._page.mouse.click(x, y)

    async def type_text(self, text: str, delay: int = 50) -> None:
        """
        在当前焦点元素逐字输入。

        Args:
            text: 要输入的文字
            delay: 字符间隔 ms
        """
        await self._page.keyboard.type(text, delay=delay)

    async def key_press(self, key: str) -> None:
        """
        模拟按键。

        Args:
            key: 按键名，如 'Enter', 'Tab', 'Escape'
        """
        await self._page.keyboard.press(key)

    async def scroll(self, delta_y: int = 300) -> None:
        """
        鼠标滚轮滚动。

        Args:
            delta_y: 滚动量，正数向下，负数向上
        """
        await self._page.mouse.wheel(0, delta_y)

    async def get_current_url(self) -> str:
        """返回当前页面 URL"""
        return self._page.url

    async def wait(self, seconds: float) -> None:
        """等待指定秒数"""
        await asyncio.sleep(seconds)
