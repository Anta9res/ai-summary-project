"""
PaddleOCR 文档解析适配器

封装 PaddleOCR skill 的 vl_caller.py 调用，提供：
  - 分批调用（每批 ≤100 页）
  - 缓存管理（{pdf_name}_paddleocr_full.json）
  - 结果合并（多批 markdown 拼接）
"""
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ParseResult:
    """PaddleOCR 解析结果"""
    success: bool
    markdown_text: str = ""
    raw_json: dict = field(default_factory=dict)
    error: Optional[str] = None


class PaddleOCRAdapter:
    """PaddleOCR 文档解析适配器"""

    SKILL_DIR = os.path.join(os.path.expanduser("~"), ".claude", "skills", "paddleocr-doc-parsing")

    def __init__(self):
        self.api_url = os.environ.get("PADDLEOCR_DOC_PARSING_API_URL", "")
        self.access_token = os.environ.get("PADDLEOCR_ACCESS_TOKEN", "")

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
        pdf_path = os.path.abspath(pdf_path)
        pdf_dir = os.path.dirname(pdf_path)
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        cache_path = os.path.join(pdf_dir, f"{pdf_name}_paddleocr_full.json")

        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    raw_json = json.load(f)
                markdown_text = self._extract_markdown(raw_json)
                return ParseResult(success=True, markdown_text=markdown_text, raw_json=raw_json)
            except (json.JSONDecodeError, KeyError):
                pass

        total_pages = self._get_total_pages(pdf_path)

        if total_pages <= 100:
            raw_json = self._call_vl_caller(pdf_path)
        else:
            raw_json = self._parse_large_pdf(pdf_path, total_pages, pdf_dir)

        if raw_json is None:
            return ParseResult(success=False, error="PaddleOCR API 调用失败")

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(raw_json, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

        markdown_text = self._extract_markdown(raw_json)
        return ParseResult(success=True, markdown_text=markdown_text, raw_json=raw_json)

    def _get_total_pages(self, pdf_path: str) -> int:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(pdf_path)
        total = len(pdf)
        pdf.close()
        return total

    def _call_vl_caller(self, file_path: str) -> Optional[dict]:
        vl_caller = os.path.join(self.SKILL_DIR, "scripts", "vl_caller.py")
        scripts_dir = os.path.join(self.SKILL_DIR, "scripts")

        env = os.environ.copy()
        env["PADDLEOCR_DOC_PARSING_API_URL"] = self.api_url
        env["PADDLEOCR_ACCESS_TOKEN"] = self.access_token

        try:
            proc = subprocess.run(
                [sys.executable, vl_caller, "--file-path", file_path, "--stdout", "--pretty"],
                capture_output=True, text=True, encoding='utf-8',
                env=env, timeout=300,
                cwd=scripts_dir
            )
            if proc.returncode != 0:
                print(f"PaddleOCR 调用失败: {proc.stderr}", file=sys.stderr)
                return None
            return json.loads(proc.stdout)
        except subprocess.TimeoutExpired:
            print("PaddleOCR API 超时 (>300秒)", file=sys.stderr)
            return None
        except json.JSONDecodeError as e:
            print(f"PaddleOCR 返回 JSON 解析失败: {e}", file=sys.stderr)
            return None

    def _parse_large_pdf(self, pdf_path: str, total_pages: int, cache_dir: str) -> Optional[dict]:
        split_pdf_script = os.path.join(self.SKILL_DIR, "scripts", "split_pdf.py")
        batch_size = 100
        all_results = []

        for start_page in range(1, total_pages + 1, batch_size):
            end_page = min(start_page + batch_size - 1, total_pages)
            pages_spec = f"{start_page}-{end_page}"
            batch_pdf = os.path.join(cache_dir, f"_paddleocr_batch_{start_page}_{end_page}.pdf")

            proc = subprocess.run(
                [sys.executable, split_pdf_script, pdf_path, batch_pdf, "--pages", pages_spec],
                capture_output=True, text=True, encoding='utf-8',
                timeout=60
            )
            if proc.returncode != 0:
                print(f"PDF 切分失败: {pages_spec} - {proc.stderr}", file=sys.stderr)
                continue

            if not os.path.exists(batch_pdf):
                print(f"PDF 切分失败: {pages_spec}", file=sys.stderr)
                continue

            result = self._call_vl_caller(batch_pdf)

            try:
                os.remove(batch_pdf)
            except OSError:
                pass

            if result is None:
                print(f"批次 {pages_spec} 解析失败", file=sys.stderr)
                continue

            all_results.append(result)

        if not all_results:
            return None

        return self._merge_batch_results(all_results)

    def _merge_batch_results(self, all_results: List[dict]) -> dict:
        if len(all_results) == 1:
            return all_results[0]

        merged = dict(all_results[0])
        merged_layouts = list(merged.get("result", {}).get("layoutParsingResults", []))

        for result in all_results[1:]:
            layouts = result.get("result", {}).get("layoutParsingResults", [])
            merged_layouts.extend(layouts)

        if "result" not in merged:
            merged["result"] = {}
        merged["result"]["layoutParsingResults"] = merged_layouts

        merged_texts = [merged.get("text", "")]
        for result in all_results[1:]:
            merged_texts.append(result.get("text", ""))
        merged["text"] = "\n\n".join(filter(None, merged_texts))

        return merged

    @staticmethod
    def _get_layouts(raw_json: dict) -> list:
        """从 PaddleOCR JSON 提取 layout 列表，兼容两层嵌套结构。"""
        result = raw_json.get("result", {})
        # 优先：result.result.layoutParsingResults
        inner = result.get("result", {})
        layouts = inner.get("layoutParsingResults", [])
        if layouts:
            return layouts
        # 回退：result.layoutParsingResults
        return result.get("layoutParsingResults", [])

    @staticmethod
    def _extract_markdown(raw_json: dict) -> str:
        layouts = PaddleOCRAdapter._get_layouts(raw_json)
        parts = []
        for layout in layouts:
            md = layout.get("markdown", {}).get("text", "")
            if md:
                parts.append(md)
        return "\n\n".join(parts)
