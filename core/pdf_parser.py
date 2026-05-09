"""
PDF解析模块
负责批量解析PDF文件,提取内容并保存为Markdown格式
支持断点续传,自动跳过已处理文件
"""
import os
import re
import glob
from pathlib import Path
from typing import Any, List, Dict, Tuple, Optional


MAX_PDF_SIZE_MB = 500


class PDFParser:
    """PDF解析器类"""
    
    def __init__(self, qwen_client_module, api_key: str = ""):
        self.qwen_client = qwen_client_module
        self.api_key = api_key
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'failed_files': []
        }
    
    @staticmethod
    def extract_lecture_number(filename: str) -> float:
        # 优先匹配开头的数字
        match_start = re.match(r'^(\d+)', filename)
        if match_start:
            return float(match_start.group(1))
        # 匹配 "第X讲" 或 "第X-Y讲"
        match = re.match(r'第(\d+)(?:-(\d+))?讲', filename)
        if match:
            major = match.group(1)
            minor = match.group(2)
            if minor:
                return float(f"{major}.{minor}")
            return float(major)
        return 999.0
    
    def find_pdf_files(self, pdf_dir: str) -> List[str]:
        """
        查找目录下所有PDF文件并按讲次排序
        
        Args:
            pdf_dir: PDF文件目录
            
        Returns:
            排序后的PDF文件路径列表
        """
        pdf_pattern = os.path.join(pdf_dir, "*.pdf")
        pdf_files = glob.glob(pdf_pattern)
        pdf_files.sort(key=lambda x: self.extract_lecture_number(os.path.basename(x)))
        return pdf_files
    
    def is_already_processed(self, output_path: str) -> bool:
        """
        检查文件是否已被处理(断点续传检测)
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            True表示已处理,应跳过
        """
        return os.path.exists(output_path)
    
    def parse_single_pdf(self, pdf_path: str, output_path: str, enable_ocr: bool = False, force_ocr: bool = False) -> Tuple[bool, Optional[str]]:
        """
        解析单个PDF文件
        
        Args:
            pdf_path: PDF文件路径
            output_path: 输出文件路径
            enable_ocr: 是否启用OCR预处理
            force_ocr: 是否强制执行OCR
            
        Returns:
            (成功标志, 错误信息)
        """
        try:
            temp_path, saved_path = self.qwen_client.extract_content_from_pdf(
                pdf_path,
                output_path,
                api_key=self.api_key
            )
            
            if temp_path and saved_path:
                return True, None
            else:
                return False, "提取失败,未返回有效路径"
                
        except Exception as e:
            return False, str(e)
    
    def process_all(
        self,
        pdf_dir: str,
        output_dir: str,
        skip_existing: bool = True,
        verbose: bool = True,
        enable_ocr: bool = False,
        force_ocr: bool = False
    ) -> Dict[str, Any]:
        """
        批量处理PDF文件
        
        Args:
            pdf_dir: PDF文件目录
            output_dir: 输出目录
            skip_existing: 是否跳过已存在文件(断点续传)
            verbose: 是否输出详细日志
            enable_ocr: 是否启用OCR预处理
            force_ocr: 是否强制执行OCR
            
        Returns:
            处理结果统计字典
        """
        # 查找PDF文件
        pdf_files = self.find_pdf_files(pdf_dir)
        
        if not pdf_files:
            if verbose:
                print(f"❌ 错误:在目录 {pdf_dir} 中未找到PDF文件")
            return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0, 'failed_files': []}
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 重置统计信息
        self.stats = {
            'total': len(pdf_files),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'failed_files': []
        }
        
        if verbose:
            print(f"找到 {len(pdf_files)} 个PDF文件")
            if enable_ocr:
                print(f"ℹ️  已启用OCR预处理 (OCRmyPDF){' [强制模式]' if force_ocr else ''}")
            print("=" * 60)
        
        # 逐个处理
        for idx, pdf_path in enumerate(pdf_files, 1):
            filename = os.path.basename(pdf_path)
            file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # MB
            
            if verbose:
                print(f"\n[{idx}/{len(pdf_files)}] {filename} ({file_size:.2f}MB)")
            
            # 生成输出文件名
            base_name = Path(filename).stem
            output_filename = f"{base_name}_提取文本.md"
            output_path = os.path.join(output_dir, output_filename)
            
            # 断点续传检测
            if skip_existing and self.is_already_processed(output_path):
                if verbose:
                    print(f"⏭️  跳过(已存在): {output_filename}")
                self.stats['skipped'] += 1
                continue

            # PDF大小检查
            if file_size > MAX_PDF_SIZE_MB:
                if verbose:
                    print(f"❌ 文件过大 ({file_size:.1f}MB > {MAX_PDF_SIZE_MB}MB)，跳过")
                self.stats['failed'] += 1
                self.stats['failed_files'].append(filename)
                continue

            # 解析PDF
            success, error = self.parse_single_pdf(
                pdf_path,
                output_path,
                enable_ocr=enable_ocr,
                force_ocr=force_ocr
            )

            if success:
                self.stats['success'] += 1
            else:
                self.stats['failed'] += 1
                self.stats['failed_files'].append(filename)
                if verbose and error:
                    print(f"❌ 失败: {error}")
        
        return self.stats
    
    def get_summary(self) -> str:
        """
        生成处理结果摘要
        
        Returns:
            格式化的摘要字符串
        """
        success_rate = (self.stats['success'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        
        summary = f"""
{'=' * 60}
PDF解析结果汇总
{'=' * 60}
总文件数: {self.stats['total']}
成功: {self.stats['success']} ✅ | 跳过: {self.stats['skipped']} ⏭️ | 失败: {self.stats['failed']} ❌
成功率: {success_rate:.1f}%
"""
        
        if self.stats['failed_files']:
            summary += "\n失败的文件:\n"
            for filename in self.stats['failed_files']:
                summary += f"  - {filename}\n"
        
        if self.stats['failed'] == 0:
            summary += "\n🎉 所有PDF文件处理完成!"
        else:
            summary += f"\n⚠️  有 {self.stats['failed']} 个文件处理失败"
        
        return summary
