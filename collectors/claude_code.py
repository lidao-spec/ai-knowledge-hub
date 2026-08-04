import json
import os
from pathlib import Path


def collect_claude_code_sessions(projects_dir: str, recent_hours: int = 0) -> list[dict]:
    """
    扫描 Claude Code 的 .jsonl 会话文件，
    提取每条会话的「用户第一条问题 + AI 最终回答」。

    返回: [{"session_id": str, "question": str, "answer": str, "timestamp": str}]
    """
    projects_path = Path(projects_dir)
    results = []

    for jsonl_file in projects_path.glob("**/*.jsonl"):
        # 只处理直接会话文件（跳过子目录里的元数据文件）
        if jsonl_file.parent.name != projects_path.name and jsonl_file.parent.parent != projects_path:
            pass  # 继续处理，Claude Code 的 sessions 就在项目文件夹下

        try:
            lines = jsonl_file.read_text(encoding="utf-8").strip().splitlines()
        except Exception:
            continue

        question = None
        last_answer = None
        timestamp = None

        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            rtype = record.get("type", "")

            if rtype == "user":
                # 用户消息结构: {"type":"user", "message":{"role":"user","content":"..."}, "timestamp":"..."}
                msg = record.get("message", {})
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    # 过滤系统命令消息（以 < 开头的标签消息）
                    stripped = content.strip()
                    if stripped.startswith("<") and not stripped.startswith("<问题"):
                        continue
                    # 只取第一条有效用户消息作为问题
                    if question is None:
                        question = stripped
                        timestamp = record.get("timestamp", "")

            elif rtype == "assistant":
                # AI 回答结构: {"type":"assistant", "message":{"content":[{"type":"text","text":"..."}]}}
                msg = record.get("message", {})
                content = msg.get("content", [])
                if isinstance(content, list):
                    # 提取所有 text 类型的内容拼接
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                    answer_text = "\n".join(text_parts).strip()
                    if answer_text:
                        last_answer = answer_text

        # 收集到有意义的问答对
        if question and last_answer:
            results.append({
                "session_id": jsonl_file.stem,
                "question": question,
                "answer": last_answer,
                "timestamp": timestamp or "",
                "source_file": str(jsonl_file),
            })

    return results
