# AI Knowledge Hub - 个人 AI 知识库助手

## 项目简介

自动从 Claude Code 对话记录、Obsidian 笔记中提取知识点，用 AI 整理成结构化知识库。

## 功能

- 从 Claude Code `.jsonl` 对话文件中提取"用户问题 + AI 最终回答"
- 从 Obsidian vault 读取笔记内容
- 调用 Claude API 生成结构化知识摘要
- 输出为带 YAML 前置信息的 Markdown 文件
- 自动更新全局索引 `index.md`

## 安装

```bash
# 使用 conda 环境
conda activate langchain2
pip install anthropic pyyaml requests
```

## 配置

编辑 `config.yaml`，设置：
- Claude API 密钥（通过环境变量 `ANTHROPIC_API_KEY`）
- Claude Code 项目目录路径
- Obsidian vault 路径
- 知识库输出目录

## 使用

```bash
python main.py
```

## 项目结构

```
ai-knowledge-hub/
├── config.yaml           # 配置文件
├── main.py               # 入口
├── collectors/           # 数据采集
│   ├── claude_code.py    # Claude Code 对话采集
│   └── obsidian.py       # Obsidian 笔记采集
├── processors/           # 数据处理
│   └── extractor.py      # 知识提取（调 AI）
├── knowledge_base/       # 知识库管理
│   ├── writer.py         # 写入 md 文件
│   └── indexer.py        # 更新索引
└── knowledge-base/       # 知识库实际存储（git 跟踪）
    ├── 技术/
    ├── 工具/
    ├── 观点/
    └── index.md
```

## License
MIT
