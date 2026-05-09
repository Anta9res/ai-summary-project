"""
Pipeline主流程编排器
负责协调各个模块完成完整的笔记生成流程
"""
import os
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from core.pdf_parser import PDFParser
from core.note_generator import NoteGenerator
from core.post_processor import PostProcessor
from core.integrator import NoteIntegrator
from utils.statistics import StatisticsPanel


class Pipeline:
    """Pipeline编排器 - 协调完整处理流程"""
    
    def __init__(self, qwen_client_module, config: Optional[Dict] = None):
        """
        初始化Pipeline
        
        Args:
            qwen_client_module: qwen_client模块
            config: 配置字典
        """
        self.qwen_client = qwen_client_module
        self.config = config or {}
        
        # 初始化各模块
        api_key = self.config.get('model', {}).get('api_key', '')
        self.post_processor = PostProcessor()
        self.pdf_parser = PDFParser(qwen_client_module, api_key=api_key)
        self.note_generator = NoteGenerator(qwen_client_module, self.post_processor, api_key=api_key)
        self.integrator = NoteIntegrator(self.post_processor)
        
        # 统计面板
        self.stats = StatisticsPanel()
        
        # Pipeline状态
        self.completed_stages = []
    
    def _infer_subject_name(self, input_dir: str, output_base: str) -> str:
        name = Path(input_dir).name
        if not name or name in ['.', '..']:
            name = Path(output_base).name
        if not name or name in ['output', 'notes']:
            name = "课程"
        return name

    def _run_quality_stage(self, verbose: bool = True) -> int:
        self.stats.start_stage("质量检测")
        quality_issues = len(self.post_processor.quality_issues)
        if verbose:
            if quality_issues == 0:
                print("✅ 所有笔记质量检测通过")
            else:
                print(f"⚠️  发现{quality_issues}个质量问题")
                print(self.post_processor.get_quality_report())
        self.stats.end_stage("质量检测")
        self.completed_stages.append("质量检测")
        return quality_issues

    def _print_banner(self, input_dir: str, output_base: str, subject_name: str,
                      prompt_version: str, skip_existing: bool,
                      enable_ocr: bool, force_ocr: bool):
        print("\n" + "="*60)
        print("🚀 启动Pipeline - 完整处理流程")
        print("="*60)
        print(f"输入目录: {input_dir}")
        print(f"输出目录: {output_base}")
        print(f"学科名称: {subject_name}")
        print(f"提示词版本: {prompt_version}")
        print(f"断点续传: {'开启' if skip_existing else '关闭'}")
        if enable_ocr:
            print(f"OCR预处理: 开启 {'(强制模式)' if force_ocr else ''}")
        print("="*60 + "\n")

    def run_full_pipeline(
        self,
        input_dir: str,
        output_base: str = "output",
        prompt_version: str = "v3.0",
        skip_existing: bool = True,
        verbose: bool = True,
        subject_name: str = None,
        enable_ocr: bool = False,
        force_ocr: bool = False
    ) -> Dict:
        start_time = time.time()
        self.post_processor.reset_issues()

        if subject_name is None:
            subject_name = self._infer_subject_name(input_dir, output_base)

        raw_texts_dir = os.path.join(output_base, "raw_texts")
        notes_dir = os.path.join(output_base, "notes")
        os.makedirs(raw_texts_dir, exist_ok=True)
        os.makedirs(notes_dir, exist_ok=True)

        if verbose:
            self._print_banner(input_dir, output_base, subject_name,
                               prompt_version, skip_existing, enable_ocr, force_ocr)

        try:
            # 阶段1: PDF解析
            if verbose:
                print("\n" + "─"*60 + "\n📄 阶段1/4: PDF内容提取\n" + "─"*60)
            pdf_results = self._run_parse_stage(
                input_dir=input_dir, output_dir=raw_texts_dir,
                skip_existing=skip_existing, verbose=verbose,
                enable_ocr=enable_ocr, force_ocr=force_ocr
            )
            if pdf_results is None:
                pdf_results = {'success': 0, 'total': 0, 'failed': 0, 'skipped': 0, 'failed_files': []}
            self.completed_stages.append("PDF解析")
            if verbose:
                print(f"\n✅ PDF解析完成: {pdf_results['success']}/{pdf_results['total']}")
                if pdf_results['failed'] > 0:
                    print(f"⚠️  警告: {pdf_results['failed']}个文件解析失败")

            # 阶段2: 笔记生成
            if verbose:
                print("\n" + "─"*60 + "\n📝 阶段2/4: 智能笔记生成\n" + "─"*60)
            note_results = self._run_generate_stage(
                pdf_dir=input_dir, output_dir=notes_dir,
                prompt_version=prompt_version, skip_existing=skip_existing, verbose=verbose
            )
            self.completed_stages.append("笔记生成")
            if verbose:
                print(f"\n✅ 笔记生成完成: {note_results['success']}/{note_results['total']}")

            # 阶段3: 质量检测
            if verbose:
                print("\n" + "─"*60 + "\n🔍 阶段3/4: 质量检测\n" + "─"*60)
            quality_issues = self._run_quality_stage(verbose=verbose)

            # 阶段4: 笔记整合
            if verbose:
                print("\n" + "─"*60 + "\n📚 阶段4/4: 笔记整合\n" + "─"*60)
            integrate_results = self._run_integrate_stage(
                notes_dir=notes_dir, output_dir=output_base,
                subject_name=subject_name, verbose=verbose
            )
            self.completed_stages.append("笔记整合")
            if verbose:
                print(f"\n✅ 笔记整合完成")

            elapsed_time = time.time() - start_time
            self.stats.set_total_time(elapsed_time)

            if verbose:
                print("\n" + "="*60)
                print(self.stats.generate_report())
                print("="*60)
                print("\n🎉 Pipeline执行完成!")
                print(f"\n📁 输出目录: {output_base}")
                print(f"   ├── raw_texts/     ({pdf_results['success']} 个文本文件)")
                print(f"   ├── notes/         ({note_results['success']} 个笔记文件)")
                print(f"   ├── 完整复习笔记.md")
                print(f"   ├── 笔记索引.md")
                print(f"   └── notes/README.md\n")

            return {
                'success': True,
                'pdf_parsed': pdf_results['success'],
                'notes_generated': note_results['success'],
                'quality_issues': quality_issues,
                'total_time': elapsed_time,
                'completed_stages': self.completed_stages
            }
        except Exception as e:
            if verbose:
                print(f"\n❌ Pipeline执行失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'completed_stages': self.completed_stages
            }
    
    def run_stage(
        self,
        stage: str,
        **kwargs
    ) -> Dict:
        """
        运行单个阶段
        
        Args:
            stage: 阶段名称(parse/generate/integrate)
            **kwargs: 阶段参数
            
        Returns:
            阶段执行结果
        """
        if stage == "parse":
            return self._run_parse_stage(**kwargs)
        elif stage == "generate":
            return self._run_generate_stage(**kwargs)
        elif stage == "integrate":
            return self._run_integrate_stage(**kwargs)
        else:
            return {'success': False, 'error': f'未知阶段: {stage}'}
    
    def _run_parse_stage(
        self,
        input_dir: str,
        output_dir: str,
        skip_existing: bool = True,
        verbose: bool = True,
        enable_ocr: bool = False,
        force_ocr: bool = False
    ) -> Dict:
        """PDF解析阶段"""
        self.stats.start_stage("PDF解析")
        
        results = self.pdf_parser.process_all(
            pdf_dir=input_dir,
            output_dir=output_dir,
            skip_existing=skip_existing,
            verbose=verbose,
            enable_ocr=enable_ocr,
            force_ocr=force_ocr
        )
        
        self.stats.end_stage("PDF解析")
        self.stats.record_pdf_parsed(results['success'])
        
        return results
    
    def _run_generate_stage(
        self,
        pdf_dir: str,
        output_dir: str,
        prompt_version: str = "v3.0",
        skip_existing: bool = True,
        verbose: bool = True
    ) -> Dict:
        """笔记生成阶段"""
        self.stats.start_stage("笔记生成")
        
        # 尝试推断 raw_texts_dir
        # output_dir 通常是 .../notes
        # raw_texts_dir 通常是 .../raw_texts
        output_base = os.path.dirname(os.path.abspath(output_dir))
        raw_texts_dir = os.path.join(output_base, "raw_texts")
        
        if not os.path.exists(raw_texts_dir):
            raw_texts_dir = None
        
        # 构建PDF列表
        pdf_files = self.pdf_parser.find_pdf_files(pdf_dir)
        pdf_list = []
        for idx, pdf in enumerate(pdf_files, 1):
            filename = os.path.basename(pdf)
            # 尝试从文件名提取讲次，失败则使用序号
            lecture_num = self.pdf_parser.extract_lecture_number(filename)
            if lecture_num >= 999:  # 无法从文件名提取，使用序号
                lecture_num = idx
            pdf_list.append((filename, lecture_num))
        pdf_list.sort(key=lambda x: x[1])
        
        results = self.note_generator.process_batch(
            pdf_list=pdf_list,
            pdf_dir=pdf_dir,
            output_dir=output_dir,
            skip_existing=skip_existing,
            prompt_version=prompt_version,
            verbose=verbose,
            raw_texts_dir=raw_texts_dir
        )
        
        self.stats.end_stage("笔记生成")
        self.stats.record_notes_generated(results['success'])
        
        return results
    
    def _run_integrate_stage(
        self,
        notes_dir: str,
        output_dir: str,
        subject_name: str = None,
        verbose: bool = True
    ) -> Dict:
        """笔记整合阶段"""
        self.stats.start_stage("笔记整合")
        
        results = self.integrator.integrate_all(
            notes_dir=notes_dir,
            output_dir=output_dir,
            subject_name=subject_name,
            verbose=verbose
        )
        
        self.stats.end_stage("笔记整合")
        
        return results
    
    def get_statistics(self) -> str:
        """获取统计报告"""
        return self.stats.generate_report()
