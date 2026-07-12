# 秋招助手

面向产品经理秋招的面试后复盘与长期训练工具。

- **项目完整介绍**：见 [docs/PROJECT_OVERVIEW.md](./docs/PROJECT_OVERVIEW.md)
- **应用代码与使用说明**：见 [app/README.md](./app/README.md)
- **本地运行**：`python3 -B app/web_app.py`，浏览器打开 http://127.0.0.1:8765
- **部署到 Render**：见 [DEPLOY_RENDER.md](./DEPLOY_RENDER.md)
- **测试**：`python3 -m pytest tests/ -q`

`docs/` 收录了项目背景与面试讲稿，与应用运行无关。

`mini_agent_python/` 是早期的一体化实现（含教学用 mini agent runtime），保留作参考；
当前聚焦版本在 `app/`。
