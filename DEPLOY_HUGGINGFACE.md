# 部署到 Hugging Face Spaces

> 重要：Hugging Face 现在**只有 Static Space 免费**，Docker / Gradio Space 需要付费 PRO。
> 所以免费展示走**方案一（静态版）**；需要实时 AI 的完整版走**方案二（Docker，付费）**。

---

## 方案一：免费静态展示版（推荐，0 成本）

用 `static_demo/` 这个纯前端目录，传到 HF **免费 Static Space**。访客打开就能看到“诊断总结 → 短期训练 → 长期记忆”的完整路径；按钮返回带 `demo_only` 的预置只读轨迹，不联网、不调用模型、不写入资料库。公开搜索和 Agent 都展示 JD 驱动的查询、公开页读取尝试、初筛和人工确认状态，不连接真实小红书。

### 步骤

1. 登录 [huggingface.co](https://huggingface.co)。
2. [huggingface.co/new-space](https://huggingface.co/new-space)：
   - Space name：如 `autumn-pm-coach`
   - **SDK：选 Static**
   - Visibility：**Public**
   - Create。
3. 上传文件：进 Space → **Files** → **Add file → Upload files**，把 `static_demo/` 里的
   **5 个文件**传到 Space 根目录：
   - `index.html`
   - `app.js`
   - `demo_data.js`
   - `styles.css`
   - `README.md`（它顶部的 `sdk: static` frontmatter 是 HF 识别所必需）

   > 注意是把 `static_demo/` 里的文件传到 **Space 根目录**，不要把 `static_demo` 文件夹本身传进去。
4. Commit。Space 会自动构建，几秒后状态变 **Running**。
5. 打开顶部的 **App**，得到公开地址 `https://你的用户名-autumn-pm-coach.hf.space`，发给面试官。

静态版不会休眠、秒开、永远免费。静态候选明确是合成演示数据，不对应真实小红书原帖；真实后端才会尝试读取限定平台的公开 HTML，遇到脚本壳或访问限制会保留待确认。演示数据还会展示 `scored_by`、outcome 样本边界、短期训练和长期记忆的降级状态。缺点：没有实时 AI 生成（但演示看的就是做好的诊断，够用）。

---

## 方案二：Docker 完整版（付费 PRO，带实时 AI）

如果你订阅了 HF PRO（可创建 Docker Space），就能跑带后端和实时 Gemini 的完整版。
本仓库已备好根目录 `Dockerfile`（`python:3.12-slim`，暴露 7860 端口）。在 HF 建一个
**Docker** Space，把仓库内容传上去；Space 需要 `sdk: docker` 的 README frontmatter，
可在 Space 内单独维护一份带该 frontmatter 的 `README.md`（与本仓库根 README 分开），
避免污染 GitHub 主页展示。记得在 Space 的 Settings → Secrets 里配 `GEMINI_API_KEY`
与 `APP_ACCESS_TOKEN`。
