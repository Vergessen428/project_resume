# 秋招助手 · 项目介绍

面向产品经理秋招的**面试后复盘与长期训练**工具。它不做实时面试作弊，而是帮你在
面试结束后，把录音 / 转写整理成**带原文证据**的结构化复盘，沉淀重复薄弱点，并随着
面试场次积累生成阶段成长报告。

---

## 1. 它解决什么问题

秋招面试最大的浪费，是「面完就忘」：

- 面试当下紧张，记不清自己到底哪句答得虚、哪个追问没接住。
- 复盘全靠感觉，没有原文证据，容易自我安慰或过度否定。
- 面了十几场，却说不清自己在「指标定义」「项目主导力」这些能力上到底有没有进步。

秋招助手把这条链路结构化：

```text
面试录音/转写  ->  AI 复盘（每条结论都带原文证据+评分）
              ->  沉淀到本地记忆
              ->  多场累积后生成阶段报告（重复薄弱点、能力变化、优先训练项）
```

## 2. 核心功能

### 面试工作台
- **JD 提取**：粘贴岗位 JD，AI 提炼职责、要求、关键词、可能追问方向。
- **录音转写**：上传面试录音（MP3/M4A/WAV/AAC/OGG/WebM，≤50MB），Gemini 转成带
  时间戳的文字。原始音频处理后从本机临时目录删除。
- **文字导入**：也可直接粘贴转写，或导入 `.txt` / `.md` / `.srt`。
- **单场复盘**：生成结构化复盘，包含——
  - 2-4 句总结
  - 表现亮点 / 需要补强（每条带原文证据）
  - 逐题复盘（问题、你的回答摘要、原文证据、评估、评分、练习建议）
  - PM 六维能力诊断（评分 + 证据 + 诊断 + 下一步练习）
  - 行动项清单（可勾选完成）

### 简历库
- 维护多个简历版本；保存面试档案时会记录当时关联的简历内容快照。
- 支持上传 PDF / PNG / JPG / WebP（≤25MB），Gemini 解析成可编辑文本。

### 面经资料库（可溯源）
- **联网发现**：用 Google Search 发现候选公开面经（牛客、小红书等），只提供原帖入口。
- **证据门槛**：你录入原帖正文摘录后，AI 预审分为 `AI 可用` / `待确认` / `不使用`。
  - 只有 `auto_approved`（置信度≥80）或你人工确认过的资料，才会进入后续复盘引用。
  - 评论只作为可信度信号，不作为事实证明。
  - 所有资料都保留原链接与发布日期。

### 阶段成长报告（长期记忆）
- 只基于**已生成复盘**的面试记录。
- 提取跨场重复出现的薄弱点、能力评分变化、最高优先级训练项。
- 单场证据与跨场趋势分开呈现，明确标注「数据边界」，避免把猜测当结论。

### PM 能力框架
六个可复用的教练维度：产品判断、项目主导力、指标与实验、推进与协作、结构化表达、
业务与岗位理解。复盘和成长报告都以此为评分锚点。

## 3. 设计原则

1. **证据优先**：复盘里每条结论都要引用原文（近似原句 + 时间戳）。转写被当作
   **不可信数据**，不是指令——从根上防 prompt injection。
2. **不臆造**：转写稀疏时，模型被要求「说数据不足」而不是编造问题、结果或录用结论。
3. **本地优先**：面试材料、简历、面经默认只存本机 JSON，联网只在你主动发起转写 /
   复盘 / 搜索时才调用 Gemini。
4. **可溯源**：外部面经必须过 AI/人工证据门槛，且永远保留来源链接和日期。

## 4. 技术架构

纯 **Python 标准库**实现，无第三方依赖，前端是原生 HTML/CSS/JS 无构建步骤。

```text
app/
  web_app.py            # http.server 路由：REST API + 静态资源 + 访问口令鉴权
  core/
    model_provider.py   # 从环境变量装配模型客户端（唯一的 provider 装配点）
    models.py           # OpenAI 兼容 / Gemini / 多模型兜底，统一 complete(prompt) 接口
    multipart.py        # 标准库 multipart 解析（替代已弃用的 cgi）
    interview_review.py # 复盘 / JD 提取 / 阶段报告的 prompt 与结果归一化
    research_grounding.py # Google Search 发现 + 证据门槛预审
    audio_transcription.py # Gemini Files API 音频转写 / 简历文件解析
    interview_store.py  # 面试记录本地 JSON 存储（原子写 + 锁）
    resume_store.py     # 简历库存储
    research_store.py   # 面经资料存储 + 状态门槛
    growth_memory.py    # 确定性长期记忆聚合（无模型调用）
    pm_skills.py        # PM 能力评分框架
  web/                  # 前端
  data/                 # 本地数据（gitignore）
tests/                  # 单元测试
docs/                   # 项目背景与面试讲稿
```

### 数据流（一次复盘）

```text
浏览器提交面试档案
  -> web_app 校验 + InterviewStore 保存
  -> build_model() 按 MODEL_FALLBACK_ORDER 选出模型
  -> generate_interview_review(): 组装 prompt（面试材料 + 已确认面经 + 长期记忆）
  -> model.complete(prompt) -> 解析 JSON -> 归一化（评分钳制、行动项生成 id）
  -> InterviewStore.save_review() 落盘
  -> 返回结构化复盘给前端渲染
```

### 多模型兜底

```text
Gemini -> OpenAI -> DeepSeek -> OpenRouter -> Custom OpenAI-compatible endpoint
```

在 `.env` 配置多个供应商后，只有**网络错误 / 超时 / 限流 / API 错误**才切换到下一个；
模型正常返回的内容（包括拒答）不会被覆盖。失败的供应商进入 60 秒冷却，避免反复卡在
不可用的 API 上。

> 注意：联网发现走 Gemini 原生 Google Search（失败可回退 OpenAI Web Search），
> 音频 / 文件解析走 Gemini Files API——这两项文本备用模型无法替代。

## 5. 安全模型

- **访问口令**：设置 `APP_ACCESS_TOKEN` 后，所有 `/api/*` 需要匹配的 `X-App-Token`，
  用 `hmac.compare_digest` 常量时间比较。`/healthz` 始终公开且不含数据。
- **本地数据不入库**：`.env` 和 `data/*.json` 均被 gitignore，简历/面试隐私不会进仓库。
- **响应头**：`X-Content-Type-Options`、`X-Frame-Options: DENY`、`Referrer-Policy: no-referrer`。
- **上传限制**：音频 50MB、简历 25MB、JSON 体 120KB；MIME 类型白名单校验。

## 6. 本地运行

需要 Python 3.12+。

```bash
cp app/.env.example app/.env      # 填入 GEMINI_API_KEY
python3 -B app/web_app.py
```

浏览器打开 http://127.0.0.1:8765 。服务只监听本机，`Ctrl-C` 停止。
本地不设口令直接进工作台；设了 `APP_ACCESS_TOKEN` 则需在登录框输入相同口令。

## 7. 部署

见 [DEPLOY_RENDER.md](../DEPLOY_RENDER.md)。已配好 `render.yaml`（Blueprint 一键部署，
带 1GB 持久盘）。**部署到公网必须设置 `APP_ACCESS_TOKEN`**。

## 8. 测试

```bash
python3 -m pytest tests/ -q
```

覆盖 multipart 解析、复盘结果归一化、成长记忆聚合、面经资料门槛等纯逻辑。

## 9. 目录里的另一份实现

`mini_agent_python/` 是早期的一体化版本，内含一个教学用的 "mini agent runtime"
（agent loop / 工具 / 权限 / 日志）。当前面试助手已从中抽出、解耦为独立的 `app/`，
老版保留作参考和面试讲解素材。相关设计文档见本目录下的 `MINI_AGENT_BUILD_PLAN.md`、
`OPENCLAW_EXPERIMENT_PLAYBOOK.md` 等。
