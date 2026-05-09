"""
统计面板模块
收集并展示处理统计信息
"""
import time
from typing import Dict, List
from datetime import timedelta


class StatisticsPanel:
    """统计面板 - 收集并展示处理统计"""
    
    def __init__(self):
        """初始化统计面板"""
        self.stats = {
            'pdf_parsed': 0,
            'notes_generated': 0,
            'quality_passed': 0,
            'quality_issues': [],
            'total_time': 0,
            'stage_times': {}
        }
        self.stage_start_time = None
    
    def start_stage(self, stage_name: str):
        """开始计时某个阶段"""
        self.stage_start_time = time.time()
        self.current_stage = stage_name
    
    def end_stage(self, stage_name: str):
        """结束某个阶段的计时"""
        if self.stage_start_time:
            elapsed = time.time() - self.stage_start_time
            self.stats['stage_times'][stage_name] = elapsed
            self.stage_start_time = None
    
    def record_pdf_parsed(self, count: int = 1):
        """记录PDF解析数量"""
        self.stats['pdf_parsed'] += count
    
    def record_notes_generated(self, count: int = 1):
        """记录笔记生成数量"""
        self.stats['notes_generated'] += count
    
    def record_quality_passed(self, count: int = 1):
        """记录质量检测通过数量"""
        self.stats['quality_passed'] += count
    
    def add_quality_issue(self, file: str, issue: str, severity: str):
        """添加质量问题"""
        self.stats['quality_issues'].append({
            'file': file,
            'issue': issue,
            'severity': severity
        })
    
    def set_total_time(self, seconds: float):
        """设置总耗时"""
        self.stats['total_time'] = seconds
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """格式化时间"""
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            return f"{seconds/60:.1f}分钟"
        else:
            return f"{seconds/3600:.2f}小时"
    
    def format_issues(self) -> str:
        """格式化问题列表"""
        if not self.stats['quality_issues']:
            return "  无"
        
        lines = []
        for issue in self.stats['quality_issues'][:10]:  # 只显示前10个
            icon = '❌' if issue['severity'] == 'error' else '⚠️'
            lines.append(f"  {icon} {issue['file']}: {issue['issue']}")
        
        if len(self.stats['quality_issues']) > 10:
            lines.append(f"  ... 还有 {len(self.stats['quality_issues']) - 10} 个问题")
        
        return '\n'.join(lines)
    
    def generate_report(self) -> str:
        """生成处理报告"""
        notes_generated = self.stats['notes_generated']
        quality_passed = self.stats['quality_passed']
        pass_rate = (quality_passed / notes_generated * 100) if notes_generated > 0 else 0
        
        report = f"""
╔══════════════════════════════════════════════╗
║         Pipeline执行报告                     ║
╚══════════════════════════════════════════════╝

📊 处理统计:
  • PDF解析: {self.stats['pdf_parsed']}
  • 笔记生成: {notes_generated}
  • 质量检测通过: {quality_passed}/{notes_generated}
  • 通过率: {pass_rate:.1f}%

⏱️  时间统计:
  • 总耗时: {self.format_time(self.stats['total_time'])}
"""
        
        for stage_name, stage_time in self.stats['stage_times'].items():
            report += f"  • {stage_name}: {self.format_time(stage_time)}\n"
        
        report += f"\n⚠️  质量问题:\n{self.format_issues()}\n"
        
        return report
    
    def reset(self):
        """重置统计"""
        self.__init__()
