# 部署到 Render

有两种部署目标，`render.yaml` 默认配置的是**方案一（免费展示 demo）**。

---

## 方案一：免费展示 demo（推荐用于给别人看）

用 Render 免费层 + demo 模式。访客免密只读浏览、打开就能看到一份带完整复盘的示例；
保存 / AI 调用 / 联网搜索需要管理口令（只有你有）。数据不持久，但 demo 模式每次启动会
自动重新灌入示例，所以重启也不影响展示。**0 成本。**

### 步骤

1. 代码已在 GitHub 仓库（`Vergessen428/project_resume`）。
2. 登录 [render.com](https://render.com) → **New → Blueprint** → 选这个仓库，Render 会
   自动读 `render.yaml`（已配置为 `plan: free` + `APP_DEMO_MODE=1`）。
3. 创建时填两个环境变量（`sync: false`，不入 Git）：
   - `GEMINI_API_KEY`：你的 Gemini key（建议用吊销重建后的新 key）
   - `APP_ACCESS_TOKEN`：一个只有你知道的管理口令。访客不需要它就能看，只有你要写入/生成时才用。
4. 创建服务，等构建完成，得到 `https://autumn-pm-coach-xxxx.onrender.com`。
5. 把这个网址直接发给面试官——**打开即用，无需登录，能看到完整复盘示例**。

### 免费层的两个限制（可接受）
- **冷启动**：15 分钟无访问会休眠，下次打开等 ~50 秒。发链接时可提一句"首次打开稍慢"。
- **数据不持久**：访客的任何改动、重启都会清空——但这正是 demo 想要的（永远回到干净示例）。

---

## 方案二：付费持久化（你自己长期在线存真实数据时才需要）

如果哪天你想把它当成自己在线用的工具（而不只是 demo），需要持久磁盘保存数据，改用付费
Starter 套餐（约 $7/月）。把 `render.yaml` 改成：

```yaml
services:
  - type: web
    name: autumn-pm-coach
    runtime: python
    plan: starter                       # 付费，支持持久盘
    buildCommand: "true"
    startCommand: "python3 -B app/web_app.py --host 0.0.0.0 --port $PORT"
    healthCheckPath: /healthz
    disk:
      name: autumn-pm-data
      mountPath: /var/data
      sizeGB: 1
    envVars:
      - key: APP_DATA_DIR
        value: /var/data                # 数据存到持久盘
      - key: APP_ACCESS_TOKEN           # 不开 demo，全站需口令
        sync: false
      - key: GEMINI_API_KEY
        sync: false
      - key: GEMINI_MODEL
        value: gemini-3.1-flash-lite
      - key: MODEL_FALLBACK_ORDER
        value: gemini,openai,deepseek,openrouter,custom
```

关键区别：付费方案**不设** `APP_DEMO_MODE`（全站需口令，保护你的真实数据），并挂持久盘。

> 提示：自己日常用其实直接本地 `python3 -B app/web_app.py` 最省事，数据就在本机
> `app/data/`。方案二只在你需要"随时随地在线访问自己的真实记录"时才有必要。

---

## 可选：多模型兜底

服务建好后，可在 Render 环境变量里再加 `OPENAI_API_KEY`、`DEEPSEEK_API_KEY`、
`OPENROUTER_API_KEY` 或 `CUSTOM_MODEL_*`，Gemini 失败时自动切换。
见 `app/.env.example` 的模型名与地址。

## 说明

- `/healthz` 公开且不含任何数据；`/api/*` 的读写权限由 `APP_ACCESS_TOKEN` 和 `APP_DEMO_MODE`
  共同决定（详见 `docs/PROJECT_OVERVIEW.md` 安全模型一节）。
- 口令校验有 per-IP 限流：连续失败 5 次锁定 60 秒。
