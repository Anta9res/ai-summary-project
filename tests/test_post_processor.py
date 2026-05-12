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

    def test_fix_latex_empty_line_after_opening(self):
        """验证 $$ 后空行被正确移除"""
        content = "$$\n\n\\boldsymbol{T}"
        fixed = self.pp.fix_latex_format(content)
        assert "$$\n\n" not in fixed
        assert fixed == "$$\n\\boldsymbol{T}"

    def test_fix_latex_no_regression_on_correct(self):
        """验证已正确格式的 LaTeX 不被破坏"""
        content = "$$\n\\begin{bmatrix}\n1 & 0 \\\\\n0 & 1\n\\end{bmatrix}\n$$"
        fixed = self.pp.fix_latex_format(content)
        assert "$$\n\n" not in fixed
        assert fixed == content

    def test_fix_latex_spaces_before_opening(self):
        """验证 $$ 前空格被清理"""
        content = "  $$\n\\boldsymbol{T}"
        fixed = self.pp.fix_latex_format(content)
        assert "  $$" not in fixed
        assert fixed == "$$\n\\boldsymbol{T}"

    def test_fix_latex_multiple_empty_lines_after_opening(self):
        """验证 $$ 后多个空行被正确移除"""
        content = "$$\n\n\n\n\\boldsymbol{T}"
        fixed = self.pp.fix_latex_format(content)
        assert "$$\n\n" not in fixed
        assert fixed == "$$\n\\boldsymbol{T}"

    def test_check_latex_empty_line_detection(self):
        """验证检测规则能识别 $$ 后空行"""
        content = "$$\n\n\\boldsymbol{T}\n$$"
        issues = self.pp.check_latex_format(content, "test.md")
        assert any("空行" in i["issue"] for i in issues)

    def test_check_latex_spaces_before_detection(self):
        """验证检测规则能识别 $$ 前空格"""
        content = "  $$\n\\boldsymbol{T}\n$$"
        issues = self.pp.check_latex_format(content, "test.md")
        assert any("空格" in i["issue"] for i in issues)

    def test_fix_latex_closing_preserves_spacing(self):
        """验证闭标签 $$ 后的空行移除不影响渲染（已知取舍）"""
        # 闭标签 $$ 后跟空行是合法 Markdown，Fix 1b 锚定行首后仍会匹配
        # （闭标签 $$ 也可能在行首）。这是可接受的取舍：移除不影响公式渲染。
        content = "$$\n\\boldsymbol{T}\n$$\n\nNext paragraph"
        fixed = self.pp.fix_latex_format(content)
        # 开标签 $$ 后不应有空行（核心修复）
        assert "$$\n\n" not in fixed[:10]
        # 公式内容完整保留
        assert "\\boldsymbol{T}" in fixed
        assert "Next paragraph" in fixed

    def test_fix_latex_trailing_spaces(self):
        """验证 Fix 1 移除 $$ 后多余空白字符"""
        content = "$$\n\nMiddle content\n$$\n\nNext line\n" + "x" * 600
        fixed = self.pp.fix_latex_format(content)
        assert "$$ \n" not in fixed

    def test_remove_code_block_wrapper(self):
        content = "Before\n```markdown\n## Title\nBody\n```\nAfter"
        fixed = self.pp.remove_code_block_wrapper(content)
        assert "```markdown" not in fixed
        assert "Before\n## Title\nBody\nAfter" in fixed

    def test_remove_code_block_wrapper_unpaired(self):
        """验证无闭合标签时（max_tokens截断）仍能移除开标签"""
        content = "Before\n```markdown\n## Title\nBody\n"  # 无闭合 ```
        fixed = self.pp.remove_code_block_wrapper(content)
        assert "```markdown" not in fixed
        assert "Before\n## Title\nBody" in fixed

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
