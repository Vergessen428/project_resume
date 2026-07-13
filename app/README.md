# 复盘助手（PM Interview Assistant）

面向产品经理的**面试后复盘与长期训练**工具。不提供实时面试辅助——它帮你在
面试结束后，把录音/转写整理成带原文证据的结构化复盘，沉淀薄弱点，并生成阶段成长报告。

## 功能

- **面试工作台**：JD 提取、录音转写（Gemini）、文字导入、单场带原文证据的复盘与行动项。
- **简历库**：维护多个简历版本；可上传 PDF / PNG / JPG / WebP 并解析成可编辑文本。
- **面经资料库**：Google Search 发现候选公开资料；录入原帖正文后由 AI 分为
  `AI 可用` / `待确认` / `不使用`。复盘只会引用可用或你确认过的资料，并保留原链接与日期。
- **PM 技能包**：产品判断、项目主导力、指标与实验、推进与协作、结构化表达、业务与岗位理解。
- **长短期记忆**：单场复盘保留当前上下文；阶段报告从历次已复盘面试中提取重复薄弱点、
  行动项和能力变化。

数据默认保存在本机 `data/`（`interviews.json` / `resumes.json` / `research.json`），已被 Git 忽略。

## 目录结构

```text
app/
  web_app.py          # HTTP 服务与路由
  core/
    model_provider.py # 从环境变量装配模型客户端（唯一的 provider 装配点）
    models.py         # OpenAI 兼容 / Gemini / 多模型兜底，统一 complete(prompt) 接口
    multipart.py      # 标准库 multipart 解析（替代已弃用的 cgi）
    interview_review.py
    research_grounding.py
    audio_transcription.py
    interview_store.py
    resume_store.py
    research_store.py
    growth_memory.py
    pm_skills.py
  web/                # 前端（原生 HTML/CSS/JS，无构建步骤）
  data/               # 本地 JSON 数据（gitignore）
tests/                # 单元测试
docs/                 # 项目文档与界面截图（与运行无关）
```

## 本地运行

需要 Python 3.12+（仅标准库，无第三方依赖）。

```bash
cp app/.env.example app/.env      # 填入 GEMINI_API_KEY
python3 -B app/web_app.py
```

浏览器打开 http://127.0.0.1:8765 。服务只监听本机，`Ctrl-C` 停止。

本地不设访问口令时直接进入工作台；设置 `APP_ACCESS_TOKEN` 后需在登录框输入相同口令。

### 多模型兜底

文本复盘、JD 提取、资料预审和阶段报告支持按顺序切换模型：

```text
Gemini -> OpenAI -> DeepSeek -> OpenRouter -> Custom OpenAI-compatible endpoint
```

在 `.env` 填入至少两个供应商的 Key，并按需修改 `MODEL_FALLBACK_ORDER`。未配置的供应商会
自动跳过。只有网络错误、超时、限流或 API 错误才会切换；模型正常返回的内容不会被覆盖。

联网资料发现与音频/文件解析走 Gemini 原生 API（Google Search / Files），文本备用模型无法
完全替代这两项。

## 部署

见仓库根的 [DEPLOY_RENDER.md](../DEPLOY_RENDER.md)。部署到公网时**务必设置 `APP_ACCESS_TOKEN`**。

## 测试

```bash
python3 -m pytest tests/ -q
```
