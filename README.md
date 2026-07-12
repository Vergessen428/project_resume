---
title: 秋招助手
emoji: 🍂
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# 秋招助手

面向产品经理秋招的面试后复盘与长期训练工具。

- **项目完整介绍**：见 [docs/PROJECT_OVERVIEW.md](./docs/PROJECT_OVERVIEW.md)
- **应用代码与使用说明**：见 [app/README.md](./app/README.md)
- **本地运行**：`python3 -B app/web_app.py`，浏览器打开 http://127.0.0.1:8765
- **部署到 Hugging Face Spaces**：见 [DEPLOY_HUGGINGFACE.md](./DEPLOY_HUGGINGFACE.md)
- **部署到 Render**：见 [DEPLOY_RENDER.md](./DEPLOY_RENDER.md)
- **数据备份与迁移**：见 [docs/DATA_BACKUP.md](./docs/DATA_BACKUP.md)
- **架构演进说明**：见 [docs/ARCHITECTURE_EVOLUTION.md](./docs/ARCHITECTURE_EVOLUTION.md)
- **面试讲稿**：见 [docs/INTERVIEW_TALKING_POINTS.md](./docs/INTERVIEW_TALKING_POINTS.md)
- **测试**：`python3 -m pytest tests/ -q`

> 顶部的 YAML frontmatter 供 Hugging Face Spaces 识别（Docker SDK，端口 7860），
> 不影响本地运行和 GitHub 展示。

`docs/` 收录了项目背景与面试讲稿，与应用运行无关。

`mini_agent_python/` 是早期的一体化实现（含教学用 mini agent runtime），保留作参考；
当前聚焦版本在 `app/`。
