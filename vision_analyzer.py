"""视觉分析层：将截图转换为结构化页面描述"""
import json
import os
import re
from typing import Optional
from PIL import Image
try:
    from .page_state import PageState, PageType, UIElement
    from .llm_client import LLMClient
except ImportError:
    from page_state import PageState, PageType, UIElement
    from llm_client import LLMClient


class VisionAnalyzer:
    """
    职责：调用多模态 LLM 分析页面截图 → 输出结构化 PageState。

    VLM 输出归一化相对坐标 (0~1)，本层负责转为绝对像素坐标，
    确保后续决策层和鼠标点击使用的都是像素坐标。
    """

    def __init__(self, llm_client: LLMClient, prompts_dir: str):
        self.llm_client = llm_client
        self.system_prompt = self._load_prompt(prompts_dir, "vision_analyze.txt")

    async def analyze(self, screenshot_path: str, url: str) -> PageState:
        """截图 → 多模态LLM → PageState"""
        img = Image.open(screenshot_path)
        img_width, img_height = img.size
        print(f"[DEBUG] 截图尺寸用于坐标转换: {img_width}x{img_height}")

        user_prompt = self._build_user_prompt(url)
        response = await self.llm_client.analyze_image(
            image_path=screenshot_path,
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
        )
        return self._parse_response(response, screenshot_path, url, img_width, img_height)

    def _build_user_prompt(self, url: str) -> str:
        return (
            f"请分析这个网页截图。当前URL: {url}\n"
            f"请严格按照系统提示词要求的JSON格式输出分析结果。"
            f"bbox 使用归一化相对坐标(0.0~1.0)。"
        )

    def _parse_response(self, response: str, screenshot_path: str, url: str,
                        img_width: int, img_height: int) -> PageState:
        json_data = self._extract_json(response)

        if json_data is None:
            print(f"[WARNING] 视觉分析 JSON 解析失败，原始响应:\n{response[:500]}")
            return PageState(
                url=url, page_type=PageType.UNKNOWN, elements=[],
                description="页面分析失败，无法解析LLM响应",
                screenshot_path=screenshot_path, raw_llm_response=response,
            )

        page_type_str = json_data.get("page_type", "unknown")
        try:
            page_type = PageType(page_type_str)
        except ValueError:
            page_type = PageType.UNKNOWN

        elements = []
        for elem_data in json_data.get("elements", []):
            try:
                raw_bbox = elem_data.get("bbox", [0, 0, 0, 0])
                pixel_bbox = self._to_pixel_bbox(raw_bbox, img_width, img_height)
                element = UIElement(
                    element_type=elem_data.get("element_type", "unknown"),
                    text=elem_data.get("text", ""),
                    bbox=pixel_bbox,
                    confidence=elem_data.get("confidence", 0.5),
                    attributes=elem_data.get("attributes", {}),
                )
                elements.append(element)
                print(f"[DEBUG] 元素 \"{element.text}\": "
                      f"归一化{raw_bbox} → 像素{pixel_bbox} → 中心({element.center[0]},{element.center[1]})")
            except Exception as e:
                print(f"[WARNING] 解析元素失败: {e}, 数据: {elem_data}")

        return PageState(
            url=url, page_type=page_type, elements=elements,
            description=json_data.get("description", ""),
            screenshot_path=screenshot_path, raw_llm_response=response,
        )

    @staticmethod
    def _to_pixel_bbox(bbox: list, img_width: int, img_height: int) -> list:
        if len(bbox) != 4:
            return [0, 0, 0, 0]
        x1, y1, x2, y2 = bbox
        if all(v > 1.0 for v in bbox):
            print(f"[FIX] VLM 输出了像素坐标而非归一化坐标，直接使用")
            if x2 < x1 or y2 < y1:
                return [int(x1), int(y1), int(x1 + x2), int(y1 + y2)]
            return [int(x1), int(y1), int(x2), int(y2)]
        if x2 < x1 or y2 < y1:
            print(f"[FIX] 归一化坐标顺序异常 [{x1},{y1},{x2},{y2}]，尝试修正")
            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)
        x1, y1 = max(0.0, min(1.0, x1)), max(0.0, min(1.0, y1))
        x2, y2 = max(0.0, min(1.0, x2)), max(0.0, min(1.0, y2))
        return [int(x1 * img_width), int(y1 * img_height),
                int(x2 * img_width), int(y2 * img_height)]

    def _extract_json(self, text: str) -> Optional[dict]:
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        brace_start = text.find("{")
        if brace_start != -1:
            brace_end = text.rfind("}")
            if brace_end > brace_start:
                try:
                    return json.loads(text[brace_start : brace_end + 1])
                except json.JSONDecodeError:
                    pass
        return None

    @staticmethod
    def _load_prompt(prompts_dir: str, filename: str) -> str:
        path = os.path.join(prompts_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
