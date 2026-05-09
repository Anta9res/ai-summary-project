"""
OCR + 章节检测 + 拆分工具 v2
将扫描版 PDF 逐页 OCR，按"编→章→节"语义边界拆分为独立文本文件。
"""
import os
import re
import sys
from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
from tqdm import tqdm


# 编/章/节边界正则（宽松匹配，编优先级最高）
STRUCT_PATTERNS = [
    ('编', re.compile(r'第[一二三四五六七八九十百\d]+编\s*[^\n]*')),
    ('章', re.compile(r'第[一二三四五六七八九十百\d]+章\s*[^\n]*')),
    ('节', re.compile(r'第[一二三四五六七八九十百\d]+节\s*[^\n]*')),
]


def ocr_pdf(pdf_path: str, dpi: int = 200) -> str:
    """逐页 OCR，分批释放内存，返回完整文本。"""
    from PyPDF2 import PdfReader
    total_pages = len(PdfReader(pdf_path).pages)
    full_text = []

    batch_size = 10
    for batch_start in range(1, total_pages + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, total_pages)
        pages = convert_from_path(pdf_path, dpi=dpi, first_page=batch_start, last_page=batch_end)
        for i, page in enumerate(pages):
            page_num = batch_start + i
            text = pytesseract.image_to_string(page, lang='chi_sim')
            full_text.append(f"## Page {page_num}\n\n{text.strip()}")
        del pages
    return "\n\n".join(full_text)


def detect_boundaries(text: str) -> list[tuple[int, str, str]]:
    """
    检测所有结构边界，优先级: 编 > 章 > 节。
    返回 [(偏移, 标签类型, 标题文本), ...]，按位置排序。
    """
    all_matches = []
    for level, pattern in STRUCT_PATTERNS:
        for m in pattern.finditer(text):
            all_matches.append((m.start(), level, m.group().strip()))
    all_matches.sort(key=lambda x: x[0])

    # 去重：同一位置只保留最高优先级的
    seen_positions = set()
    deduped = []
    for pos, level, title in all_matches:
        # 允许 50 字符范围内的近似去重
        nearby = [p for p in seen_positions if abs(p - pos) < 50]
        if not nearby:
            deduped.append((pos, level, title))
            seen_positions.add(pos)
    return deduped


def split_by_boundaries(full_text: str, boundaries: list, pdf_name: str, output_dir: str) -> list:
    """按边界拆分文本，写入 output_dir。第一个边界之前的内容作为"前言/总则"。"""
    os.makedirs(output_dir, exist_ok=True)
    files = []

    if not boundaries:
        out_path = os.path.join(output_dir, f"{pdf_name}_全文_提取文本.md")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(f"# PDF文档: {pdf_name}.pdf\n\n{full_text}")
        files.append(out_path)
        return files

    # 第一个边界之前的内容 → 前言
    first_pos = boundaries[0][0]
    if first_pos > 200:  # 有实质性前言内容
        preamble = full_text[:first_pos].strip()
        out_path = os.path.join(output_dir, f"00_前言_总则_提取文本.md")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(f"# PDF文档: {pdf_name}.pdf - 前言/总则\n\n{preamble}")
        files.append(out_path)
        print(f"  ✓ 前言/总则 → {os.path.basename(out_path)} ({len(preamble)} 字符)")

    # 按边界拆分
    for idx, (pos, level, title) in enumerate(boundaries):
        start = pos
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(full_text)
        chunk = full_text[start:end].strip()
        if len(chunk) < 200:
            continue  # 跳过内容过少的片段

        safe_title = re.sub(r'[\\/*?:"<>|\n\r]', '_', title)[:50]
        prefix = f"{idx + 1:02d}_{level}"
        out_path = os.path.join(output_dir, f"{prefix}_{safe_title}_提取文本.md")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(f"# PDF文档: {pdf_name}.pdf - {title}\n\n{chunk}")
        files.append(out_path)
        print(f"  ✓ [{level}] {title} → {os.path.basename(out_path)} ({len(chunk)} 字符)")

    return files


def main():
    if len(sys.argv) < 2:
        print("用法: python ocr_and_split.py <PDF路径> [输出目录]")
        print("示例: python ocr_and_split.py 民法/民法.pdf 民法/raw_texts")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(pdf_path), 'raw_texts')
    pdf_name = Path(pdf_path).stem

    print(f"PDF: {pdf_path}")
    print(f"输出: {output_dir}")

    # 1. OCR (skip if cached)
    cache_path = os.path.join(os.path.dirname(pdf_path), f"{pdf_name}_ocr_full.txt")
    if os.path.exists(cache_path):
        print(f"\n[1/3] 使用缓存的 OCR 结果: {cache_path}")
        with open(cache_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
    else:
        print("\n[1/3] 开始 OCR (可能需要 5-15 分钟)...")
        full_text = ocr_pdf(pdf_path)
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        print(f"  已缓存到: {cache_path}")
    print(f"  提取总字符数: {len(full_text):,}")

    # 2. 检测章节边界
    print("\n[2/3] 检测章节边界...")
    boundaries = detect_boundaries(full_text)
    print(f"  检测到 {len(boundaries)} 个结构标记:")
    for pos, level, title in boundaries:
        print(f"    [{level}] {title} (偏移 {pos})")

    # 3. 拆分
    print(f"\n[3/3] 按边界拆分到 {output_dir}...")
    files = split_by_boundaries(full_text, boundaries, pdf_name, output_dir)
    print(f"\n完成! 共生成 {len(files)} 个文件。")
    print(f"\n下一步运行:")
    print(f'  PYTHONIOENCODING=utf-8 "D:/anaconda3/python.exe" cli.py --input "{output_dir}" --stage generate --output "{os.path.join(os.path.dirname(output_dir), "output")}"')


if __name__ == '__main__':
    main()
