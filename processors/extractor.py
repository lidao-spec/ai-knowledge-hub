import os
import anthropic


def get_client(config: dict) -> anthropic.Anthropic:
    """从配置和环境变量创建 Claude API 客户端"""
    api_key = os.environ.get(config["api"]["key_env"], "")
    base_url = os.environ.get(config["api"]["base_url_env"], None)

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    return anthropic.Anthropic(**kwargs)


def extract_knowledge(client: anthropic.Anthropic, model: str, question: str, answer: str) -> str:
    """
    调用 Claude API，从一段问答中提取核心知识点，生成结构化 md 片段。

    返回: 一段包含 YAML 前置信息的 md 文本
    """
    prompt = f"""请从以下 Claude Code 对话中提取核心知识点，生成一段结构化的 Markdown 内容。

要求：
1. 用简洁的语言总结核心知识点
2. 如果涉及代码，保留关键代码片段
3. 标注知识类型（技术/工具/经验/其他）
4. 用中文输出

对话内容：
用户问题：{question}

AI回答：{answer}

请输出：
- 知识标题（一行）
- 知识类型（技术/工具/经验/其他）
- 核心要点（3-8 条，简洁）
- 关键代码片段（如有）
- 注意事项（如有）

直接输出内容，不要加任何解释。"""

    message = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text


def extract_from_note(client: anthropic.Anthropic, model: str, filename: str, content: str) -> str:
    """
    调用 Claude API，从 Obsidian 笔记中提取/整理知识点。

    返回: 一段结构化 md 文本
    """
    # 截断过长内容，避免超 token
    if len(content) > 4000:
        content = content[:4000] + "\n...(内容已截断)"

    prompt = f"""请整理以下 Obsidian 笔记，提取核心知识点，生成结构化的 Markdown 内容。

要求：
1. 用简洁的语言重新组织内容
2. 标注知识类型（技术/工具/经验/其他）
3. 补充笔记中隐含但未明确说明的关联知识
4. 用中文输出

笔记标题：{filename}

笔记内容：
{content}

请输出：
- 知识标题（一行）
- 知识类型（技术/工具/经验/其他）
- 核心要点（3-8 条，简洁）
- 关键代码片段（如有）
- 与其他知识的关联（如有）

直接输出内容，不要加任何解释。"""

    message = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text
