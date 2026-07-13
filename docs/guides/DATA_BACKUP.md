# 数据备份与迁移

## 数据存在哪

秋招助手的所有记录都保存在**本机的 JSON 文件**里，默认在 `app/data/`：

```text
app/data/interviews.json   # 面试记录 + AI 复盘 + 行动项
app/data/resumes.json      # 简历库各版本
app/data/research.json     # 面经资料库
```

可以用 `APP_DATA_DIR` 环境变量改到别处（Render 部署时就指向持久盘 `/var/data`）。

## 重要：这些数据不会上传到 GitHub

`data/*.json` 被 `.gitignore` 忽略，仓库里只有一个空的 `data/.gitkeep`。这是刻意的——
简历和面试是隐私，不该进公开仓库。

由此带来两个必须知道的后果：

- **从 GitHub clone/下载到新电脑，只有代码，没有数据**（一条记录都没有）。
- **换电脑、重装系统，数据不会自动跟过去**，必须手动迁移。

## 备份（手动）

数据就是三个 JSON 文件，直接复制即可：

```bash
# 备份到某个目录（按日期命名）
cp app/data/*.json ~/autumn-backup-$(date +%Y%m%d)/
```

建议定期把 `app/data/` 整个拷到网盘或另一块硬盘。因为是纯 JSON，任何文本编辑器都能打开查看。

## 迁移到新电脑

1. 在新电脑 clone 代码：`git clone https://github.com/Vergessen428/project_resume.git`
2. 配置 `.env`（填 `GEMINI_API_KEY`）。
3. 把旧电脑的 `app/data/*.json` 拷到新电脑的 `app/data/` 下。
4. `python3 -B app/web_app.py`，数据就回来了。

## Render 部署时的数据

Render 上的数据存在它挂载的**持久盘**（`/var/data`，由 `render.yaml` 配置），和你本地
的 `app/data/` 是**两份独立数据**，不会互通：

- 本地记录不会自动出现在线上，反之亦然。
- 持久盘在重新部署后会保留，但**换套餐、删服务时可能丢失**，重要数据仍要另外备份。
- 想从线上取回数据，可以用 Render 的 Shell 把 `/var/data/*.json` 下载下来。

## 写入安全性

每次写入都是「先写临时文件再原子替换」（`os.replace`），并有线程锁保护，所以正常使用
不会因为并发或中途崩溃损坏 JSON。但这**不能替代备份**——误删文件、磁盘损坏仍会丢数据。
