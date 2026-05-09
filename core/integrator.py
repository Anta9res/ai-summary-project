"""
笔记整合模块
负责合并单讲笔记,生成完整文档、索引和README
"""
import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict
from collections import defaultdict
from core.pdf_parser import PDFParser


class NoteIntegrator:
    """笔记整合器类"""
    
    def __init__(self, post_processor=None):
        """
        初始化整合器
        
        Args:
            post_processor: 后处理器实例(可选)
        """
        self.post_processor = post_processor
    
    extract_lecture_number = staticmethod(PDFParser.extract_lecture_number)

    @staticmethod
    def remove_metadata_header(content: str) -> str:
        """移除单个笔记的元数据头部"""
        lines = content.split('\n')
        
        # 查找分隔符---的位置
        separator_idx = -1
        for i, line in enumerate(lines):
            if line.strip() == '---':
                separator_idx = i
                break
        
        if separator_idx != -1:
            # 保留标题和---之后的内容
            title_line = lines[0] if lines[0].startswith('#') else ''
            content_after_sep = '\n'.join(lines[separator_idx+1:])
            
            if title_line:
                return f"{title_line}\n\n{content_after_sep}"
            else:
                return content_after_sep
        
        return content
    
    @staticmethod
    def count_importance_marks(content: str) -> Dict[str, int]:
        """统计重要性标记数量"""
        return {
            'core': content.count('⭐⭐⭐'),
            'important': content.count('⭐⭐'),
            'exam': content.count('🎯'),
            'practice': content.count('💻'),
        }
    
    @staticmethod
    def extract_core_topics(content: str) -> List[str]:
        """提取核心主题(⭐⭐⭐标记的前3个知识点)"""
        pattern = r'### ⭐⭐⭐.*?\n\n(.*?)(?=\n### |\Z)'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            # 提取**加粗**的概念名称
            topics = re.findall(r'\*\*([^*]+)\*\*', match.group(1))
            return topics[:3]
        
        return []
    
    def load_notes(self, notes_dir: str) -> List[Tuple[str, str]]:
        """
        加载所有笔记文件
        
        Args:
            notes_dir: 笔记目录路径
            
        Returns:
            [(filename, content), ...]
        """
        notes_path = Path(notes_dir)
        md_files = list(notes_path.glob("*.md"))
        
        # 过滤掉README等特殊文件,只保留笔记文件（以_笔记.md结尾）
        lecture_files = [f for f in md_files if f.name.endswith('_笔记.md')]
        
        # 按讲次编号排序 (自然顺序: 1, 2, 10...)
        sorted_files = sorted(lecture_files, key=lambda f: self.extract_lecture_number(f.name))
        
        # 读取所有笔记
        notes_data = []
        for md_file in sorted_files:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            notes_data.append((md_file.name, content))
        
        return notes_data
    
    def merge_notes(self, notes_data: List[Tuple[str, str]], subject_name: str = "课程") -> str:
        """
        合并所有笔记为完整文档
        
        Args:
            notes_data: [(filename, content), ...]
            subject_name: 学科名称（默认"课程"）
            
        Returns:
            完整笔记内容
        """
        merged_lines = []
        
        # 文档头部
        merged_lines.append("---")
        merged_lines.append(f"title: {subject_name}完整复习笔记")
        merged_lines.append("author: AI生成(基于Qwen-long模型)")
        merged_lines.append(f"source: 课件PDF(共{len(notes_data)}讲)")
        merged_lines.append(f"generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        merged_lines.append(f"total_lectures: {len(notes_data)}")
        
        total_size = sum(len(content) for _, content in notes_data)
        merged_lines.append(f"total_size: {total_size // 1024}KB")
        merged_lines.append("---\n")
        
        # 主标题
        merged_lines.append(f"# {subject_name} - 完整复习笔记\n")
        merged_lines.append("> 本文档整合了所有讲次的复习笔记,包含完整的知识点、公式和思维导图素材。")
        merged_lines.append("> ")
        merged_lines.append("> - ⭐⭐⭐ 标记核心必考知识点")
        merged_lines.append("> - 🎯 标记考试重点")
        merged_lines.append("> - 💻 标记实践应用\n")
        
        # 总目录
        merged_lines.append("## 📚 总目录\n")
        for filename, content in notes_data:
            # 从文件名提取显示标题（去掉_笔记.md后缀）
            display_name = filename.replace('_笔记.md', '')
            
            # 提取主标题
            first_heading = ''
            for line in content.split('\n'):
                if line.startswith('##') and not line.startswith('###'):
                    first_heading = line.lstrip('#').strip()
                    break
            
            if first_heading:
                merged_lines.append(f"- {display_name} - {first_heading}")
        
        merged_lines.append("\n---\n")
        
        # 逐讲追加内容
        for filename, content in notes_data:
            # 从文件名提取显示标题（去掉_笔记.md后缀）
            display_name = filename.replace('_笔记.md', '')
            lecture_num = self.extract_lecture_number(filename)
            
            # 添加分隔符
            merged_lines.append(f"<!-- {display_name} 开始 -->\n")
            
            # 移除元数据头部
            clean_content = self.remove_metadata_header(content)
            
            # 重写标题
            # 查找第一行是否是标题
            lines = clean_content.split('\n')
            if lines and lines[0].startswith('# '):
                # 移除原有标题
                lines = lines[1:]
                clean_content = '\n'.join(lines)
            
            # 生成新标题
            if lecture_num < 999:  # 有有效编号
                if isinstance(lecture_num, float) and lecture_num.is_integer():
                    lecture_num = int(lecture_num)
                new_title = f"# 第{lecture_num}讲 {display_name}"
            else:  # 无编号 (如 梳理)
                new_title = f"# {display_name}"
            
            merged_lines.append(new_title)
            
            # 追加内容
            merged_lines.append(clean_content)
            merged_lines.append(f"\n<!-- {display_name} 结束 -->\n")
            merged_lines.append("---\n")
        
        return '\n'.join(merged_lines)
    
    def generate_index(self, notes_data: List[Tuple[str, str]]) -> str:
        """
        生成笔记索引文档
        
        Args:
            notes_data: [(filename, content), ...]
            
        Returns:
            索引Markdown文本
        """
        index_lines = []
        
        # 文档头部
        index_lines.append("# 复习笔记索引\n")
        index_lines.append("> 快速导航和统计概览\n")
        index_lines.append("---\n")
        
        # 快速导航表格
        index_lines.append("## 📖 快速导航\n")
        index_lines.append("| 笔记名称 | 核心主题 | ⭐⭐⭐ | ⭐⭐ | 🎯 | 文件大小 |")
        index_lines.append("|---------|---------|-------|-----|-----|----------|")
        
        total_stats = defaultdict(int)
        
        for filename, content in notes_data:
            # 从文件名提取显示标题（去掉_笔记.md后缀）
            display_name = filename.replace('_笔记.md', '')
            
            # 提取核心主题
            topics = self.extract_core_topics(content)
            topics_str = '、'.join(topics[:2]) if topics else '-'
            
            # 统计标记
            stats = self.count_importance_marks(content)
            for key, value in stats.items():
                total_stats[key] += value
            
            # 文件大小
            size_kb = len(content) // 1024
            
            # 添加表格行
            index_lines.append(
                f"| {display_name} | {topics_str} | "
                f"{stats['core']} | {stats['important']} | {stats['exam']} | "
                f"{size_kb}KB |"
            )
        
        index_lines.append("")
        
        # 重点分布统计
        index_lines.append("## 📊 重点分布统计\n")
        index_lines.append(f"- ⭐⭐⭐ **核心知识点**: 共计 **{total_stats['core']}** 个")
        index_lines.append(f"- ⭐⭐ **重要知识点**: 共计 **{total_stats['important']}** 个")
        index_lines.append(f"- 🎯 **考试标注**: 共计 **{total_stats['exam']}** 处")
        index_lines.append(f"- 💻 **实践应用**: 共计 **{total_stats['practice']}** 处\n")
        
        # 使用建议
        index_lines.append("## 💡 使用建议\n")
        index_lines.append("1. **快速复习**: 查看上方统计,重点关注⭐⭐⭐和🎯标记内容")
        index_lines.append("2. **章节复习**: 按章节概览定位相关讲次")
        index_lines.append("3. **深入学习**: 阅读单讲笔记文件获取详细内容")
        index_lines.append("4. **考前冲刺**: 重点查看所有🎯考试标注\n")
        
        return '\n'.join(index_lines)
    
    def generate_readme(self, notes_count: int) -> str:
        """
        生成README使用说明
        
        Args:
            notes_count: 笔记文件数量
            
        Returns:
            README Markdown文本
        """
        readme_lines = []
        
        readme_lines.append("# 复习笔记使用说明\n")
        readme_lines.append("本目录包含了完整的课程复习笔记。\n")
        readme_lines.append("## 📁 文件结构\n")
        readme_lines.append("```")
        readme_lines.append("notes/")
        readme_lines.append("├── README.md              (本文档)")
        readme_lines.append(f"├── *_笔记.md              ({notes_count}个单讲笔记)")
        readme_lines.append("├── 完整复习笔记.md         (所有笔记合并)")
        readme_lines.append("└── 笔记索引.md            (快速导航)")
        readme_lines.append("```\n")
        
        readme_lines.append("## 📝 文件说明\n")
        readme_lines.append("- **单讲笔记**: 独立的章节笔记,适合逐章学习")
        readme_lines.append("- **完整笔记**: 包含所有章节的完整版,适合通读和打印")
        readme_lines.append("- **索引**: 提供快速导航和统计信息\n")
        
        readme_lines.append("## ⭐ 标记说明\n")
        readme_lines.append("- ⭐⭐⭐ 核心知识点(必须掌握)")
        readme_lines.append("- ⭐⭐ 重要知识点(需要理解)")
        readme_lines.append("- ⭐ 补充内容(了解即可)")
        readme_lines.append("- 🎯 考试重点")
        readme_lines.append("- 💻 实践应用")
        readme_lines.append("- 💡 重点总结")
        readme_lines.append("- 🔗 知识关联\n")
        
        return '\n'.join(readme_lines)
    
    def integrate_all(
        self, 
        notes_dir: str, 
        output_dir: str,
        subject_name: str = None,
        verbose: bool = True
    ) -> Dict:
        """
        执行完整的整合流程
        
        Args:
            notes_dir: 笔记目录
            output_dir: 输出目录
            subject_name: 学科名称（可选，从目录名自动推断）
            verbose: 是否输出详细日志
            
        Returns:
            处理结果统计
        """
        # 自动推断学科名称
        if subject_name is None:
            from pathlib import Path
            # 从输出目录路径提取学科名称
            subject_name = Path(output_dir).name
            if subject_name in ['output', 'notes']:
                subject_name = Path(output_dir).parent.name
            if not subject_name or subject_name == '.':
                subject_name = "课程"
        
        if verbose:
            print("\n📚 开始笔记整合...")
            print("="*60)
        
        # 加载笔记
        notes_data = self.load_notes(notes_dir)
        
        if verbose:
            print(f"✅ 加载 {len(notes_data)} 个笔记文件")
        
        # 生成完整笔记
        if verbose:
            print("\n生成完整复习笔记...")
        
        merged_content = self.merge_notes(notes_data, subject_name)
        merged_path = os.path.join(output_dir, "完整复习笔记.md")
        
        # 后处理(如果有)
        if self.post_processor:
            merged_content, _ = self.post_processor.process(merged_content, merged_path)
        
        with open(merged_path, 'w', encoding='utf-8') as f:
            f.write(merged_content)
        
        if verbose:
            print(f"✅ {merged_path} ({len(merged_content)//1024}KB)")
        
        # 生成索引
        if verbose:
            print("\n生成笔记索引...")
        
        index_content = self.generate_index(notes_data)
        index_path = os.path.join(output_dir, "笔记索引.md")
        
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        if verbose:
            print(f"✅ {index_path}")
        
        # 生成README
        if verbose:
            print("\n生成README...")
        
        readme_content = self.generate_readme(len(notes_data))
        readme_path = os.path.join(notes_dir, "README.md")
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        if verbose:
            print(f"✅ {readme_path}")
        
        # 返回统计
        stats = {
            'notes_count': len(notes_data),
            'merged_size': len(merged_content),
            'files_generated': 3
        }
        
        if verbose:
            print("\n" + "="*60)
            print("🎉 整合完成!")
            print(f"  • 笔记数量: {stats['notes_count']}")
            print(f"  • 完整笔记大小: {stats['merged_size']//1024}KB")
            print(f"  • 生成文件: {stats['files_generated']}个")
        
        return stats
