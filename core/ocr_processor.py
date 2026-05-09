import os
import sys
import subprocess
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class OCRProcessor:
    """
    处理PDF OCR的封装类
    使用OCRmyPDF为扫描版PDF添加文本层
    """
    
    def __init__(self):
        self._ensure_env_paths()
        self.available = self._check_availability()
        
    def _ensure_env_paths(self):
        """
        尝试将 Tesseract 和 Ghostscript 的常见安装路径添加到 PATH
        解决 Windows 下环境变量未及时生效或配置错误的问题
        """
        # 常见路径列表
        common_paths = [
            r"C:\Program Files\Tesseract-OCR",
            r"C:\Program Files (x86)\Tesseract-OCR",
        ]
        
        # 查找 Ghostscript bin 目录
        gs_base = r"C:\Program Files\gs"
        if os.path.exists(gs_base):
            for item in os.listdir(gs_base):
                bin_path = os.path.join(gs_base, item, "bin")
                if os.path.exists(bin_path):
                    common_paths.append(bin_path)
        
        current_path = os.environ.get('PATH', '')
        updated = False
        
        for path in common_paths:
            if os.path.exists(path) and path.lower() not in current_path.lower():
                logger.info(f"Adding to PATH: {path}")
                os.environ['PATH'] = path + os.pathsep + os.environ['PATH']
                updated = True
                
        if updated:
            logger.info("Environment PATH updated with OCR dependencies.")

    def _check_availability(self) -> bool:
        """检查OCRmyPDF是否可用"""
        try:
            import ocrmypdf
            # 简单验证 tesseract 是否可调用
            subprocess.run(['tesseract', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except (ImportError, FileNotFoundError, subprocess.CalledProcessError):
            logger.warning("OCRmyPDF module not found or external dependencies missing.")
            return False
            
    def process_pdf(self, input_path: str, output_path: str, language: str = 'chi_sim+eng', redo_ocr: bool = False) -> Tuple[bool, str]:
        """
        对PDF进行OCR处理
        
        Args:
            input_path: 输入PDF路径
            output_path: 输出PDF路径
            language: 语言代码 (默认: chi_sim+eng)
            redo_ocr: 是否强制重做OCR (force-ocr)
            
        Returns:
            (是否成功, 信息/错误描述)
        """
        if not self.available:
            return False, "OCRmyPDF library is not installed or dependencies missing."
            
        import ocrmypdf
        
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            logger.info(f"Starting OCR for: {input_path} (Force: {redo_ocr})")
            
            # 构建参数
            # skip_text=True: 如果已有文本则跳过 (默认，除非 redo_ocr=True)
            # force_ocr=True: 强制光栅化并重做OCR (对应 redo_ocr参数)
            
            # 如果 redo_ocr 为 True，则 force_ocr=True, skip_text=False
            # 如果 redo_ocr 为 False，则 force_ocr=False, skip_text=True
            
            result = ocrmypdf.ocr(
                input_file=input_path,
                output_file=output_path,
                language=language,
                skip_text=not redo_ocr,
                force_ocr=redo_ocr,
                progress_bar=False,
                deskew=True,       # 自动纠偏
                jobs=4,            # 并行作业数
                keep_temporary_files=False,
                output_type='pdf',  # 确保输出 PDF
                optimize=0          # 减少优化以避免图像损坏风险
            )
            
            if result == 0:
                 return True, "OCR completed successfully"
            else:
                 return True, "OCR completed successfully"

        except ocrmypdf.exceptions.PriorOcrFoundError:
            logger.info(f"Text layer already exists for: {input_path}")
            import shutil
            try:
                shutil.copy2(input_path, output_path)
                return True, "Text layer already exists (skipped OCR)"
            except Exception as e:
                return False, f"Copy failed: {str(e)}"
                
        except ocrmypdf.exceptions.MissingDependencyError as e:
            return False, f"Missing dependency: {str(e)} (Check Tesseract/Ghostscript)"
            
        except Exception as e:
            logger.error(f"OCR failed for {input_path}: {str(e)}")
            return False, f"OCR failed: {str(e)}"

    def get_installation_guide(self) -> str:
        return """
        OCRmyPDF Installation Requirements for Windows:
        1. Install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
           - Add to PATH
        2. Install Ghostscript: https://ghostscript.com/releases/gsdnld.html
           - Add to PATH
        3. Install Python package: pip install ocrmypdf
        """
