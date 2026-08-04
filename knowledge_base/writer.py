from pathlib import Path


def ensure_dirs(kb_path: str) -> dict:
    """确保知识库目录存在，返回各分类目录路径"""
    root = Path(kb_path)
    categories = ["技术", "工具", "经验", "其他"]
    paths = {}
    for cat in categories:
        p = root / cat
        p.mkdir(parents=True, exist_ok=True)
        paths[cat] = str(p)
    return paths


def _classify_category(text: str) -> str:
    """根据 AI 输出判断分类，匹配'知识类型：xxx'行"""
    for line in text.split("\n"):
        line = line.strip()
        if "知识类型" in line:
            if "技术" in line:
                return "技术"
            elif "工具" in line:
                return "工具"
            elif "经验" in line:
                return "经验"
    return "其他"


def _make_filename(text: str) -> str:
    """从 AI 输出中提取标题作为文件名（跳过'知识类型'行）"""
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip().strip("#").strip()
        if not line:
            continue
        if "知识类型" in line or "知识标题" in line:
            continue
        # 取第一个有意义的行作为标题
        safe = "".join(c for c in line if c.isalnum() or c in " _-（）()：:").strip()
        if safe:
            return safe[:60]
    import time
    return f"知识点-{int(time.time())}"


def write_entry(kb_path: str, content: str) -> str:
    """
    将 AI 生成的知识内容写入知识库 md 文件。
    返回写入的文件路径。
    """
    paths = ensure_dirs(kb_path)
    category = _classify_category(content)
    filename = _make_filename(content)
    filepath = Path(paths[category]) / f"{filename}.md"

    # 如果文件名重复，加时间戳
    if filepath.exists():
        import time
        filepath = filepath.with_name(f"{filename}-{int(time.time())}.md")

    # 构建完整 md 文件（加上 YAML 前置信息）
    from datetime import datetime
    header = f"""---
created: {datetime.now().strftime('%Y-%m-%d %H:%M')}
category: {category}
---

"""
    full_content = header + content
    filepath.write_text(full_content, encoding="utf-8")
    return str(filepath)
