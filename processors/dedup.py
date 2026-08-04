import os
import sys            # 加这行
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent)) 
import yaml
from processors.extractor import get_client


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _read_all_entries(kb_path: str) -> list[dict]:
    """读取知识库所有 md 文件，返回 [{path, title, content, category}]"""
    root = Path(kb_path)
    entries = []
    for md_file in root.rglob("*.md"):
        if md_file.name == "index.md":
            continue
        content = md_file.read_text(encoding="utf-8")
        # 提取标题（跳过 YAML 前置信息）
        title = md_file.stem
        in_yaml = False
        for line in content.split("\n"):
            if line.strip() == "---":
                in_yaml = not in_yaml
                continue
            if not in_yaml and line.strip() and not line.startswith("#"):
                title = line.strip().lstrip("#").strip()
                break
            if not in_yaml and line.strip().startswith("#"):
                title = line.strip().lstrip("#").strip()
                break
        entries.append({
            "path": str(md_file),
            "title": title,
            "content": content,
            "category": md_file.parent.name,
        })
    return entries


def _find_similar_pairs(client, model: str, entries: list[dict]) -> list[dict]:
    """
    用 AI 批量判断，找出相似或矛盾的文档对。
    返回: [{"file_a": str, "file_b": str, "relation": "重复/矛盾/无关", "reason": str}]
    """
    if len(entries) < 2:
        return []

    # 构建文档摘要列表给 AI 判断
    summary_lines = []
    for i, e in enumerate(entries):
        # 只取前 100 字作为摘要，减少 token 消耗
        brief = e["content"][:100].replace("\n", " ").strip()
        summary_lines.append(f"[{i}] {e['title']}：{brief}")
    summary_text = "\n".join(summary_lines)

    prompt = f"""以下是知识库中所有文档的摘要，请找出内容相关（相似或矛盾）的文档对。

{summary_text}

请输出 JSON 数组，格式：
[{{"index_a": 0, "index_b": 1, "relation": "重复", "reason": "说明原因"}}]

relation 取值：
- "重复"：两篇讲的是同一件事，内容高度重叠
- "矛盾"：两篇讲的是同一件事，但观点/结论互相矛盾
- "无关"：两篇讲的是不同话题

只输出有关系的文档对（重复或矛盾），无关的不需要输出。
如果没有相关文档对，输出空数组 []。
只输出 JSON，不要其他内容。"""

    message = client.messages.create(
        model=model,
        max_tokens=8192,
        temperature=0.1,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    import re
    raw = message.content[0].text.strip()
    # 去除 markdown 代码块标记
    if raw.startswith("```json"):
        raw = raw[6:]
    elif raw.startswith("```JSON"):
        raw = raw[6:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()
    # 如果开头不是 [，尝试找第一个 [
    if raw and not raw.startswith("["):
        idx = raw.find("[")
        if idx >= 0:
            raw = raw[idx:]
    # 如果结尾不是 ]，尝试找最后一个 ]
    if raw and not raw.endswith("]"):
        idx = raw.rfind("]")
        if idx >= 0:
            raw = raw[:idx+1]
    try:
        pairs = json.loads(raw)
        # 转换为文件路径
        results = []
        for p in pairs:
            if p.get("relation") in ("重复", "矛盾"):
                results.append({
                    "file_a": entries[p["index_a"]]["path"],
                    "file_b": entries[p["index_b"]]["path"],
                    "relation": p["relation"],
                    "reason": p.get("reason", ""),
                })
        return results
    except Exception as e:
        print(f"[去重] AI 输出解析失败: {e}")
        return []


def _merge_duplicates(client, model: str, file_a: str, file_b: str) -> str:
    """合并两篇重复文档，返回合并后的内容"""
    content_a = Path(file_a).read_text(encoding="utf-8")
    content_b = Path(file_b).read_text(encoding="utf-8")

    prompt = f"""以下两篇文档讲的是同一件事，请合并成一篇最完整的版本。

保留所有有价值的信息，去除冗余，结构清晰。

文档A：
{content_a}

文档B：
{content_b}

直接输出合并后的完整文档内容，不要解释。"""

    message = client.messages.create(
        model=model,
        max_tokens=8192,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def _resolve_conflict(client, model: str, file_a: str, file_b: str, reason: str) -> str:
    """处理矛盾文档，生成争议记录"""
    content_a = Path(file_a).read_text(encoding="utf-8")
    content_b = Path(file_b).read_text(encoding="utf-8")

    prompt = f"""以下两篇文档观点矛盾，请综合两篇内容，生成一篇争议记录。

矛盾原因：{reason}

文档A：
{content_a}

文档B：
{content_b}

请输出：
1. 争议主题
2. 各方观点（A 和 B 各自的核心论点）
3. 你的判断（哪方更准确，或各有道理）
4. 建议

直接输出内容，不要解释。"""

    message = client.messages.create(
        model=model,
        max_tokens=8192,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def run_dedup(config: dict, kb_path: str, dry_run: bool = True) -> list[dict]:
    """
    执行去重+冲突合并。
    dry_run=True（默认）：只分析，不修改任何文件
    dry_run=False：真正执行合并和删除（请先备份）
    """
    model = config["api"]["model"]
    client = get_client(config)
    log = []

    mode = "[预览]" if dry_run else "[执行]"
    print(f"{mode} 读取知识库所有文档...")
    entries = _read_all_entries(kb_path)
    print(f"{mode} 共 {len(entries)} 篇文档，开始分析相似度...")

    pairs = _find_similar_pairs(client, model, entries)
    print(f"{mode} 发现 {len(pairs)} 对相关文档")

    for pair in pairs:
        file_a = pair["file_a"]
        file_b = pair["file_b"]
        relation = pair["relation"]

        if relation == "重复":
            print(f"  {mode} [合并] {Path(file_a).name} + {Path(file_b).name}")
            if dry_run:
                log.append({
                    "action": "合并(预览)",
                    "kept": file_a,
                    "removed": file_b,
                    "reason": pair["reason"],
                })
            else:
                merged = _merge_duplicates(client, model, file_a, file_b)
                Path(file_a).write_text(merged, encoding="utf-8")
                Path(file_b).unlink()
                log.append({
                    "action": "合并",
                    "kept": file_a,
                    "removed": file_b,
                    "reason": pair["reason"],
                })

        elif relation == "矛盾":
            print(f"  {mode} [争议] {Path(file_a).name} vs {Path(file_b).name}")
            if dry_run:
                log.append({
                    "action": "争议标记(预览)",
                    "files": [file_a, file_b],
                    "reason": pair["reason"],
                })
            else:
                resolution = _resolve_conflict(client, model, file_a, file_b, pair["reason"])
                from knowledge_base.writer import ensure_dirs
                paths = ensure_dirs(kb_path)
                conflict_path = Path(paths["观点"]) / f"{Path(file_a).stem}-争议.md"
                conflict_path.write_text(resolution, encoding="utf-8")
                log.append({
                    "action": "争议标记",
                    "files": [file_a, file_b],
                    "resolution_file": str(conflict_path),
                    "reason": pair["reason"],
                })

    print(f"{mode} 完成，分析了 {len(log)} 项")
    if dry_run and log:
        print(f"\n{mode} 这是预览，未修改任何文件。")
        print(f"  确认要执行？请调用 run_dedup(config, kb_path, dry_run=False)")
    return log


