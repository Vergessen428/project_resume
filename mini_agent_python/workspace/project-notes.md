# Project Notes

目标：从零复刻一个最小 agent runtime，帮助非工程背景的 PM 理解 agent 的系统逻辑。

范围：第一版只做 CLI、mock 模型、文件工具、权限检查、agent loop 和日志。

关键取舍：先不用 LangChain，也不接复杂消息平台。先把工具调用和权限边界跑通，再接真实模型。

难点：模型输出不稳定、上下文可能混入恶意指令、工具权限容易过宽、长任务需要 step limit。

验证方式：读取单文件、多文件生成 summary、拒绝 SSH key 读取、处理 prompt injection 文件、限制最大执行步数。

