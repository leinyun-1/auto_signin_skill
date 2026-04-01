---
name: auto-signin-skill
description: "使用浏览器自动登录某网站时使用。本 skill 适用于多模态 Agent（具备读图能力）。"
metadata:
  {
    "openclaw":
      {
        "requires": { "bins": ["python"] },
        "platforms": ["macos", "linux", "windows"],
      },
  }
---

# Auto Sign Skill

网页自动登录工具集。所有 tool 命令加 `--no-analyze` 参数，执行操作后返回截图文件路径，由你自行读取截图分析页面。识别成功登录后结束(询问用户是否关闭浏览器)。
！执行工具时，必须进入到本skill的项目根目录内！
**环境要求：** Python 3.8+

---

## 能力边界

能做：打开网页、点击按钮/链接、在输入框中输入文字、处理常见登录流程（账号密码（输入前询问user获得）、第三方登录选择（优先qq\微信登录）、扫码页切换到密码登录）。

做不到：文件上传、滑块/图形验证码自动破解、手机短信验证码获取、双因素认证（2FA）、非 Web 登录、iframe 嵌套登录框、JavaScript 原生弹窗。

---

## 配置

创建 `config.json`：

```json
{
  "browser": {
    "channel": "msedge",
    "headless": false,
    "viewport_width": 1280,
    "viewport_height": 800,
    "default_timeout": 30000,
    "screenshot_dir": "./screenshots"
  }
}
```

运行 `python scripts/setup.py` 安装依赖。

---

## 启动与关闭

```bash
python scripts/start_browser.py
# ... 执行 tool ...
python scripts/stop_browser.py # 询问user是否关闭
```

`start_browser.py` 启动后立即返回，浏览器作为独立进程保持运行。重复执行是安全的（幂等）。

---

## Tool 列表

所有命令必须加 `--no-analyze`。

| Tool | 命令 | 参数 | 前置条件 | 工具说明 |
|------|------|------|---------|---------|
| open_webpage | `python scripts/open_webpage.py --url <URL> --no-analyze` | `--url` (必填) | 浏览器已启动 | 如果打开目标网址发现已是登录状态，则任务直接结束。
| click | `python scripts/click.py --x <X> --y <Y> --no-analyze` | `--x` (必填), `--y` (必填)。归一化坐标(0~1) | 浏览器已启动，已有页面打开 | 若点击后页面状态未改变，则反思坐标的精准度
| type_text | `python scripts/type_text.py --text <TEXT> --no-analyze` | `--text` (必填) | 必须先用 click 点击目标账号/密码输入框获取焦点 | 若输入后页面内未增加输入字符，说明未聚焦

**调用顺序：**

```
setup.py ──→ start_browser.py ──→ open_webpage.py ──→ click.py / type_text.py
（一次性）                         （必须先打开页面）

type_text.py 前必须先 click.py 点击输入框获取焦点。
```

---

## stdout 输出格式
调用任一tool后会返回stdout结果
```
操作: <操作描述>

当前页面状态:
截图: <截图文件绝对路径>
URL: <当前页面URL>

[分析指令] ...
```

解析方法：
- 截图路径：匹配 `截图: ` 开头的行，取其后的完整路径
- URL：匹配 `URL: ` 开头的行，取其后的完整 URL
- 用文件读取工具读取截图路径指向的 PNG 图片，自行分析页面内容
- 严禁使用 list_dir 或类似手段在 screenshots/ 目录下寻找截图。必须且仅能 使用当前工具调用返回的 stdout 中的“截图: ”路径。

---

## 读图分析指引

读取截图后，完成以下分析：

1. **判断页面状态**（见下方"页面状态模型"）
2. **识别所有可交互元素**：按钮、输入框、链接、二维码
3. **输出归一化坐标（0~1）**，严禁输出像素坐标。`click.py` 只接受归一化坐标。
4. **优先关注登录相关元素**

**⚠️ 坐标精度指引：**

截图可能被框架压缩或缩放，实际分辨率未知。**必须使用归一化坐标（0~1）。**

分析截图时使用以下格式：

```
分析这张网页截图，完成以下任务：

1. 判断页面类型：login_entry / login_form / qr_code_login / third_party_select / captcha / login_success / error_page / unknown

2. 识别所有可交互的 UI 元素（按钮、输入框、链接、二维码），每个元素输出：
   - type: button / input / link / qrcode
   - text: 元素上显示的文字
   - x: 中心点 x 归一化坐标（0~1，0=左边缘，1=右边缘）
   - y: 中心点 y 归一化坐标（0~1，0=上边缘，1=下边缘）

3. 以 JSON 格式输出：
{"page_type": "login_form", "elements": [{"type": "input", "text": "请输入用户名", "x": 0.39, "y": 0.39}, {"type": "button", "text": "登录", "x": 0.39, "y": 0.53}]}

坐标为元素中心相对于图片宽高的比例，将直接用于点击操作。
```
坐标校验： 若点击后截图显示的页面状态（Page State）与预期完全不符，Agent 应立即停止操作并重新分析截图，而不是盲目继续下一步。



### 登录成功判断

读取截图，需满足以下特征中的 **2 个或以上**：

| 判断依据 | 具体特征 |
|---------|---------|
| 用户信息出现 | 页面上出现用户昵称、头像、邮箱地址等 |
| 已登录菜单 | 出现"个人中心"、"退出登录"、"我的账户"等 |
| 登录入口消失 | 之前的"登录"按钮已替换为用户头像或昵称 |
| URL 变化 | 从登录页跳转到新 URL（`/login` → `/home`、`/index`、`/dashboard`） |
| 登录表单消失 | 之前存在的登录弹窗/表单/输入框已不可见 |


登录失败特征：登录表单仍在且出现红色错误提示、页面未变化、出现 captcha 验证码页面。

---

## 页面状态模型

| 状态 | 典型特征 | 应采取的行动 |
|------|---------|-------------|
| `login_entry` | 有"登录"按钮或默认头像，登录表单未打开 | 点击"登录"按钮 |
| `third_party_select` | 多个登录选项（QQ/微信/手机号等） | 选择一种登录方式并点击 |
| `qr_code_login` | 页面显示二维码 | 点击"密码登录"链接切换 |
| `login_form` | 用户名输入框、密码输入框、登录按钮 | 点击输入框→输入账号→点击密码框→输入密码→点击登录 |
| `captcha` | 滑块验证、图形验证码 | **通知用户手动完成** |
| `login_success` | 用户昵称/头像可见，登录表单消失 | **任务完成，停止操作** |
| `error_page` | 404、500、空白页 | 重试 `open_webpage.py`；多次失败则终止 |
| `unknown` | 加载中、无法识别 | 等待 2-3 秒后重新截图；多次仍 unknown 则终止 |

状态转换：

```
open_webpage → login_entry → third_party_select → login_form → login_success
                    │                │                  │            ▲
                    │                ▼                  ▼            │
                    │         qr_code_login         captcha ────────┘
                    │                │               (人工完成后)
                    │                ▼
                    └──→ login_form ─┘

异常路径：error_page → 重试或终止 / unknown → 等待或终止
```

### 终止条件

| 条件 | 判断方式 | 处理 |
|------|---------|------|
| 登录成功 | 满足≥1个登录成功特征 | 报告成功 |
| 验证码拦截 | 页面状态为 `captcha` | 通知用户手动完成 |
| 页面错误 | `error_page` 且重试 2 次仍失败 | 报告错误 |
| 状态无法推进 | 连续 3 步状态未变化 | 报告卡住，请求指导 |
| 步数上限 | 超过 20 步 | 报告超时 |
| Tool 执行失败 | exit code = 1 且重试 1 次仍失败 | 报告错误 |

---

## 错误处理

| 错误类型 | stderr 特征 | 处理 |
|---------|------------|------|
| 浏览器未启动 | `错误: 浏览器未启动` | 运行 `start_browser.py` |
| CDP 连接失败 | `connect_over_cdp` / `Connection refused` | `stop_browser.py` 后重新 `start_browser.py` |
| 页面导航失败 | `net::ERR_` / `Timeout` | 检查 URL，重试 `open_webpage.py` |
| 配置缺失 | `错误: 配置文件不存在` | 创建 config.json |

---


## 交互规范
1. 需要账号密码时，询问用户。
2. 登录成功后，详细描述登录成功的依据，清理截图，然后结束本次任务。

## 完整工作流示例

```
步骤 1: 打开网页
$ python scripts/open_webpage.py --url "https://mail.qq.com" --no-analyze
→ 读取截图，判断 login_form，如果已经是登录状态说明网站有cookie，直接结束。若未登录，识别输入框 x=0.66 y=0.38

步骤 2: 点击用户名输入框
$ python scripts/click.py --x 0.66 --y 0.38 --no-analyze
→ 读取截图，确认输入框获取焦点

步骤 3: 输入用户名
$ python scripts/type_text.py --text "myuser" --no-analyze
→ 读取截图，确认已输入

步骤 4: 点击密码输入框
$ python scripts/click.py --x 0.66 --y 0.44 --no-analyze
→ 读取截图，确认点击结果

步骤 5: 输入密码
$ python scripts/type_text.py --text "mypassword" --no-analyze
→ 读取截图，确认输入成功

步骤 6: 点击登录按钮
$ python scripts/click.py --x 0.66 --y 0.52 --no-analyze
→ 读取截图，URL 已变化 + 登录表单消失 → 登录成功，任务完成

步骤 7：清理登录过程中暂存的截图，结束任务。
```

---

## 注意事项

- 所有 tool 的工作目录必须是 skill 根目录（即本文件所在目录）
- 每次 tool 调用会自动递增截图编号（step_001.png, step_002.png, ...）
