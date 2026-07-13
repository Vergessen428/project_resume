# 秋招助手 · Autumn PM Coach

> 面向产品经理秋招的**面试后复盘与长期训练**工具。不做实时面试辅助——
> 它在面试结束后，把你的录音 / 转写整理成**带原文证据**的结构化复盘，
> 沉淀重复出现的薄弱点，并生成阶段成长报告。

<p align="center">
  <img src="docs/screenshots/02-review-output.png" alt="带原文证据的 PM 复盘" width="820">
</p>

- **在线演示（只读）**：<https://huggingface.co/spaces/Vergessne/autumn-pm-coach>
- **纯 Python 标准库**，无第三方依赖，本地一条命令即可运行
- **数据默认留在本机**，转写 / 复盘 / 搜索仅在你主动发起时才调用大模型

---

## ✨ 功能特性

| 模块 | 作用 |
| --- | --- |
| **面试工作台** | JD 提取、录音转写（Gemini）、文字导入，生成单场带原文证据的复盘与行动项 |
| **简历库** | 维护多个简历版本；上传 PDF / PNG / JPG / WebP 并解析成可编辑文本 |
| **面经资料库** | Google Search 发现公开资料；录入原帖后由 AI 分为 `AI 可用` / `待确认` / `不使用`，复盘只引用可用来源并保留原链接 |
| **PM 技能包** | 产品判断、项目主导力、指标与实验、推进与协作、结构化表达、业务与岗位理解 六维诊断 |
| **长短期记忆** | 单场复盘保留当前上下文；阶段报告从历次复盘中提取重复薄弱点、行动项和能力变化 |

设计原则：**证据优先**——每条结论都要引用转写原文（含时间戳）；转写内容被当作
**不可信数据**处理，避免提示词注入把面试材料里的指令当成命令执行。

---

## 🚀 快速开始

需要 **Python 3.12+**（仅标准库，无需 `pip install`）。

```bash
# 1. 克隆仓库
git clone https://github.com/Vergessen428/project_resume.git
cd project_resume

# 2. 配置模型 Key（至少填一个供应商）
cp app/.env.example app/.env
#   编辑 app/.env，填入 GEMINI_API_KEY 或 OPENAI_API_KEY 等

# 3. 启动
python3 -B app/web_app.py
```

浏览器打开 <http://127.0.0.1:8765> 即可使用。服务只监听本机，`Ctrl-C` 停止。

> 本地不设口令时直接进入工作台；设置 `APP_ACCESS_TOKEN` 后需在登录框输入相同口令。
> 想快速看效果？进入工作台点 **载入演示档案**，会填充一份带完整复盘的示例。

---

## 🧭 使用流程

```text
① 新建面试        →  填公司 / 岗位 / 轮次，粘贴 JD（可一键提取岗位画像）
② 导入面试材料    →  上传录音自动转写，或直接粘贴带时间戳的转写 / 手写记录
③ 生成 PM 复盘    →  产出「表现亮点 / 需要补强 / 能力诊断 / 逐题复盘 / 行动项」，每条都带原文证据
④ 沉淀面经        →  在面经资料库录入公开原帖，AI 预审后作为可追溯参考
⑤ 阶段成长报告    →  跨多场面试提取重复薄弱点和能力变化，形成长期训练计划
```

---

## 🖼️ 界面展示

**面试工作台**：左侧档案列表 + 顶部指标概览，右侧录入面试材料。

![面试工作台](docs/screenshots/01-review-workspace.png)

**带原文证据的复盘**：亮点 / 补强 / PM 能力诊断，每条结论都引用转写原文与时间戳。

![证据优先复盘](docs/screenshots/02-review-output.png)

**面经资料库**：搜索发现候选资料，录入原帖后经 AI 预审，标注可用状态与置信度。

![面经资料库](docs/screenshots/03-research-library.png)

**阶段成长报告**：跨场记忆快照，统计重复出现的薄弱点与六维 PM 技能。

![阶段成长报告](docs/screenshots/04-growth-report.png)

---

## 🔀 多模型兜底

文本复盘、JD 提取、资料预审和阶段报告支持按顺序自动切换模型：

```text
Gemini → OpenAI → DeepSeek → OpenRouter → Custom (任意 OpenAI 兼容端点)
```

在 `app/.env` 填入至少两个供应商的 Key，按需修改 `MODEL_FALLBACK_ORDER`。未配置的供应商
会自动跳过。**只有**网络错误、超时、限流或 API 报错才会切换；模型正常返回的内容不会被覆盖。

> 联网资料发现与音频 / 文件解析走 Gemini 原生 API（Google Search / Files），
> 文本备用模型无法完全替代这两项。

---

## 🧱 技术栈

- **后端**：Python 3.12+ 标准库 `http.server`，零第三方依赖
- **前端**：原生 HTML / CSS / JS，无构建步骤
- **模型**：Gemini / OpenAI / DeepSeek / OpenRouter / 自定义 OpenAI 兼容端点
- **存储**：本地 JSON（原子写入 + 文件锁），默认 `.gitignore`
- **测试 / CI**：`unittest` + GitHub Actions（push / PR 自动跑）

```text
app/
  web_app.py          # HTTP 服务与路由、三级访问控制、限流
  core/
    model_provider.py # 从环境变量装配模型客户端（唯一 provider 装配点）
    models.py         # OpenAI 兼容 / Gemini / 多模型兜底，统一 complete(prompt)
    multipart.py      # 标准库 multipart 解析（替代已弃用的 cgi）
    interview_review.py / research_grounding.py / audio_transcription.py
    interview_store.py / resume_store.py / research_store.py / growth_memory.py / pm_skills.py
  web/                # 前端（原生 HTML/CSS/JS）
  data/               # 本地 JSON 数据（gitignore）
static_demo/          # 纯前端只读演示版（部署到 Hugging Face Static Space）
tests/                # 单元测试
docs/                 # 项目文档、面试讲稿与界面截图
```

---

## 🔐 数据与隐私

- 面试记录、简历、面经默认保存在本机 `app/data/`（`interviews.json` 等），已被 Git 忽略。
- 三级访问控制：本地免密 / 公网需 `APP_ACCESS_TOKEN` / `APP_DEMO_MODE=1` 只读演示。
- 口令连错 5 次锁定 60 秒（按 IP 限流），防暴力破解。
- 上传的音频处理后即从临时目录删除。

---

## 🌐 部署

- **免费只读演示**：`static_demo/` 是纯前端 Mock 版，部署到 Hugging Face Static Space
  即可拿到公开可点的展示链接，见 [DEPLOY_HUGGINGFACE.md](./DEPLOY_HUGGINGFACE.md)。
- **完整功能部署**：带后端的动态部署见 [DEPLOY_RENDER.md](./DEPLOY_RENDER.md)。
  部署到公网时**务必设置 `APP_ACCESS_TOKEN`**。

## ✅ 测试

```bash
python3 -m pytest tests/ -q
```

## 📚 更多文档

- [docs/PROJECT_OVERVIEW.md](./docs/PROJECT_OVERVIEW.md) — 项目完整介绍
- [docs/ARCHITECTURE_EVOLUTION.md](./docs/ARCHITECTURE_EVOLUTION.md) — 架构演进
- [docs/DATA_BACKUP.md](./docs/DATA_BACKUP.md) — 数据备份与迁移
- [docs/INTERVIEW_TALKING_POINTS.md](./docs/INTERVIEW_TALKING_POINTS.md) — 面试讲稿
- [app/README.md](./app/README.md) — 应用代码说明

## 👥 贡献者

- [**Vergessen428**](https://github.com/Vergessen428) — 项目作者
- **Codex** — AI 结对编程助手

## 📄 许可

本项目为个人求职作品，欢迎参考交流。
