"""
性能测试 - 分析和优化Pipeline性能
"""
import sys
import os
import time
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PerformanceProfiler:
    """性能分析器"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
    
    def start(self, label: str):
        """开始计时"""
        self.start_times[label] = time.time()
    
    def end(self, label: str):
        """结束计时"""
        if label in self.start_times:
            elapsed = time.time() - self.start_times[label]
            if label not in self.metrics:
                self.metrics[label] = []
            self.metrics[label].append(elapsed)
            del self.start_times[label]
            return elapsed
        return None
    
    def get_statistics(self, label: str) -> Dict:
        """获取统计信息"""
        if label not in self.metrics or not self.metrics[label]:
            return {}
        
        times = self.metrics[label]
        return {
            'count': len(times),
            'total': sum(times),
            'avg': sum(times) / len(times),
            'min': min(times),
            'max': max(times)
        }
    
    def report(self):
        """生成报告"""
        print("\n" + "="*60)
        print("📊 性能分析报告")
        print("="*60)
        
        for label in sorted(self.metrics.keys()):
            stats = self.get_statistics(label)
            if stats:
                print(f"\n{label}:")
                print(f"  总计: {stats['total']:.2f}秒")
                print(f"  平均: {stats['avg']:.2f}秒")
                print(f"  最小: {stats['min']:.2f}秒")
                print(f"  最大: {stats['max']:.2f}秒")
                print(f"  次数: {stats['count']}")
        
        print("\n" + "="*60)


def analyze_bottlenecks():
    """分析性能瓶颈"""
    print("\n" + "="*60)
    print("🔍 性能瓶颈分析")
    print("="*60)
    
    bottlenecks = {
        "API调用延迟": {
            "描述": "调用qwen-long API生成笔记",
            "预估时间": "10-30秒/次",
            "优化建议": [
                "1. 使用异步并发调用（需注意API限流）",
                "2. 实现请求队列和重试机制",
                "3. 缓存已处理结果"
            ]
        },
        "PDF解析": {
            "描述": "提取PDF文本内容",
            "预估时间": "2-5秒/PDF",
            "优化建议": [
                "1. 使用多进程并行解析",
                "2. 优化文本提取算法",
                "3. 缓存解析结果"
            ]
        },
        "文件IO": {
            "描述": "读写笔记文件",
            "预估时间": "<1秒",
            "优化建议": [
                "1. 批量写入减少IO次数",
                "2. 使用内存缓冲",
                "3. 异步IO操作"
            ]
        },
        "后处理": {
            "描述": "格式修复和质量检测",
            "预估时间": "<1秒",
            "优化建议": [
                "1. 优化正则表达式",
                "2. 减少重复遍历",
                "3. 并行处理多个文件"
            ]
        }
    }
    
    for name, info in bottlenecks.items():
        print(f"\n🔴 {name}")
        print(f"   描述: {info['描述']}")
        print(f"   预估时间: {info['预估时间']}")
        print(f"   优化建议:")
        for suggestion in info['优化建议']:
            print(f"      {suggestion}")
    
    print("\n" + "="*60)


def estimate_processing_time(num_pdfs: int):
    """估算处理时间"""
    print("\n" + "="*60)
    print("⏱️  处理时间估算")
    print("="*60)
    
    # 各阶段平均时间（秒）
    pdf_parse_time = 3  # PDF解析
    note_generate_time = 20  # 笔记生成（API调用）
    post_process_time = 0.5  # 后处理
    integrate_time = 2  # 整合
    
    total_per_pdf = pdf_parse_time + note_generate_time + post_process_time
    total_time = total_per_pdf * num_pdfs + integrate_time
    
    print(f"\nPDF数量: {num_pdfs}")
    print(f"\n单个PDF处理时间:")
    print(f"  PDF解析: ~{pdf_parse_time}秒")
    print(f"  笔记生成: ~{note_generate_time}秒 (API调用)")
    print(f"  后处理: ~{post_process_time}秒")
    print(f"  小计: ~{total_per_pdf}秒")
    
    print(f"\n总处理时间:")
    print(f"  预估: ~{total_time:.1f}秒 ({total_time/60:.1f}分钟)")
    print(f"  考虑网络波动: ~{total_time*1.2/60:.1f}-{total_time*1.5/60:.1f}分钟")
    
    # 优化后估算
    optimized_time = num_pdfs * 15 + integrate_time  # 假设优化后15秒/PDF
    print(f"\n优化后预估:")
    print(f"  处理时间: ~{optimized_time:.1f}秒 ({optimized_time/60:.1f}分钟)")
    print(f"  提升: ~{(1-optimized_time/total_time)*100:.1f}%")
    
    print("\n" + "="*60)


def optimization_recommendations():
    """优化建议"""
    print("\n" + "="*60)
    print("💡 性能优化建议")
    print("="*60)
    
    recommendations = [
        {
            "优先级": "⭐⭐⭐ 高",
            "方案": "API调用优化",
            "措施": [
                "实现请求队列和并发控制",
                "添加智能重试机制",
                "缓存已生成笔记"
            ],
            "预期提升": "20-30%"
        },
        {
            "优先级": "⭐⭐ 中",
            "方案": "PDF解析并行化",
            "措施": [
                "使用多进程并行解析",
                "预加载PDF内容到内存"
            ],
            "预期提升": "10-15%"
        },
        {
            "优先级": "⭐ 低",
            "方案": "文件IO优化",
            "措施": [
                "批量写入文件",
                "使用异步IO"
            ],
            "预期提升": "5%"
        }
    ]
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['方案']} ({rec['优先级']})")
        print(f"   措施:")
        for measure in rec['措施']:
            print(f"      • {measure}")
        print(f"   预期提升: {rec['预期提升']}")
    
    print("\n" + "="*60)
    print("\n⚠️  注意事项:")
    print("1. 当前瓶颈主要在API调用，优化空间有限")
    print("2. 并行处理需注意API限流和错误处理")
    print("3. 优先保证稳定性，其次考虑性能")
    print("4. 断点续传已是最有效的优化")
    print("\n" + "="*60)


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 性能测试与分析")
    print("="*60)
    
    # 分析瓶颈
    analyze_bottlenecks()
    
    # 估算处理时间
    estimate_processing_time(19)  # 19个PDF
    
    # 优化建议
    optimization_recommendations()
    
    print("\n✅ 性能分析完成\n")


if __name__ == "__main__":
    main()
