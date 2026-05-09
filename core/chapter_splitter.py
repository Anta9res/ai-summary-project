"""
章节文本拆分模块

从 PaddleOCR 的 markdown 输出中按章切割。

检测策略（按优先级）：
  1. prunedResult block_label == "paragraph_title" + 内容匹配 第X章
  2. markdown 正则匹配 /^## 第[一二三四五六七八九十百\\d]+章/
  3. LLM 识别章节标题（兜底，遗留问题）

零检测降级链：
  - ≥1 章 → 按章拆分
  - 0 章 + ≥1 节 → 降级按节拆分（警告用户）
  - 0 章 + 0 节 → 正则 fallback → 仍无 → 报错退出
"""
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# 匹配章/节标题的正则
CHAPTER_PATTERN = re.compile(r'第[一二三四五六七八九十百\d]+章')
SECTION_PATTERN = re.compile(r'第[一二三四五六七八九十百\d]+节')
# markdown 中带 ## 前缀的标题行
MARKDOWN_HEADING_PATTERN = re.compile(
    r'^#{1,3}\s+第[一二三四五六七八九十百\d]+[章节]',
    re.MULTILINE
)
# markdown 中裸的章标题行（无 ## 前缀，如 "第五章 法人"）
BARE_CHAPTER_PATTERN = re.compile(
    r'^第[一二三四五六七八九十百\d]+章\b',
    re.MULTILINE
)


@dataclass
class Chapter:
    """章节信息"""
    title: str
    position: int          # 在 markdown 全文中的字符位置
    level: str = "chapter"  # "chapter" | "section"
    page: int = 0           # 来源页码（prunedResult），0 表示未知


@dataclass
class SplitResult:
    """拆分结果"""
    success: bool
    chapter_count: int = 0
    output_files: List[str] = field(default_factory=list)
    text_list_override: List[Tuple[str, int, str]] = field(default_factory=list)
    error: Optional[str] = None
    level: str = "chapter"  # 实际拆分级别


class ChapterSplitter:
    """章节文本拆分"""

    # 最小片段字符数
    MIN_CHUNK_CHARS = 200

    # 安全文件名禁止字符
    SAFE_FILENAME_RE = re.compile(r'[\\/:*?"<>|]')

    def detect_chapters(self, markdown_text: str, parse_result: dict) -> List[Chapter]:
        """
        从 prunedResult + markdown 互补提取章/节标题。

        策略 1（主）：prunedResult paragraph_title blocks
        策略 2（互补）：markdown 正则（始终运行，补策略1的遗漏）
        """
        titles = self._extract_titles_from_pruned(parse_result)

        pruned_chapters = [t for t in titles if CHAPTER_PATTERN.search(t.title)]
        regex_chapters = self._detect_from_regex(markdown_text)

        # 合并两路结果（去重），prunedResult 优先级更高
        all_chapters = self._merge_chapter_lists(pruned_chapters, regex_chapters, markdown_text)

        if all_chapters:
            return self._dedup_and_sort(all_chapters, markdown_text, level="chapter")

        # 0 章 → 检查是否有节
        sections = [t for t in titles if SECTION_PATTERN.search(t.title)]
        if sections:
            return self._dedup_and_sort(sections, markdown_text, level="section")

        return []

    def _extract_titles_from_pruned(self, parse_result: dict) -> List[Chapter]:
        """从 prunedResult 提取 paragraph_title 类型的 block"""
        titles = []
        from core.paddleocr_adapter import PaddleOCRAdapter
        layouts = PaddleOCRAdapter._get_layouts(parse_result)

        for page_idx, layout in enumerate(layouts):
            pruned = layout.get("prunedResult", {})
            parsing_list = pruned.get("parsing_res_list", [])

            for item in parsing_list:
                if item.get("block_label") == "paragraph_title":
                    content = item.get("block_content", "").strip()
                    # 归一化空白字符（换行→空格），确保与 markdown 匹配
                    content = re.sub(r'\s+', ' ', content)
                    if content:
                        titles.append(Chapter(
                            title=content,
                            position=0,
                            level="unknown",
                            page=page_idx + 1
                        ))

        return titles

    def _detect_from_regex(self, markdown_text: str) -> List[Chapter]:
        """正则匹配 markdown 中的章标题行（含 ## 前缀和无前缀两种）"""
        chapters = []
        seen_positions = set()

        for pattern in (MARKDOWN_HEADING_PATTERN, BARE_CHAPTER_PATTERN):
            for m in pattern.finditer(markdown_text):
                line_start = m.start()
                if line_start in seen_positions:
                    continue
                seen_positions.add(line_start)

                line_end = markdown_text.find('\n', m.start())
                if line_end == -1:
                    line_end = len(markdown_text)
                title = markdown_text[line_start:line_end].strip()
                title = re.sub(r'^#{1,3}\s+', '', title)

                if CHAPTER_PATTERN.search(title):
                    chapters.append(Chapter(
                        title=title,
                        position=line_start,
                        level="chapter"
                    ))
        return chapters

    def _merge_chapter_lists(
        self,
        pruned: List[Chapter],
        regex: List[Chapter],
        markdown_text: str
    ) -> List[Chapter]:
        """合并 prunedResult 和 regex 两路检测结果。

        prunedResult 优先（page 信息更准），regex 补漏。
        去重依据：章编号（如 "第一章"）。
        当 pruned 条目无法在 markdown 中定位时，回退到 regex 同名条目。
        """
        merged: dict[str, Chapter] = {}

        for c in pruned:
            key = self._chapter_number_key(c.title)
            merged[key] = c

        for c in regex:
            key = self._chapter_number_key(c.title)
            c_pos = markdown_text.find(c.title)
            if key not in merged:
                merged[key] = c
            else:
                existing_pos = markdown_text.find(merged[key].title)
                if existing_pos < 0 and c_pos >= 0:
                    # pruned 条目有换行等问题无法定位 → 用 regex 条目替换
                    merged[key] = c
                elif existing_pos >= 0 and c_pos >= 0 and len(c.title) > len(merged[key].title):
                    merged[key] = c

        return list(merged.values())

    @staticmethod
    def _chapter_number_key(title: str) -> str:
        """提取章编号作为去重 key，如 '第一章' → 'ch1'"""
        m = CHAPTER_PATTERN.search(title)
        if m:
            return m.group()
        return title

    def _dedup_and_sort(self, items: List[Chapter], markdown_text: str, level: str) -> List[Chapter]:
        """去重并按在 markdown 中的位置排序"""
        seen_titles = set()
        unique = []

        for item in items:
            # 在 markdown 中定位标题
            pos = markdown_text.find(item.title)
            if pos == -1:
                # 尝试模糊匹配（去掉首尾空白）
                pos = markdown_text.find(item.title.strip())

            if item.title in seen_titles:
                continue
            seen_titles.add(item.title)

            item.position = pos if pos >= 0 else 999999
            item.level = level
            unique.append(item)

        unique.sort(key=lambda x: x.position)
        return [c for c in unique if 0 <= c.position < 999999]

    def split_by_chapters(
        self,
        markdown_text: str,
        chapters: List[Chapter],
        pdf_name: str,
        output_dir: str
    ) -> List[str]:
        """
        按检测到的章边界切割 markdown 文本。

        - 第一个章边界之前的内容 → 00_前言_{pdf_name}_提取文本.md
        - 每个章 → {idx:02d}_{章标题}_{pdf_name}_提取文本.md
        - 过滤内容 <200 字符的片段
        """
        os.makedirs(output_dir, exist_ok=True)
        output_files = []

        if not chapters:
            return output_files

        # 按位置排序
        chapters.sort(key=lambda c: c.position)

        # 第一个边界之前的内容 → 前言
        if chapters[0].position > 0:
            preamble = markdown_text[:chapters[0].position].strip()
            if len(preamble) >= self.MIN_CHUNK_CHARS:
                filename = f"00_前言_{pdf_name}_提取文本.md"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(preamble)
                output_files.append(filepath)

        # 逐章切割
        for i, chapter in enumerate(chapters):
            start_pos = chapter.position
            if i + 1 < len(chapters):
                end_pos = chapters[i + 1].position
            else:
                end_pos = len(markdown_text)

            content = markdown_text[start_pos:end_pos].strip()
            if len(content) < self.MIN_CHUNK_CHARS:
                continue

            safe_title = self.SAFE_FILENAME_RE.sub('', chapter.title)[:50]
            filename = f"{i + 1:02d}_{safe_title}_{pdf_name}_提取文本.md"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            output_files.append(filepath)

        return output_files

    def run(self, pdf_path: str, parse_result: dict, output_dir: str) -> SplitResult:
        """
        完整流程：检测 → 切割 → 写入文件。

        Returns:
            SplitResult(success, chapter_count, output_files, text_list_override)
        """
        from core.paddleocr_adapter import PaddleOCRAdapter

        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        markdown_text = PaddleOCRAdapter._extract_markdown(parse_result)

        chapters = self.detect_chapters(markdown_text, parse_result)

        if not chapters:
            return SplitResult(
                success=False,
                error="未检测到章节结构，可尝试 --split-strategy llm（LLM 策略暂未实现）"
            )

        output_files = self.split_by_chapters(markdown_text, chapters, pdf_name, output_dir)

        actual_level = chapters[0].level if chapters else "chapter"

        text_list_override = []
        for i, filepath in enumerate(output_files):
            chapter_name = os.path.splitext(os.path.basename(filepath))[0]
            # 去掉 pdf_name 后缀
            chapter_name = chapter_name.replace(f"_{pdf_name}_提取文本", "")
            text_list_override.append((chapter_name, i + 1, filepath))

        return SplitResult(
            success=True,
            chapter_count=len(output_files),
            output_files=output_files,
            text_list_override=text_list_override,
            level=actual_level
        )
