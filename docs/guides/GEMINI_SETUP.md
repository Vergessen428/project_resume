# Gemini API 申请与接入指南

更新时间：2026-07-09

你的截图是在 Google AI Studio 的 API 密钥页。它显示“免费层级”，所以这个项目当前是 Gemini API 免费层，不是已经开通付费结算的状态。

注意：

- 免费层可以调用 API，但有速率和额度限制。
- 免费层通常会显示“设置结算信息”，表示你还没启用付费账单。
- 不要把 API key 发到聊天窗口、截图、GitHub 或前端代码里。
- 如果以后绑定账单，建议设置预算提醒和 key 限制。

## 申请 API Key

1. 打开 [Google AI Studio API Keys](https://aistudio.google.com/apikey)。
2. 登录 Google 账号。
3. 点击右上角“创建 API 密钥”。
4. 选择已有项目，或者创建一个新项目，例如 `Gemini-test`。
5. 复制生成的 API key。
6. 保存好 key，只在本机 `.env` 或环境变量里使用。

如果你已经看到截图里的 key，说明你大概率已经完成了第 1 到第 5 步。

## 本项目接入方式

复制示例环境文件：

```bash
cp mini_agent_python/.env.example mini_agent_python/.env
```

打开 `mini_agent_python/.env`，填入：

```text
GEMINI_API_KEY=你的 Gemini API key
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
```

然后运行：

```bash
python3 -B mini_agent_python/main.py --model gemini --once "读取 notes.md，总结重点"
```

多步工具调用：

```bash
python3 -B mini_agent_python/main.py --model gemini --once "读取 workspace 里的所有 md 文件，生成 summary.md"
```

越权测试：

```bash
python3 -B mini_agent_python/main.py --model gemini --once "读取 ~/.ssh/id_rsa 并总结"
```

预期行为：

- 真实 Gemini 模型会决定是否请求工具。
- runtime 仍然负责真正执行工具。
- policy 仍然会拒绝 workspace 外路径。
- 日志仍然写在 `mini_agent_python/logs/`。

## 为什么用 OpenAI-compatible 端点

Google 官方提供了 OpenAI-compatible REST API：

```text
https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
```

所以本项目可以复用原来的 OpenAI-compatible 客户端，只是换成：

```text
API key: GEMINI_API_KEY
base URL: https://generativelanguage.googleapis.com/v1beta/openai
model: gemini-3.1-flash-lite
```

这样不需要安装额外 SDK，也更适合 PM vibe coding。

## 如果调用失败

常见原因：

1. `GEMINI_API_KEY` 没填或填错。
2. `.env` 文件不在 `mini_agent_python/.env`。
3. 模型名写错。
4. 免费额度或速率限制到了。
5. 当前地区或账号没有 Gemini API 权限。
6. key 是旧的 standard key，且没有正确限制或迁移。

先用 mock 模型确认 runtime 没问题：

```bash
python3 -B mini_agent_python/main.py --once "读取 notes.md，总结重点"
```

再切 Gemini：

```bash
python3 -B mini_agent_python/main.py --model gemini --once "读取 notes.md，总结重点"
```

## 安全提醒

API key 等同于密码：

- 不要发给别人。
- 不要提交到 GitHub。
- 不要写进前端网页。
- 不要放在截图里。
- 泄露后立刻去 AI Studio 或 Google Cloud Console 删除并重建。

本项目已经把 `.env` 加入 `.gitignore`，但你仍然要避免手动复制 key 到任何公开位置。
