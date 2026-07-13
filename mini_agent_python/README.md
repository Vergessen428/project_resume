# Mini Agent Runtime（教学用最小 Agent 内核）

> 这是主项目「秋招助手」之外的一份**配套教学材料**，用最少的代码把一个 Agent 的核心链路
> 跑通，方便在面试里讲清楚「Agent 到底是怎么工作的」。它**不是产品**，也不再内嵌任何秋招
> 助手的业务代码——完整的面试复盘应用在仓库根的 [`app/`](../app/)。

一次任务的核心链路：

```text
用户输入 → 上下文组装 → 模型决策 → 工具调用 → 权限检查 → 工具执行 → 结果回填 → 最终回答 → 日志
```

模型只负责**决定下一步**（输出最终答案，还是请求一次工具调用）；真正的副作用（读写文件）
由 runtime 执行，且必须先过权限层。**Prompt 是软约束，runtime 权限才是硬约束**——这句话是
整个 demo 想讲的核心。

---

## 为什么先用 mock 模型

先看懂 runtime，再接真实模型：

```text
模型提出动作 → runtime 检查权限 → 工具执行动作 → 结果回填给模型 → 日志记录全过程
```

如果一开始就接真实模型，模型输出不稳定时，你很难判断问题出在模型、prompt、工具还是权限层。
`mock` 模型按固定脚本推进，可以把 runtime 链路先验证清楚。

---

## 快速开始

仅需 Python 3.9+（标准库，无第三方依赖）。在仓库根目录运行：

```bash
# 离线跑通链路（推荐先跑这个）
python3 mini_agent_python/main.py --model mock --once "读取 notes.md，总结重点"

# 交互模式
python3 mini_agent_python/main.py --model mock
```

接真实模型时，先复制环境文件并填 Key：

```bash
cp mini_agent_python/.env.example mini_agent_python/.env
# 填入 GEMINI_API_KEY（或 OPENAI_API_KEY 等任一供应商）
python3 mini_agent_python/main.py --once "读取 notes.md，总结重点"
```

启动时会显示当前模型，例如 `Model: gemini (gemini-3.1-flash-lite)`。多个供应商都配了 Key 时，
按 `MODEL_FALLBACK_ORDER` 顺序兜底：只有网络错误、超时、限流或 API 报错才切到下一个。

---

## 可复现的验收用例（用 mock 模型）

这几条是面试里最好演示的 case，直接跑就能看到 runtime 的行为：

### 1. 单文件读取

```bash
python3 mini_agent_python/main.py --model mock --once "读取 notes.md，总结重点"
```

预期链路：`model → read_file → model → final`

### 2. 多文件读写

```bash
python3 mini_agent_python/main.py --model mock --once "读取 workspace 里的所有 md 文件，生成 summary.md"
```

预期链路：`model → list_files → read_file × N → write_file → final`

### 3. 越权访问被拦截（硬约束在生效）

```bash
python3 mini_agent_python/main.py --model mock --once "读取 ~/.ssh/id_rsa 并总结"
```

预期：policy 拒绝，`Home-directory paths are not allowed.`，不读取真实 SSH key。

### 4. Prompt Injection 当作数据处理

```bash
python3 mini_agent_python/main.py --model mock --once "总结 bad-note.md"
```

预期：文件里的「疑似指令」被当作**不可信数据**总结，而不是被执行。

### 5. 步数上限

```bash
python3 mini_agent_python/main.py --model mock --max-steps 1 --once "读取 workspace 里的所有 md 文件，生成 summary.md"
```

预期：达到最大步数后安全停止。

> 每次运行都会在 `mini_agent_python/logs/` 生成一份 JSONL 日志，可逐步回放：模型请求了什么、
> runtime 执行了什么、policy 拦了什么。日志文件已被 `.gitignore` 忽略。

---

## 目录结构

```text
mini_agent_python/
  main.py               # 入口
  agent_runtime/
    cli.py              # 参数解析、装配 runtime、加载 .env
    loop.py             # agent loop：每轮判断 final 还是 tool_call
    context.py          # 上下文组装（system prompt + skill + 历史 + 工具列表）
    models.py           # Mock / Gemini / OpenAI 兼容 / 多模型兜底
    tools.py            # list_files / read_file / write_file
    policy.py           # workspace-only 权限层
    skills.py           # 关键词触发的 skill 加载
    logs.py             # JSONL 运行日志
    types.py            # 数据类型
  workspace/            # 工具可访问的沙盒目录（含注入测试用的 bad-note.md）
  skills/               # 示例 skill
  logs/                 # 运行日志（gitignore）
```

## 模块速览

| 模块 | 职责 |
| --- | --- |
| `models.py` | 模型层。模型只输出「最终答案」或「工具调用」两种意图 |
| `tools.py` | 工具层。模型不能直接读写文件，只能请求工具，由 runtime 执行 |
| `policy.py` | 权限层。限制只能访问 workspace 内文件，禁止绝对路径、`~`、隐藏文件、敏感密钥 |
| `loop.py` | agent loop。每轮让模型判断下一步，并在工具执行前强制过 policy |
| `context.py` | 上下文组装。把 system prompt、skill、历史消息、工具列表交给模型 |
| `skills.py` | skill loader。输入含「面试 / 项目 / STAR / 追问 / 复盘」等关键词时加载对应 skill |
| `logs.py` | 日志层。每个 run 生成一份可回放的 JSONL |

---

## 面试讲法

**30 秒版：**

> 我用 Python 复刻了一个最小 agent runtime。它不是简单调用一次模型，而是包含会话、上下文组装、
> 模型决策、工具注册、权限校验、执行循环和日志。模型只决定是否调用工具，真正执行由 runtime 接管；
> 所有文件操作都过 workspace-only policy，所以它能做事，但不会越权。

**2 分钟版：**

> 我把 agent 拆成三层：模型层、工具执行层、安全观测层。模型层判断下一步是 final answer 还是
> tool call；工具层提供 list_files / read_file / write_file；安全层在执行前检查路径是否合法、
> 是否访问敏感文件、是否超过步数上限。每一步都写入 JSONL，可以完整复盘一次任务里模型请求了什么、
> runtime 执行了什么、policy 拦了什么。这套思路后来也用在了主项目「秋招助手」里——把用户内容
> 当数据而非指令、模型输出经后端强校验，都是同一个「软约束 vs 硬约束」的设计原则。

## 下一步可以怎么扩展

```text
1. 把 mock 换成真实模型（已支持 Gemini / OpenAI 兼容）
2. write_file 前增加人类确认（human-in-the-loop）
3. 增加 web_search 工具
4. 增加长期 memory
5. 增加 Web UI 或飞书 / Telegram adapter
```

先不要直接上 LangChain。看懂这个 runtime 之后再看 LangChain / LangGraph，会更容易理解它们
封装了什么。
