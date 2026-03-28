"""页面状态数据模型"""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class PageType(str, Enum):
    """页面类型枚举"""
    HOMEPAGE = "homepage"                       # 普通首页
    LOGIN_ENTRY = "login_entry"                 # 含登录入口的页面
    LOGIN_FORM = "login_form"                   # 账号密码登录表单
    QR_CODE_LOGIN = "qr_code_login"             # 扫码登录页面
    THIRD_PARTY_SELECT = "third_party_select"   # 第三方登录选择页面
    CAPTCHA = "captcha"                         # 验证码页面
    LOGIN_SUCCESS = "login_success"             # 登录成功
    UNKNOWN = "unknown"


@dataclass
class UIElement:
    """页面 UI 元素"""
    element_type: str       # "button" | "input" | "link" | "qrcode" | "image" | "text"
    text: str               # 元素上的文字
    bbox: List[int]         # [x1, y1, x2, y2] 像素坐标（左上+右下）
    confidence: float = 0.0 # 置信度 0~1
    attributes: dict = field(default_factory=dict)
    # 额外属性示例: {"input_type": "password"}, {"platform": "qq"}

    @property
    def center(self) -> List[int]:
        """计算元素中心点坐标"""
        return [
            (self.bbox[0] + self.bbox[2]) // 2,
            (self.bbox[1] + self.bbox[3]) // 2,
        ]


@dataclass
class PageState:
    """一次页面分析的完整结果"""
    url: str
    page_type: PageType
    elements: List[UIElement]
    description: str            # 页面内容的自然语言摘要
    screenshot_path: str        # 截图文件路径
    raw_llm_response: str = ""  # LLM 原始返回，用于调试

    def get_elements_by_type(self, element_type: str) -> List[UIElement]:
        """按类型筛选元素"""
        return [e for e in self.elements if e.element_type == element_type]

    def get_element_by_text(self, text: str) -> Optional[UIElement]:
        """按文字查找元素（模糊匹配）"""
        for e in self.elements:
            if text in e.text:
                return e
        return None

    def to_text_summary(self) -> str:
        """将页面状态转为文本摘要，供决策层使用"""
        lines = [
            f"URL: {self.url}",
            f"页面类型: {self.page_type.value}",
            f"页面描述: {self.description}",
            f"识别到 {len(self.elements)} 个元素:",
        ]
        for i, e in enumerate(self.elements):
            attr_str = f", 属性: {e.attributes}" if e.attributes else ""
            lines.append(
                f"  [{i}] {e.element_type} - \"{e.text}\" "
                f"位置: bbox={e.bbox}, 中心=({e.center[0]},{e.center[1]}), "
                f"置信度: {e.confidence:.2f}{attr_str}"
            )
        return "\n".join(lines)
