# 数据备份与迁移

## 数据存在哪

秋招助手的所有记录都保存在**本机的 JSON 文件**里，默认在 `app/data/`：

```text
app/data/interviews.json   # 面试记录 + AI 复盘 + 行动项
app/data/resumes.json      # 简历库各版本
app/data/research.json     # 面经资料库
app/data/memory_overrides.json # 长期记忆的用户治理记录
app/data/memory_override_events.json # 标签修改/忽略/删除审计事件
app/data/tasks.json          # 不含原始输入/结果的后台任务状态元数据
app/data/operations.jsonl    # 字段白名单的本地运维事件（按大小轮换）
app/data/backups/          # 版本化备份（默认保留最近 7 份已校验备份）
```

可以用 `APP_DATA_DIR` 环境变量改到别处（Render 部署时就指向持久盘 `/var/data`）。

## 重要：这些数据不会上传到 GitHub

`data/*.json` 被 `.gitignore` 忽略，仓库里只有一个空的 `data/.gitkeep`。这是刻意的——
简历和面试是隐私，不该进公开仓库。

由此带来两个必须知道的后果：

- **从 GitHub clone/下载到新电脑，只有代码，没有数据**（一条记录都没有）。
- **换电脑、重装系统，数据不会自动跟过去**，必须手动迁移。

## 备份（手动）

数据就是几个 JSON 文件，直接复制即可：

```bash
# 备份到某个目录（按日期命名）
cp app/data/*.json ~/autumn-backup-$(date +%Y%m%d)/
```

也可以在本地完整版调用 `POST /api/backup` 创建带 SHA-256 校验的备份。每次创建后默认只
轮换最近 7 份**已校验**备份；损坏、不可读或旧版未校验备份不会被自动删除。可通过
`APP_BACKUP_KEEP` 调整保留数量（范围 1–100）。`GET /api/backups` 会显示每份备份的完整性状态。

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

恢复失败时，系统会写入 `recovery-required.json`。下一次启动或访问 `/healthz`、`/api/health`
时会返回需要恢复的状态，不会继续把服务伪装成健康。可先通过 `GET /api/recovery` 查看标记
和受影响的文件，再使用已校验备份恢复。恢复成功后，系统会清除本次恢复产生的标记。

长期记忆标签的修改、忽略和删除会写入 `memory_override_events.json`，只保存缺口标识、标签、
动作和时间，不保存转写正文。`GET /api/memory/overrides/audit` 可查看最近事件；备份和导出
也会包含这份事件历史。`POST /api/memory/overrides/audit/{event_id}/revert` 携带
`confirm: true` 可以确定性地恢复某次修改之前的标签状态；撤销本身也会写入事件历史，不能
直接再次撤销。旧备份没有事件字段时按空历史兼容读取。

`tasks.json` 只记录后台任务类型、状态、尝试次数、时间和安全错误，不进入用户数据备份，
也不保存转写、JD、任务输入、模型结果或可恢复 runner。应用重启时未完成任务会标记为
`abandoned`，需要重新提交；这是一层本地可解释性和重试提示，不是可靠消息队列。
排队任务可以通过 `POST /api/tasks/{id}/cancel` 取消；运行中的调用无法被 Python 强制杀死，系统会丢弃晚到结果并记录 `cancelled`。

`operations.jsonl` 只记录任务生命周期和有限的运维字段，按大小轮换，不进入用户数据备份。
它不保存 prompt、模型原始响应、JD、转写、面经正文或原帖 URL；即使有操作日志，也不能替代
正式生产环境的集中式错误追踪和日志访问控制。

## 保留策略

本地完整版提供 `GET /api/data/retention` 预览和 `POST /api/data/retention` 执行接口。
执行时需要传入 `retention_days` 和 `confirm: true`；策略默认不自动运行，避免用户在
不了解影响时丢失原文。它只清理超过期限的面试转写和面经正文，保留结构化复盘、来源
链接、评分元数据和长期统计。建议先创建备份，再执行保留策略。
