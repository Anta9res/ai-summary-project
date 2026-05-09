# 项目结构说明

## 📁 目录结构

```
Fall-Network/
├── core/                       # 核心功能模块
│   ├── __init__.py
│   ├── pdf_parser.py          # PDF解析器（206行）
│   ├── note_generator.py      # 笔记生成器（331行）
│   ├── post_processor.py      # 后处理器（294行）
│   ├── integrator.py          # 笔记整合器（332行）
│   └── pipeline.py            # Pipeline编排器（358行）
│
├── utils/                      # 工具模块
│   ├── __init__.py
│   ├── file_utils.py          # 文件操作工具（60行）
│   ├── config_loader.py       # 配置加载器（57行）
│   ├── statistics.py          # 统计面板（123行）
│   └── logger.py              # 日志系统（149行）
│
├── config/                     # 配置模块
│   ├── __init__.py
│   ├── prompts.py             # 提示词管理（270行）
│   └── config_manager.py      # 配置管理器（178行）
│
├── tests/                      # 测试模块
│   ├── test_integration.py    # 集成测试（280行）
│   └── test_performance.py    # 性能测试（180行）
│
├── scripts_backup/             # 旧代码备份
│   ├── analyze_structure.py
│   ├── batch_pdf_processor.py
│   ├── fix_notes_format.py
│   ├── generate_notes.py
│   ├── merge_notes.py
│   └── test_qwen_client.py
│
├── output/                     # 输出目录
│   ├── raw_texts/             # PDF提取文本
│   ├── notes/                 # 生成的笔记
│   ├── 完整复习笔记.md
│   └── 笔记索引.md
│
├── logs/                       # 日志目录
│   └── Pipeline_*.log
│
├── 课件/                       # 输入PDF目录
│   ├── 数据通信与网络-第1讲.pdf
│   └── ...
│
├── cli.py                      # 命令行入口（335行）
├── qwen_client.py              # API客户端（保留原有）
├── config.yaml                 # 配置文件
├── config.yaml.example         # 配置示例
├── requirements.txt            # 依赖列表
├── README.md                   # 项目文档
├── QUICKSTART.md               # 快速开始
├── CHANGELOG.md                # 更新日志
└── PROJECT_STRUCTURE.md        # 本文件
```

## 📝 文件说明

### 核心模块 (core/)

#### pdf_parser.py
- **功能**：PDF内容提取
- **核心类**：`PDFParser`
- **主要方法**：
  - `extract_single()`: 提取单个PDF
  - `process_all()`: 批量处理
  - `find_pdf_files()`: 查找PDF文件
  - `extract_lecture_number()`: 提取讲次编号

#### note_generator.py
- **功能**：AI笔记生成
- **核心类**：`NoteGenerator`
- **主要方法**：
  - `generate_single_note()`: 生成单个笔记
  - `process_batch()`: 批量生成
  - `get_prompt()`: 获取提示词
  - `check_if_processed()`: 断点续传检测

#### post_processor.py
- **功能**：格式修复和质量检测
- **核心类**：`PostProcessor`
- **主要方法**：
  - `process()`: 处理单个文件
  - `fix_markdown_wrapper()`: 移除代码块包裹
  - `quality_check()`: 6种质量检测
  - `generate_quality_report()`: 生成质量报告

#### integrator.py
- **功能**：笔记整合
- **核心类**：`NoteIntegrator`
- **主要方法**：
  - `integrate_all()`: 完整整合流程
  - `merge_all_notes()`: 合并笔记
  - `generate_index()`: 生成索引
  - `generate_readme()`: 生成README

#### pipeline.py
- **功能**：流程编排
- **核心类**：`Pipeline`
- **主要方法**：
  - `run_full_pipeline()`: 完整流程
  - `run_stage()`: 单阶段执行
  - `_run_parse_stage()`: PDF解析阶段
  - `_run_generate_stage()`: 笔记生成阶段
  - `_run_integrate_stage()`: 笔记整合阶段

### 工具模块 (utils/)

#### file_utils.py
- **功能**：文件操作工具
- **主要函数**：
  - `ensure_dir()`: 确保目录存在
  - `find_files()`: 查找文件
  - `read_file()`: 读取文件
  - `write_file()`: 写入文件

#### config_loader.py
- **功能**：配置加载（旧版，被config_manager替代）
- **核心类**：`ConfigLoader`

#### statistics.py
- **功能**：统计信息收集和展示
- **核心类**：`StatisticsPanel`
- **主要方法**：
  - `start_stage()`: 开始阶段计时
  - `end_stage()`: 结束阶段计时
  - `generate_report()`: 生成统计报告

#### logger.py
- **功能**：日志系统
- **核心类**：`Logger`
- **主要方法**：
  - `info()`, `warning()`, `error()`: 日志记录
  - `log_stage_start()`: 记录阶段开始
  - `log_file_process()`: 记录文件处理

### 配置模块 (config/)

#### prompts.py
- **功能**：提示词管理
- **核心类**：`PromptManager`
- **支持版本**：
  - v2.0: 重要性分级版本
  - v3.0: 应试化版本（推荐）

#### config_manager.py
- **功能**：配置管理
- **核心类**：`ConfigManager`
- **主要方法**：
  - `get()`: 获取配置项
  - `set()`: 设置配置项
  - `validate()`: 验证配置
  - `save()`: 保存配置

### 测试模块 (tests/)

#### test_integration.py
- **功能**：集成测试
- **测试内容**：
  1. 完整Pipeline流程
  2. 断点续传功能
  3. 单阶段执行
  4. 配置加载
  5. 输出质量验证

#### test_performance.py
- **功能**：性能测试和分析
- **测试内容**：
  - 性能瓶颈分析
  - 处理时间估算
  - 优化建议

### 命令行工具

#### cli.py
- **功能**：命令行入口
- **支持参数**：15个命令行参数
- **核心功能**：
  - 参数解析
  - 配置加载
  - Pipeline调用
  - 错误处理

### 原有文件

#### qwen_client.py
- **功能**：通义千问API客户端
- **状态**：保留原有实现，被各模块调用

## 📊 代码统计

### 新增代码

| 模块 | 文件数 | 总行数 | 平均行数 |
|------|--------|--------|---------|
| core/ | 5 | ~1521 | ~304 |
| utils/ | 4 | ~389 | ~97 |
| config/ | 2 | ~448 | ~224 |
| tests/ | 2 | ~460 | ~230 |
| cli.py | 1 | ~335 | ~335 |
| **总计** | **14** | **~3153** | **~225** |

### 旧代码（已备份）

| 文件 | 行数 | 功能 |
|------|------|------|
| analyze_structure.py | ~200 | 结构分析 |
| batch_pdf_processor.py | ~150 | 批量PDF处理 |
| fix_notes_format.py | ~164 | 格式修复 |
| generate_notes.py | ~333 | 笔记生成 |
| merge_notes.py | ~545 | 笔记合并 |
| test_qwen_client.py | ~100 | 客户端测试 |
| **总计** | **~1492** | - |

## 🔄 代码复用

### 从旧代码提取的逻辑

1. **PDF解析** (batch_pdf_processor.py → pdf_parser.py)
   - 提取讲次编号逻辑
   - PDF查找和过滤逻辑
   - 批量处理流程

2. **笔记生成** (generate_notes.py → note_generator.py)
   - 提示词定义
   - API调用逻辑
   - 笔记头部生成

3. **格式修复** (fix_notes_format.py → post_processor.py)
   - 代码块包裹移除
   - 正则表达式模式
   - 文件遍历逻辑

4. **笔记整合** (merge_notes.py → integrator.py)
   - 讲次提取
   - 元数据处理
   - 索引生成

5. **结构分析** (analyze_structure.py → 废弃)
   - 部分逻辑整合到integrator.py

## 🎯 设计原则

1. **模块化**：清晰的职责划分，高内聚低耦合
2. **可配置**：通过YAML配置文件灵活控制
3. **可扩展**：预留接口，便于添加新功能
4. **可测试**：提供集成测试和性能测试
5. **用户友好**：CLI工具+完整文档

## 📚 依赖关系

```
cli.py
  ├── config_manager.py
  ├── logger.py
  └── pipeline.py
        ├── pdf_parser.py
        │     └── qwen_client.py
        ├── note_generator.py
        │     ├── qwen_client.py
        │     ├── prompts.py
        │     └── post_processor.py
        ├── post_processor.py
        ├── integrator.py
        │     └── post_processor.py
        └── statistics.py
```

## 🔮 扩展点

### 未来可添加的模块

1. **extensions/knowledge_graph/** - 知识图谱
2. **extensions/mindmap/** - 思维导图
3. **extensions/rag_qa/** - RAG问答系统

### 预留的接口

1. `Pipeline.run_stage()` - 支持新阶段
2. `PromptManager.get_prompt()` - 支持新版本提示词
3. `PostProcessor.quality_check()` - 支持新检测规则
4. `ConfigManager` - 支持新配置项

## 📖 命名规范

- **类名**: 大驼峰（如`Pipeline`, `NoteGenerator`）
- **函数名**: 小写下划线（如`run_full_pipeline`, `process_batch`）
- **常量**: 大写下划线（如`DEFAULT_CONFIG`）
- **私有方法**: 前缀下划线（如`_run_parse_stage`）

## 🛠️ 开发建议

1. **添加新功能**：优先考虑模块化，避免影响现有功能
2. **修改提示词**：在`config/prompts.py`中添加新版本
3. **扩展检测规则**：在`post_processor.py`的`quality_check`方法中添加
4. **添加新阶段**：在`pipeline.py`中添加`_run_xxx_stage`方法

## 📄 许可证

MIT License

---

**最后更新**: 2025-11-17  
**版本**: 1.0.0
