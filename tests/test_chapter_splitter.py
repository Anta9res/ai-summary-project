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


class TestChineseNumConversion:
    def test_chinese_to_int_basic(self):
        splitter = ChapterSplitter()
        assert splitter._chinese_to_int('一') == 1
        assert splitter._chinese_to_int('五') == 5
        assert splitter._chinese_to_int('十') == 10

    def test_chinese_to_int_multi(self):
        splitter = ChapterSplitter()
        assert splitter._chinese_to_int('十一') == 11
        assert splitter._chinese_to_int('十二') == 12
        assert splitter._chinese_to_int('二十') == 20
        assert splitter._chinese_to_int('十五') == 15

    def test_chinese_to_int_digit(self):
        splitter = ChapterSplitter()
        assert splitter._chinese_to_int('3') == 3
        assert splitter._chinese_to_int('12') == 12

    def test_int_to_chinese(self):
        splitter = ChapterSplitter()
        assert splitter._int_to_chinese(1) == '一'
        assert splitter._int_to_chinese(7) == '七'
        assert splitter._int_to_chinese(12) == '十二'

    def test_chinese_to_int_invalid(self):
        """无效输入应返回 0（哨兵值，下游跳过 num==0）"""
        splitter = ChapterSplitter()
        assert splitter._chinese_to_int('') == 0
        assert splitter._chinese_to_int('abc') == 0
        assert splitter._chinese_to_int('零') == 0

    def test_int_to_chinese_boundary(self):
        """超出 _CHINESE_NUMS 范围的数字降级为阿拉伯数字字符串"""
        splitter = ChapterSplitter()
        assert splitter._int_to_chinese(0) == '0'
        assert splitter._int_to_chinese(20) == '二十'
        assert splitter._int_to_chinese(21) == '21'


class TestSectionResetInference:
    def test_infer_chapters_basic(self):
        """节编号从 N→1 复位时推断新章边界"""
        markdown = (
            "## 第一章 总则\n\n" + "x" * 200 + "\n\n"
            "## 第一节 基本概念\n\n" + "y" * 200 + "\n\n"
            "## 第二节 基本原则\n\n" + "z" * 200 + "\n\n"
            "## 第一节 民事法律关系\n\n" + "w" * 200 + "\n\n"
        )
        raw = _make_pruned_result([
            (0, [("paragraph_title", "第一章 总则")]),
        ])
        splitter = ChapterSplitter()
        chapters = splitter.detect_chapters(markdown, raw)

        assert len(chapters) == 2
        assert chapters[0].title.startswith("第一章")
        assert chapters[1].title.startswith("第二章")
        assert chapters[1].position > chapters[0].position

    def test_infer_chapters_near_known_excluded(self):
        """已知章附近的节复位不产生推断章（距离 < 300 字符，应被排除）"""
        ch2_pos = 100
        markdown = (
            "## 第一章 引言\n\n" + "x" * 200 + "\n\n"
            + " " * ch2_pos + "第二章\n\n"
            "## 第一节 基本原则\n\n" + "y" * 200 + "\n\n"
        )
        known = [Chapter(title="第二章", position=ch2_pos, level="chapter")]
        splitter = ChapterSplitter()
        inferred = splitter._infer_chapters_from_section_reset(markdown, known)
        assert len(inferred) == 0

    def test_infer_chapters_multi_reset(self):
        """多次复位产生多个推断章"""
        markdown = (
            "## 第一章 引言\n\n" + "x" * 200 + "\n\n"
            "## 第一节 A\n\n" + "a" * 100 + "\n\n"
            "## 第二节 B\n\n" + "b" * 100 + "\n\n"
            "## 第三节 C\n\n" + "c" * 100 + "\n\n"
            "## 第一节 D\n\n" + "d" * 100 + "\n\n"
            "## 第二节 E\n\n" + "e" * 100 + "\n\n"
            "## 第一节 F\n\n" + "f" * 100 + "\n\n"
        )
        raw = _make_pruned_result([
            (0, [("paragraph_title", "第一章 引言")]),
        ])
        splitter = ChapterSplitter()
        chapters = splitter.detect_chapters(markdown, raw)

        assert len(chapters) == 3  # 第一章 + 2 inferred

    def test_infer_chapters_no_reset(self):
        """节编号连续递增，不产生任何推断章"""
        markdown = (
            "## 第一章 唯章\n\n"
            "## 第一节 A\n\n" + "a" * 100 + "\n\n"
            "## 第二节 B\n\n" + "b" * 100 + "\n\n"
            "## 第三节 C\n\n" + "c" * 100 + "\n\n"
        )
        raw = _make_pruned_result([
            (0, [("paragraph_title", "第一章 唯章")]),
        ])
        splitter = ChapterSplitter()
        chapters = splitter.detect_chapters(markdown, raw)

        assert len(chapters) == 1

    def test_infer_chapter_title_derivation(self):
        """推断章标题从第一节标题推导"""
        markdown = (
            "## 第一章 总则\n\n" + "x" * 200 + "\n\n"
            "## 第一节 基础概念\n\n" + "a" * 200 + "\n\n"
            "## 第二节 原则\n\n" + "b" * 200 + "\n\n"
            "## 第一节 民事法律关系概述\n\n" + "c" * 200 + "\n\n"
        )
        raw = _make_pruned_result([
            (0, [("paragraph_title", "第一章 总则")]),
        ])
        splitter = ChapterSplitter()
        chapters = splitter.detect_chapters(markdown, raw)

        assert len(chapters) == 2
        assert chapters[1].title == "第二章 民事法律关系"

    def test_infer_chapters_section_num_dedup(self):
        """同编号节跨页重复不应产生误判"""
        markdown = (
            "## 第一章 引言\n\n" + "x" * 200 + "\n\n"
            "## 第一节 概念\n\n" + "a" * 100 + "\n\n"
            "## 第一节 概念\n\n" + "b" * 100 + "\n\n"  # 跨页重复
            "## 第二节 特征\n\n" + "c" * 200 + "\n\n"
            "## 第一节 新章\n\n" + "d" * 200 + "\n\n"
        )
        raw = _make_pruned_result([
            (0, [("paragraph_title", "第一章 引言")]),
        ])
        splitter = ChapterSplitter()
        chapters = splitter.detect_chapters(markdown, raw)

        assert len(chapters) == 2  # 重复第一节被去重，仅在新章边界产生推断

    def test_infer_chapters_proximity_threshold(self):
        """距离恰好在阈值边界：299 排除，300 不排除（PROXIMITY_THRESHOLD=300）"""
        splitter = ChapterSplitter()
        # known chapter at position 0, verified by title match
        known = [Chapter(title="第二章", position=0, level="chapter")]

        # "第二章\n\n"(5) + "## 第二节 前置\n\n"(11) + "z"*282 + "\n" + "## 第一节" at pos 299
        markdown_299 = "第二章\n\n## 第二节 前置\n\n" + "z" * 282 + "\n## 第一节 概念\n\n" + "y" * 200
        inferred_299 = splitter._infer_chapters_from_section_reset(markdown_299, known)
        assert len(inferred_299) == 0

        # "第二章\n\n"(5) + "## 第二节 前置\n\n"(11) + "z"*283 + "\n" + "## 第一节" at pos 300
        markdown_300 = "第二章\n\n## 第二节 前置\n\n" + "z" * 283 + "\n## 第一节 概念\n\n" + "y" * 200
        inferred_300 = splitter._infer_chapters_from_section_reset(markdown_300, known)
        assert len(inferred_300) == 1


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
