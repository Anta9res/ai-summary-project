"""Unit tests for chapter_splitter.py"""
import os
import tempfile
import pytest
from core.chapter_splitter import ChapterSplitter, Chapter, SplitResult, CHAPTER_PATTERN, SECTION_PATTERN


def _make_pruned_result(titles_by_page):
    """Helper: build a parse_result dict with prunedResult from title specs.

    titles_by_page: [(page_idx, [("paragraph_title", "block_content"), ...]), ...]

    Uses the actual PaddleOCR API response structure:
      result.result.layoutParsingResults[n].prunedResult.parsing_res_list[m]
    """
    layouts = []
    for page_idx, blocks in titles_by_page:
        parsing_list = []
        for block_label, block_content in blocks:
            parsing_list.append({"block_label": block_label, "block_content": block_content})
        layouts.append({
            "prunedResult": {"parsing_res_list": parsing_list},
            "markdown": {"text": ""}
        })
    return {"result": {"result": {"layoutParsingResults": layouts}}}


class TestChapterDetection:
    def test_detect_from_pruned_result(self):
        """prunedResult 中 paragraph_title 应被正确提取为章标题"""
        raw = _make_pruned_result([
            (0, [("paragraph_title", "第一章 民法基本原理")]),
            (0, [("text", "民法是调整平等主体之间...")]),
            (1, [("paragraph_title", "第二章 民事法律关系")]),
            (1, [("text", "民事法律关系是指...")]),
        ])
        markdown = "第一章 民法基本原理\n\n民法是调整...\n\n第二章 民事法律关系\n\n民事法律关系是指..."

        splitter = ChapterSplitter()
        chapters = splitter.detect_chapters(markdown, raw)

        assert len(chapters) == 2
        assert chapters[0].title == "第一章 民法基本原理"
        assert chapters[1].title == "第二章 民事法律关系"
        assert all(c.level == "chapter" for c in chapters)

    def test_detect_chinese_chapter(self):
        """匹配中文数字章标题"""
        raw = _make_pruned_result([
            (0, [("paragraph_title", "第一编 总则")]),
            (0, [("paragraph_title", "第一章 民法概述")]),
        ])
        markdown = "第一编 总则\n\n第一章 民法概述\n\n内容..."

        splitter = ChapterSplitter()
        chapters = splitter.detect_chapters(markdown, raw)

        assert len(chapters) >= 1
        assert any("第一章" in c.title for c in chapters)

    def test_detect_chinese_section(self):
        """0 章时降级检测节标题"""
        raw = _make_pruned_result([
            (0, [("paragraph_title", "第一节 民法的概念")]),
            (1, [("paragraph_title", "第二节 民法的渊源")]),
        ])
        markdown = "第一节 民法的概念\n\n...\n\n第二节 民法的渊源\n\n..."

        splitter = ChapterSplitter()
        chapters = splitter.detect_chapters(markdown, raw)

        assert len(chapters) == 2
        assert all(c.level == "section" for c in chapters)

    def test_dedup_cross_page(self):
        """跨页重复标题去重"""
        raw = _make_pruned_result([
            (0, [("paragraph_title", "第一章 概述")]),
            (1, [("paragraph_title", "第一章 概述")]),  # 页眉重复
        ])
        markdown = "第一章 概述\n\n第一页内容\n\n第一章 概述\n\n第二页内容"

        splitter = ChapterSplitter()
        chapters = splitter.detect_chapters(markdown, raw)

        assert len(chapters) == 1
        assert chapters[0].title == "第一章 概述"


class TestRegexFallback:
    def test_fallback_to_regex(self):
        """prunedResult 无章标题时应 fallback 到正则匹配 markdown"""
        raw = _make_pruned_result([
            (0, [("text", "一些正文内容没有标题")]),
        ])
        markdown = "前言内容\n\n## 第一章 总则\n\n正文...\n\n## 第二章 分则\n\n更多正文"

        splitter = ChapterSplitter()
        chapters = splitter.detect_chapters(markdown, raw)

        assert len(chapters) >= 1


class TestSplitByChapters:
    def test_split_output_files(self):
        """切割后文件数量和命名正确性"""
        markdown = "## 第一章 总则\n\n" + "内容" * 100 + "\n\n## 第二章 分则\n\n" + "内容" * 100
        chapters = [
            Chapter(title="第一章 总则", position=markdown.find("## 第一章 总则"), level="chapter"),
            Chapter(title="第二章 分则", position=markdown.find("## 第二章 分则"), level="chapter"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            splitter = ChapterSplitter()
            files = splitter.split_by_chapters(markdown, chapters, "test_pdf", tmpdir)

            assert len(files) == 2
            for f in files:
                assert os.path.exists(f)
                assert f.endswith("_提取文本.md")
                assert "test_pdf" in os.path.basename(f)

    def test_skip_small_chunks(self):
        """<200 字符片段应跳过"""
        markdown = "## 第一章 总则\n\n" + "x" * 250 + "\n\n## 第二章 短章\n\n短" + "\n\n## 第三章 更多\n\n" + "y" * 250
        chapters = [
            Chapter(title="第一章 总则", position=markdown.find("## 第一章 总则"), level="chapter"),
            Chapter(title="第二章 短章", position=markdown.find("## 第二章 短章"), level="chapter"),
            Chapter(title="第三章 更多", position=markdown.find("## 第三章 更多"), level="chapter"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            splitter = ChapterSplitter()
            files = splitter.split_by_chapters(markdown, chapters, "test_pdf", tmpdir)

            assert len(files) == 2  # 第二章 因 <200 字符被跳过
            assert all("短章" not in os.path.basename(f) for f in files)

    def test_preamble_handling(self):
        """第一个章边界之前的内容应输出为前言文件"""
        preamble = "这是前言内容" + "x" * 200
        markdown = preamble + "\n\n## 第一章 总则\n\n" + "y" * 250
        chapters = [
            Chapter(title="第一章 总则", position=len(preamble) + 2, level="chapter"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            splitter = ChapterSplitter()
            files = splitter.split_by_chapters(markdown, chapters, "test_pdf", tmpdir)

            preamble_files = [f for f in files if "前言" in os.path.basename(f)]
            assert len(preamble_files) == 1


class TestRun:
    def test_zero_chapters_error(self):
        """零检测时返回失败结果"""
        raw = _make_pruned_result([
            (0, [("text", "没有任何标题的纯文本")]),
        ])
        markdown = "没有任何标题的纯文本" * 50

        splitter = ChapterSplitter()

        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf_file:
                pdf_path = pdf_file.name

            try:
                parse_result = raw
                parse_result["markdown_text"] = markdown
                # Override _extract_markdown to avoid PaddleOCRAdapter dependency
                splitter._extract_markdown = lambda _: markdown
                result = splitter.run(pdf_path, parse_result, tmpdir)
                assert not result.success
                assert result.error is not None
            finally:
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)


class TestPatterns:
    def test_chapter_pattern_matches_arabic(self):
        assert CHAPTER_PATTERN.search("第一章 概述")
        assert CHAPTER_PATTERN.search("第1章 概述")

    def test_chapter_pattern_matches_chinese(self):
        assert CHAPTER_PATTERN.search("第十一章 合同")
        assert CHAPTER_PATTERN.search("第二十章 侵权")

    def test_section_pattern(self):
        assert SECTION_PATTERN.search("第一节 概念")
        assert not SECTION_PATTERN.search("第一章 概述")  # 章不是节
