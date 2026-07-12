# 部署到 Hugging Face Spaces

> 重要：Hugging Face 现在**只有 Static Space 免费**，Docker / Gradio Space 需要付费 PRO。
> 所以免费展示走**方案一（静态版）**；需要实时 AI 的完整版走**方案二（Docker，付费）**。

---

## 方案一：免费静态展示版（推荐，0 成本）

用 `static_demo/` 这个纯前端目录，传到 HF **免费 Static Space**。访客打开就能看到完整界面
和一份带原文证据的示例复盘；写操作（保存/AI/上传/搜索）会提示"需在完整版体验"。

### 步骤

1. 登录 [huggingface.co](https://huggingface.co)。
2. [huggingface.co/new-space](https://huggingface.co/new-space)：
   - Space name：如 `autumn-pm-coach`
   - **SDK：选 Static**
   - Visibility：**Public**
   - Create。
3. 上传文件：进 Space → **Files** → **Add file → Upload files**，把 `static_demo/` 里的
   **4 个文件**传到 Space 根目录：
   - `index.html`
   - `app.js`
   - `styles.css`
   - `README.md`（它顶部的 `sdk: static` frontmatter 是 HF 识别所必需）

   > 注意是把 `static_demo/` 里的文件传到 **Space 根目录**，不要把 `static_demo` 文件夹本身传进去。
4. Commit。Space 会自动构建，几秒后状态变 **Running**。
5. 打开顶部的 **App**，得到公开地址 `https://你的用户名-autumn-pm-coach.hf.space`，发给面试官。

静态版不会休眠、秒开、永远免费。缺点：没有实时 AI 生成（但演示看的就是做好的复盘，够用）。

---

## 方案二：Docker 完整版（付费 PRO，带实时 AI）

如果你订阅了 HF PRO（可创建 Docker Space），就能跑带后端和实时 Gemini 的完整版。
本仓库已备好 `Dockerfile` 与根 `README.md` 的 `sdk: docker` frontmatter。
