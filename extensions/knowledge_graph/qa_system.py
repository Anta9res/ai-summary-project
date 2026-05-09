"""
QA System
基于知识库的问答系统，支持Function Calling
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from extensions.knowledge_graph.retrieval_tool import KBRetrievalTool
import qwen_client


class QASystem:
    """
    Question Answering System
    基于知识库的智能问答系统
    """
    
    def __init__(
        self,
        storage_dir: str = "knowledge_bases",
        model: str = "qwen-plus",
        api_key: str = ""
    ):
        self.retrieval_tool = KBRetrievalTool(storage_dir=storage_dir)
        self.model = model
        self.api_key = api_key
        
        # 对话历史
        self.conversation_history: List[Dict[str, Any]] = []
        
        # QA对记录
        self.qa_pairs: List[Dict[str, Any]] = []
    
    def ask(
        self,
        question: str,
        subject: str,
        use_tool: bool = True,
        mode: str = "hybrid"
    ) -> Dict[str, Any]:
        """
        提问
        
        Args:
            question: 问题
            subject: 学科名称
            use_tool: 是否使用工具（Function Calling）
            mode: 检索模式
            
        Returns:
            答案及元数据
        """
        print(f"\n{'='*60}")
        print(f"问题: {question}")
        print(f"学科: {subject}")
        print(f"使用工具: {use_tool}")
        print(f"{'='*60}\n")
        
        start_time = datetime.now()
        
        if use_tool:
            # 使用Function Calling
            answer, history, tool_log = self._ask_with_tool(
                question, subject, mode
            )
        else:
            # 直接检索
            answer, history, tool_log = self._ask_direct(
                question, subject, mode
            )
        
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()
        
        # 记录QA对
        qa_record = {
            "timestamp": start_time.isoformat(),
            "question": question,
            "subject": subject,
            "answer": answer,
            "use_tool": use_tool,
            "mode": mode,
            "response_time": response_time,
            "tool_calls": tool_log
        }
        self.qa_pairs.append(qa_record)
        
        # 评估答案质量
        quality = self._evaluate_answer(answer, tool_log)
        
        return {
            "question": question,
            "answer": answer,
            "subject": subject,
            "response_time": response_time,
            "quality_score": quality,
            "tool_calls": tool_log,
            "sources": self._extract_sources(tool_log)
        }
    
    def _ask_with_tool(
        self,
        question: str,
        subject: str,
        mode: str
    ) -> Tuple[str, List, List]:
        """使用Function Calling提问"""
        # 注册工具
        tools = [self.retrieval_tool.get_tool_definition()]
        
        # 工具处理函数
        def search_knowledge_base(**kwargs):
            """知识库检索工具处理函数"""
            return self.retrieval_tool.search(**kwargs)
        
        tool_handlers = {
            "search_knowledge_base": search_knowledge_base
        }
        
        # 系统提示词
        system_prompt = f"""You are a helpful assistant with access to a knowledge base about {subject}.

When answering questions:
1. Use the search_knowledge_base tool to find relevant information
2. Provide accurate answers based on the retrieved information
3. Always cite your sources
4. If information is not in the knowledge base, say so clearly

Be concise and helpful."""
        
        # 调用模型
        try:
            answer, history, tool_log = qwen_client.chat_with_tools(
                question=question,
                tools=tools,
                tool_handlers=tool_handlers,
                api_key=self.api_key,
                system_prompt=system_prompt,
                conversation_history=self.conversation_history,
                model=self.model
            )
            
            return answer, history, tool_log
        except Exception as e:
            error_msg = f"工具调用失败: {str(e)}"
            print(f"[错误] {error_msg}")
            return error_msg, [], []
    
    def _ask_direct(
        self,
        question: str,
        subject: str,
        mode: str
    ) -> Tuple[str, List, List]:
        """直接检索提问"""
        # 直接调用检索工具
        result = self.retrieval_tool.search(
            query=question,
            subject=subject,
            mode=mode
        )
        
        tool_log = [{
            "iteration": 1,
            "tool": "search_knowledge_base",
            "arguments": {"query": question, "subject": subject, "mode": mode},
            "result": result
        }]
        
        if result.get("success"):
            answer = result.get("result", "No answer found.")
            if result.get("result_with_citation"):
                answer = result["result_with_citation"]
        else:
            answer = f"检索失败: {result.get('error', 'Unknown error')}"
        
        return answer, [], tool_log
    
    def batch_ask(
        self,
        questions: List[str],
        subject: str,
        use_tool: bool = True
    ) -> List[Dict[str, Any]]:
        """
        批量提问
        
        Args:
            questions: 问题列表
            subject: 学科名称
            use_tool: 是否使用工具
            
        Returns:
            答案列表
        """
        results = []
        for i, question in enumerate(questions, 1):
            print(f"\n处理问题 {i}/{len(questions)}")
            result = self.ask(question, subject, use_tool)
            results.append(result)
        
        return results
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        获取对话历史
        
        Returns:
            对话历史列表
        """
        return self.conversation_history.copy()
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        print("对话历史已清空")
    
    def export_qa_pairs(self, output_path: str) -> bool:
        """
        导出问答对
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "total_qa_pairs": len(self.qa_pairs),
                    "export_time": datetime.now().isoformat(),
                    "qa_pairs": self.qa_pairs
                }, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 问答对已导出到: {output_path}")
            return True
        except Exception as e:
            print(f"❌ 导出失败: {e}")
            return False
    
    def _evaluate_answer(
        self,
        answer: str,
        tool_log: List[Dict]
    ) -> float:
        """
        评估答案质量
        
        Args:
            answer: 答案文本
            tool_log: 工具调用日志
            
        Returns:
            质量分数 (0-1)
        """
        score = 0.0
        
        # 基础分：有答案
        if answer and len(answer) > 10:
            score += 0.3
        
        # 使用了工具
        if tool_log:
            score += 0.2
            
            # 工具调用成功
            successful_calls = sum(
                1 for log in tool_log
                if log.get("result", {}).get("success", False)
            )
            if successful_calls > 0:
                score += 0.2
        
        # 答案长度合理
        if 50 <= len(answer) <= 2000:
            score += 0.15
        
        # 包含来源引用
        if "source" in answer.lower() or "来源" in answer.lower():
            score += 0.15
        
        return min(score, 1.0)
    
    def _extract_sources(self, tool_log: List[Dict]) -> List[str]:
        """
        从工具日志中提取来源
        
        Args:
            tool_log: 工具调用日志
            
        Returns:
            来源列表
        """
        sources = []
        for log in tool_log:
            result = log.get("result", {})
            if result.get("success"):
                source = result.get("source")
                if source and source not in sources:
                    sources.append(source)
        
        return sources
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息
        """
        if not self.qa_pairs:
            return {
                "total_questions": 0,
                "average_response_time": 0,
                "average_quality_score": 0,
                "tool_usage_rate": 0
            }
        
        total = len(self.qa_pairs)
        avg_time = sum(qa["response_time"] for qa in self.qa_pairs) / total
        
        # 计算平均质量分
        quality_scores = [
            self._evaluate_answer(qa["answer"], qa.get("tool_calls", []))
            for qa in self.qa_pairs
        ]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # 工具使用率
        tool_usage = sum(1 for qa in self.qa_pairs if qa.get("use_tool")) / total
        
        return {
            "total_questions": total,
            "average_response_time": round(avg_time, 2),
            "average_quality_score": round(avg_quality, 2),
            "tool_usage_rate": round(tool_usage, 2)
        }


def main():
    """测试问答系统"""
    print("=" * 60)
    print("QA System 测试")
    print("=" * 60)
    
    # 创建问答系统
    qa = QASystem(storage_dir="knowledge_bases")
    
    # 测试学科
    test_subject = "Fall-Network-Test"
    
    # 检查学科是否存在
    subjects = qa.retrieval_tool.list_available_subjects()
    if test_subject not in subjects:
        print(f"\n测试学科 '{test_subject}' 不存在")
        print("可用学科:", subjects)
        return
    
    # 测试单个问题（使用工具）
    print("\n【测试1：使用Function Calling】")
    result1 = qa.ask(
        question="What is the Internet?",
        subject=test_subject,
        use_tool=True
    )
    print(f"\n答案: {result1['answer'][:200]}...")
    print(f"响应时间: {result1['response_time']:.2f}s")
    print(f"质量分数: {result1['quality_score']:.2f}")
    print(f"来源: {result1['sources']}")
    
    # 测试单个问题（直接检索）
    print("\n【测试2：直接检索】")
    result2 = qa.ask(
        question="What is the Internet?",
        subject=test_subject,
        use_tool=False
    )
    print(f"\n答案: {result2['answer'][:200]}...")
    print(f"响应时间: {result2['response_time']:.2f}s")
    print(f"质量分数: {result2['quality_score']:.2f}")
    
    # 统计信息
    print("\n【统计信息】")
    stats = qa.get_statistics()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 导出QA对
    print("\n【导出问答对】")
    qa.export_qa_pairs("output_v1/qa_test.json")


if __name__ == "__main__":
    main()
