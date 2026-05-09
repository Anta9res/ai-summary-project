"""
Mindmap Generator
思维导图生成器 - 基于知识图谱生成多格式思维导图
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json
import networkx as nx

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from extensions.mindmap.graph_analyzer import GraphAnalyzer


class MindmapGenerator:
    """
    Mindmap Generator
    生成多种格式的思维导图
    """
    
    def __init__(self):
        """初始化思维导图生成器"""
        self.analyzer = GraphAnalyzer()
    
    def generate_from_graph(
        self,
        graph: nx.Graph,
        format: str = "mermaid",
        title: str = "Knowledge Map",
        max_nodes: int = 50,
        color_scheme: str = "importance"
    ) -> str:
        """
        从图谱生成思维导图
        
        Args:
            graph: NetworkX图对象
            format: 输出格式 (mermaid/markmap/json)
            title: 思维导图标题
            max_nodes: 最大节点数
            color_scheme: 颜色方案 (importance/cluster)
            
        Returns:
            思维导图内容（字符串）
        """
        # 如果节点太多，提取核心节点
        if len(graph.nodes()) > max_nodes:
            core_entities = self.analyzer.identify_core_entities(
                graph, top_n=max_nodes
            )
            core_nodes = [entity for entity, score in core_entities]
            graph = self.analyzer.extract_subgraph(graph, core_nodes, depth=1)
        
        # 构建层级结构
        hierarchy = self.analyzer.build_hierarchy(graph, max_depth=3)
        
        # 根据格式生成
        if format == "mermaid":
            return self._generate_mermaid(hierarchy, title)
        elif format == "markmap":
            return self._generate_markmap(hierarchy, title)
        elif format == "json":
            return json.dumps(hierarchy, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_mermaid(
        self,
        hierarchy: Dict[str, Any],
        title: str
    ) -> str:
        """
        生成Mermaid格式思维导图
        
        Args:
            hierarchy: 层级结构
            title: 标题
            
        Returns:
            Mermaid格式文本
        """
        lines = [
            "```mermaid",
            "mindmap",
            f"  root(({title}))"
        ]
        
        def add_node(node, indent=2):
            name = node["name"].replace("(", "").replace(")", "")
            lines.append("  " * indent + f"{name}")
            for child in node.get("children", []):
                add_node(child, indent + 1)
        
        # 添加根节点的子节点
        for child in hierarchy.get("children", []):
            add_node(child, indent=2)
        
        lines.append("```")
        return "\n".join(lines)
    
    def _generate_markmap(
        self,
        hierarchy: Dict[str, Any],
        title: str
    ) -> str:
        """
        生成Markmap格式思维导图
        
        Args:
            hierarchy: 层级结构
            title: 标题
            
        Returns:
            Markdown格式文本
        """
        lines = [f"# {title}\n"]
        
        def add_node(node, level=2):
            name = node["name"]
            lines.append("#" * level + f" {name}\n")
            for child in node.get("children", []):
                add_node(child, level + 1)
        
        # 添加根节点
        lines.append(f"## {hierarchy['name']}\n")
        
        # 添加子节点
        for child in hierarchy.get("children", []):
            add_node(child, level=3)
        
        return "\n".join(lines)
    
    def generate_chapter_mindmap(
        self,
        graph: nx.Graph,
        chapter_name: str,
        format: str = "mermaid"
    ) -> str:
        """
        生成章节级思维导图
        
        Args:
            graph: NetworkX图对象
            chapter_name: 章节名称
            format: 输出格式
            
        Returns:
            思维导图内容
        """
        return self.generate_from_graph(
            graph,
            format=format,
            title=f"{chapter_name} - Knowledge Map",
            max_nodes=30
        )
    
    def generate_subject_overview(
        self,
        graph: nx.Graph,
        subject_name: str,
        format: str = "mermaid"
    ) -> str:
        """
        生成学科总览思维导图
        
        Args:
            graph: NetworkX图对象
            subject_name: 学科名称
            format: 输出格式
            
        Returns:
            思维导图内容
        """
        # 识别核心主题
        core_entities = self.analyzer.identify_core_entities(graph, top_n=10)
        core_nodes = [entity for entity, score in core_entities]
        
        # 使用核心节点作为根
        hierarchy = self.analyzer.build_hierarchy(
            graph,
            root_entities=core_nodes[:1],
            max_depth=2
        )
        
        if format == "mermaid":
            return self._generate_mermaid(hierarchy, f"{subject_name} Overview")
        elif format == "markmap":
            return self._generate_markmap(hierarchy, f"{subject_name} Overview")
        elif format == "json":
            return json.dumps(hierarchy, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def generate_with_colors(
        self,
        graph: nx.Graph,
        color_by: str = "importance",
        format: str = "mermaid"
    ) -> str:
        """
        生成带颜色编码的思维导图
        
        Args:
            graph: NetworkX图对象
            color_by: 颜色编码方式 (importance/cluster)
            format: 输出格式
            
        Returns:
            思维导图内容
        """
        if color_by == "importance":
            # 按PageRank重要性着色
            pagerank = self.analyzer.calculate_pagerank(graph)
            # 简化：生成基础思维导图（颜色编码在可视化阶段处理）
            return self.generate_from_graph(graph, format=format)
        
        elif color_by == "cluster":
            # 按聚类着色
            clusters = self.analyzer.cluster_entities(graph)
            # 简化：生成基础思维导图
            return self.generate_from_graph(graph, format=format)
        
        else:
            raise ValueError(f"Unknown color_by: {color_by}")
    
    def save_mindmap(
        self,
        content: str,
        output_path: str,
        format: str = "mermaid"
    ) -> bool:
        """
        保存思维导图到文件
        
        Args:
            content: 思维导图内容
            output_path: 输出路径
            format: 格式
            
        Returns:
            是否成功
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 根据格式决定文件扩展名
            if format == "mermaid":
                if not output_path.endswith('.md'):
                    output_path += '.md'
            elif format == "markmap":
                if not output_path.endswith('.md'):
                    output_path += '.md'
            elif format == "json":
                if not output_path.endswith('.json'):
                    output_path += '.json'
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ 思维导图已保存到: {output_path}")
            return True
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return False


def main():
    """测试思维导图生成器"""
    print("=" * 60)
    print("Mindmap Generator 测试")
    print("=" * 60)
    
    # 创建测试图
    G = nx.Graph()
    
    # 网络主题知识图谱
    entities = [
        "Computer Network", "Internet", "Protocol", 
        "TCP", "IP", "HTTP", "DNS", "FTP",
        "Router", "Switch", "Hub",
        "OSI Model", "Application Layer", "Transport Layer",
        "Network Layer", "Data Link Layer", "Physical Layer"
    ]
    
    edges = [
        ("Computer Network", "Internet"),
        ("Computer Network", "Protocol"),
        ("Computer Network", "OSI Model"),
        ("Protocol", "TCP"),
        ("Protocol", "IP"),
        ("Protocol", "HTTP"),
        ("Protocol", "DNS"),
        ("Protocol", "FTP"),
        ("Internet", "Router"),
        ("Internet", "Switch"),
        ("Router", "Network Layer"),
        ("OSI Model", "Application Layer"),
        ("OSI Model", "Transport Layer"),
        ("OSI Model", "Network Layer"),
        ("OSI Model", "Data Link Layer"),
        ("OSI Model", "Physical Layer"),
        ("TCP", "Transport Layer"),
        ("IP", "Network Layer"),
        ("HTTP", "Application Layer"),
    ]
    
    G.add_nodes_from(entities)
    G.add_edges_from(edges)
    
    print(f"\n测试图: {len(G.nodes())} 个节点, {len(G.edges())} 条边\n")
    
    # 创建生成器
    generator = MindmapGenerator()
    
    # 测试1: Mermaid格式
    print("【测试1：Mermaid格式】")
    mermaid_map = generator.generate_from_graph(
        G,
        format="mermaid",
        title="Network Knowledge"
    )
    print(mermaid_map[:300] + "...")
    
    # 测试2: Markmap格式
    print("\n【测试2：Markmap格式】")
    markmap_map = generator.generate_from_graph(
        G,
        format="markmap",
        title="Network Knowledge"
    )
    print(markmap_map[:300] + "...")
    
    # 测试3: JSON格式
    print("\n【测试3：JSON格式】")
    json_map = generator.generate_from_graph(
        G,
        format="json",
        title="Network Knowledge"
    )
    print(json_map[:200] + "...")
    
    # 测试4: 章节级思维导图
    print("\n【测试4：章节级思维导图】")
    chapter_map = generator.generate_chapter_mindmap(
        G,
        chapter_name="Chapter 1: Introduction",
        format="mermaid"
    )
    print(f"生成章节思维导图，长度: {len(chapter_map)} 字符")
    
    # 测试5: 学科总览
    print("\n【测试5：学科总览】")
    overview_map = generator.generate_subject_overview(
        G,
        subject_name="Computer Networks",
        format="markmap"
    )
    print(f"生成学科总览，长度: {len(overview_map)} 字符")
    
    # 测试6: 保存思维导图
    print("\n【测试6：保存思维导图】")
    output_dir = Path("output_v1/mindmaps")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    generator.save_mindmap(
        mermaid_map,
        str(output_dir / "test_network_mermaid"),
        format="mermaid"
    )
    
    generator.save_mindmap(
        markmap_map,
        str(output_dir / "test_network_markmap"),
        format="markmap"
    )
    
    print("\n✅ 所有测试完成！")


if __name__ == "__main__":
    main()
