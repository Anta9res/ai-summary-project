"""
Knowledge Graph Builder
基于LightRAG构建知识图谱，从笔记中提取实体和关系
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from lightrag import LightRAG, QueryParam
from openai import OpenAI


class KnowledgeGraphBuilder:
    """
    Knowledge Graph Builder
    从Markdown笔记构建知识图谱
    """
    
    def __init__(
        self,
        working_dir: str,
        subject_name: str,
        api_key: str,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        llm_model: str = "qwen-long",
        embedding_model: str = "text-embedding-v3"
    ):
        """
        初始化知识图谱构建器
        
        Args:
            working_dir: 工作目录（知识库存储路径）
            subject_name: 学科名称（用于命名空间隔离）
            api_key: 通义千问API密钥
            base_url: API基础URL
            llm_model: LLM模型名称
            embedding_model: Embedding模型名称
        """
        self.working_dir = Path(working_dir) / subject_name
        self.subject_name = subject_name
        self.api_key = api_key
        self.base_url = base_url
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        
        # 确保工作目录存在
        self.working_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化OpenAI客户端（兼容通义千问）
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # 初始化LightRAG
        self.rag = None
        self._init_lightrag()
        
        # 统计信息
        self.stats = {
            "total_notes": 0,
            "total_entities": 0,
            "total_relations": 0,
            "processed_files": [],
            "last_update": None
        }
    
    def _init_lightrag(self):
        """初始化LightRAG实例"""
        
        # 定义LLM函数（通义千问）
        async def llm_model_func(
            prompt, system_prompt=None, history_messages=[], **kwargs
        ) -> str:
            """LLM调用函数"""
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.extend(history_messages)
            messages.append({"role": "user", "content": prompt})
            
            # 过滤掉不兼容的参数
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
        
        # 定义Embedding函数（通义千问）
        async def embedding_func(texts: List[str]) -> List[List[float]]:
            """Embedding函数"""
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            return [item.embedding for item in response.data]
        
        # 为embedding函数添加embedding_dim属性
        # text-embedding-v3的维度是1024
        embedding_func.embedding_dim = 1024
        
        # 初始化LightRAG
        self.rag = LightRAG(
            working_dir=str(self.working_dir),
            llm_model_func=llm_model_func,
            embedding_func=embedding_func,
            llm_model_name=self.llm_model
        )
        
        # 初始化存储
        import asyncio
        async def init_storages():
            await self.rag.initialize_storages()
            # 初始化pipeline status
            from lightrag.kg.shared_storage import initialize_pipeline_status
            await initialize_pipeline_status()
        
        try:
            asyncio.run(init_storages())
        except RuntimeError:
            # 如果事件循环已存在
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(init_storages())
            loop.close()
    
    def build_from_notes(
        self,
        notes_dir: str,
        pattern: str = "*.md",
        skip_existing: bool = True
    ) -> Dict[str, Any]:
        """
        从笔记目录构建知识图谱
        
        Args:
            notes_dir: 笔记目录路径
            pattern: 文件匹配模式
            skip_existing: 是否跳过已处理的文件
            
        Returns:
            构建统计信息
        """
        notes_path = Path(notes_dir)
        if not notes_path.exists():
            raise ValueError(f"Notes directory not found: {notes_dir}")
        
        # 查找所有笔记文件
        note_files = sorted(notes_path.glob(pattern))
        
        print(f"\n{'='*60}")
        print(f"开始构建知识图谱: {self.subject_name}")
        print(f"{'='*60}")
        print(f"笔记目录: {notes_dir}")
        print(f"找到笔记: {len(note_files)} 个文件")
        print(f"{'='*60}\n")
        
        success_count = 0
        skipped_count = 0
        failed_files = []
        
        for idx, note_file in enumerate(note_files, 1):
            try:
                # 检查是否已处理
                if skip_existing and str(note_file) in self.stats["processed_files"]:
                    print(f"[{idx}/{len(note_files)}] ⏭️  跳过已处理: {note_file.name}")
                    skipped_count += 1
                    continue
                
                print(f"[{idx}/{len(note_files)}] 📝 处理中: {note_file.name}")
                
                # 添加笔记到知识图谱
                result = self.add_note_incremental(str(note_file))
                
                if result["success"]:
                    success_count += 1
                    print(f"   ✅ 成功 - 提取 {result.get('entities', 0)} 个实体")
                else:
                    failed_files.append(note_file.name)
                    print(f"   ❌ 失败: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                failed_files.append(note_file.name)
                print(f"   ❌ 异常: {e}")
        
        # 更新统计
        self.stats["total_notes"] = success_count + skipped_count
        self.stats["last_update"] = datetime.now().isoformat()
        
        # 保存统计信息
        self._save_stats()
        
        # 返回结果摘要
        summary = {
            "success": success_count,
            "skipped": skipped_count,
            "failed": len(failed_files),
            "total": len(note_files),
            "failed_files": failed_files,
            "subject": self.subject_name,
            "working_dir": str(self.working_dir)
        }
        
        print(f"\n{'='*60}")
        print(f"构建完成")
        print(f"{'='*60}")
        print(f"成功: {success_count} | 跳过: {skipped_count} | 失败: {len(failed_files)}")
        print(f"{'='*60}\n")
        
        return summary
    
    def add_note_incremental(self, note_path: str) -> Dict[str, Any]:
        """
        增量添加单个笔记到知识图谱
        
        Args:
            note_path: 笔记文件路径
            
        Returns:
            处理结果
        """
        try:
            # 读取笔记内容
            with open(note_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 过滤掉元数据头部
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    content = parts[2].strip()
            
            # 检查内容长度
            if len(content) < 100:
                return {
                    "success": False,
                    "error": "Content too short"
                }
            
            # 插入到LightRAG
            import asyncio
            
            async def insert_async():
                await self.rag.ainsert(content)
            
            # 运行异步插入
            try:
                asyncio.run(insert_async())
            except RuntimeError:
                # 如果事件循环已存在
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(insert_async())
                loop.close()
            
            # 记录已处理文件
            self.stats["processed_files"].append(note_path)
            
            return {
                "success": True,
                "file": note_path,
                "entities": "N/A"  # LightRAG不直接返回提取的实体数量
            }
            
        except Exception as e:
            return {
                "success": False,
                "file": note_path,
                "error": str(e)
            }
    
    def query(
        self,
        question: str,
        mode: str = "hybrid",
        only_need_context: bool = False
    ) -> str:
        """
        查询知识图谱
        
        Args:
            question: 查询问题
            mode: 检索模式 (naive/local/global/hybrid)
            only_need_context: 是否只返回上下文
            
        Returns:
            查询结果
        """
        import asyncio
        
        async def query_async():
            return await self.rag.aquery(
                question,
                param=QueryParam(mode=mode, only_need_context=only_need_context)
            )
        
        try:
            result = asyncio.run(query_async())
        except RuntimeError:
            # 如果事件循环已存在
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(query_async())
            loop.close()
        
        return result
    
    def export_graph(self, format: str = 'json') -> Dict[str, Any]:
        """
        导出知识图谱数据
        
        Args:
            format: 导出格式 (json)
            
        Returns:
            图谱数据
        """
        if format == 'json':
            # 导出统计和元数据
            return {
                "subject": self.subject_name,
                "stats": self.stats,
                "working_dir": str(self.working_dir),
                "export_time": datetime.now().isoformat()
            }
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取知识图谱统计信息
        
        Returns:
            统计信息
        """
        return {
            "subject": self.subject_name,
            "total_notes": self.stats["total_notes"],
            "processed_files": len(self.stats["processed_files"]),
            "last_update": self.stats["last_update"],
            "working_dir": str(self.working_dir)
        }
    
    def _save_stats(self):
        """保存统计信息到文件"""
        stats_file = self.working_dir / "stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
    
    def _load_stats(self):
        """从文件加载统计信息"""
        stats_file = self.working_dir / "stats.json"
        if stats_file.exists():
            with open(stats_file, 'r', encoding='utf-8') as f:
                self.stats = json.load(f)


def main():
    """测试知识图谱构建器"""
    import yaml
    
    # 加载配置
    config_path = project_root / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    api_key = os.getenv('DASHSCOPE_API_KEY') or config['model']['api_key']
    
    # 创建构建器
    builder = KnowledgeGraphBuilder(
        working_dir="knowledge_bases",
        subject_name="Fall-Network-Test",
        api_key=api_key
    )
    
    # 测试单个笔记
    test_note = project_root / "output_v1" / "notes" / "第1讲_笔记_v2.md"
    if test_note.exists():
        print("测试单个笔记...")
        result = builder.add_note_incremental(str(test_note))
        print(f"结果: {result}")
        
        # 测试查询
        print("\n测试查询...")
        answer = builder.query("什么是互联网?")
        print(f"回答: {answer[:200]}...")
        
        # 获取统计
        stats = builder.get_statistics()
        print(f"\n统计信息: {stats}")
    else:
        print(f"测试文件不存在: {test_note}")


if __name__ == "__main__":
    main()
