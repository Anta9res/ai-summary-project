"""
Knowledge Base Manager
知识库管理器 - 管理多个学科的知识库
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
import shutil

from extensions.knowledge_graph.lightrag_adapter import LightRAGAdapter


class KnowledgeBaseManager:
    """
    Knowledge Base Manager
    管理多个学科的知识库，提供统一的创建、加载、更新接口
    """
    
    def __init__(
        self,
        storage_dir: str = "knowledge_bases",
        config_path: Optional[str] = None
    ):
        """
        初始化知识库管理器
        
        Args:
            storage_dir: 知识库存储根目录
            config_path: 配置文件路径
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_path = config_path
        self.index_file = self.storage_dir / "index.json"
        
        # 加载索引
        self.index = self._load_index()
        
        # LightRAG适配器
        self.adapter = LightRAGAdapter(
            working_dir=str(self.storage_dir),
            config_path=config_path
        )
    
    def _load_index(self) -> Dict[str, Any]:
        """加载知识库索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"knowledge_bases": {}, "last_update": None}
    
    def _save_index(self):
        """保存知识库索引"""
        self.index["last_update"] = datetime.now().isoformat()
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)
    
    def create_kb(
        self,
        subject_name: str,
        description: str = "",
        notes_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建新的知识库
        
        Args:
            subject_name: 学科名称
            description: 学科描述
            notes_dir: 笔记目录（可选，如果提供则自动构建图谱）
            
        Returns:
            创建结果
        """
        # 检查是否已存在
        if subject_name in self.index["knowledge_bases"]:
            return {
                "success": False,
                "error": f"Knowledge base '{subject_name}' already exists"
            }
        
        # 创建学科目录
        subject_dir = self.storage_dir / subject_name
        subject_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建元数据
        metadata = {
            "subject_name": subject_name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "notes_count": 0,
            "entities_count": 0,
            "relations_count": 0,
            "status": "created"
        }
        
        # 保存元数据
        metadata_file = subject_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # 更新索引
        self.index["knowledge_bases"][subject_name] = {
            "path": str(subject_dir),
            "created_at": metadata["created_at"],
            "status": "created"
        }
        self._save_index()
        
        # 如果提供了笔记目录，自动构建图谱
        if notes_dir:
            print(f"开始从笔记构建知识图谱: {notes_dir}")
            build_result = self.update_kb(subject_name, notes_dir)
            return {
                "success": True,
                "subject": subject_name,
                "metadata": metadata,
                "build_result": build_result
            }
        
        return {
            "success": True,
            "subject": subject_name,
            "metadata": metadata
        }
    
    def load_kb(self, subject_name: str) -> Optional[LightRAGAdapter]:
        """
        加载知识库
        
        Args:
            subject_name: 学科名称
            
        Returns:
            LightRAG适配器实例，如果不存在返回None
        """
        if subject_name not in self.index["knowledge_bases"]:
            return None
        
        # 通过适配器获取RAG实例
        return self.adapter
    
    def update_kb(
        self,
        subject_name: str,
        notes_dir: str,
    ) -> Dict[str, Any]:
        """
        更新知识库（从笔记目录）

        Args:
            subject_name: 学科名称
            notes_dir: 笔记目录

        Returns:
            更新结果
        """
        if subject_name not in self.index["knowledge_bases"]:
            return {
                "success": False,
                "error": f"Knowledge base '{subject_name}' not found"
            }
        
        notes_path = Path(notes_dir)
        if not notes_path.exists():
            return {"success": False, "error": f"Notes directory not found: {notes_dir}"}

        note_files = sorted(notes_path.glob("*.md"))
        success_count = 0
        failed_files = []

        for note_file in note_files:
            try:
                with open(note_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                insert_result = self.adapter.insert(subject_name, content)
                if insert_result.get("success"):
                    success_count += 1
                else:
                    failed_files.append(str(note_file))
            except Exception as e:
                failed_files.append(str(note_file))

        result = {
            "success": success_count,
            "failed": len(failed_files),
            "total": len(note_files),
            "failed_files": failed_files,
            "subject": subject_name
        }
        
        # 更新元数据
        metadata = self.get_kb_info(subject_name)
        if metadata:
            metadata["last_update"] = datetime.now().isoformat()
            metadata["notes_count"] = result.get("success", 0)
            metadata["status"] = "ready"
            
            metadata_file = self.storage_dir / subject_name / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # 更新索引
            self.index["knowledge_bases"][subject_name]["status"] = "ready"
            self._save_index()
        
        return result
    
    def delete_kb(self, subject_name: str) -> Dict[str, Any]:
        """
        删除知识库
        
        Args:
            subject_name: 学科名称
            
        Returns:
            删除结果
        """
        if subject_name not in self.index["knowledge_bases"]:
            return {
                "success": False,
                "error": f"Knowledge base '{subject_name}' not found"
            }
        
        # 删除目录
        subject_dir = self.storage_dir / subject_name
        try:
            if subject_dir.exists():
                shutil.rmtree(subject_dir)
            
            # 更新索引
            del self.index["knowledge_bases"][subject_name]
            self._save_index()
            
            # 从适配器缓存中移除
            if subject_name in self.adapter.rag_instances:
                del self.adapter.rag_instances[subject_name]
            
            return {
                "success": True,
                "subject": subject_name
            }
        except Exception as e:
            return {
                "success": False,
                "subject": subject_name,
                "error": str(e)
            }
    
    def list_all_kbs(self) -> List[Dict[str, Any]]:
        """
        列出所有知识库
        
        Returns:
            知识库列表
        """
        result = []
        for subject_name, info in self.index["knowledge_bases"].items():
            kb_info = self.get_kb_info(subject_name)
            if kb_info:
                result.append(kb_info)
        
        return result
    
    def get_kb_info(self, subject_name: str) -> Optional[Dict[str, Any]]:
        """
        获取知识库信息
        
        Args:
            subject_name: 学科名称
            
        Returns:
            知识库信息，不存在返回None
        """
        if subject_name not in self.index["knowledge_bases"]:
            return None
        
        subject_dir = self.storage_dir / subject_name
        metadata_file = subject_dir / "metadata.json"
        
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            metadata.setdefault('num_entities', metadata.get('entities_count', 0))
            metadata.setdefault('num_relations', metadata.get('relations_count', 0))
            metadata.setdefault('num_documents', metadata.get('notes_count', 0))
            return metadata

        # 如果元数据不存在，返回基本信息
        return {
            "subject_name": subject_name,
            "path": str(subject_dir),
            "status": "unknown"
        }
    
    def query_kb(
        self,
        subject_name: str,
        question: str,
        mode: str = "hybrid"
    ) -> Optional[str]:
        """
        查询知识库
        
        Args:
            subject_name: 学科名称
            question: 查询问题
            mode: 检索模式
            
        Returns:
            查询结果，如果失败返回None
        """
        if subject_name not in self.index["knowledge_bases"]:
            return None
        
        try:
            return self.adapter.query(subject_name, question, mode)
        except Exception as e:
            print(f"查询失败: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取全局统计信息
        
        Returns:
            统计信息
        """
        total_kbs = len(self.index["knowledge_bases"])
        ready_kbs = sum(
            1 for info in self.index["knowledge_bases"].values()
            if info.get("status") == "ready"
        )
        
        return {
            "total_knowledge_bases": total_kbs,
            "ready_knowledge_bases": ready_kbs,
            "storage_dir": str(self.storage_dir),
            "last_update": self.index.get("last_update")
        }


def main():
    """测试知识库管理器"""
    manager = KnowledgeBaseManager(storage_dir="knowledge_bases")
    
    print("=" * 60)
    print("Knowledge Base Manager 测试")
    print("=" * 60)
    
    # 列出所有知识库
    print("\n当前知识库:")
    kbs = manager.list_all_kbs()
    for kb in kbs:
        print(f"  - {kb['subject_name']}: {kb.get('status', 'unknown')}")
    
    # 全局统计
    stats = manager.get_statistics()
    print(f"\n全局统计: {stats}")
    
    # 测试创建新知识库
    test_subject = "Test-Subject-Manager"
    print(f"\n测试创建知识库: {test_subject}")
    
    # 先删除如果存在
    if test_subject in manager.index["knowledge_bases"]:
        manager.delete_kb(test_subject)
    
    result = manager.create_kb(
        subject_name=test_subject,
        description="Test knowledge base for manager"
    )
    print(f"创建结果: {result['success']}")
    
    # 获取知识库信息
    info = manager.get_kb_info(test_subject)
    print(f"知识库信息: {info}")
    
    # 删除测试知识库
    print(f"\n删除测试知识库...")
    del_result = manager.delete_kb(test_subject)
    print(f"删除结果: {del_result['success']}")


if __name__ == "__main__":
    main()
