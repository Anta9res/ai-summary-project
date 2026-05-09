"""
LightRAG Adapter
封装LightRAG的初始化和配置，提供统一的接口
支持多学科知识库隔离和多种检索模式
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import json
import yaml

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from lightrag import LightRAG, QueryParam
from openai import OpenAI


class LightRAGAdapter:
    """
    LightRAG适配器
    封装LightRAG初始化和配置，提供统一接口
    """
    
    def __init__(
        self,
        working_dir: str = "knowledge_bases",
        config_path: Optional[str] = None
    ):
        """
        初始化LightRAG适配器
        
        Args:
            working_dir: 知识库根目录
            config_path: 配置文件路径
        """
        self.working_dir = Path(working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self.config = self._load_config(config_path)
        
        # API配置
        self.api_key = os.getenv('DASHSCOPE_API_KEY') or self.config['model']['api_key']
        self.base_url = self.config['model'].get('base_url', 
            'https://dashscope.aliyuncs.com/compatible-mode/v1')
        self.llm_model = self.config['model'].get('name', 'qwen-long')
        
        # Embedding配置
        self.embedding_model = self.config.get('knowledge_graph', {}).get(
            'embedding_model', {}).get('model', 'text-embedding-v3')
        
        # OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # LightRAG实例缓存（按学科）
        self.rag_instances: Dict[str, LightRAG] = {}
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """加载配置文件"""
        if config_path is None:
            config_path = project_root / "config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _create_llm_func(self) -> Callable:
        """创建LLM函数"""
        async def llm_model_func(
            prompt, system_prompt=None, history_messages=[], **kwargs
        ) -> str:
            """LLM调用函数（通义千问）"""
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.extend(history_messages)
            messages.append({"role": "user", "content": prompt})
            
            # 过滤不兼容的参数
            filtered_kwargs = {
                k: v for k, v in kwargs.items() 
                if k not in ['hashing_kv', 'keyword_extraction', 'function_name']
            }
            
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                **filtered_kwargs
            )
            
            return response.choices[0].message.content
        
        return llm_model_func
    
    def _create_embedding_func(self) -> Callable:
        """创建Embedding函数"""
        async def embedding_func(texts: List[str]) -> List[List[float]]:
            """Embedding函数（通义千问）"""
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            return [item.embedding for item in response.data]
        
        # 添加embedding_dim属性
        embedding_func.embedding_dim = 1024  # text-embedding-v3
        
        return embedding_func
    
    def get_or_create_rag(self, subject_name: str) -> LightRAG:
        """
        获取或创建指定学科的LightRAG实例
        
        Args:
            subject_name: 学科名称
            
        Returns:
            LightRAG实例
        """
        if subject_name in self.rag_instances:
            return self.rag_instances[subject_name]
        
        # 创建学科工作目录
        subject_dir = self.working_dir / subject_name
        subject_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建LightRAG实例
        rag = LightRAG(
            working_dir=str(subject_dir),
            llm_model_func=self._create_llm_func(),
            embedding_func=self._create_embedding_func(),
            llm_model_name=self.llm_model
        )
        
        # 初始化存储
        import asyncio
        async def init_storages():
            await rag.initialize_storages()
            from lightrag.kg.shared_storage import initialize_pipeline_status
            await initialize_pipeline_status()
        
        try:
            asyncio.run(init_storages())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(init_storages())
            loop.close()
        
        # 缓存实例
        self.rag_instances[subject_name] = rag
        
        return rag
    
    def insert(
        self,
        subject_name: str,
        content: str
    ) -> Dict[str, Any]:
        """
        插入内容到知识库
        
        Args:
            subject_name: 学科名称
            content: 要插入的内容
            
        Returns:
            插入结果
        """
        rag = self.get_or_create_rag(subject_name)
        
        import asyncio
        async def insert_async():
            await rag.ainsert(content)
        
        try:
            asyncio.run(insert_async())
            return {"success": True, "subject": subject_name}
        except Exception as e:
            return {"success": False, "subject": subject_name, "error": str(e)}
    
    def query(
        self,
        subject_name: str,
        question: str,
        mode: str = "hybrid",
        only_need_context: bool = False
    ) -> str:
        """
        查询知识库
        
        Args:
            subject_name: 学科名称
            question: 查询问题
            mode: 检索模式 (naive/local/global/hybrid)
            only_need_context: 是否只返回上下文
            
        Returns:
            查询结果
        """
        rag = self.get_or_create_rag(subject_name)
        
        import asyncio
        async def query_async():
            return await rag.aquery(
                question,
                param=QueryParam(mode=mode, only_need_context=only_need_context)
            )
        
        try:
            result = asyncio.run(query_async())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(query_async())
            loop.close()
        
        return result
    
    def list_subjects(self) -> List[str]:
        """
        列出所有学科
        
        Returns:
            学科名称列表
        """
        if not self.working_dir.exists():
            return []
        
        subjects = []
        for item in self.working_dir.iterdir():
            if item.is_dir():
                subjects.append(item.name)
        
        return sorted(subjects)
    
    def get_subject_info(self, subject_name: str) -> Dict[str, Any]:
        """
        获取学科信息
        
        Args:
            subject_name: 学科名称
            
        Returns:
            学科信息
        """
        subject_dir = self.working_dir / subject_name
        
        if not subject_dir.exists():
            return {"exists": False, "subject": subject_name}
        
        # 统计文件
        files = list(subject_dir.glob("*.json")) + list(subject_dir.glob("*.graphml"))
        
        return {
            "exists": True,
            "subject": subject_name,
            "working_dir": str(subject_dir),
            "files_count": len(files),
            "files": [f.name for f in files]
        }
    
    def delete_subject(self, subject_name: str) -> Dict[str, Any]:
        """
        删除学科知识库
        
        Args:
            subject_name: 学科名称
            
        Returns:
            删除结果
        """
        subject_dir = self.working_dir / subject_name
        
        if not subject_dir.exists():
            return {"success": False, "error": "Subject not found"}
        
        # 从缓存中移除
        if subject_name in self.rag_instances:
            del self.rag_instances[subject_name]
        
        # 删除目录
        import shutil
        try:
            shutil.rmtree(subject_dir)
            return {"success": True, "subject": subject_name}
        except Exception as e:
            return {"success": False, "subject": subject_name, "error": str(e)}


def main():
    """测试LightRAG适配器"""
    # 创建适配器
    adapter = LightRAGAdapter(working_dir="knowledge_bases")
    
    # 测试学科列表
    print("=" * 60)
    print("现有学科:")
    subjects = adapter.list_subjects()
    for subject in subjects:
        info = adapter.get_subject_info(subject)
        print(f"  - {subject}: {info['files_count']} files")
    
    # 测试插入和查询
    test_subject = "Fall-Network-AdapterTest"
    print(f"\n测试学科: {test_subject}")
    
    # 插入测试内容
    print("\n插入测试内容...")
    result = adapter.insert(
        test_subject,
        "互联网是指将多个计算机网络互相连接而形成的全球性网络。"
    )
    print(f"插入结果: {result}")
    
    # 查询测试
    print("\n查询测试...")
    answer = adapter.query(test_subject, "什么是互联网?", mode="hybrid")
    print(f"查询结果: {answer[:200]}..." if answer else "无结果")
    
    # 获取学科信息
    info = adapter.get_subject_info(test_subject)
    print(f"\n学科信息: {info}")


if __name__ == "__main__":
    main()
