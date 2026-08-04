import os
import sys
import yaml
from pathlib import Path

# 把项目根目录加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from collectors.claude_code import collect_claude_code_sessions
from collectors.obsidian import collect_obsidian_notes
from processors.extractor import get_client, extract_knowledge, extract_from_note
from knowledge_base.writer import write_entry
from knowledge_base.indexer import update_index


def load_config(config_path: str = "config.yaml") -> dict:
    """加载配置文件"""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    # 1. 加载配置
    config = load_config()
    kb_path = config["knowledge_base"]["path"]
    api_config = config["api"]
    model = api_config["model"]
    recent_hours = config.get("collector", {}).get("recent_hours", 0)

    print("=" * 50)
    print("AI Knowledge Hub - 知识库更新开始")
    print("=" * 50)

    # 2. 创建 API 客户端
    client = get_client(config)
    print(f"[OK] API 客户端已创建，模型: {model}")

    # 3. 采集 Claude Code 对话
    claude_dir = config["sources"]["claude_code"]
    print(f"\n[采集] 扫描 Claude Code 项目目录: {claude_dir}")
    sessions = collect_claude_code_sessions(claude_dir, recent_hours)
    print(f"[OK] 找到 {len(sessions)} 条有效对话")

    # 4. 采集 Obsidian 笔记
    obsidian_dir = config["sources"].get("obsidian", "")
    notes = []
    if obsidian_dir:
        print(f"\n[采集] 扫描 Obsidian vault: {obsidian_dir}")
        notes = collect_obsidian_notes(obsidian_dir, recent_hours)
        print(f"[OK] 找到 {len(notes)} 篇笔记")

    # 5. 处理 Claude Code 对话 → 提取知识 → 写入
    print(f"\n[处理] 开始提取 Claude Code 对话中的知识点...")
    written_files = []
    for i, session in enumerate(sessions, 1):
        print(f"  [{i}/{len(sessions)}] 处理会话: {session['session_id'][:8]}... 问题: {session['question'][:30]}...")
        try:
            knowledge = extract_knowledge(client, model, session["question"], session["answer"])
            filepath = write_entry(kb_path, knowledge)
            written_files.append(filepath)
            print(f"         → 写入: {Path(filepath).name}")
        except Exception as e:
            print(f"         ✗ 失败: {e}")

    # 6. 处理 Obsidian 笔记 → 提取知识 → 写入
    print(f"\n[处理] 开始整理 Obsidian 笔记...")
    for i, note in enumerate(notes, 1):
        print(f"  [{i}/{len(notes)}] 处理笔记: {note['filename']}")
        try:
            knowledge = extract_from_note(client, model, note["filename"], note["content"])
            filepath = write_entry(kb_path, knowledge)
            written_files.append(filepath)
            print(f"         → 写入: {Path(filepath).name}")
        except Exception as e:
            print(f"         ✗ 失败: {e}")

    # 7. 更新索引
    print(f"\n[索引] 更新全局索引...")
    index_path = update_index(kb_path)
    print(f"[OK] 索引已更新: {index_path}")

    # 8. 汇总
    print("\n" + "=" * 50)
    print(f"完成！本次新增 {len(written_files)} 个知识点")
    print(f"知识库路径: {Path(kb_path).resolve()}")
    print("=" * 50)


if __name__ == "__main__":
    main()
