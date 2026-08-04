import os
import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from collectors.claude_code import collect_claude_code_sessions
from collectors.obsidian import collect_obsidian_notes
from processors.extractor import get_client, extract_knowledge, extract_from_note
from processors.dedup import run_dedup
from knowledge_base.writer import write_entry
from knowledge_base.indexer import update_index


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    config = load_config()
    kb_path = config["knowledge_base"]["path"]
    api_config = config["api"]
    model = api_config["model"]
    recent_hours = config.get("collector", {}).get("recent_hours", 0)

    print("=" * 50)
    print("AI Knowledge Hub - 知识库更新开始")
    print("=" * 50)

    client = get_client(config)
    print(f"[OK] API 客户端已创建，模型: {model}")

    claude_dir = config["sources"]["claude_code"]
    print(f"\n[采集] 扫描 Claude Code 项目目录: {claude_dir}")
    sessions = collect_claude_code_sessions(claude_dir, recent_hours)
    print(f"[OK] 找到 {len(sessions)} 条有效对话")

    obsidian_dir = config["sources"].get("obsidian", "")
    notes = []
    if obsidian_dir:
        print(f"\n[采集] 扫描 Obsidian vault: {obsidian_dir}")
        notes = collect_obsidian_notes(obsidian_dir, recent_hours)
        print(f"[OK] 找到 {len(notes)} 篇笔记")

    written_files = []
    print(f"\n[处理] 开始提取 Claude Code 对话中的知识点...")
    for i, session in enumerate(sessions, 1):
        print(f"  [{i}/{len(sessions)}] 处理会话: {session['session_id'][:8]}...")
        try:
            knowledge = extract_knowledge(client, model, session["question"], session["answer"])
            filepath = write_entry(kb_path, knowledge)
            written_files.append(filepath)
        except Exception as e:
            print(f"         [FAIL] {e}")

    print(f"\n[处理] 开始整理 Obsidian 笔记...")
    for i, note in enumerate(notes, 1):
        print(f"  [{i}/{len(notes)}] 处理笔记: {note['filename']}")
        try:
            knowledge = extract_from_note(client, model, note["filename"], note["content"])
            filepath = write_entry(kb_path, knowledge)
            written_files.append(filepath)
        except Exception as e:
            print(f"         [FAIL] {e}")

    # 7. 去重 + 冲突合并
    print(f"\n[去重] 扫描知识库，查找重复和矛盾内容...")
    dedup_log = run_dedup(config, kb_path)
    if dedup_log:
        print(f"[去重] 处理了 {len(dedup_log)} 项")
        for entry in dedup_log:
            if entry["action"] == "合并":
                print(f"  [合并] 保留: {Path(entry['kept']).name}，删除: {Path(entry['removed']).name}")
            elif entry["action"] == "争议标记":
                files_str = ", ".join(Path(f).name for f in entry["files"])
                print(f"  [争议] {files_str}")
    else:
        print("[去重] 未发现重复或矛盾内容")

    # 8. 更新索引
    print(f"\n[索引] 更新全局索引...")
    index_path = update_index(kb_path)
    print(f"[OK] 索引已更新: {index_path}")

    # 9. 汇总
    print("\n" + "=" * 50)
    print(f"完成！本次新增 {len(written_files)} 个知识点，去重处理 {len(dedup_log)} 项")
    print(f"知识库路径: {Path(kb_path).resolve()}")
    print("=" * 50)


if __name__ == "__main__":
    main()