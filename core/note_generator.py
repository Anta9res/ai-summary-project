"""
笔记生成模块
负责使用通义千问qwen-long模型生成结构化复习笔记
支持断点续传,自动跳过已生成文件
"""
import os
import time
from datetime import datetime
from typing import Tuple, Optional, Dict, List

from config.prompts import PromptManager


class NoteGenerator:
    """笔记生成器类"""

    def __init__(self, qwen_client_module, post_processor=None, api_key: str = "",
                 model_config: dict = None):
        self.qwen_client = qwen_client_module
        self.post_processor = post_processor
        self.api_key = api_key
        mc = model_config or {}
        self.model_name = mc.get('name', 'qwen-long')
        self.base_url = mc.get('base_url', '')
        self._use_dashscope = not self.base_url or 'dashscope' in self.base_url
        self.temperature = mc.get('temperature', 0.7)
        self.max_tokens = mc.get('max_tokens', 4096)
        # 推理模型（如 kimi-k2.6）需要更大的 max_tokens，否则推理 token 会挤占输出空间
        if not self._use_dashscope:
            self.max_tokens = mc.get('max_tokens', 8192)
        self.top_p = mc.get('top_p', 1.0)
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'failed_files': []
        }

    def get_prompt(self, version: str = "v3.0") -> tuple:
        """
        获取笔记生成提示词

        Args:
            version: 提示词版本

        Returns:
            (system_prompt, user_prompt) 元组
        """
        return PromptManager.get_prompt(version)
    
    def is_already_processed(self, output_path: str) -> bool:
        """
        检查笔记是否已生成(断点续传检测)
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            True表示已处理,应跳过
        """
        return os.path.exists(output_path)
    
    def generate_single_note(
        self, 
        pdf_path: str, 
        output_path: str,
        lecture_num: Optional[int] = None,
        prompt_version: str = "v3.0",
        verbose: bool = True,
        raw_text_path: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        为单个PDF生成笔记
        
        Args:
            pdf_path: PDF文件路径
            output_path: 输出路径
            lecture_num: 讲次编号
            prompt_version: 提示词版本
            verbose: 是否输出详细日志
            raw_text_path: 预提取的文本文件路径(可选)
            
        Returns:
            (成功标志, 错误信息)
        """
        filename = os.path.basename(pdf_path)
        
        if verbose:
            print(f"\n{'='*60}")
            if lecture_num:
                print(f"生成第{lecture_num}讲笔记")
            print(f"课件: {filename}")
            if raw_text_path and os.path.exists(raw_text_path):
                print(f"使用预提取文本: {os.path.basename(raw_text_path)}")
            print(f"{'='*60}")
        
        # 获取提示词
        system_prompt, user_prompt = self.get_prompt(version=prompt_version)

        # 调用 LLM 处理
        try:
            kwargs = dict(
                api_key=self.api_key,
                model=self.model_name,
                system_prompt=system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
            )
            if self.base_url:
                kwargs['base_url'] = self.base_url

            if self._use_dashscope:
                if raw_text_path and os.path.exists(raw_text_path):
                    success, notes_content, _ = self.qwen_client.process_text_file(
                        raw_text_path, user_prompt, **kwargs
                    )
                else:
                    success, notes_content, _ = self.qwen_client.process_pdf_file(
                        pdf_path, user_prompt, save_path=None, **kwargs
                    )
            else:
                if not (raw_text_path and os.path.exists(raw_text_path)):
                    return False, "非 DashScope 端点需要预提取的文本文件，请先运行 --stage parse"
                print(f"使用直接文本模式 ({self.model_name})")
                success, notes_content, _ = self.qwen_client.process_text_direct(
                    raw_text_path, system_prompt, user_prompt, **kwargs
                )
            
            if not success:
                return False, notes_content
            
            # 添加头部元数据
            header = self._generate_header(filename, lecture_num)
            full_content = header + notes_content
            
            # 后处理(如果有后处理器)
            if self.post_processor:
                full_content, quality_passed = self.post_processor.process(
                    full_content, 
                    output_path
                )
                if verbose and not quality_passed:
                    print("⚠️  质量检测发现问题,已记录")
            
            # 保存笔记
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            # 统计信息
            if verbose:
                line_count = full_content.count('\n')
                char_count = len(full_content)
                print(f"✅ 成功 ({line_count}行, {char_count}字符)")
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def _generate_header(self, filename: str, lecture_num: Optional[int] = None) -> str:
        """
        生成笔记头部元数据
        
        Args:
            filename: 源PDF文件名
            lecture_num: 讲次编号
            
        Returns:
            头部文本
        """
        if lecture_num:
            header = f"# 第{lecture_num}讲复习笔记\n\n"
        else:
            header = "# 复习笔记\n\n"
        
        header += f"**来源课件**: {filename}\n"
        header += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        header += "---\n\n"
        
        return header
    
    def process_batch(
        self,
        pdf_list: List[Tuple[str, int]],
        pdf_dir: str,
        output_dir: str,
        skip_existing: bool = True,
        prompt_version: str = "v3.0",
        verbose: bool = True,
        raw_texts_dir: Optional[str] = None
    ) -> Dict:
        """
        批量生成笔记
        
        Args:
            pdf_list: PDF文件列表 [(文件名, 讲次编号), ...]
            pdf_dir: PDF目录
            output_dir: 输出目录
            skip_existing: 是否跳过已存在文件
            prompt_version: 提示词版本
            verbose: 是否输出详细日志
            raw_texts_dir: 预提取文本目录(可选)
            
        Returns:
            处理结果统计
        """
        # 重置统计
        if self.post_processor:
            self.post_processor.reset_issues()
        self.stats = {
            'total': len(pdf_list),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'failed_files': []
        }
        
        if verbose:
            print(f"\n📚 批量生成笔记: {len(pdf_list)}个文件")
            print("="*60)
        
        # 逐个处理
        for idx, (pdf_filename, lecture_num) in enumerate(pdf_list, 1):
            pdf_path = os.path.join(pdf_dir, pdf_filename)
            # 使用原文件名（去掉.pdf扩展名）+ "_笔记.md"
            base_name = os.path.splitext(pdf_filename)[0]  # 去掉.pdf
            output_filename = f"{base_name}_笔记.md"
            output_path = os.path.join(output_dir, output_filename)
            
            # 查找对应的预提取文本
            raw_text_path = None
            if raw_texts_dir:
                # 匹配 PDFParser 的命名规则: "{base_name}_提取文本.md"
                text_filename = f"{base_name}_提取文本.md"
                candidate_path = os.path.join(raw_texts_dir, text_filename)
                if os.path.exists(candidate_path):
                    raw_text_path = candidate_path
            
            if verbose:
                print(f"\n[{idx}/{len(pdf_list)}] {pdf_filename}")
            
            # 检查PDF是否存在
            if not os.path.exists(pdf_path):
                if verbose:
                    print("❌ PDF不存在")
                self.stats['failed'] += 1
                self.stats['failed_files'].append((lecture_num, "PDF不存在"))
                continue
            
            # 断点续传检测
            if skip_existing and self.is_already_processed(output_path):
                if verbose:
                    print("⏭️  跳过(已存在)")
                self.stats['skipped'] += 1
                continue
            
            # 生成笔记
            success, error = self.generate_single_note(
                pdf_path=pdf_path,
                output_path=output_path,
                lecture_num=lecture_num,
                prompt_version=prompt_version,
                verbose=verbose,
                raw_text_path=raw_text_path
            )
            
            if success:
                self.stats['success'] += 1
            else:
                if verbose:
                    print(f"❌ 失败: {error}")
                self.stats['failed'] += 1
                self.stats['failed_files'].append((lecture_num, error[:100]))
            
            # API频率控制
            if idx < len(pdf_list):
                time.sleep(2)
        
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
笔记生成结果汇总
{'=' * 60}
总文件数: {self.stats['total']}
成功: {self.stats['success']} ✅ | 跳过: {self.stats['skipped']} ⏭️ | 失败: {self.stats['failed']} ❌
成功率: {success_rate:.1f}%
"""
        
        if self.stats['failed_files']:
            summary += "\n失败的文件:\n"
            for lecture_num, error in self.stats['failed_files']:
                summary += f"  - 第{lecture_num}讲: {error}\n"
        
        if self.stats['failed'] == 0:
            summary += "\n🎉 所有笔记生成完成!"
        else:
            summary += f"\n⚠️  有 {self.stats['failed']} 个文件处理失败"
        
        return summary
