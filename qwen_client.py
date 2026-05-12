#!/usr/bin/env python3
"""
阿里云通义千问API客户端库
提供文件上传和基于文件对话的功能接口
"""
import os
import tempfile
import logging
from typing import Optional, Tuple
from unstructured.partition.pdf import partition_pdf
from openai import OpenAI
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

def upload_file(file_path: str, api_key: str, base_url: str = _DEFAULT_BASE_URL) -> Optional[str]:
    if not os.path.exists(file_path):
        print(f"错误：文件不存在 - {file_path}")
        return None

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        
        print(f"正在上传文件: {file_path}")
        
        # 使用OpenAI兼容接口上传文件
        with open(file_path, 'rb') as f:
            file_object = client.files.create(
                file=f,
                purpose="file-extract"
            )
        
        file_id = file_object.id
        print(f"文件上传成功，文件ID: {file_id}")
        
        return file_id
            
    except Exception as e:
        logger.error(f"文件上传异常: {str(e)}")
        return None


def _partition_pdf_robust(pdf_path: str):
    """多策略鲁棒解析：避免单一路径导致 poppler/page count 错误。
    优先 fast（pdfminer，无需poppler），失败后再 hi_res（OCR）。
    """
    last_err = None
    # 1) fast 路径（更快，依赖少）
    try:
        return partition_pdf(
            pdf_path,
            include_metadata=True,
            strategy="fast",
            infer_table_structure=False,
            include_page_breaks=False,
        )
    except Exception as e:
        last_err = e
        logger.warning(f"fast解析失败: {e}")
    # 2) hi_res + OCR 路径（慢，但更强壮）
    try:
        return partition_pdf(
            pdf_path,
            include_metadata=True,
            strategy="hi_res",
            infer_table_structure=False,
            include_page_breaks=False,
            ocr_languages="eng+chi_sim",
        )
    except Exception as e:
        logger.error(f"hi_res解析失败: {e}")
        raise last_err or e


def extract_content_from_pdf(pdf_path: str, save_path: Optional[str] = None,
                              api_key: str = "", base_url: str = _DEFAULT_BASE_URL) -> Tuple[Optional[str], Optional[str]]:
    """
    从PDF文件中提取文本和表格（使用Unstructured.io）并保存到临时文件
    
    Args:
        pdf_path (str): PDF文件路径
        save_path (str, optional): 保存处理后文件的路径
        
    Returns:
        str: 包含提取内容的临时文件路径，失败返回 None
        str: 保存的处理后文件路径(如果指定了save_path)，否则为None
    """
    print(f"检测到PDF文件，正在使用Unstructured提取内容: {pdf_path}")
    try:
        # 使用多策略鲁棒解析
        elements = _partition_pdf_robust(pdf_path)
        
        # 过滤掉PageBreak元素并将内容拼接为Markdown格式
        markdown_content = ""
        
        # 添加文件标题
        markdown_content += f"# PDF文档: {Path(pdf_path).name}\n\n"
        
        # 记录当前页码
        current_page = None
        
        # 遍历所有元素，按类型处理
        for i, el in enumerate(elements):
            # 获取元素所在页码（如果有）
            page_num = None
            if hasattr(el, "metadata"):
                metadata = el.metadata
                if hasattr(metadata, "page_number"):
                    page_num = metadata.page_number
            
            # 如果页码变化，添加页码标记
            if page_num and page_num != current_page:
                current_page = page_num
                markdown_content += f"\n## Page {current_page}\n\n"
            
            # 根据元素类型添加不同的格式
            element_type = el.__class__.__name__
            
            # 跳过PageBreak元素
            if element_type == "PageBreak" or not hasattr(el, "text") or not el.text:
                continue
                
            # 处理标题元素
            elif element_type == "Title":
                markdown_content += f"### {el.text.strip()}\n\n"
                
            # 处理表格元素
            elif element_type == "Table":
                markdown_content += f"**Table:**\n{el.text.strip()}\n\n"
                
            # 处理列表元素
            elif element_type == "ListItem":
                markdown_content += f"- {el.text.strip()}\n"
                
            # 处理其他文本元素
            else:
                markdown_content += f"{el.text.strip()}\n\n"
        
        if not markdown_content.strip():
            logger.warning("PDF文件为空或无法提取任何内容。")
            return None, None

        # 创建一个扩展名为.md的临时文件
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, encoding='utf-8', suffix='.md', prefix='pdf_extract_'
        )
        with temp_file as f:
            f.write(markdown_content)
            temp_file_path = f.name
        
        print(f"内容已提取到临时Markdown文件: {temp_file_path}")
        
        # 如果指定了保存路径，则将内容也保存到该路径
        saved_path = None
        if save_path:
            try:
                # 确保目标目录存在
                os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
                
                # 保存处理后的内容
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                print(f"处理后的内容已保存到: {save_path}")
                saved_path = save_path
            except Exception as e:
                logger.error(f"保存处理后内容失败: {str(e)}")
        
        return temp_file_path, saved_path
            
    except Exception as e:
        logger.error(f"从PDF提取内容时出错: {e}")
        logger.info("已尝试 fast 与 hi_res 两种策略。请检查PDF完整性，或提供可复现样本。")
        return None, None

# 其余对话/流程函数保持不变

def chat_with_file(file_id: str, question: str, api_key: str,
                   base_url: str = _DEFAULT_BASE_URL,
                   model: str = "qwen-long",
                   system_prompt: str = "",
                   temperature: float = 0.7,
                   max_tokens: int = 4096,
                   top_p: float = 1.0) -> Optional[str]:
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        print(f"正在调用模型 {model} ...")

        messages = [
            {
                "role": "system",
                "content": system_prompt + (f"\nfileid://{file_id}" if system_prompt else f"fileid://{file_id}")
            },
            {
                "role": "user",
                "content": question
            }
        ]

        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
        )

        print("API 响应成功")

        if completion.choices and len(completion.choices) > 0:
            answer = completion.choices[0].message.content
            return answer
        else:
            logger.error("响应格式异常：没有找到choices")
            return None

    except Exception as e:
        print(f"对话请求异常: {str(e)}")
        return None


def process_pdf_file(file_path: str, question: str, save_path: Optional[str] = None,
                     api_key: str = "", base_url: str = _DEFAULT_BASE_URL,
                     model: str = "qwen-long", system_prompt: str = "",
                     temperature: float = 0.7, max_tokens: int = 4096,
                     top_p: float = 1.0) -> Tuple[bool, str, Optional[str]]:
    temp_file_path = None
    saved_file_path = None
    try:
        temp_file_path, saved_file_path = extract_content_from_pdf(file_path, save_path,
                                                                    api_key=api_key, base_url=base_url)
        if not temp_file_path:
            return False, "PDF处理失败", None

        file_id = upload_file(temp_file_path, api_key=api_key, base_url=base_url)
        if not file_id:
            return False, "文件上传失败", saved_file_path

        answer = chat_with_file(file_id, question, api_key=api_key, base_url=base_url,
                                model=model, system_prompt=system_prompt,
                                temperature=temperature, max_tokens=max_tokens, top_p=top_p)
        if not answer:
            return False, "模型对话失败", saved_file_path

        return True, answer, saved_file_path

    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                print(f"删除临时文件失败: {e}")


def process_text_file(file_path: str, question: str, api_key: str,
                      base_url: str = _DEFAULT_BASE_URL,
                      model: str = "qwen-long", system_prompt: str = "",
                      temperature: float = 0.7, max_tokens: int = 4096,
                      top_p: float = 1.0) -> Tuple[bool, str, None]:
    try:
        if not os.path.exists(file_path):
            return False, f"文件不存在: {file_path}", None

        file_id = upload_file(file_path, api_key=api_key, base_url=base_url)
        if not file_id:
            return False, "文件上传失败", None

        answer = chat_with_file(file_id, question, api_key=api_key, base_url=base_url,
                                model=model, system_prompt=system_prompt,
                                temperature=temperature, max_tokens=max_tokens, top_p=top_p)
        if not answer:
            return False, "模型对话失败", None

        return True, answer, None

    except Exception as e:
        return False, f"处理文本文件失败: {str(e)}", None


def chat_with_tools(
    question: str,
    tools: list,
    tool_handlers: dict,
    *,
    api_key: str,
    base_url: str = _DEFAULT_BASE_URL,
    system_prompt: str = None,
    conversation_history: list = None,
    model: str = "qwen-plus",
    max_iterations: int = 5
) -> Tuple[str, list, list]:
    import json

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    
    # 初始化消息历史
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # 添加对话历史
    if conversation_history:
        messages.extend(conversation_history)
    
    # 添加用户问题
    messages.append({"role": "user", "content": question})
    
    # 工具调用日志
    tool_calls_log = []
    
    # 迭代调用工具
    for iteration in range(max_iterations):
        print(f"\n[迭代 {iteration + 1}/{max_iterations}] 调用模型...")
        
        try:
            # 调用模型
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            
            assistant_message = response.choices[0].message
            
            # 检查是否需要调用工具
            if assistant_message.tool_calls:
                print(f"模型请求调用 {len(assistant_message.tool_calls)} 个工具")
                
                # 添加助手消息到历史
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })
                
                # 处理每个工具调用
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    print(f"  - 调用工具: {tool_name}")
                    print(f"    参数: {tool_args}")
                    
                    # 调用工具处理函数
                    if tool_name in tool_handlers:
                        try:
                            tool_result = tool_handlers[tool_name](**tool_args)
                            
                            # 记录工具调用
                            tool_calls_log.append({
                                "iteration": iteration + 1,
                                "tool": tool_name,
                                "arguments": tool_args,
                                "result": tool_result
                            })
                            
                            # 将工具结果添加到消息历史
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(tool_result, ensure_ascii=False)
                            })
                            
                            print(f"    工具执行成功")
                            
                        except Exception as e:
                            error_msg = f"工具执行失败: {str(e)}"
                            print(f"    {error_msg}")
                            
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps({"error": error_msg}, ensure_ascii=False)
                            })
                    else:
                        error_msg = f"未找到工具处理函数: {tool_name}"
                        print(f"    {error_msg}")
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps({"error": error_msg}, ensure_ascii=False)
                        })
                
                # 继续下一轮迭代
                continue
            
            # 没有工具调用，返回最终答案
            else:
                print("模型生成最终答案")
                final_answer = assistant_message.content
                messages.append({"role": "assistant", "content": final_answer})
                
                return final_answer, messages, tool_calls_log
        
        except Exception as e:
            error_msg = f"模型调用失败: {str(e)}"
            print(f"[错误] {error_msg}")
            return error_msg, messages, tool_calls_log
    
    # 达到最大迭代次数
    warning_msg = f"达到最大迭代次数 ({max_iterations})，停止工具调用"
    print(f"[警告] {warning_msg}")
    return warning_msg, messages, tool_calls_log


# ── 直接文本对话（非 DashScope 端点） ──

def chat_direct(text_content: str, system_prompt: str, user_prompt: str,
                api_key: str, base_url: str, model: str,
                temperature: float = 0.7, max_tokens: int = 8192,
                top_p: float = 1.0) -> Optional[str]:
    """将文本内容内联发送给 LLM（不使用文件上传机制）"""
    http_client = None
    try:
        proxy_url = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY') or os.environ.get('https_proxy') or os.environ.get('http_proxy')
        if proxy_url:
            import httpx
            http_client = httpx.Client(proxy=proxy_url)

        client = OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)

        full_user = f"{user_prompt}\n\n---\n## 课件内容\n\n{text_content}"

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
        )

        if completion.choices and len(completion.choices) > 0:
            return completion.choices[0].message.content
        else:
            print("错误：响应格式异常，没有找到 choices")
            return None

    except Exception as e:
        print(f"直接对话异常: {str(e)}")
        return None
    finally:
        if http_client:
            http_client.close()


def process_text_direct(text_path: str, system_prompt: str, user_prompt: str,
                        api_key: str, base_url: str, model: str,
                        temperature: float = 0.7, max_tokens: int = 8192,
                        top_p: float = 1.0) -> Tuple[bool, str, None]:
    """读取文本文件内容并直接发送给 LLM"""
    try:
        if not os.path.exists(text_path):
            return False, f"文件不存在: {text_path}", None

        with open(text_path, 'r', encoding='utf-8') as f:
            text_content = f.read()

        if not text_content.strip():
            return False, "文件内容为空", None

        print(f"读取文本: {os.path.basename(text_path)} ({len(text_content)} 字符)")

        answer = chat_direct(
            text_content, system_prompt, user_prompt,
            api_key=api_key, base_url=base_url, model=model,
            temperature=temperature, max_tokens=max_tokens, top_p=top_p,
        )

        if not answer:
            return False, "模型对话失败", None

        return True, answer, None

    except Exception as e:
        return False, f"处理文本文件失败: {str(e)}", None