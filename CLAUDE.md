# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

课程笔记生成 Pipeline：将 PPT/PDF 课件通过通义千问 qwen-long 模型转换为结构化、应试导向的复习笔记。附带知识图谱（LightRAG + ChromaDB）和思维导图功能。

## Essential Commands

### PPT → PDF 转换（前置步骤）
```bash
D:\anaconda3\python.exe scripts/ppt2pdf.py "C:\Users\LENOVO\Desktop\Fall-Network\<课程名>"
```
依赖本地 Microsoft PowerPoint（win32com），仅 Windows 可用。

### 主 Pipeline
```bash
# 完整流程（默认 kimi-k2.6 / opencode.ai）
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --input <PDF目录> --output <输出目录> --prompt-version v3.0

# 使用 DashScope / qwen-long
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --input <PDF目录> --output <输出目录> --model qwen-long --endpoint ""

# 单文件模式：大PDF按章节拆分（需 PaddleOCR；输入仅含 1 个 PDF 且 > 5MB 自动启用）
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --single-file --input <含单个PDF的目录> --output <输出目录>

# 仅 PDF 解析
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --input <PDF目录> --stage parse

# 仅笔记生成
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --input <PDF目录> --stage generate

# 仅笔记整合
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --input <PDF目录> --stage integrate --output <输出目录>
```
`PYTHONIOENCODING=utf-8` 是 Windows 下必须的，否则 emoji 字符会导致 `UnicodeEncodeError`（GBK 编码不兼容）。
始终使用 `D:\anaconda3\python.exe`，不要用系统 `python`。

### 知识图谱
```bash
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --build-kg --subject <学科名> --input <notes目录>
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --qa "问题" --subject <学科名>
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --qa-interactive --subject <学科名>
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --generate-mindmap --subject <学科名> --mindmap-format markmap
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --kb-info --subject <学科名>
```

### 测试
```bash
D:\anaconda3\python.exe -m pytest tests/ -v
```

## Architecture

```
cli.py                     # 唯一入口：参数解析 → ConfigManager → Pipeline / KG 命令
  │                          run_kg_commands 拆分为 _cmd_build_kg / _cmd_update_kg /
  │                          _cmd_qa / _cmd_qa_interactive / _cmd_generate_mindmap / _cmd_kb_info
  ├── config/config_manager.py   # YAML 配置加载、.env 加载、验证
  │     └── config/prompts.py    # v3.0 提示词模板 (system + user 元组)
  ├── utils/logger.py            # 日志（文件 + 控制台）
  ├── utils/statistics.py        # 阶段计时 + 统计报告
  └── core/pipeline.py           # 流程编排（拆分为 4 个阶段方法 + run_stage 路由）
        ├── core/pdf_parser.py        # unstructured + pdfminer 提取 PDF 文本
        ├── core/note_generator.py    # 调用 qwen_client → Qwen API 生成笔记
        │     ├── qwen_client.py      # OpenAI-compatible client (DashScope)，所有函数接受 api_key 参数
        │     └── core/post_processor.py  # 格式修复 + 6 种质量检测规则 + 跨运行重置
        ├── core/integrator.py        # 合并笔记 → 完整复习笔记 + 索引 + README
        ├── core/paddleocr_adapter.py  # PaddleOCR 文档解析（单文件模式）
        └── core/chapter_splitter.py   # 按章切割（prunedResult + markdown 互补检测 + 裸章标题识别）

### Pipeline 流程

**常规模式** (`--stage all`)：
1. **parse** — `pdf_parser.py` 提取 PDF 文本 → `raw_texts/`，含 500MB 文件大小限制
2. **generate** — `note_generator.py` 调用 Qwen API → `notes/`，生成后自动跑 `post_processor.py` 质量检测
3. **quality_check** — 自动：结构完整性、最小长度（<500字符）、标题结构、代码块残留、重复内容、必要标注。每次运行前自动重置 issues（防止跨运行累积）
4. **integrate** — `integrator.py` 合并所有笔记 → `完整复习笔记.md` + `笔记索引.md`

**单文件模式** (`--single-file --stage all`)：
1. **PaddleOCR预处理** — `paddleocr_adapter.py` 调用 PaddleOCR API 解析 PDF → `chapter_splitter.py` 按章切割 → `raw_texts/`（含按章拆分的 `*_提取文本.md` 文件）
2. **generate** — `note_generator.py` 从拆分文本逐章生成笔记 → `notes/`（`text_list_override` 驱动）
3. **integrate** — 合并 + 质量检测 → `完整复习笔记.md` + `笔记索引.md`
   - `--single-file`：单文件模式开关
   - `--split-strategy paddleocr`：章节检测策略（仅 paddleocr，llm 待实现）
   - PaddleOCR 缓存：`{pdf_name}_paddleocr_full.json`（写入 PDF 所在目录，删除可强制重新解析）

### 扩展模块
- `extensions/knowledge_graph/` — LightRAG 知识图谱（`lightrag_adapter.py`）+ ChromaDB 向量检索（`retrieval_tool.py`）+ Function Calling 问答（`qa_system.py`）+ KB 管理（`kb_manager.py`）
- `extensions/mindmap/` — Mermaid/Markmap/HTML 思维导图生成（`visualizer.py`, `mindmap_generator.py`）
- `scripts/ppt2pdf.py` — 独立工具，Windows COM 调用 PowerPoint 批量转换
- `scripts/deploy_production.py` — 生产环境部署脚本

### 多端点支持
- 默认模型 `kimi-k2.6`（opencode.ai），使用 `chat_direct` 直接文本注入
- DashScope（qwen-long）：使用 `fileid://` 文件上传机制 — `--model qwen-long --endpoint ""`
- 其他 OpenAI 兼容端点：`--model <model> --endpoint <url>`
- 智能回退：未检测到 `OPENCODE_API_KEY` 时自动回退到 DashScope (qwen-long)
- 非 DashScope 端点默认 `max_tokens=8192`（推理模型需更多 token 空间）
- 通过 `HTTPS_PROXY` 环境变量支持代理连接

## Key Conventions

- skip_existing 默认开启（断点续传），检查 output 目录是否已有对应文件
- 提示词版本 v3.0 是应试化版本（题型标注、答题要点、对比表格），已拆分为 system prompt + user prompt
- API 密钥：优先 `OPENCODE_API_KEY`（默认 kimi-k2.6），回退 `DASHSCOPE_API_KEY`（qwen-long），优先级: env > .env > config.yaml
- `qwen_client.py` 所有函数接受 `api_key` 参数，不持有模块级密钥常量
- `chat_with_file` 中 `fileid://` 作为 system message 唯一内容，system_prompt 移入 user message（避免 DashScope 解析失败）
- 密钥注入链路: `ConfigManager.api_key → Pipeline → PDFParser / NoteGenerator` 以及 `ConfigManager.api_key → run_kg_commands → QASystem`
- `extract_lecture_number()` 返回 `float`，支持 "第3-4讲" → 3.4，未知讲次返回 999.0
- `integrator.py` 中 `extract_lecture_number = staticmethod(PDFParser.extract_lecture_number)` 引用统一实现
- 当前 API 限制 max_workers=1，不支持并行处理
- `PromptManager.get_prompt()` 返回 `(system_prompt, user_prompt)` 元组，不是单字符串
- 已移除 v2.0 提示词；未知版本会警告并回退到 v3.0
- 模型参数 (temperature/max_tokens/top_p) 从 config.yaml → ConfigManager → Pipeline → NoteGenerator → qwen_client 链路传递
- 遗留：`use_custom` 自定义提示路径功能未实现，当前仅支持内置 v3.0
- 使用 `pyproject.toml` 管理依赖，`pip install -e .` 后可移除 `sys.path.insert()` 依赖
- `config_manager.py` 使用 `copy.deepcopy()` 防止 DEFAULT_CONFIG 被意外修改
- `_merge_batch_results` 使用 `_get_layouts()` 统一读写 `result.result.layoutParsingResults`（两层嵌套结构），修复分批合并丢失数据
- 单文件自动分流：`cli.py` 检测到单 PDF > 5MB 时自动设置 `args.single_file = True`
