# Fall-Network 课程笔记生成Pipeline

## 📚 项目简介

基于通义千问qwen-long模型的智能课程笔记生成系统，支持从PDF课件自动生成结构化、应试导向的复习笔记。

## ✨ 核心特性

### 笔记生成功能
- ✅ **模块化架构**: 清晰的模块划分，易于维护和扩展
- ✅ **应试导向**: v3.0提示词专为考试服务，包含题型标注和答题要点
- ✅ **多端点支持**: DashScope（qwen-long）、opencode.ai（kimi-k2.6）等兼容端点
- ✅ **单文件模式**: 大PDF自动按章拆分，逐章生成笔记（PaddleOCR驱动）
- ✅ **断点续传**: 智能跳过已处理文件，支持中断后继续执行
- ✅ **质量检测**: 6种自动质量检测规则，生成质量报告
- ✅ **笔记整合**: 自动生成完整笔记、索引和README

### 知识图谱功能（NEW! 🔥）
- ✅ **知识图谱构建**: 基于LightRAG自动提取实体和关系
- ✅ **智能问答**: Function Calling驱动的知识库问答系统
- ✅ **思维导图生成**: 支持Mermaid/Markmap/HTML多种格式
- ✅ **多学科管理**: 支持创建和管理多个学科知识库
- ✅ **向量检索**: ChromaDB支持的语义检索
- ✅ **命令行工具**: 友好的CLI界面，支持灵活配置

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置API密钥

方式1：环境变量
```bash
# 设置对应端点的 API 密钥
export OPENCODE_API_KEY="your_api_key_here"   # opencode.ai 等兼容端点
export DASHSCOPE_API_KEY="your_api_key_here"   # DashScope (qwen-long)
```

方式2：配置文件
编辑`config.yaml`，填入API密钥

### 基础使用

```bash
# 完整流程（使用默认模型）
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --input 课件/ --output output/

# 切换为其他模型（任意 OpenAI 兼容端点）
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --input 课件/ --output output/ \
  --model <模型名> --endpoint <API端点URL>

# 单文件模式：大PDF按章拆分生成（输入仅含1个PDF且>5MB时自动启用）
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --single-file --input 民法/ --output output/

# 仅PDF解析
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --input 课件/ --stage parse

# 仅笔记生成
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --input 课件/ --stage generate

# 仅笔记整合
PYTHONIOENCODING=utf-8 D:\anaconda3\python.exe cli.py --input 课件/ --stage integrate --output output/
```

### 知识图谱使用

```bash
# 1. 构建知识图谱
D:\anaconda3\python.exe cli.py --build-kg --subject Fall-Network --input FN_output/notes/

# 2. 知识库问答
D:\anaconda3\python.exe cli.py --qa "什么是TCP三次握手？" --subject Fall-Network

# 3. 交互式问答
D:\anaconda3\python.exe cli.py --qa-interactive --subject Fall-Network

# 4. 生成思维导图
D:\anaconda3\python.exe cli.py --generate-mindmap --subject Fall-Network --mindmap-format markmap

# 5. 查看知识库信息
D:\anaconda3\python.exe cli.py --kb-info --subject Fall-Network
```

**详细文档**: 查看 [docs/knowledge-graph.md](./docs/knowledge-graph.md)

## 📖 使用指南

### CLI参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--input`, `-i` | 输入目录（PDF文件） | 必需 |
| `--output`, `-o` | 输出目录 | `output` |
| `--stage` | 执行阶段：`all`/`parse`/`generate`/`integrate` | `all` |
| `--single-file` | 单文件模式：大PDF按章拆分（单PDF>5MB自动启用） | `False` |
| `--split-strategy` | 章节检测策略（当前仅 `paddleocr`） | `paddleocr` |
| `--model` | 模型名称（支持任意 OpenAI 兼容模型） | `kimi-k2.6` |
| `--endpoint` | API端点 URL（OpenAI 兼容） | `https://opencode.ai/zen/go/v1` |
| `--prompt-version` | 提示词版本 | `v3.0` |
| `--skip-existing` | 断点续传 | `True` |
| `--no-skip` | 强制重新生成 | - |
| `--config` | 配置文件 | `config.yaml` |
| `--verbose`, `-v` | 详细输出 | `True` |
| `--quiet`, `-q` | 静默模式 | - |
| `--log-dir` | 日志目录 | `logs` |
| `--validate-config` | 验证配置 | - |

### Pipeline阶段

1. **PDF解析** (`parse`): 提取PDF文本内容（常规模式：unstructured + pdfminer）
2. **PaddleOCR预处理** (单文件模式): PaddleOCR文档解析 + 按章切割（`--single-file`）
3. **笔记生成** (`generate`): 使用AI生成结构化笔记（支持多端点）
4. **质量检测** (自动): 检测并修复格式问题
5. **笔记整合** (`integrate`): 合并生成完整文档

### 提示词版本

- **v3.0**（默认）：应试化版本，包含题型标注、答题要点、对比表格

## 📁 项目结构

```
AI-summary-project/
├── core/                    # 核心功能模块
│   ├── pdf_parser.py       # PDF解析器（unstructured + pdfminer）
│   ├── note_generator.py   # 笔记生成器（多端点支持）
│   ├── post_processor.py   # 后处理器（格式修复+质量检测）
│   ├── integrator.py       # 笔记整合器
│   ├── pipeline.py         # Pipeline编排器（常规+单文件模式）
│   ├── paddleocr_adapter.py # PaddleOCR适配器（单文件模式）
│   └── chapter_splitter.py  # 章节切分器（prunedResult+正则）
├── config/                  # 配置模块
│   ├── prompts.py          # 提示词管理（仅v3.0）
│   └── config_manager.py   # 配置管理器（多端点密钥）
├── utils/                   # 工具模块
│   ├── logger.py           # 日志系统
│   └── statistics.py       # 统计面板
├── extensions/              # 扩展模块
│   ├── knowledge_graph/    # LightRAG 知识图谱
│   └── mindmap/            # 思维导图生成
├── scripts/                 # 独立工具脚本
│   ├── ppt2pdf.py          # PPT→PDF 转换器（Windows）
│   └── deploy_production.py # 生产部署脚本
├── tests/                   # 测试模块
├── docs/                    # 文档
│   ├── CHANGELOG.md        # 变更日志
│   ├── knowledge-graph.md  # 知识图谱使用指南
│   └── single-file-pipeline-plan.md  # 单文件模式设计文档
├── cli.py                   # 命令行入口
├── config.yaml.example      # 配置文件示例
├── qwen_client.py           # API客户端（DashScope+兼容端点）
└── README.md                # 本文档
```

## 🔧 配置说明

### config.yaml配置文件

```yaml
model:
  name: qwen-long
  api_key: ""           # 留空，从环境变量读取
  base_url: ""

prompt:
  version: v3.0         # 提示词版本

pipeline:
  skip_existing: true   # 断点续传
  verbose: true         # 详细输出
  parallel: false       # 并行处理（未来支持）

output:
  base_dir: output
  raw_texts_dir: raw_texts
  notes_dir: notes
  backup_enabled: true
```

## 📊 输出说明

### 目录结构

```
output/
├── raw_texts/              # PDF提取的原始文本
│   ├── 第1讲_提取文本.md
│   ├── 第2讲_提取文本.md
│   └── ...（单文件模式：按章拆分的多个文件）
├── notes/                  # 生成的笔记
│   ├── 第1讲_笔记.md
│   ├── 第2讲_笔记.md
│   ├── ...
│   └── README.md           # 笔记使用说明
├── 完整复习笔记.md          # 所有笔记合并
└── 笔记索引.md              # 快速导航索引
```

单文件模式额外输出：`<pdf名>_paddleocr_full.json`（PaddleOCR缓存，位于PDF所在目录）。

### 笔记特性（v3.0）

- ✅ 题型标注（📝名词解释/📊计算题/✅选择题等）
- ✅ 答题要点说明
- ✅ 对比辨析表格
- ✅ 考试重点标注
- ✅ 易混淆点总结
- ✅ 计算示例

## 🔍 质量检测

自动检测6种常见问题：
1. 结构完整性（缺少核心知识点标记）
2. 最小长度要求（<500字符）
3. 标题结构检测
4. 代码块残留问题
5. 重复内容检测
6. 必要标注检测（💡🔗等）

## 🐛 故障排查

### API调用失败

- 检查API密钥是否正确配置
- 检查网络连接
- 查看日志文件：`logs/Pipeline_*.log`

### 文件生成失败

- 确保PDF文件可正常访问
- 检查输出目录权限
- 使用`--verbose`查看详细错误信息

### 断点续传不工作

- 使用`--no-skip`强制重新生成
- 检查输出目录中的文件是否完整

## 📝 开发说明

### 添加新模块

1. 在`core/`或`utils/`目录创建新模块
2. 在Pipeline中集成调用
3. 更新配置文件和CLI参数（如需）

### 自定义提示词

1. 编辑`config/prompts.py`
2. 添加新版本的提示词方法
3. 在`PromptManager`中注册新版本

### 扩展质量检测规则

编辑`core/post_processor.py`的`quality_check`方法

## 📊 处理时间估算

| PDF数量 | 预估时间 |
|---------|---------|
| 1-5个   | 2-5分钟 |
| 10个    | 5-10分钟 |
| 19个    | 10-15分钟 |

*实际时间取决于PDF大小和网络状况*

## 💡 最佳实践

1. **首次使用**：先用少量PDF测试（3-5个）
2. **断点续传**：保持默认开启，避免重复工作
3. **配置备份**：备份你的 `config.yaml`
4. **日志查看**：遇到问题先查看 `logs/` 目录
5. **质量验证**：生成后检查自动生成的质量报告

## 📄 许可证

MIT License

## 👥 贡献

欢迎提交Issue和Pull Request！

## 📧 联系方式

- 项目地址：[GitHub仓库链接]
- 问题反馈：[Issue页面]

---

**版本**: v1.2.0  
**最后更新**: 2026-05-12
