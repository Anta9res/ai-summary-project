"""
统一后处理模块
整合格式修复和质量检测功能
自动检测并修复常见问题,生成质量报告
"""
import re
from typing import Tuple, List, Dict


class PostProcessor:
    """后处理器类 - 格式修复 + 质量检测"""
    
    def __init__(self):
        """初始化后处理器"""
        self.quality_issues = []
    
    def process(self, content: str, file_path: str) -> Tuple[str, bool]:
        """
        处理生成的内容
        
        Args:
            content: 原始内容
            file_path: 文件路径(用于日志)
            
        Returns:
            (处理后的内容, 质量检测通过标志)
        """
        # 步骤1: 格式修复
        content = self.fix_markdown_format(content)
        content = self.remove_code_block_wrapper(content)
        content = self.clean_trailing_markers(content)
        content = self.fix_latex_format(content)  # 🆕 LaTeX格式修复
        
        # 步骤2: 质量检测
        issues = self.quality_check(content, file_path)
        latex_issues = self.check_latex_format(content, file_path)  # 🆕 LaTeX格式检测
        issues.extend(latex_issues)
        
        # 步骤3: 记录问题
        if issues:
            self.quality_issues.extend(issues)
            quality_passed = False
        else:
            quality_passed = True
        
        # 步骤4: 添加质量标记(如果通过)
        if quality_passed:
            content = self.add_quality_marker(content)
        
        return content, quality_passed
    
    def fix_markdown_format(self, content: str) -> str:
        """
        修复基本Markdown格式问题
        
        Args:
            content: 原始内容
            
        Returns:
            修复后的内容
        """
        # 修复连续空行(超过2个连续空行合并为2个)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 修复标题前后空行
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # 检测标题行
            if line.strip().startswith('#'):
                # 确保标题前有空行(除非是第一行)
                if i > 0 and fixed_lines and fixed_lines[-1].strip() != '':
                    fixed_lines.append('')
                fixed_lines.append(line)
                # 确保标题后有空行(除非是最后一行)
                if i < len(lines) - 1 and lines[i+1].strip() != '':
                    fixed_lines.append('')
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def remove_code_block_wrapper(self, content: str) -> str:
        """
        移除错误的```markdown代码块包裹
        
        Args:
            content: 原始内容
            
        Returns:
            修复后的内容
        """
        lines = content.split('\n')
        
        # 查找```markdown开始标记
        markdown_start_idx = -1
        for i, line in enumerate(lines):
            if line.strip() == '```markdown':
                markdown_start_idx = i
                break
        
        # 如果找到开始标记,从后往前找结束标记```
        markdown_end_idx = -1
        if markdown_start_idx != -1:
            for i in range(len(lines) - 1, markdown_start_idx, -1):
                if lines[i].strip() == '```':
                    markdown_end_idx = i
                    break
        
        # 如果找到完整包裹,移除
        if markdown_start_idx != -1 and markdown_end_idx != -1:
            fixed_lines = []
            fixed_lines.extend(lines[:markdown_start_idx])
            fixed_lines.extend(lines[markdown_start_idx+1:markdown_end_idx])
            if markdown_end_idx + 1 < len(lines):
                fixed_lines.extend(lines[markdown_end_idx+1:])
            return '\n'.join(fixed_lines)
        
        return content
    
    def clean_trailing_markers(self, content: str) -> str:
        """
        清理孤立的尾部标记
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        lines = content.split('\n')
        
        # 清理末尾孤立的```
        while len(lines) > 0 and lines[-1].strip() == '```':
            lines = lines[:-1]
        
        # 清理末尾多余空行
        while len(lines) > 0 and lines[-1].strip() == '':
            lines = lines[:-1]
        
        return '\n'.join(lines)
    
    def quality_check(self, content: str, file_path: str) -> List[Dict]:
        """
        质量检测
        
        Args:
            content: 内容
            file_path: 文件路径
            
        Returns:
            问题列表 [{file, issue, severity}, ...]
        """
        issues = []
        
        # 检测1: 基本结构完整性
        if not re.search(r'### ⭐⭐⭐', content):
            issues.append({
                'file': file_path,
                'issue': '缺少核心知识点标记(⭐⭐⭐)',
                'severity': 'warning'
            })
        
        # 检测2: 最小长度要求
        if len(content) < 500:
            issues.append({
                'file': file_path,
                'issue': '内容过短(<500字符),可能不完整',
                'severity': 'error'
            })
        
        # 检测3: 标题结构
        if content.count('##') == 0:
            issues.append({
                'file': file_path,
                'issue': '缺少章节标题(##)',
                'severity': 'error'
            })
        
        # 检测4: 代码块残留
        if '```markdown' in content:
            issues.append({
                'file': file_path,
                'issue': '存在代码块包裹问题',
                'severity': 'error'
            })
        
        # 检测5: 重复段落检测(简单版)
        lines = content.split('\n')
        seen_lines = set()
        duplicate_count = 0
        
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 20:  # 只检测长行
                if stripped in seen_lines:
                    duplicate_count += 1
                else:
                    seen_lines.add(stripped)
        
        if duplicate_count > 3:
            issues.append({
                'file': file_path,
                'issue': f'存在{duplicate_count}处重复内容',
                'severity': 'warning'
            })
        
        # 检测6: 必要标注
        required_markers = ['💡', '🔗']
        for marker in required_markers:
            if marker not in content:
                issues.append({
                    'file': file_path,
                    'issue': f'缺少必要标注: {marker}',
                    'severity': 'warning'
                })
        
        return issues
    
    def add_quality_marker(self, content: str) -> str:
        """
        添加质量通过标记
        
        Args:
            content: 内容
            
        Returns:
            添加标记后的内容
        """
        # 在文档开头添加HTML注释标记
        marker = "<!-- QUALITY_PASSED -->\n"
        
        # 检查是否已有标记
        if "QUALITY_PASSED" in content:
            return content
        
        # 在元数据头部后添加标记
        lines = content.split('\n')
        
        # 找到元数据结束位置(通常是第一个---)
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip() == '---':
                insert_idx = i + 1
                break
        
        # 插入标记
        lines.insert(insert_idx, marker)
        return '\n'.join(lines)
    
    def get_quality_report(self) -> str:
        """
        生成质量报告
        
        Returns:
            格式化的质量报告
        """
        if not self.quality_issues:
            return "\n✅ 质量检测: 所有文件通过检测\n"
        
        # 统计问题
        error_count = len([i for i in self.quality_issues if i['severity'] == 'error'])
        warning_count = len([i for i in self.quality_issues if i['severity'] == 'warning'])
        
        report = f"""
{'='*60}
质量检测报告
{'='*60}
总问题数: {len(self.quality_issues)}
严重问题: {error_count} ❌
警告问题: {warning_count} ⚠️

问题详情:
"""
        
        for issue in self.quality_issues:
            severity_icon = '❌' if issue['severity'] == 'error' else '⚠️'
            report += f"{severity_icon} {issue['file']}\n"
            report += f"   {issue['issue']}\n"
        
        return report
    
    def reset_issues(self):
        """重置问题列表"""
        self.quality_issues = []
    
    def fix_latex_format(self, content: str) -> str:
        """
        自动修复LaTeX公式格式问题
        
        Args:
            content: 原始内容
            
        Returns:
            修复后的内容
        """
        # 修复1: 移除 $$ 后的多余空格
        content = re.sub(r'\$\$\s+\n', '$$\n', content)
        
        # 修复2: 移除公式块内的Markdown引用符号 "> "
        # 匹配 $$\n> 开头的行，移除所有 "> "前缀
        content = re.sub(r'\$\$\n((?:>\s+[^\n]+\n)+)>\s+\$\$', 
                         lambda m: '$$\n' + re.sub(r'^>\s+', '', m.group(1), flags=re.MULTILINE) + '$$', 
                         content)
        
        # 修复3: 确保公式块后有空行（匹配emoji）
        content = re.sub(
            r'\$\$\n(📌|📊|✏️|📝|✅|📄|🔄)', 
            r'$$\n\n\1', 
            content
        )
        
        # 修复4: 确保公式块后紧跟普通文字也有空行
        # 但不要匹配公式块($符号开头)或已经有空行的情况
        content = re.sub(
            r'\$\$\n([^\n$])', 
            r'$$\n\n\1', 
            content
        )
        
        return content
    
    def check_latex_format(self, content: str, file_path: str) -> List[Dict]:
        """
        检测LaTeX公式格式问题
        
        Args:
            content: 内容
            file_path: 文件路径
            
        Returns:
            问题列表
        """
        issues = []
        
        # 检测1: $$ 后有空格（修复后应该不会有，但保留检测）
        if re.search(r'\$\$\s+\n', content):
            issues.append({
                'file': file_path,
                'issue': 'LaTeX公式块末尾有多余空格',
                'severity': 'warning'
            })
        
        # 检测2: 公式块后没有空行（宽松检测）
        # 只检测明显的问题，允许一些边界情况
        problematic_patterns = re.findall(r'\$\$\n(📌|📊|✏️|📝|✅|📄|🔄)', content)
        if problematic_patterns:
            issues.append({
                'file': file_path,
                'issue': f'发现{len(problematic_patterns)}处公式块后缺少空行',
                'severity': 'warning'
            })
        
        return issues
