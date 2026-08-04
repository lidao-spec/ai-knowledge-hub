from pathlib import Path


def update_index(kb_path: str) -> str:
    """
    扫描知识库目录，生成/更新 index.md 全局索引。
    返回 index.md 的路径。
    """
    root = Path(kb_path)
    categories = ["技术", "工具", "经验", "其他"]

    lines = ["# 知识库索引\n", f"*最后更新: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"]

    total = 0
    for cat in categories:
        cat_dir = root / cat
        if not cat_dir.exists():
            continue
        files = sorted(cat_dir.glob("*.md"))
        if not files:
            continue

        lines.append(f"\n## {cat}（{len(files)} 篇）\n")
        for f in files:
            # 读取文件第一行作为标题
            try:
                first_lines = f.read_text(encoding="utf-8").splitlines()
                title = f.stem
                for line in first_lines:
                    line = line.strip().lstrip("#").strip()
                    if line and not line.startswith("---") and not line.startswith("created:") and not line.startswith("category:"):
                        title = line
                        break
            except Exception:
                title = f.stem
            lines.append(f"- [{title}]({cat}/{f.name})")
            total += 1

    lines.insert(1, f"*共收录 {total} 个知识点*\n")

    index_path = root / "index.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return str(index_path)
