"""
Knowledge Base Retrieval Tool
知识库检索工具 - 为Function Calling提供检索功能
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from extensions.knowledge_graph.lightrag_adapter import LightRAGAdapter


class KBRetrievalTool:
    """
    Knowledge Base Retrieval Tool
    提供向量检索、图谱检索和混合检索功能
    """
    
    def __init__(self, storage_dir: str = "knowledge_bases"):
        """
        初始化检索工具
        
        Args:
            storage_dir: 知识库存储目录
        """
        self.adapter = LightRAGAdapter(working_dir=storage_dir)
        self.storage_dir = storage_dir
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """
        获取Function Calling工具定义
        
        Returns:
            工具定义（OpenAI Function Calling格式）
        """
        return {
            "type": "function",
            "function": {
                "name": "search_knowledge_base",
                "description": "Search the knowledge base for relevant information about a specific subject. Use this when you need to find detailed information from course notes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query or question"
                        },
                        "subject": {
                            "type": "string",
                            "description": "The subject name (e.g., 'Fall-Network')"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["naive", "local", "global", "hybrid"],
                            "description": "Search mode: naive (simple), local (entity-focused), global (high-level), hybrid (combined)",
                            "default": "hybrid"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (1-10)",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 10
                        }
                    },
                    "required": ["query", "subject"]
                }
            }
        }
    
    def vector_search(
        self,
        query: str,
        subject: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        向量检索（基于语义相似度）
        
        Args:
            query: 查询问题
            subject: 学科名称
            top_k: 返回结果数量
            
        Returns:
            检索结果
        """
        try:
            # 使用naive模式进行纯向量检索
            result = self.adapter.query(
                subject_name=subject,
                question=query,
                mode="naive",
                only_need_context=True
            )
            
            return {
                "success": True,
                "mode": "vector",
                "query": query,
                "subject": subject,
                "result": result if result else "No relevant information found.",
                "top_k": top_k
            }
        except Exception as e:
            return {
                "success": False,
                "mode": "vector",
                "query": query,
                "subject": subject,
                "error": str(e)
            }
    
    def graph_search(
        self,
        query: str,
        subject: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        图谱检索（基于实体关系）
        
        Args:
            query: 查询问题
            subject: 学科名称
            depth: 图谱遍历深度
            
        Returns:
            检索结果
        """
        try:
            # 使用local模式进行图谱检索
            result = self.adapter.query(
                subject_name=subject,
                question=query,
                mode="local",
                only_need_context=False
            )
            
            return {
                "success": True,
                "mode": "graph",
                "query": query,
                "subject": subject,
                "result": result if result else "No relevant information found.",
                "depth": depth
            }
        except Exception as e:
            return {
                "success": False,
                "mode": "graph",
                "query": query,
                "subject": subject,
                "error": str(e)
            }
    
    def hybrid_search(
        self,
        query: str,
        subject: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        混合检索（向量+图谱）
        
        Args:
            query: 查询问题
            subject: 学科名称
            top_k: 返回结果数量
            
        Returns:
            检索结果
        """
        try:
            # 使用hybrid模式进行混合检索
            result = self.adapter.query(
                subject_name=subject,
                question=query,
                mode="hybrid",
                only_need_context=False
            )
            
            return {
                "success": True,
                "mode": "hybrid",
                "query": query,
                "subject": subject,
                "result": result if result else "No relevant information found.",
                "top_k": top_k
            }
        except Exception as e:
            return {
                "success": False,
                "mode": "hybrid",
                "query": query,
                "subject": subject,
                "error": str(e)
            }
    
    def search(
        self,
        query: str,
        subject: str,
        mode: str = "hybrid",
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        通用检索接口
        
        Args:
            query: 查询问题
            subject: 学科名称
            mode: 检索模式 (naive/local/global/hybrid)
            top_k: 返回结果数量
            
        Returns:
            检索结果（格式化后，包含来源引用）
        """
        # 根据模式选择检索方法
        if mode == "naive":
            result = self.vector_search(query, subject, top_k)
        elif mode == "local":
            result = self.graph_search(query, subject)
        elif mode == "global":
            # Global模式用于高层次概览
            try:
                answer = self.adapter.query(
                    subject_name=subject,
                    question=query,
                    mode="global",
                    only_need_context=False
                )
                result = {
                    "success": True,
                    "mode": "global",
                    "query": query,
                    "subject": subject,
                    "result": answer if answer else "No relevant information found."
                }
            except Exception as e:
                result = {
                    "success": False,
                    "mode": "global",
                    "query": query,
                    "subject": subject,
                    "error": str(e)
                }
        else:  # hybrid
            result = self.hybrid_search(query, subject, top_k)
        
        # 格式化结果
        return self._format_result(result)
    
    def _format_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化检索结果，添加来源引用
        
        Args:
            result: 原始检索结果
            
        Returns:
            格式化后的结果
        """
        if not result.get("success"):
            return result
        
        # 添加元数据
        formatted = {
            **result,
            "formatted": True,
            "source": f"Knowledge Base: {result['subject']}",
            "retrieval_mode": result['mode']
        }
        
        # 如果结果是字符串，添加引用标记
        if isinstance(result.get("result"), str):
            formatted["result_with_citation"] = (
                f"{result['result']}\n\n"
                f"[Source: {result['subject']} knowledge base, "
                f"retrieved via {result['mode']} search]"
            )
        
        return formatted
    
    def list_available_subjects(self) -> List[str]:
        """
        列出可用的知识库
        
        Returns:
            学科名称列表
        """
        return self.adapter.list_subjects()
    
    def get_subject_info(self, subject: str) -> Dict[str, Any]:
        """
        获取学科信息
        
        Args:
            subject: 学科名称
            
        Returns:
            学科信息
        """
        return self.adapter.get_subject_info(subject)


def main():
    """测试检索工具"""
    print("=" * 60)
    print("Knowledge Base Retrieval Tool 测试")
    print("=" * 60)
    
    # 创建检索工具
    tool = KBRetrievalTool(storage_dir="knowledge_bases")
    
    # 列出可用知识库
    print("\n可用知识库:")
    subjects = tool.list_available_subjects()
    for subject in subjects:
        info = tool.get_subject_info(subject)
        print(f"  - {subject}: {info.get('files_count', 0)} files")
    
    # 测试Function Calling定义
    print("\n工具定义:")
    tool_def = tool.get_tool_definition()
    print(json.dumps(tool_def, indent=2, ensure_ascii=False))
    
    # 测试检索（如果有Fall-Network-Test知识库）
    test_subject = "Fall-Network-Test"
    if test_subject in subjects:
        print(f"\n测试检索: {test_subject}")
        
        # 测试混合检索
        print("\n【混合检索】")
        result = tool.search(
            query="什么是互联网？",
            subject=test_subject,
            mode="hybrid"
        )
        print(f"成功: {result.get('success')}")
        if result.get('success'):
            print(f"结果: {result.get('result', '')[:200]}...")
        else:
            print(f"错误: {result.get('error')}")
    else:
        print(f"\n测试知识库 '{test_subject}' 不存在，跳过检索测试")


if __name__ == "__main__":
    main()
