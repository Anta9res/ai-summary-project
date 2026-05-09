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
from core.paddleocr_adapter import PaddleOCRAdapter
from core.chapter_splitter import ChapterSplitter
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
    
    def _run_paddleocr_stage(
        self,
        pdf_path: str,
        raw_texts_dir: str,
        verbose: bool = True
    ) -> Dict:
        """
        单文件预处理阶段：PaddleOCR 提取 + 按章切割

        1. PaddleOCRAdapter.parse_pdf() → 合并 markdown + ParseResult（缓存到 PDF 所在目录）
        2. ChapterSplitter.run() → 检测章节 + 拆分写入 raw_texts_dir
        3. 返回章节文件列表供 generate 阶段使用
        """
        self.stats.start_stage("PaddleOCR预处理")

        adapter = PaddleOCRAdapter()
        parse_result = adapter.parse_pdf(pdf_path)

        if not parse_result.success:
            self.stats.end_stage("PaddleOCR预处理")
            return {'success': False, 'error': parse_result.error}

        splitter = ChapterSplitter()
        split_result = splitter.run(pdf_path, parse_result.raw_json, raw_texts_dir)

        self.stats.end_stage("PaddleOCR预处理")
        self.completed_stages.append("PaddleOCR预处理")

        if not split_result.success:
            return {'success': False, 'error': split_result.error}

        if verbose and split_result.level == "section":
            print(f"⚠️  未检测到章结构，已降级按节拆分")

        return {
            'success': True,
            'chapter_count': split_result.chapter_count,
            'output_files': split_result.output_files,
            'text_list_override': split_result.text_list_override,
            'level': split_result.level
        }

    def run_single_file_pipeline(
        self,
        input_dir: str,
        output_base: str,
        prompt_version: str = "v3.0",
        split_strategy: str = "paddleocr",
        skip_existing: bool = True,
        verbose: bool = True,
        subject_name: str = None
    ) -> Dict:
        """
        单文件模式:
          [PaddleOCR + 按章切割] → generate(逐章笔记) → integrate(整合)
        """
        start_time = time.time()
        self.post_processor.reset_issues()

        if subject_name is None:
            subject_name = self._infer_subject_name(input_dir, output_base)

        pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
        if not pdf_files:
            return {'success': False, 'error': '输入目录中没有 PDF 文件'}
        pdf_path = os.path.join(input_dir, pdf_files[0])

        raw_texts_dir = os.path.join(output_base, "raw_texts")
        notes_dir = os.path.join(output_base, "notes")
        os.makedirs(raw_texts_dir, exist_ok=True)
        os.makedirs(notes_dir, exist_ok=True)

        if verbose:
            self._print_banner(input_dir, output_base, subject_name,
                               prompt_version, skip_existing, False, False)

        # 阶段1: PaddleOCR + 按章切割
        if verbose:
            print("\n" + "─" * 60 + "\n📄 阶段1/3: PaddleOCR 文档解析 + 章节拆分\n" + "─" * 60)
        ocr_result = self._run_paddleocr_stage(pdf_path, raw_texts_dir, verbose)
        if not ocr_result['success']:
            return {'success': False, 'error': ocr_result['error']}
        if verbose:
            print(f"\n✅ PaddleOCR 完成: 检测到 {ocr_result['chapter_count']} 个章节")

        # 阶段2: 逐章生成笔记
        if verbose:
            print("\n" + "─" * 60 + "\n📝 阶段2/3: 智能笔记生成\n" + "─" * 60)
        note_results = self._run_generate_stage(
            pdf_dir=input_dir,
            output_dir=notes_dir,
            prompt_version=prompt_version,
            skip_existing=skip_existing,
            verbose=verbose,
            text_list_override=ocr_result['text_list_override']
        )
        self.completed_stages.append("笔记生成")
        if verbose:
            print(f"\n✅ 笔记生成完成: {note_results['success']}/{note_results['total']}")

        # 阶段3: 笔记整合（含质量检测）
        if verbose:
            print("\n" + "─" * 60 + "\n📚 阶段3/3: 笔记整合\n" + "─" * 60)
        quality_issues = self._run_quality_stage(verbose=verbose)
        integrate_results = self._run_integrate_stage(
            notes_dir=notes_dir,
            output_dir=output_base,
            subject_name=subject_name,
            verbose=verbose
        )
        self.completed_stages.append("笔记整合")

        elapsed_time = time.time() - start_time
        self.stats.set_total_time(elapsed_time)

        if verbose:
            print("\n" + "=" * 60)
            print(self.stats.generate_report())
            print("=" * 60)
            print(f"\n🎉 单文件Pipeline执行完成!")
            print(f"\n📁 输出目录: {output_base}")
            print(f"   ├── raw_texts/     ({ocr_result['chapter_count']} 个拆分文件)")
            print(f"   ├── notes/         ({note_results['success']} 个笔记文件)")
            print(f"   ├── 完整复习笔记.md")
            print(f"   └── 笔记索引.md\n")

        return {
            'success': True,
            'chapters_detected': ocr_result['chapter_count'],
            'notes_generated': note_results['success'],
            'quality_issues': quality_issues,
            'total_time': elapsed_time
        }

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
        verbose: bool = True,
        text_list_override: Optional[List[Tuple[str, int, str]]] = None
    ) -> Dict:
        """
        笔记生成阶段

        Args:
            text_list_override: 可选，单文件模式下的拆分文本列表。
                [(章节名称, 章序号, raw_text完整路径), ...]
                当提供时，忽略 pdf_dir 的 PDF 列表，直接从此列表驱动。
        """
        self.stats.start_stage("笔记生成")

        if text_list_override:
            results = self._generate_from_text_list(
                text_list_override, output_dir, prompt_version,
                skip_existing, verbose
            )
        else:
            # 原有逻辑：从 pdf_dir 构建 pdf_list
            output_base = os.path.dirname(os.path.abspath(output_dir))
            raw_texts_dir = os.path.join(output_base, "raw_texts")
            if not os.path.exists(raw_texts_dir):
                raw_texts_dir = None

            pdf_files = self.pdf_parser.find_pdf_files(pdf_dir)
            pdf_list = []
            for idx, pdf in enumerate(pdf_files, 1):
                filename = os.path.basename(pdf)
                lecture_num = self.pdf_parser.extract_lecture_number(filename)
                if lecture_num >= 999:
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

    def _generate_from_text_list(
        self,
        text_list: List[Tuple[str, int, str]],
        output_dir: str,
        prompt_version: str,
        skip_existing: bool,
        verbose: bool
    ) -> Dict:
        """从拆分文本文件列表驱动笔记生成（单文件模式）"""
        if self.post_processor:
            self.post_processor.reset_issues()

        stats = {
            'total': len(text_list),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'failed_files': []
        }

        if verbose:
            print(f"\n📚 单文件模式 - 逐章生成笔记: {len(text_list)}个章节")
            print("=" * 60)

        for idx, (chapter_name, chapter_num, text_path) in enumerate(text_list, 1):
            output_filename = f"{idx:02d}_{chapter_name[:30]}_笔记.md"
            output_path = os.path.join(output_dir, output_filename)

            if verbose:
                print(f"\n[{idx}/{len(text_list)}] {chapter_name}")

            if skip_existing and os.path.exists(output_path):
                if verbose:
                    print("⏭️  跳过(已存在)")
                stats['skipped'] += 1
                continue

            if not os.path.exists(text_path):
                if verbose:
                    print(f"❌ 文本文件不存在: {text_path}")
                stats['failed'] += 1
                stats['failed_files'].append((chapter_num, "文本文件不存在"))
                continue

            success, error = self.note_generator.generate_single_note(
                pdf_path=text_path,
                output_path=output_path,
                lecture_num=chapter_num,
                prompt_version=prompt_version,
                verbose=verbose,
                raw_text_path=text_path
            )

            if success:
                stats['success'] += 1
            else:
                if verbose:
                    print(f"❌ 失败: {error}")
                stats['failed'] += 1
                stats['failed_files'].append((chapter_num, (error or "")[:100]))

            if idx < len(text_list):
                time.sleep(2)

        return stats
    
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
