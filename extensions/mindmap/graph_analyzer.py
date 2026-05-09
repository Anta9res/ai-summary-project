"""
Graph Analyzer
图谱分析器 - 从知识图谱中提取核心节点和层级结构
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
import networkx as nx
from collections import defaultdict

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class GraphAnalyzer:
    """
    Graph Analyzer
    分析知识图谱，提取核心实体和层级结构
    """
    
    def __init__(self):
        """初始化图谱分析器"""
        pass
    
    def identify_core_entities(
        self,
        graph: nx.Graph,
        top_n: int = 20,
        method: str = "pagerank"
    ) -> List[Tuple[str, float]]:
        """
        识别核心实体
        
        Args:
            graph: NetworkX图对象
            top_n: 返回前N个核心实体
            method: 识别方法 (pagerank/degree/betweenness)
            
        Returns:
            核心实体列表 [(entity, score), ...]
        """
        if len(graph.nodes()) == 0:
            return []
        
        # 根据方法计算节点重要性
        if method == "pagerank":
            scores = nx.pagerank(graph, alpha=0.85)
        elif method == "degree":
            scores = dict(graph.degree())
            # 归一化
            max_degree = max(scores.values()) if scores else 1
            scores = {k: v / max_degree for k, v in scores.items()}
        elif method == "betweenness":
            scores = nx.betweenness_centrality(graph)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # 排序并返回前N个
        sorted_entities = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        return sorted_entities
    
    def build_hierarchy(
        self,
        graph: nx.Graph,
        root_entities: List[str] = None,
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        构建层级结构
        
        Args:
            graph: NetworkX图对象
            root_entities: 根实体列表（如果为None，自动识别）
            max_depth: 最大深度
            
        Returns:
            层级结构字典
        """
        if len(graph.nodes()) == 0:
            return {"name": "Empty Graph", "children": []}
        
        # 如果没有指定根实体，自动识别核心实体作为根
        if root_entities is None:
            core_entities = self.identify_core_entities(graph, top_n=5)
            root_entities = [entity for entity, score in core_entities]
        
        # 如果图太小或没有根实体，使用第一个节点
        if not root_entities:
            root_entities = [list(graph.nodes())[0]]
        
        # 构建层级树（使用第一个根实体）
        root = root_entities[0]
        hierarchy = self._build_tree_from_node(
            graph, root, max_depth, visited=set()
        )
        
        return hierarchy
    
    def _build_tree_from_node(
        self,
        graph: nx.Graph,
        node: str,
        max_depth: int,
        visited: Set[str],
        current_depth: int = 0
    ) -> Dict[str, Any]:
        """
        从节点构建树结构（递归）
        
        Args:
            graph: NetworkX图对象
            node: 当前节点
            max_depth: 最大深度
            visited: 已访问节点集合
            current_depth: 当前深度
            
        Returns:
            树节点字典
        """
        # 标记为已访问
        visited.add(node)
        
        # 创建节点
        tree_node = {
            "name": node,
            "children": []
        }
        
        # 如果达到最大深度，返回
        if current_depth >= max_depth:
            return tree_node
        
        # 获取邻居节点
        neighbors = list(graph.neighbors(node))
        
        # 递归构建子节点
        for neighbor in neighbors:
            if neighbor not in visited:
                child = self._build_tree_from_node(
                    graph, neighbor, max_depth, visited, current_depth + 1
                )
                tree_node["children"].append(child)
        
        return tree_node
    
    def cluster_entities(
        self,
        graph: nx.Graph,
        method: str = "community"
    ) -> Dict[int, List[str]]:
        """
        实体聚类
        
        Args:
            graph: NetworkX图对象
            method: 聚类方法 (community/connected_components)
            
        Returns:
            聚类结果字典 {cluster_id: [entities]}
        """
        if len(graph.nodes()) == 0:
            return {}
        
        clusters = defaultdict(list)
        
        if method == "community":
            # 使用社区发现算法
            try:
                import networkx.algorithms.community as nx_comm
                communities = nx_comm.greedy_modularity_communities(graph)
                for i, community in enumerate(communities):
                    clusters[i] = list(community)
            except Exception as e:
                print(f"社区发现失败，使用连通分量: {e}")
                # 降级为连通分量
                method = "connected_components"
        
        if method == "connected_components":
            # 使用连通分量
            for i, component in enumerate(nx.connected_components(graph)):
                clusters[i] = list(component)
        
        return dict(clusters)
    
    def calculate_pagerank(
        self,
        graph: nx.Graph,
        alpha: float = 0.85
    ) -> Dict[str, float]:
        """
        计算PageRank重要性
        
        Args:
            graph: NetworkX图对象
            alpha: 阻尼系数
            
        Returns:
            PageRank分数字典
        """
        if len(graph.nodes()) == 0:
            return {}
        
        try:
            pagerank_scores = nx.pagerank(graph, alpha=alpha)
            return pagerank_scores
        except Exception as e:
            print(f"PageRank计算失败: {e}")
            return {}
    
    def get_graph_statistics(self, graph: nx.Graph) -> Dict[str, Any]:
        """
        获取图谱统计信息
        
        Args:
            graph: NetworkX图对象
            
        Returns:
            统计信息字典
        """
        if len(graph.nodes()) == 0:
            return {
                "num_nodes": 0,
                "num_edges": 0,
                "density": 0,
                "num_connected_components": 0,
                "average_degree": 0,
                "diameter": 0
            }
        
        stats = {
            "num_nodes": graph.number_of_nodes(),
            "num_edges": graph.number_of_edges(),
            "density": nx.density(graph),
            "num_connected_components": nx.number_connected_components(graph)
        }
        
        # 平均度数
        degrees = [d for n, d in graph.degree()]
        stats["average_degree"] = sum(degrees) / len(degrees) if degrees else 0
        
        # 直径（仅对连通图计算）
        if nx.is_connected(graph):
            stats["diameter"] = nx.diameter(graph)
        else:
            stats["diameter"] = None
        
        return stats
    
    def extract_subgraph(
        self,
        graph: nx.Graph,
        entities: List[str],
        depth: int = 1
    ) -> nx.Graph:
        """
        提取子图
        
        Args:
            graph: NetworkX图对象
            entities: 中心实体列表
            depth: 提取深度（邻居的邻居...）
            
        Returns:
            子图对象
        """
        # 收集所有相关节点
        nodes_to_include = set(entities)
        
        for _ in range(depth):
            new_nodes = set()
            for node in nodes_to_include:
                if node in graph:
                    new_nodes.update(graph.neighbors(node))
            nodes_to_include.update(new_nodes)
        
        # 创建子图
        subgraph = graph.subgraph(nodes_to_include).copy()
        return subgraph


def main():
    """测试图谱分析器"""
    print("=" * 60)
    print("Graph Analyzer 测试")
    print("=" * 60)
    
    # 创建测试图
    G = nx.Graph()
    
    # 添加节点和边（模拟知识图谱）
    entities = ["Internet", "TCP", "IP", "HTTP", "DNS", "Router", "Switch", 
                "Network", "Protocol", "Data", "Packet", "Server", "Client"]
    
    edges = [
        ("Internet", "Network"),
        ("Internet", "Protocol"),
        ("TCP", "Protocol"),
        ("IP", "Protocol"),
        ("HTTP", "Protocol"),
        ("DNS", "Protocol"),
        ("TCP", "IP"),
        ("HTTP", "TCP"),
        ("Network", "Router"),
        ("Network", "Switch"),
        ("Router", "Packet"),
        ("Server", "HTTP"),
        ("Client", "HTTP"),
        ("Data", "Packet"),
    ]
    
    G.add_nodes_from(entities)
    G.add_edges_from(edges)
    
    print(f"\n测试图: {len(G.nodes())} 个节点, {len(G.edges())} 条边")
    
    # 创建分析器
    analyzer = GraphAnalyzer()
    
    # 测试1: 识别核心实体
    print("\n【测试1：识别核心实体】")
    core_entities = analyzer.identify_core_entities(G, top_n=5)
    print("核心实体 (PageRank):")
    for entity, score in core_entities:
        print(f"  {entity}: {score:.4f}")
    
    # 测试2: 构建层级结构
    print("\n【测试2：构建层级结构】")
    hierarchy = analyzer.build_hierarchy(G, root_entities=["Internet"], max_depth=2)
    
    def print_tree(node, indent=0):
        print("  " * indent + f"- {node['name']}")
        for child in node.get('children', []):
            print_tree(child, indent + 1)
    
    print_tree(hierarchy)
    
    # 测试3: 实体聚类
    print("\n【测试3：实体聚类】")
    clusters = analyzer.cluster_entities(G, method="community")
    print(f"发现 {len(clusters)} 个聚类:")
    for cluster_id, members in clusters.items():
        print(f"  聚类 {cluster_id}: {', '.join(members[:5])}" + 
              (f" (+{len(members)-5} more)" if len(members) > 5 else ""))
    
    # 测试4: PageRank计算
    print("\n【测试4：PageRank计算】")
    pagerank_scores = analyzer.calculate_pagerank(G)
    top_5 = sorted(pagerank_scores.items(), key=lambda x: x[1], reverse=True)[:5]
    print("PageRank Top 5:")
    for entity, score in top_5:
        print(f"  {entity}: {score:.4f}")
    
    # 测试5: 图谱统计
    print("\n【测试5：图谱统计】")
    stats = analyzer.get_graph_statistics(G)
    print("图谱统计:")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    
    # 测试6: 提取子图
    print("\n【测试6：提取子图】")
    subgraph = analyzer.extract_subgraph(G, entities=["HTTP"], depth=2)
    print(f"子图: {len(subgraph.nodes())} 个节点, {len(subgraph.edges())} 条边")
    print(f"节点: {', '.join(list(subgraph.nodes())[:10])}")
    
    print("\n✅ 所有测试完成！")


if __name__ == "__main__":
    main()
