# 部署到 Hugging Face Spaces（免费，境外节点，保留全功能）

Hugging Face Spaces 免费、服务器在境外（能访问 Google/OpenAI，所以 Gemini 全功能可用，
包括音频转写和简历文件解析），控制台在国内通常也能打开。用 Docker SDK 部署。

本仓库已经准备好所需文件：
- `Dockerfile`：Python 3.12 镜像，监听 `0.0.0.0:7860`，以 UID 1000 运行。
- `README.md` 顶部的 YAML frontmatter：`sdk: docker` + `app_port: 7860`，Spaces 靠它识别。
- 纯标准库，无 `requirements.txt`，构建很快。

---

## 步骤

### 1. 注册 / 登录 Hugging Face
浏览器打开 [huggingface.co](https://huggingface.co) → 注册或登录（邮箱即可，不强制 GitHub）。

### 2. 新建 Space
- 打开 [huggingface.co/new-space](https://huggingface.co/new-space)
- **Owner**：你的用户名
- **Space name**：例如 `autumn-pm-coach`
- **License**：随意（如 mit）
- **SDK**：选 **Docker** → **Blank**（空白模板）
- **Visibility**：**Public**（公开才免费；里面是 demo，不含你的真实隐私数据）
- 点 **Create Space**

### 3. 把代码传上去（二选一）

**方式 A：网页上传（不用命令行，最简单）**
- 进入刚建的 Space → **Files** 标签 → **Add file → Upload files**
- 把整个项目拖上去（关键是这几样都要有）：`Dockerfile`、`README.md`、`app/` 整个文件夹
- **不要传** `app/.env`（含你的 key）——它本来就被 gitignore，本地 git 里也没有
- Commit

**方式 B：用 git 推送（如果你网络能连 HF 的 git）**
```bash
git clone https://huggingface.co/spaces/你的用户名/autumn-pm-coach
# 把本项目文件复制进去（不含 app/.env、app/data/*.json），然后：
git add Dockerfile README.md app tests docs DEPLOY_*.md
git commit -m "Deploy to HF Spaces"
git push
```

### 4. 配置环境变量（Secrets）
进入 Space → **Settings** → **Variables and secrets** → 逐个 **New secret**：

| 名称 | 值 | 说明 |
|---|---|---|
| `APP_DEMO_MODE` | `1` | 开启只读演示：访客免密浏览，写入/AI 需口令 |
| `APP_ACCESS_TOKEN` | 你自定义的管理口令 | 只有你写入/生成新复盘时用；访客不需要 |
| `GEMINI_API_KEY` | 你的 Gemini key | **建议用吊销重建后的新 key** |

可选（多模型动态切换，填了就会自动兜底）：
`OPENAI_API_KEY`、`DEEPSEEK_API_KEY`、`OPENROUTER_API_KEY`，以及 `MODEL_FALLBACK_ORDER`
（默认 `gemini,openai,deepseek,openrouter,custom`）。

> 注意：`Dockerfile` 里已把 `APP_DATA_DIR` 指到容器内目录，不用你配。

### 5. 等待构建 → 打开
- Space 会自动开始 **Building**（看 **Logs** 标签）。构建完状态变 **Running**。
- 页面顶部的 **App** 就是你的公开地址，形如
  `https://你的用户名-autumn-pm-coach.hf.space`
- 打开它：**访客免密直接进工作台**，能看到一份带完整复盘的示例。把这个链接发给面试官即可。

---

## 关于数据持久化
Spaces 免费层的磁盘是**临时的**，重启 / 休眠会重置。但这对 demo 无所谓——
`APP_DEMO_MODE=1` 会在每次启动自动重新灌入示例，所以面试官永远看得到完整效果。
你自己的真实面试记录，仍然用**本地** `python3 -B app/web_app.py`（存本机 `app/data/`）。

## 关于休眠
免费 Space 一段时间无访问会休眠，下次打开需要几十秒冷启动。发链接时可提一句"首次打开稍慢"。

## 安全
- 访客只读，改不了数据、也用不了会消耗配额的 AI 功能（那些需要 `APP_ACCESS_TOKEN`）。
- 口令校验有 per-IP 限流：连续失败 5 次锁定 60 秒。
- Space 设为 Public 只暴露 demo 示例，不含你的真实简历/面试隐私。
