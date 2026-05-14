# 单文件 PDF 章节拆分 Pipeline 方案

> 需求：大型单 PDF 文件（如民法.pdf，26MB，含全部章节）在现有 Pipeline 中被当作"一讲"处理，输出笔记粒度过粗。需为单文件类型提供按章拆分的专用通道。
>
> 最后更新：2026-05-09（grill-me 终版）

## 方案概述

**OCR 引擎**：PaddleOCR PP-StructureV3 完全替代 ocrmypdf（Tesseract）。实测对比 Tesseract 存在严重的"第"→"用/项/图/境"误识，PaddleOCR 中文识别零错误，且输出结构化 layout blocks（block_label 直接区分 paragraph_title / text / image）。

**拆分策略**：PaddleOCR 自带 layout 分析输出 `prunedResult.parsing_res_list`，其中 `block_label == "paragraph_title"` 的块可直接判定标题类型。优先用此结构化数据筛选章标题 → 在合并后的 markdown 全文中定位 → 切割。正则匹配作为 fallback，LLM 作为最后兜底。

**架构**：单文件模式合并 PaddleOCR 提取与章节拆分为一个预处理阶段（不走现有 parse 阶段）。

```
常规 Pipeline:  parse → generate → integrate
单文件 Pipeline: [PaddleOCR + 按章切割] → generate → integrate
                       ↑ 合并为一个阶段
```

## 关键决策记录

| # | 决策点 | 结论 | 状态 |
|---|--------|------|------|
| 1 | OCR 引擎 | PaddleOCR PP-StructureV3 完全替代 ocrmypdf | 已定 |
| 2 | 拆分粒度 | 按"章"级别拆分 | 已定 |
| 3 | 架构 | 合并阶段：PaddleOCR 提取 + 按章切割 = 一步完成 | 已定 |
| 4 | 章检测策略 | 三路互补：prunedResult block_label + markdown 正则 + 节复位推断 | 已定 |
| 5 | 章标题定位方式 | prunedResult 筛选章标题 → 在合并后 markdown 全文中定位 → 切割 | 已定 |
| 6 | 100 页 API 限制 | 分批调用（每批 ≤100页）+ `{pdf_name}_paddleocr_full.md` 缓存 | 已定 |
| 7 | generate 阶段适配 | `_run_generate_stage` 增加 `text_list_override` 参数，从拆分文本文件驱动 | 已定 |
| 8 | 零检测失败 | 报错退出，不静默回退（`--split-strategy llm` 当前不可用） | 已定 |
| 9 | 章节检测优化 | prunedResult + markdown 互补合并（不再互斥），新增 BARE_CHAPTER_PATTERN 匹配无 ## 前缀的裸章标题，prunedResult 空白归一化 + 合并智能回退 | 已实现 |
| 10 | 零检测降级到 LLM | 标记为遗留问题，当前不实现 | 遗留 |
| 11 | 无章有节时的降级 | 检测到 ≥1 节但 0 章时，降级按节拆分并警告用户 | 已定 |
| 12 | 缓存位置 | PDF 所在目录（`input_dir`），与 PDF 关联 | 已定 |
| 13 | API 配置来源 | `PaddleOCRAdapter.__init__` 从环境变量读取，不通过构造参数传入 | 已定 |
| 14 | 文本 PDF 处理 | 单文件模式统一走 PaddleOCR（需要 layout blocks 做章节检测）；常规模式保留 unstructured | 已定 |

### 文本 PDF vs 扫描 PDF 处理路径

单文件模式统一走 PaddleOCR，无论 PDF 是否有文本层。原因：需要 `prunedResult` 的 `block_label` 做章节检测，`unstructured` 无法提供结构化标题信息。

常规多文件 Pipeline 保持现有路径（`unstructured` + `pdfminer` 提取文本）。

| 模式 | 文本 PDF | 扫描 PDF |
|------|----------|----------|
| 常规（`--stage all`） | unstructured 直接提取 | --ocr 已移除（PaddleOCR 替代后暂无替代 OCR） |
| 单文件（`--single-file`） | PaddleOCR | PaddleOCR |

> 注意：常规模式对扫描 PDF 的 OCR 通道在删除 `ocr_processor.py` 后暂时空缺。若后续需要，可在 `paddleocr_adapter.py` 中增加纯文本提取方法（跳过章节检测），供常规模式使用。当前常规模式主要面向 PPT 导出的文本 PDF，暂不处理常规扫描 PDF。

## 模块设计

### 1. 新增 `core/paddleocr_adapter.py`

封装 PaddleOCR skill 的 `scripts/vl_caller.py` 调用。不依赖 skill 内部模块，通过 subprocess 调用脚本。

```python
class PaddleOCRAdapter:
    """
    PaddleOCR 文档解析适配器
    
    封装 vl_caller.py 调用，处理：
      - 分批调用（每批 ≤100 页）
      - 缓存管理（`{pdf_name}_paddleocr_full.json` — 完整 JSON，含 prunedResult）
      - 结果合并（多批 markdown 拼接）
    """
    
    # PaddleOCR skill 脚本路径
    SKILL_DIR = os.path.join(os.path.expanduser("~"), ".claude", "skills", "paddleocr-doc-parsing")
    
    def __init__(self):
        """
        从环境变量读取 API 配置。
        settings.local.json 的 env 节由宿主注入为环境变量。
        """
        self.api_url = os.environ.get("PADDLEOCR_DOC_PARSING_API_URL", "")
        self.access_token = os.environ.get("PADDLEOCR_ACCESS_TOKEN", "")
        ...
    
    def parse_pdf(self, pdf_path: str) -> ParseResult:
        """
        解析 PDF，返回结构化结果。
        
        1. 检查缓存 {pdf_dir}/{pdf_name}_paddleocr_full.json
        2. 缓存命中 → 反序列化还原 ParseResult（含 prunedResult）
        3. 缓存未命中：
           a. 若 PDF ≤100 页：一次调用 vl_caller.py
           b. 若 PDF >100 页：用 split_pdf.py 分批，多次调用，合并结果
           c. 写入完整 JSON 缓存到 PDF 所在目录
        """
        ...
```

**API 配置读取**：`PaddleOCRAdapter.__init__` 从环境变量读取（宿主将 `settings.local.json` 的 `env` 节注入为环境变量）。不通过构造参数传入。

**分批调用逻辑**：

```python
def _parse_large_pdf(self, pdf_path: str, total_pages: int, cache_dir: str) -> str:
    """分批调用 PaddleOCR，合并 markdown 输出"""
    all_markdown = []
    batch_size = 100
    
    for start_page in range(1, total_pages + 1, batch_size):
        end_page = min(start_page + batch_size - 1, total_pages)
        # 用 split_pdf.py 切分
        batch_pdf = os.path.join(cache_dir, f"batch_{start_page}_{end_page}.pdf")
        self._split_pdf(pdf_path, batch_pdf, start_page, end_page)
        # 调用 vl_caller.py
        result = self._call_vl_caller(batch_pdf)
        all_markdown.append(result.markdown_text)
        # 清理临时 PDF
        os.remove(batch_pdf)
    
    return "\n\n".join(all_markdown)
```

### 2. 新增 `core/chapter_splitter.py`

从 PaddleOCR 的 markdown 输出中按章切割。

```python
class ChapterSplitter:
    """
    章节文本拆分
    
    输入：PaddleOCR 输出的合并 markdown + ParseResult
    输出：N 个按章拆分的文本文件
    
    检测策略（三路互补，非互斥）：
      1. prunedResult block_label == "paragraph_title" + 内容匹配 第X章
         - 空白归一化（\n → 空格），确保与 markdown 可匹配
      2. markdown 正则匹配：
         - MARKDOWN_HEADING_PATTERN: /^#{1,3}\s+第[一二三四五六七八九十百\d]+[章节]/
         - BARE_CHAPTER_PATTERN: /^第[一二三四五六七八九十百\d]+章\b/（无 ## 前缀的裸章标题）
      3. 节复位推断：当节编号从 N 重置为 1 且附近无已知章时，推断新章边界
         - PROXIMITY_THRESHOLD = 300 字符（近邻排除）
         - 推断标题从第一节标题推导（例："第一节 民事法律关系概述" → "第X章 民事法律关系"）
      3. _merge_chapter_lists(): prunedResult 优先，regex 补漏；pruned 条目无法定位时回退到 regex 条目
      4. LLM 识别章节标题（兜底，当前标记为遗留问题）
    """
    
    def detect_chapters(self, markdown_text: str, parse_result: dict) -> List[Chapter]:
        """
        策略 1 + 策略 2 同时运行，结果互补合并。
        
        _extract_titles_from_pruned():
        遍历 parse_result.result.layoutParsingResults[n].prunedResult.parsing_res_list
        → 筛选 block_label == "paragraph_title"
        → 空白归一化（re.sub(r'\s+', ' ', content)）
        
        _detect_from_regex():
        → MARKDOWN_HEADING_PATTERN: /^#{1,3}\s+第...章/ 的行
        → BARE_CHAPTER_PATTERN: /^第...章\b/ 的行（无 ## 前缀）
        
        _merge_chapter_lists():
        → 按章编号（_chapter_number_key）去重
        → prunedResult 优先（page 信息更准）
        → regex 补漏（prunedResult 遗漏的章节）
        → pruned 条目在 markdown 中无法定位时，回退到 regex 同名条目
        """
        ...
    
    def split_by_chapters(
        self, 
        markdown_text: str, 
        chapters: List[Chapter],
        pdf_name: str, 
        output_dir: str
    ) -> List[str]:
        """
        按检测到的章边界切割 markdown 文本。
        
        - 第一个章边界之前的内容 → 00_前言_提取文本.md
        - 每个章 → {idx:02d}_{章标题}_提取文本.md（safe_filename 处理）
        - 过滤内容 <200 字符的片段
        """
        ...
    
    def run(self, pdf_path: str, parse_result: ParseResult, output_dir: str) -> SplitResult:
        """
        完整流程：检测 → 切割 → 写入文件。
        返回 SplitResult(success, chapter_count, output_files)。
        """
        ...
```

**章标题去重逻辑**：同一标题（如"第一章 民法基本原理"）在相邻页中可能重复出现（页眉/页脚）。去重规则：相同标题文本取第一次出现的位置。

**零检测处理**：章和节都检测不到时，报错退出并提示用户尝试 `--split-strategy llm`（LLM 策略暂未实现，标记为遗留问题）。

### 3. 修改 `core/pipeline.py`

#### 3.1 新增 `_run_paddleocr_stage()`

```python
def _run_paddleocr_stage(
    self,
    pdf_path: str,
    raw_texts_dir: str,
    verbose: bool = True
) -> Dict:
    """
    单文件预处理阶段：PaddleOCR 提取 + 按章切割
    
    1. PaddleOCRAdapter.parse_pdf() → 合并 markdown + ParseResult（缓存到 PDF 所在目录）
    2. ChapterSplitter.run() → 检测章节 + 拆分写入 raw_texts_dir
    3. 返回章节文件列表供 generate 阶段使用
    
    缓存文件写入 PDF 所在目录（与 PDF 关联），而非 raw_texts_dir。
    """
    self.stats.start_stage("PaddleOCR预处理")
    
    adapter = PaddleOCRAdapter()
    parse_result = adapter.parse_pdf(pdf_path)
    
    if not parse_result.success:
        return {'success': False, 'error': parse_result.error}
    
    splitter = ChapterSplitter()
    split_result = splitter.run(pdf_path, parse_result, raw_texts_dir)
    
    if not split_result.success:
        return {'success': False, 'error': '未检测到章节结构，尝试 --split-strategy llm'}
    
    self.stats.end_stage("PaddleOCR预处理")
    self.completed_stages.append("PaddleOCR预处理")
    return {
        'success': True,
        'chapter_count': split_result.chapter_count,
        'output_files': split_result.output_files,
        'text_list_override': split_result.text_list_override
    }
```

#### 3.2 新增 `run_single_file_pipeline()`

```python
def run_single_file_pipeline(
    self,
    input_dir: str,
    output_base: str,
    prompt_version: str = "v3.0",
    split_strategy: str = "paddleocr",  # 当前仅 paddleocr
    skip_existing: bool = True,
    verbose: bool = True,
    subject_name: str = None
) -> Dict:
    """
    单文件模式:
      [PaddleOCR + 按章切割] → generate(逐章笔记) → integrate(整合)
    """
    start_time = time.time()
    self.post_processor.reset_issues()
    
    if subject_name is None:
        subject_name = self._infer_subject_name(input_dir, output_base)
    
    # 找到唯一的 PDF
    pdf_files = [f for f in os.listdir(input_dir) if f.endswith('.pdf')]
    pdf_path = os.path.join(input_dir, pdf_files[0])
    
    raw_texts_dir = os.path.join(output_base, "raw_texts")
    notes_dir = os.path.join(output_base, "notes")
    os.makedirs(raw_texts_dir, exist_ok=True)
    os.makedirs(notes_dir, exist_ok=True)
    
    if verbose:
        self._print_banner(input_dir, output_base, subject_name,
                           prompt_version, skip_existing, False, False)
    
    # 阶段1: PaddleOCR + 按章切割
    if verbose:
        print("\n" + "─"*60 + "\n📄 阶段1/3: PaddleOCR 文档解析 + 章节拆分\n" + "─"*60)
    ocr_result = self._run_paddleocr_stage(pdf_path, raw_texts_dir, verbose)
    if not ocr_result['success']:
        return {'success': False, 'error': ocr_result['error']}
    if verbose:
        print(f"\n✅ PaddleOCR 完成: 检测到 {ocr_result['chapter_count']} 个章节")
    
    # 阶段2: 逐章生成笔记（用 text_list_override 驱动）
    if verbose:
        print("\n" + "─"*60 + "\n📝 阶段2/3: 智能笔记生成\n" + "─"*60)
    note_results = self._run_generate_stage(
        pdf_dir=input_dir,
        output_dir=notes_dir,
        prompt_version=prompt_version,
        skip_existing=skip_existing,
        verbose=verbose,
        text_list_override=ocr_result['text_list_override']
    )
    self.completed_stages.append("笔记生成")
    if verbose:
        print(f"\n✅ 笔记生成完成: {note_results['success']}/{note_results['total']}")
    
    # 阶段3: 笔记整合（含质量检测）
    if verbose:
        print("\n" + "─"*60 + "\n📚 阶段3/3: 笔记整合\n" + "─"*60)
    quality_issues = self._run_quality_stage(verbose=verbose)
    integrate_results = self._run_integrate_stage(
        notes_dir=notes_dir,
        output_dir=output_base,
        subject_name=subject_name,
        verbose=verbose
    )
    self.completed_stages.append("笔记整合")
    
    elapsed_time = time.time() - start_time
    self.stats.set_total_time(elapsed_time)
    
    if verbose:
        print("\n" + "="*60)
        print(self.stats.generate_report())
        print("="*60)
        print(f"\n🎉 单文件Pipeline执行完成!")
        print(f"\n📁 输出目录: {output_base}")
        print(f"   ├── raw_texts/     ({ocr_result['chapter_count']} 个拆分文件)")
        print(f"   ├── notes/         ({note_results['success']} 个笔记文件)")
        print(f"   ├── 完整复习笔记.md")
        print(f"   └── 笔记索引.md\n")
    
    return {
        'success': True,
        'chapters_detected': ocr_result['chapter_count'],
        'notes_generated': note_results['success'],
        'quality_issues': quality_issues,
        'total_time': elapsed_time
    }
```

#### 3.3 修改 `_run_generate_stage()`

增加可选参数 `text_list_override`，格式为 `List[Tuple[str, int, str]]`：

- `item[0]`: 章节展示名称（如 "第一章 民法基本原理"）
- `item[1]`: 章序号（整数，用于笔记头部"第N讲"）
- `item[2]`: 拆分文本文件的完整路径

`ChapterSplitter.run()` 在写入拆分文件后返回 `text_list_override`，Pipeline 原样传入 `_run_generate_stage`。generate 阶段见此参数后跳过 PDF 列表构建，直接按列表顺序逐个生成笔记。

```python
def _run_generate_stage(
    self,
    pdf_dir: str,
    output_dir: str,
    prompt_version: str = "v3.0",
    skip_existing: bool = True,
    verbose: bool = True,
    text_list_override: Optional[List[Tuple[str, int, str]]] = None
) -> Dict:
    """
    笔记生成阶段
    
    Args:
        text_list_override: 可选，单文件模式下的拆分文本列表。
            [(章节名称, 章序号, raw_text完整路径), ...]
            当提供时，忽略 pdf_dir 的 PDF 列表，直接从此列表驱动。
            每个 item[2] 作为 generate_single_note 的 raw_text_path。
    """
    self.stats.start_stage("笔记生成")
    
    if text_list_override:
        # 单文件模式：从拆分文本文件列表驱动
        self.stats['total'] = len(text_list_override)
        for idx, (chapter_name, chapter_num, text_path) in enumerate(text_list_override, 1):
            output_filename = f"{idx:02d}_{chapter_name[:30]}_笔记.md"
            output_path = os.path.join(output_dir, output_filename)
            ...
            self.generate_single_note(
                pdf_path=text_path,  # 用于展示文件名
                output_path=output_path,
                lecture_num=chapter_num,
                prompt_version=prompt_version,
                verbose=verbose,
                raw_text_path=text_path  # 直接用拆分文本
            )
    else:
        # 原有逻辑：从 pdf_dir 构建 pdf_list
        ...
    ...
```

### 4. 修改 `cli.py`

#### 4.1 新增参数

```python
parser.add_argument(
    '--single-file',
    action='store_true',
    help='单文件模式：将单个大PDF按章节拆分后分别生成笔记'
)

parser.add_argument(
    '--split-strategy',
    type=str,
    choices=['paddleocr'],
    default='paddleocr',
    help='章节检测策略（当前仅 paddleocr，llm 策略待实现）'
)
```

#### 4.2 修改 `validate_inputs()`

```python
def validate_inputs(args) -> bool:
    ...
    pdf_files = [f for f in os.listdir(args.input) if f.endswith('.pdf')]
    
    if args.single_file:
        if len(pdf_files) != 1:
            print(f"❌ 单文件模式要求输入目录恰好包含1个PDF，当前: {len(pdf_files)}")
            return False
        return True  # 单文件模式跳过 PDF 数量检查
    
    if not pdf_files:
        print(f"❌ 错误: 输入目录中没有PDF文件 - {args.input}")
        return False
    return True
```

#### 4.3 修改 `run_pipeline()`

```python
def run_pipeline(args, config, logger):
    pipeline = Pipeline(qwen_client, config=config.config)
    skip_existing = not args.no_skip if args.no_skip else args.skip_existing
    
    if args.single_file and args.stage == 'all':
        results = pipeline.run_single_file_pipeline(
            input_dir=args.input,
            output_base=args.output,
            prompt_version=args.prompt_version,
            skip_existing=skip_existing,
            verbose=args.verbose and not args.quiet,
        )
        ...
    elif args.stage == 'all':
        results = pipeline.run_full_pipeline(...)
    ...
```

#### 4.4 自动检测提示

```python
# 在 main() 中，validate_inputs 之后
if not args.single_file and not is_kg_command:
    pdf_files = [f for f in os.listdir(args.input) if f.endswith('.pdf')]
    if len(pdf_files) == 1:
        file_size_mb = os.path.getsize(os.path.join(args.input, pdf_files[0])) / (1024*1024)
        if file_size_mb > 10:
            print(f"💡 检测到单个大PDF ({file_size_mb:.1f}MB)，建议使用 --single-file 按章节拆分")
```

### 5. 移除旧模块

| 文件 | 操作 | 原因 |
|------|------|------|
| `core/ocr_processor.py` | **删除** | PaddleOCR 完全替代 ocrmypdf |
| `scripts/ocr_and_split.py` | **删除** | 功能已整合到 `paddleocr_adapter.py` + `chapter_splitter.py` |

### 6. PaddleOCR 环境变量配置

`core/paddleocr_adapter.py` 读取以下环境变量（需在 `~/.claude/settings.local.json` 的 `env` 节中配置）：

```
PADDLEOCR_DOC_PARSING_API_URL=<your-paddleocr-api-url>
PADDLEOCR_ACCESS_TOKEN=<your-paddleocr-access-token>
```

首次运行时需要安装 PaddleOCR skill 依赖：
```bash
pip install -r ~/.claude/skills/paddleocr-doc-parsing/scripts/requirements.txt
```

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `core/paddleocr_adapter.py` | **新增** | PaddleOCR API 封装：分批调用、缓存管理、结果合并 |
| `core/chapter_splitter.py` | **新增** | 章节检测（三路互补：prunedResult + 正则 + 节复位推断）与 markdown 文本切割 |
| `core/ocr_processor.py` | **删除** | PaddleOCR 替代 ocrmypdf |
| `scripts/ocr_and_split.py` | **删除** | 功能已整合 |
| `core/pipeline.py` | 修改 | 新增 `_run_paddleocr_stage` + `run_single_file_pipeline`；`_run_generate_stage` 增加 `text_list_override` |
| `cli.py` | 修改 | 新增 `--single-file`、`--split-strategy` 参数 + 路由 + 自动检测提示 |
| `tests/test_chapter_splitter.py` | **新增** | 单元测试 |

## 执行顺序

```
Phase 1: core/paddleocr_adapter.py (新增)
         └── 封装 vl_caller.py 调用
         └── 分批 + 缓存逻辑
    ↓
Phase 2: core/chapter_splitter.py (新增)
         └── prunedResult 章标题检测
         └── 正则 fallback
         └── markdown 文本切割
    ↓
Phase 3: core/pipeline.py (修改)
         └── 新增 _run_paddleocr_stage
         └── 新增 run_single_file_pipeline
         └── 修改 _run_generate_stage
    ↓
Phase 4: cli.py (修改)
         └── --single-file / --split-strategy
         └── 路由 + 自动检测提示
    ↓
Phase 5: 清理旧模块
         └── 删除 core/ocr_processor.py
         └── 删除 scripts/ocr_and_split.py
    ↓
Phase 6: 测试
         └── tests/test_chapter_splitter.py
         └── 民法.pdf 集成验证
```

## 检测策略降级链

```
PaddleOCR prunedResult (block_label == "paragraph_title" + 第X章匹配)
    │                                     │
    │                                     ├── 空白归一化（\n → 空格）
    │                                     └── 按章编号提取 key
    │                                                           │
    └── 同时运行 ──────────────────────────────────────────────┘
                                                        │
    markdown 正则匹配                                      │
    ├── MARKDOWN_HEADING_PATTERN (^#{1,3}\s+第X章)         │
    └── BARE_CHAPTER_PATTERN (^第X章)  ← 无 ## 前缀的裸章标题  │
                                                        │
    ┌──────────────────── 两路合并 ──────────────────────┘
    │  _merge_chapter_lists():
    │  - prunedResult 优先（page 信息更准）
    │  - regex 补漏（prunedResult 遗漏的章节）
    │  - 当 pruned 条目在 markdown 中无法定位时，回退到 regex 同名条目
    │
    ├── 合并后 ≥1 个章 → _dedup_and_sort → 节复位推断（策略3）
    │       │
    │       ├── MARKDOWN_SECTION_PATTERN 提取节标题
    │       ├── 检测节编号复位（N→1，300字符外无已知章）
    │       ├── 推断章标题从第一节标题推导
    │       └── 12/12 章完整覆盖 ✓
    │
    └── 合并后 0 个章
            │
            ├── prunedResult 有 ≥1 个节 → 按节拆分（降级）⚠️ 警告用户
            │
            └── 章和节都检测不到 → ❌ 报错退出
                    提示: "未检测到章节结构，可尝试 --split-strategy llm"
                    LLM 策略当前未实现（遗留问题）
```

## 缓存机制

```
{input_dir}/
├── {pdf_name}.pdf
└── {pdf_name}_paddleocr_full.json  ← PaddleOCR 完整 JSON 缓存
                                       (含 prunedResult + markdown)
                                       后续重跑直接反序列化，跳过 API 调用
```

缓存写入 `input_dir`（PDF 所在目录）。若需强制重新解析，删除缓存文件即可。

**缓存格式**：vl_caller.py 输出的完整 JSON（`--stdout` 模式），包含 `result.layoutParsingResults[n].prunedResult` 和 `result.layoutParsingResults[n].markdown.text`。缓存命中时反序列化为 `ParseResult`，保持 prunedResult 可用——这是章节检测的首要数据来源。

## 测试计划

### 单元测试 (`test_chapter_splitter.py`)

- `test_detect_from_pruned_result` — 从 prunedResult 正确提取章标题
- `test_detect_chinese_chapter` — 匹配 "第一章 民法基本原理" 等
- `test_detect_chinese_section` — 匹配 "第一节 xxx" 等
- `test_dedup_cross_page` — 跨页重复标题去重
- `test_fallback_to_regex` — prunedResult 无结果时正则兜底
- `test_split_output_files` — 切割后文件数量和命名正确性
- `test_skip_small_chunks` — <200 字符片段跳过
- `test_preamble_handling` — 第一个章边界之前的内容 → 前言文件
- `test_zero_chapters_error` — 零检测时抛出明确错误

### 集成测试

- 用 民法.pdf（102 页）跑完整单文件流程：
  ```
  PYTHONIOENCODING=utf-8 D:/anaconda3/python.exe cli.py --single-file --input 民法/ --output 民法/output/
  ```
- 验证点：
  - `raw_texts/` 有 N 个按章拆分的 `*_提取文本.md` 文件
  - `notes/` 有 N 个 `*_笔记.md` 文件
  - `完整复习笔记.md` + `笔记索引.md` 正确生成
  - 缓存文件 `民法_paddleocr_full.md` 已创建

## 风险与遗留问题

| 项目 | 类型 | 说明 |
|------|------|------|
| PaddleOCR API 费用 | 风险 | 按页计费，大 PDF 成本需关注 |
| 章节检测优化 | 已实现 | 三路互补（prunedResult + 正则 + 节复位推断），覆盖无显式"第X章"标题的章节 |
| LLM 兜底策略 | 遗留 | `--split-strategy llm` 未实现，零检测时提示用户但不可用 |
| 非中文教材 | 风险 | 正则 fallback 支持 Chapter/Unit/Module，但 prunedResult 可能不适用 |
| PaddleOCR 依赖安装 | 前置 | 需先 `pip install -r ~/.claude/skills/paddleocr-doc-parsing/scripts/requirements.txt` |

---

*文档版本: v2.0 | 生成时间: 2026-05-09 | grill-me 终版*
