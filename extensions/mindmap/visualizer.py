"""
Mindmap Visualizer
思维导图可视化工具 - 生成静态和交互式可视化
"""

import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Any
import networkx as nx

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from extensions.mindmap.graph_analyzer import GraphAnalyzer


class MindmapVisualizer:
    """
    Mindmap Visualizer
    可视化思维导图
    """
    
    def __init__(self):
        """初始化可视化工具"""
        self.analyzer = GraphAnalyzer()
    
    def render_static(
        self,
        graph: nx.Graph,
        output_path: str,
        title: str = "Knowledge Graph",
        figsize: tuple = (12, 8),
        node_size: int = 1000
    ) -> bool:
        """
        渲染静态图片
        
        Args:
            graph: NetworkX图对象
            output_path: 输出路径
            title: 标题
            figsize: 图片大小
            node_size: 节点大小
            
        Returns:
            是否成功
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')  # 使用非交互式后端
            
            # 创建图形
            fig, ax = plt.subplots(figsize=figsize)
            
            # 计算布局
            pos = nx.spring_layout(graph, k=0.5, iterations=50)
            
            # 计算节点重要性（用于设置节点大小）
            pagerank = self.analyzer.calculate_pagerank(graph)
            if pagerank:
                node_sizes = [pagerank.get(node, 0.01) * 10000 for node in graph.nodes()]
            else:
                node_sizes = [node_size] * len(graph.nodes())
            
            # 绘制图
            nx.draw_networkx_nodes(
                graph, pos,
                node_size=node_sizes,
                node_color='lightblue',
                alpha=0.7,
                ax=ax
            )
            
            nx.draw_networkx_edges(
                graph, pos,
                width=1.0,
                alpha=0.5,
                edge_color='gray',
                ax=ax
            )
            
            nx.draw_networkx_labels(
                graph, pos,
                font_size=8,
                font_family='sans-serif',
                ax=ax
            )
            
            ax.set_title(title, fontsize=16, fontweight='bold')
            ax.axis('off')
            
            # 保存
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"✅ 静态图片已保存到: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 渲染静态图片失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def render_interactive(
        self,
        graph: nx.Graph,
        output_path: str,
        title: str = "Knowledge Graph",
        height: str = "750px",
        width: str = "100%"
    ) -> bool:
        """
        渲染交互式HTML
        
        Args:
            graph: NetworkX图对象
            output_path: 输出路径
            title: 标题
            height: 高度
            width: 宽度
            
        Returns:
            是否成功
        """
        try:
            from pyvis.network import Network
            
            # 创建pyvis网络
            net = Network(
                height=height,
                width=width,
                bgcolor='#ffffff',
                font_color='#000000',
                heading=title
            )
            
            # 设置物理引擎
            net.set_options("""
            {
              "physics": {
                "enabled": true,
                "barnesHut": {
                  "gravitationalConstant": -8000,
                  "centralGravity": 0.3,
                  "springLength": 95,
                  "springConstant": 0.04,
                  "damping": 0.09
                },
                "minVelocity": 0.75
              }
            }
            """)
            
            # 计算节点重要性
            pagerank = self.analyzer.calculate_pagerank(graph)
            
            # 添加节点
            for node in graph.nodes():
                importance = pagerank.get(node, 0.05) if pagerank else 0.05
                # 根据重要性设置节点大小和颜色
                node_size = 10 + importance * 100
                
                # 颜色：重要性高=红色，低=蓝色
                r = int(importance * 255)
                b = int((1 - importance) * 255)
                color = f'#{r:02x}00{b:02x}'
                
                net.add_node(
                    node,
                    label=node,
                    title=f"{node}\nImportance: {importance:.4f}",
                    size=node_size,
                    color=color
                )
            
            # 添加边
            for edge in graph.edges():
                net.add_edge(edge[0], edge[1])
            
            # 保存
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            net.save_graph(str(output_file))
            
            print(f"✅ 交互式HTML已保存到: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 渲染交互式HTML失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def export_pdf(
        self,
        graph: nx.Graph,
        output_path: str,
        title: str = "Knowledge Graph"
    ) -> bool:
        """
        导出为PDF
        
        Args:
            graph: NetworkX图对象
            output_path: 输出路径
            title: 标题
            
        Returns:
            是否成功
        """
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_pdf import PdfPages
            import matplotlib
            matplotlib.use('Agg')
            
            # 创建PDF
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with PdfPages(output_path) as pdf:
                fig, ax = plt.subplots(figsize=(12, 8))
                
                # 计算布局
                pos = nx.spring_layout(graph, k=0.5, iterations=50)
                
                # 计算节点重要性
                pagerank = self.analyzer.calculate_pagerank(graph)
                if pagerank:
                    node_sizes = [pagerank.get(node, 0.01) * 10000 for node in graph.nodes()]
                else:
                    node_sizes = [1000] * len(graph.nodes())
                
                # 绘制
                nx.draw_networkx_nodes(
                    graph, pos,
                    node_size=node_sizes,
                    node_color='lightblue',
                    alpha=0.7,
                    ax=ax
                )
                
                nx.draw_networkx_edges(
                    graph, pos,
                    width=1.0,
                    alpha=0.5,
                    edge_color='gray',
                    ax=ax
                )
                
                nx.draw_networkx_labels(
                    graph, pos,
                    font_size=8,
                    font_family='sans-serif',
                    ax=ax
                )
                
                ax.set_title(title, fontsize=16, fontweight='bold')
                ax.axis('off')
                
                plt.tight_layout()
                pdf.savefig(fig, dpi=150, bbox_inches='tight')
                plt.close()
            
            print(f"✅ PDF已保存到: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 导出PDF失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_clustered_visualization(
        self,
        graph: nx.Graph,
        output_path: str,
        format: str = "html"
    ) -> bool:
        """
        创建聚类可视化
        
        Args:
            graph: NetworkX图对象
            output_path: 输出路径
            format: 格式 (html/png/pdf)
            
        Returns:
            是否成功
        """
        # 进行聚类
        clusters = self.analyzer.cluster_entities(graph)
        
        # 为每个聚类分配颜色
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', 
                  '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788']
        
        node_colors = {}
        for cluster_id, members in clusters.items():
            color = colors[cluster_id % len(colors)]
            for member in members:
                node_colors[member] = color
        
        if format == "html":
            return self._render_clustered_html(graph, output_path, node_colors)
        else:
            return self._render_clustered_static(graph, output_path, node_colors, format)
    
    def _render_clustered_html(
        self,
        graph: nx.Graph,
        output_path: str,
        node_colors: Dict[str, str]
    ) -> bool:
        """渲染聚类HTML"""
        try:
            from pyvis.network import Network
            
            net = Network(height="750px", width="100%", bgcolor='#ffffff')
            
            # 添加节点（带聚类颜色）
            for node in graph.nodes():
                color = node_colors.get(node, '#999999')
                net.add_node(node, label=node, color=color, size=25)
            
            # 添加边
            for edge in graph.edges():
                net.add_edge(edge[0], edge[1])
            
            # 保存
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            net.save_graph(str(output_file))
            
            print(f"✅ 聚类可视化已保存到: {output_path}")
            return True
        except Exception as e:
            print(f"❌ 聚类可视化失败: {e}")
            return False
    
    def _render_clustered_static(
        self,
        graph: nx.Graph,
        output_path: str,
        node_colors: Dict[str, str],
        format: str
    ) -> bool:
        """渲染聚类静态图"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')
            
            fig, ax = plt.subplots(figsize=(12, 8))
            pos = nx.spring_layout(graph, k=0.5, iterations=50)
            
            # 按颜色分组绘制节点
            color_to_nodes = defaultdict(list)
            for node, color in node_colors.items():
                color_to_nodes[color].append(node)
            
            for color, nodes in color_to_nodes.items():
                nx.draw_networkx_nodes(
                    graph, pos,
                    nodelist=nodes,
                    node_color=color,
                    node_size=500,
                    alpha=0.7,
                    ax=ax
                )
            
            nx.draw_networkx_edges(graph, pos, alpha=0.3, ax=ax)
            nx.draw_networkx_labels(graph, pos, font_size=8, ax=ax)
            
            ax.set_title("Clustered Knowledge Graph", fontsize=16, fontweight='bold')
            ax.axis('off')
            
            plt.tight_layout()
            
            if format == "png":
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
            elif format == "pdf":
                from matplotlib.backends.backend_pdf import PdfPages
                with PdfPages(output_path) as pdf:
                    pdf.savefig(fig, dpi=150, bbox_inches='tight')
            
            plt.close()
            print(f"✅ 聚类静态图已保存到: {output_path}")
            return True
        except Exception as e:
            print(f"❌ 聚类静态图失败: {e}")
            return False


def main():
    """测试可视化工具"""
    print("=" * 60)
    print("Mindmap Visualizer 测试")
    print("=" * 60)
    
    # 创建测试图
    G = nx.Graph()
    
    entities = [
        "Internet", "Protocol", "TCP", "IP", "HTTP", "DNS",
        "Router", "Switch", "Network", "OSI Model",
        "Application Layer", "Transport Layer", "Network Layer"
    ]
    
    edges = [
        ("Internet", "Network"),
        ("Internet", "Protocol"),
        ("Protocol", "TCP"),
        ("Protocol", "IP"),
        ("Protocol", "HTTP"),
        ("Protocol", "DNS"),
        ("TCP", "Transport Layer"),
        ("IP", "Network Layer"),
        ("HTTP", "Application Layer"),
        ("Network", "Router"),
        ("Network", "Switch"),
        ("OSI Model", "Application Layer"),
        ("OSI Model", "Transport Layer"),
        ("OSI Model", "Network Layer"),
    ]
    
    G.add_nodes_from(entities)
    G.add_edges_from(edges)
    
    print(f"\n测试图: {len(G.nodes())} 个节点, {len(G.edges())} 条边\n")
    
    # 创建可视化工具
    visualizer = MindmapVisualizer()
    
    # 输出目录
    output_dir = Path("output_v1/mindmaps")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 测试1: 静态PNG图片
    print("【测试1：静态PNG图片】")
    visualizer.render_static(
        G,
        str(output_dir / "test_static.png"),
        title="Network Knowledge Graph"
    )
    
    # 测试2: 交互式HTML
    print("\n【测试2：交互式HTML】")
    visualizer.render_interactive(
        G,
        str(output_dir / "test_interactive.html"),
        title="Network Knowledge Graph (Interactive)"
    )
    
    # 测试3: PDF导出
    print("\n【测试3：PDF导出】")
    visualizer.export_pdf(
        G,
        str(output_dir / "test_export.pdf"),
        title="Network Knowledge Graph"
    )
    
    # 测试4: 聚类可视化
    print("\n【测试4：聚类可视化】")
    visualizer.create_clustered_visualization(
        G,
        str(output_dir / "test_clustered.html"),
        format="html"
    )
    
    print("\n✅ 所有测试完成！")
    print(f"输出目录: {output_dir.absolute()}")


if __name__ == "__main__":
    main()
