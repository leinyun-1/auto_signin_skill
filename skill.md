# Auto Sign Skill

完全独立的网页自动化工具集。将浏览器控制（Playwright）和 VLM 视觉分析封装为 shell 可执行的 tool 脚本，可直接复制到任何 Agent 框架的 skills/ 目录下使用。

## 核心特性

- **操作即感知**：每个 tool 执行操作后自动截图 + VLM 分析，stdout 输出操作结果和页面状态
- **双模式**：默认调用 VLM 分析页面；加 `--no-analyze` 仅截图返回路径，供多模态 Agent 自行读图分析（更快、更灵活）
- **Shell 调用**：任何语言的 Agent 框架都能通过 `python scripts/xxx.py --param value` 调用
- **完全自包含**：所有代码、提示词内聚在本文件夹，无外部文件依赖
- **浏览器复用**：通过 CDP 端口跨脚本共享同一个浏览器实例

## 使用流程

```bash
# 1. 首次使用：安装依赖 + 配置 API Key
python scripts/setup.py

# 2. 启动持久浏览器（后台运行，保持终端开着或用 nohup）
python scripts/start_browser.py &

# 3. 调用 tool（每个脚本 = 一个 tool）
python scripts/open_webpage.py --url "https://www.bilibili.com"
python scripts/click.py --x 1130 --y 35
python scripts/type_text.py --text "my_username"
python scripts/press_key.py --key Enter
python scripts/scroll.py --direction down --amount 300

# 3b. 快速模式：仅截图不调VLM，Agent自行读图分析（更快）
python scripts/open_webpage.py --url "https://www.bilibili.com" --no-analyze
python scripts/click.py --x 1130 --y 35 --no-analyze

# 4. 使用完毕，关闭浏览器
python scripts/stop_browser.py
```

## Tool 列表

### setup — 环境准备（一次性）

```bash
python scripts/setup.py
python scripts/setup.py --api-key sk-xxx --api-base https://api.openai.com/v1 --model gpt-4o
```

自动安装 Python 依赖（playwright/Pillow/httpx/pyyaml）、浏览器驱动、交互式配置 API Key。配置保存在 `config.json`。

### start_browser — 启动浏览器

```bash
python scripts/start_browser.py
python scripts/start_browser.py --headless
```

启动 Edge/Chrome 浏览器并监听 CDP 端口（9222）。浏览器保持后台运行，后续 tool 通过 CDP 连接复用。

### open_webpage — 打开网页并分析

```bash
python scripts/open_webpage.py --url "https://www.bilibili.com"
```

**参数：** `--url` (必填) 网页 URL

**stdout 输出示例：**
```
操作: 已打开网页 https://www.bilibili.com

当前页面状态:
URL: https://www.bilibili.com
页面类型: login_entry
页面描述: B站首页，右上角有登录按钮
识别到 2 个元素:
  [0] button - "登录" 位置: bbox=[1100,20,1160,50], 中心=(1130,35), 置信度: 0.95
  [1] button - "注册" 位置: bbox=[1170,20,1230,50], 中心=(1200,35), 置信度: 0.90
```

### click — 点击坐标

```bash
python scripts/click.py --x 1130 --y 35
```

**参数：** `--x` (必填) x像素坐标, `--y` (必填) y像素坐标

坐标来自之前 tool 返回的元素中心坐标。点击后自动截图分析新页面。

### type_text — 输入文字

```bash
python scripts/type_text.py --text "my_username"
```

**参数：** `--text` (必填) 要输入的文字

使用前必须先用 click 点击输入框使其获得焦点。

### press_key — 按键

```bash
python scripts/press_key.py --key Enter
```

**参数：** `--key` (必填) 按键名: Enter / Tab / Escape / Backspace / Space

### scroll — 滚动

```bash
python scripts/scroll.py --direction down
python scripts/scroll.py --direction up --amount 500
```

**参数：** `--direction` (必填) up/down, `--amount` (可选, 默认300) 滚动像素量

### stop_browser — 关闭浏览器

```bash
python scripts/stop_browser.py
```

## Agent 框架集成示例

Agent 框架通过 shell 命令调用 tool，读取 stdout 作为 tool 返回值：

```javascript
// JavaScript Agent 示例
const result = execSync('python scripts/open_webpage.py --url "https://example.com"').toString();
// result 是纯文本：操作结果 + 页面状态
messages.push({role: "tool", content: result});
```

```java
// Java Agent 示例
Process p = Runtime.getRuntime().exec("python scripts/click.py --x 640 --y 400");
String result = new String(p.getInputStream().readAllBytes());
```

```python
# Python Agent 示例
import subprocess
result = subprocess.run(["python", "scripts/open_webpage.py", "--url", url], capture_output=True, text=True)
tool_output = result.stdout
```

## 文件结构

```
auto_sign_skill/
├── skill.md                  # 本文件
├── config.json               # 运行时配置（setup.py 生成，含 API Key）
├── state.json                # 浏览器运行状态（start_browser.py 生成）
├── llm_client.py             # LLM API 客户端
├── vision_analyzer.py        # VLM 视觉分析
├── browser.py                # Playwright 浏览器控制
├── page_state.py             # 数据模型
├── prompts/
│   └── vision_analyze.txt    # VLM 系统提示词
└── scripts/                  # tool 脚本（每个脚本 = 一个 tool）
    ├── setup.py              # 环境准备
    ├── start_browser.py      # 启动浏览器
    ├── stop_browser.py       # 关闭浏览器
    ├── open_webpage.py       # Tool: 打开网页
    ├── click.py              # Tool: 点击
    ├── type_text.py          # Tool: 输入文字
    ├── press_key.py          # Tool: 按键
    ├── scroll.py             # Tool: 滚动
    └── _shared.py            # 共享工具（CDP连接、VLM分析）
```

## 配置

`config.json`（由 setup.py 生成）：

```json
{
  "llm": {
    "api_key": "sk-your-key",
    "api_base": "https://api.moonshot.cn/v1",
    "model": "kimi-k2.5",
    "min_request_interval": 4
  },
  "browser": {
    "channel": "msedge",
    "viewport_width": 1280,
    "viewport_height": 800
  }
}
```

支持 Kimi、OpenAI、通义千问等任何 OpenAI 兼容 API。
