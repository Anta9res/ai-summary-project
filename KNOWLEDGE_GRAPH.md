# 知识图谱使用指南

## 📖 目录

- [简介](#简介)
- [快速开始](#快速开始)
- [功能详解](#功能详解)
- [CLI命令](#cli命令)
- [配置说明](#配置说明)
- [最佳实践](#最佳实践)
- [故障排查](#故障排查)

---

## 简介

Fall-Network项目的知识图谱功能基于**LightRAG**构建，提供以下核心能力：

- **知识图谱构建**：从课程笔记自动提取实体和关系
- **智能问答**：基于知识库的问答系统（支持Function Calling）
- **思维导图生成**：自动生成多格式思维导图
- **多学科管理**：支持管理多个学科的独立知识库

**技术栈**：
- **LightRAG**：知识图谱核心引擎
- **ChromaDB**：向量数据库
- **NetworkX**：图计算库
- **通义千问**：LLM和Embedding模型

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 构建知识图谱

从已生成的笔记构建知识图谱：

```bash
D:\anaconda3\python.exe cli.py --build-kg --subject Fall-Network --input FN_output/notes/
```

**预期输出**：
```
📊 构建知识图谱: Fall-Network
找到 19 个笔记文件
处理 (1/19): 第1讲_笔记.md
处理 (2/19): 第2讲_笔记.md
...
✅ 知识图谱构建完成!
  实体数: 450
  关系数: 380
  文档数: 19
```

### 3. 知识库问答

单次问答：

```bash
D:\anaconda3\python.exe cli.py --qa "什么是TCP三次握手？" --subject Fall-Network
```

交互式问答：

```bash
D:\anaconda3\python.exe cli.py --qa-interactive --subject Fall-Network
```

### 4. 生成思维导图

```bash
D:\anaconda3\python.exe cli.py --generate-mindmap --subject Fall-Network --mindmap-format markmap --output FN_output/
```

---

## 功能详解

### 知识图谱构建

**功能**：从Markdown笔记中自动提取实体（概念、协议、技术等）和关系，构建知识图谱。

**实现原理**：
1. 使用LightRAG的LLM提取实体和关系
2. 使用text-embedding-v3生成向量
3. 存储到ChromaDB向量数据库
4. 构建NetworkX图结构

**输出**：
- `knowledge_bases/{subject}/` - 知识库存储目录
  - `vdb_entities.json` - 实体向量数据库
  - `vdb_relationships.json` - 关系向量数据库
  - `graph_chunk_entity_relation.graphml` - 图谱结构

**示例**：

```python
from extensions.knowledge_graph.kb_manager import KnowledgeBaseManager

kb_manager = KnowledgeBaseManager()

# 创建知识库
kb = kb_manager.create_knowledge_base(
    subject_name="Fall-Network",
    description="计算机网络知识库"
)

# 添加笔记
notes = ["第1讲笔记内容...", "第2讲笔记内容..."]
kb_manager.add_notes_to_kb("Fall-Network", notes)

# 查看信息
info = kb_manager.get_kb_info("Fall-Network")
print(info)
```

### 增量更新

**功能**：向已存在的知识库中添加新笔记，无需重新构建。

**命令**：

```bash
D:\anaconda3\python.exe cli.py --update-kg --subject Fall-Network --new-notes FN_output/notes/第20讲_笔记.md
```

**注意事项**：
- 新添加的笔记会与现有知识图谱合并
- 重复实体会自动去重
- 关系会自动合并

### 知识库问答

**功能**：基于知识图谱回答问题，支持两种模式：

1. **Function Calling模式**：模型自动调用检索工具
2. **直接检索模式**：直接检索+模型回答

**检索模式**：
- `naive`：向量检索（快速）
- `local`：图谱检索（精确）
- `global`：高层概览
- `hybrid`：混合检索（推荐）

**示例**：

```python
from extensions.knowledge_graph.qa_system import QASystem

qa = QASystem("Fall-Network")

# Function Calling模式
answer, sources, score = qa.ask(
    "什么是TCP三次握手？",
    use_tool_calling=True
)

print(f"答案: {answer}")
print(f"来源: {sources}")
print(f"质量分数: {score}")
```

### 思维导图生成

**功能**：从知识图谱生成思维导图，支持多种格式。

**支持格式**：
- **Mermaid**：可嵌入Markdown
- **Markmap**：层级Markdown（推荐）
- **HTML**：交互式网页

**命令**：

```bash
# Markmap格式（可在VSCode中预览）
D:\anaconda3\python.exe cli.py --generate-mindmap --subject Fall-Network --mindmap-format markmap

# 交互式HTML
D:\anaconda3\python.exe cli.py --generate-mindmap --subject Fall-Network --mindmap-format html
```

**示例**：

```python
from extensions.mindmap.mindmap_generator import MindmapGenerator
from extensions.mindmap.visualizer import MindmapVisualizer

generator = MindmapGenerator()

# 生成Markmap格式
content = generator.generate_from_graph(
    graph,
    format="markmap",
    title="Fall-Network Knowledge Map"
)

# 保存
generator.save_mindmap(content, "output/mindmap.md", format="markmap")

# 生成交互式HTML
visualizer = MindmapVisualizer()
visualizer.render_interactive(graph, "output/mindmap.html")
```

---

## CLI命令

### 构建知识图谱

```bash
D:\anaconda3\python.exe cli.py --build-kg --subject <学科名> --input <笔记目录>
```

**参数**：
- `--build-kg`：启用构建模式
- `--subject`：学科名称（必需）
- `--input`：笔记目录路径

### 更新知识图谱

```bash
D:\anaconda3\python.exe cli.py --update-kg --subject <学科名> --new-notes <笔记文件>
```

**参数**：
- `--update-kg`：启用更新模式
- `--subject`：学科名称（必需）
- `--new-notes`：新笔记文件路径

### 单次问答

```bash
D:\anaconda3\python.exe cli.py --qa "问题内容" --subject <学科名>
```

**参数**：
- `--qa`：问题字符串
- `--subject`：学科名称（必需）

### 交互式问答

```bash
D:\anaconda3\python.exe cli.py --qa-interactive --subject <学科名>
```

**退出方式**：输入 `quit`, `exit`, 或 `q`

### 生成思维导图

```bash
D:\anaconda3\python.exe cli.py --generate-mindmap --subject <学科名> --mindmap-format <格式> --output <输出目录>
```

**参数**：
- `--generate-mindmap`：启用生成模式
- `--subject`：学科名称（必需）
- `--mindmap-format`：格式（mermaid/markmap/html，默认markmap）
- `--output`：输出目录（默认output）

### 查看知识库信息

```bash
D:\anaconda3\python.exe cli.py --kb-info --subject <学科名>
```

**输出**：
- 学科名称
- 描述
- 实体数量
- 关系数量
- 文档数量
- 创建/更新时间

---

## 配置说明

在`config.yaml`中配置知识图谱功能：

```yaml
# 知识图谱配置
knowledge_graph:
  enabled: true                   # 功能开关
  storage_dir: "knowledge_bases"  # 存储目录
  vector_db: "chromadb"           # 向量数据库
  graph_db: "networkx"            # 图数据库
  
  embedding_model:
    provider: "dashscope"
    model: "text-embedding-v3"
    dimension: 1024
  
  extraction:
    entity_extraction: true
    relation_extraction: true
    max_entities_per_doc: 100
  
  retrieval:
    default_mode: "hybrid"        # 默认检索模式
    top_k: 5
    rerank: true

# 思维导图配置
mindmap:
  enabled: true
  format: "markmap"
  max_depth: 3
  core_entities_limit: 30
```

**关键参数**：
- `default_mode`：影响检索准确率和速度
- `top_k`：返回的结果数量
- `max_depth`：思维导图最大深度
- `core_entities_limit`：核心实体数量

---

## 最佳实践

### 1. 知识图谱构建

**推荐流程**：
1. 先生成高质量的笔记（v3.0提示词）
2. 一次性构建完整知识图谱
3. 后续使用增量更新

**性能优化**：
- 单次构建所有笔记比多次增量更快
- 使用`hybrid`检索模式获得最佳准确率
- 定期备份`knowledge_bases/`目录

### 2. 问答系统

**提问技巧**：
- 使用清晰、具体的问题
- 避免过于宽泛或模糊的问题
- 可以要求列举、对比、解释

**示例**：
- ✅ 好："TCP和UDP的主要区别是什么？"
- ✅ 好："OSI模型的七层结构是什么？"
- ❌ 差："网络是什么？"

### 3. 思维导图

**格式选择**：
- **日常使用**：Markmap（可在VSCode中实时预览）
- **演示分享**：HTML（交互式，适合浏览器）
- **文档嵌入**：Mermaid（直接嵌入Markdown）

**层级控制**：
- `max_depth=2`：概览
- `max_depth=3`：推荐（平衡细节和可读性）
- `max_depth=4+`：详细（可能过于复杂）

### 4. 多学科管理

**命名规范**：
- 使用清晰的学科名称（如：Fall-Network, Data-Structure）
- 避免特殊字符和空格
- 使用连字符分隔

**独立性**：
- 每个学科的知识库完全独立
- 可以使用不同的配置
- 互不干扰

---

## 故障排查

### 1. 知识图谱构建失败

**症状**：`'function' object has no attribute 'func'`

**原因**：LightRAG库的事件循环问题

**解决**：
- 这是已知的LightRAG问题，不影响整体功能
- 知识图谱仍然成功构建
- 可以正常使用检索和问答功能

### 2. 问答没有返回结果

**可能原因**：
1. 知识库为空或未正确构建
2. 问题与知识库内容不相关
3. 检索模式设置不当

**解决**：
```bash
# 检查知识库信息
D:\anaconda3\python.exe cli.py --kb-info --subject Fall-Network

# 尝试不同的检索模式
# 在qa_system.py中修改search_mode参数
```

### 3. 思维导图生成为空

**可能原因**：
- 知识图谱节点数过少
- `core_entities_limit`设置过小

**解决**：
- 增加`core_entities_limit`
- 降低`max_depth`
- 检查知识库是否正确构建

### 4. API调用失败

**症状**：`API key not found` 或 `Connection error`

**解决**：
1. 检查`config.yaml`中的API密钥
2. 确认网络连接正常
3. 检查API额度是否充足

### 5. 依赖安装问题

**症状**：`ModuleNotFoundError`

**解决**：
```bash
# 重新安装所有依赖
pip install -r requirements.txt

# 单独安装缺失的包
pip install lightrag-hku chromadb networkx pyvis matplotlib
```

### 6. 内存占用过高

**症状**：程序运行缓慢或崩溃

**解决**：
- 减少`max_entities_per_doc`
- 分批构建知识图谱
- 使用更小的`top_k`值

---

## 高级用法

### Python API

```python
# 完整的知识图谱工作流
from extensions.knowledge_graph.kb_manager import KnowledgeBaseManager
from extensions.knowledge_graph.qa_system import QASystem
from extensions.mindmap.mindmap_generator import MindmapGenerator

# 1. 创建和构建
kb_manager = KnowledgeBaseManager()
kb = kb_manager.create_knowledge_base("MySubject", "描述")
kb_manager.add_notes_to_kb("MySubject", notes)

# 2. 问答
qa = QASystem("MySubject")
answer, sources, score = qa.ask("问题")

# 3. 批量问答
questions = ["问题1", "问题2", "问题3"]
results = qa.batch_ask(questions)

# 4. 导出问答对
qa.export_qa_pairs("output/qa_pairs.json")

# 5. 生成思维导图
generator = MindmapGenerator()
content = generator.generate_subject_overview(graph, "MySubject")
```

### 自定义配置

```python
from extensions.knowledge_graph.lightrag_adapter import LightRAGAdapter

# 自定义embedding函数
def custom_embedding(texts):
    # 你的embedding逻辑
    return vectors

# 创建适配器
adapter = LightRAGAdapter(
    working_dir="custom_kb",
    embedding_func=custom_embedding
)
```

---

## 性能指标

基于Fall-Network课程（19讲笔记）的测试数据：

| 操作 | 时间 | 资源消耗 |
|------|------|----------|
| 知识图谱构建（19讲） | ~3-5分钟 | API调用: ~100次 |
| 单次检索 | <2秒 | 内存: ~200MB |
| 问答（Function Calling） | ~10秒 | API调用: 2-3次 |
| 思维导图生成 | <1秒 | 内存: ~50MB |

---

## 更新日志

### v1.0.0 (2025-11-17)
- ✅ 基础知识图谱构建
- ✅ LightRAG集成
- ✅ Function Calling问答
- ✅ 多格式思维导图
- ✅ CLI支持

### 计划功能
- [ ] 知识图谱可视化界面
- [ ] 实体关系编辑
- [ ] 知识图谱导出（GraphML、JSON）
- [ ] 多语言支持

---

## 参考资料

- [LightRAG文档](https://github.com/HKUDS/LightRAG)
- [通义千问API](https://help.aliyun.com/zh/dashscope/)
- [NetworkX文档](https://networkx.org/)
- [ChromaDB文档](https://docs.trychroma.com/)

---

**问题反馈**：如遇到问题，请检查日志文件`logs/`目录。
