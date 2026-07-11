# Mini Agent Runtime Notes

Agent runtime is the execution system that lets an LLM use tools in a controlled loop.

The core chain is user input, session state, context building, model reasoning, tool call, policy check, tool execution, tool result, final answer, and logs.

Prompt engineering is a soft instruction layer. Runtime policy is a hard control layer.

The first version should stay small: CLI, mock model, file tools, workspace-only policy, and JSONL logs.

