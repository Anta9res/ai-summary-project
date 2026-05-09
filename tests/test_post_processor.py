"""
测试 PostProcessor 6 种质量检测规则
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.post_processor import PostProcessor


class TestPostProcessor:
    def setup_method(self):
        self.pp = PostProcessor()

    def test_structural_integrity_core_markers_missing(self):
        content = "## Some title\n\nNo core markers here."
        issues = self.pp.quality_check(content, "test.md")
        assert any("⭐⭐⭐" in i["issue"] for i in issues)

    def test_min_length_too_short(self):
        content = "Too short"
        issues = self.pp.quality_check(content, "test.md")
        assert any("<500" in i["issue"] for i in issues)

    def test_min_length_ok(self):
        content = "## Title\n\n" + "x" * 600
        issues = self.pp.quality_check(content, "test.md")
        assert not any("<500" in i["issue"] for i in issues)

    def test_heading_structure_missing(self):
        content = "No headings at all\n" + "x" * 600
        issues = self.pp.quality_check(content, "test.md")
        assert any("章节标题" in i["issue"] for i in issues)

    def test_code_block_residual_detected(self):
        content = "```markdown\n## Title\ncontent\n```\n" + "x" * 600
        issues = self.pp.quality_check(content, "test.md")
        assert any("代码块包裹" in i["issue"] for i in issues)

    def test_duplicate_content_detected(self):
        long_line = "A" * 30
        content = (long_line + "\n") * 5 + "x" * 600
        issues = self.pp.quality_check(content, "test.md")
        assert any("重复内容" in i["issue"] for i in issues)

    def test_missing_required_markers(self):
        content = "Content without required markers\n" + "x" * 600
        issues = self.pp.quality_check(content, "test.md")
        assert any("💡" in i["issue"] for i in issues) or any("🔗" in i["issue"] for i in issues)

    def test_reset_issues_clears_history(self):
        self.pp.quality_issues = [{"file": "x", "issue": "test", "severity": "error"}]
        self.pp.reset_issues()
        assert len(self.pp.quality_issues) == 0

    def test_fix_latex_trailing_spaces(self):
        content = "$$\n\nMiddle content\n$$\n\nNext line\n" + "x" * 600
        fixed = self.pp.fix_latex_format(content)
        assert "$$ \n" not in fixed

    def test_remove_code_block_wrapper(self):
        content = "Before\n```markdown\n## Title\nBody\n```\nAfter"
        fixed = self.pp.remove_code_block_wrapper(content)
        assert "```markdown" not in fixed
        assert "Before\n## Title\nBody\nAfter" in fixed

    def test_clean_trailing_markers_removes_trailing_blank_lines(self):
        content = "Real content\n\n\n"
        fixed = self.pp.clean_trailing_markers(content)
        assert fixed == "Real content"

    def test_clean_trailing_markers_removes_trailing_backticks(self):
        content = "Real content\n```"
        fixed = self.pp.clean_trailing_markers(content)
        assert not fixed.endswith("```")

    def test_integration_process_passes_quality(self):
        content = "### ⭐⭐⭐ Core Topic\n\n💡 Summary\n\n🔗 Related\n\n" + "P" * 600
        result, passed = self.pp.process(content, "test.md")
        assert passed
        assert "QUALITY_PASSED" in result

    def test_integration_process_fails_quality(self):
        content = "Too short"
        result, passed = self.pp.process(content, "test.md")
        assert not passed
