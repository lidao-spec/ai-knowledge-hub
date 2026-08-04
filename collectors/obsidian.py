from pathlib import Path


def collect_obsidian_notes(vault_dir: str, recent_hours: int = 0) -> list[dict]:
    """
    扫描 Obsidian vault 目录，读取所有 .md 文件。

    返回: [{"path": str, "filename": str, "content": str, "modified": float}]
    """
    vault_path = Path(vault_dir)
    results = []

    if not vault_path.exists():
        print(f"[Obsidian] 路径不存在: {vault_dir}")
        return results

    for md_file in vault_path.rglob("*.md"):
        # 跳过 Obsidian 配置目录
        if ".obsidian" in md_file.parts:
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
            stat = md_file.stat()
            results.append({
                "path": str(md_file),
                "filename": md_file.stem,
                "content": content,
                "modified": stat.st_mtime,
            })
        except Exception as e:
            print(f"[Obsidian] 读取失败 {md_file}: {e}")

    return results
