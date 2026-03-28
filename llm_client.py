"""Kimi 多模态 LLM 客户端封装"""
import asyncio
import base64
import json
import time
import httpx


class LLMClient:
    """
    统一封装 Kimi LLM API 调用（OpenAI 兼容格式）。
    内置限速控制（RPM=20 → 每次请求间隔至少 4 秒）和 429 自动重试。
    """

    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 8       # 429 重试首次等待秒数

    def __init__(self, config: dict):
        self.api_key = config["api_key"]
        self.api_base = config["api_base"].rstrip("/")
        # 视觉模型参数
        self.vision_model = config["model"]
        self.vision_temperature = config.get("temperature", 1.0)
        self.vision_max_tokens = config.get("max_tokens", 4096)
        self.vision_thinking = config.get("thinking", False)
        # 决策模型参数
        self.decision_model = config.get("decision_model", config["model"])
        self.decision_temperature = config.get("decision_temperature", self.vision_temperature)
        self.decision_max_tokens = config.get("decision_max_tokens", self.vision_max_tokens)
        self.decision_thinking = config.get("decision_thinking", True)
        # 限速配置（0 表示关闭限速）
        self.min_request_interval = config.get("min_request_interval", 4)

        self.client = httpx.AsyncClient(timeout=180.0)
        self._last_request_time = 0.0

    async def analyze_image(
        self,
        image_path: str,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """多模态调用：发送图片 + 文本 → LLM 文本响应"""
        image_b64 = self._encode_image(image_path)
        image_size = len(image_b64) * 3 // 4
        print(f"[DEBUG] 图片大小: {image_size / 1024:.1f} KB")

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}"
                        },
                    },
                    {"type": "text", "text": user_prompt},
                ],
            },
        ]

        return await self._request(
            messages, model=self.vision_model,
            temperature=self.vision_temperature,
            max_tokens=self.vision_max_tokens,
            thinking=self.vision_thinking,
        )

    async def chat(
        self,
        messages: list,
        system_prompt: str,
    ) -> str:
        """纯文本对话调用 → LLM 文本响应（决策层）"""
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        return await self._request(
            full_messages, model=self.decision_model,
            temperature=self.decision_temperature,
            max_tokens=self.decision_max_tokens,
            thinking=self.decision_thinking,
        )

    async def _request(self, messages: list, model: str,
                       temperature: float = 1.0, max_tokens: int = 4096,
                       thinking: bool = True) -> str:
        """发送请求到 Kimi API，内置限速控制和 429 自动重试"""
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "thinking": {"type": "enabled" if thinking else "disabled"},
        }

        for attempt in range(self.MAX_RETRIES + 1):
            # 限速：确保两次请求间隔 >= min_request_interval（0 则关闭）
            if self.min_request_interval > 0:
                elapsed = time.time() - self._last_request_time
                if elapsed < self.min_request_interval:
                    wait = self.min_request_interval - elapsed
                    print(f"[RATE] 限速等待 {wait:.1f}s ...")
                    await asyncio.sleep(wait)

            try:
                print(f"[DEBUG] 请求模型: {model}, thinking={'on' if thinking else 'off'}" +
                      (f" (重试 {attempt}/{self.MAX_RETRIES})" if attempt > 0 else ""))
                self._last_request_time = time.time()
                response = await self.client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                # 调试：打印响应结构
                choice = data["choices"][0]
                message = choice["message"]
                finish_reason = choice.get("finish_reason", "unknown")
                print(f"[DEBUG] finish_reason: {finish_reason}")

                if message.get("reasoning_content"):
                    print(f"[DEBUG] 模型有思考链，长度: {len(message['reasoning_content'])} 字符")

                content = message.get("content") or ""
                if not content and message.get("reasoning_content"):
                    content = message["reasoning_content"]
                    print(f"[WARNING] content 为空，使用 reasoning_content")

                print(f"[DEBUG] 响应内容前300字符:\n{content[:300]}")
                return content

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                print(f"[ERROR] LLM API HTTP错误: {status}")
                print(f"[ERROR] 响应内容: {e.response.text[:500]}")

                # 429 限流或 500+ 服务端错误：自动重试
                if status in (429, 500, 502, 503) and attempt < self.MAX_RETRIES:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)  # 8s, 16s, 32s
                    print(f"[RETRY] 等待 {delay}s 后重试...")
                    await asyncio.sleep(delay)
                    continue
                raise

            except (KeyError, IndexError) as e:
                print(f"[ERROR] LLM API 响应格式异常: {e}")
                try:
                    print(f"[ERROR] 完整响应: {json.dumps(data, ensure_ascii=False)[:500]}")
                except Exception:
                    pass
                raise
            except Exception as e:
                print(f"[ERROR] LLM API 调用失败: {e}")
                raise

    def _encode_image(self, image_path: str) -> str:
        """读取图片文件并 base64 编码"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
