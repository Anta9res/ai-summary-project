"""
命令行接口(CLI)
提供友好的命令行交互方式
"""
import argparse
import sys
import os
import re
import networkx as nx

# 依赖检查 - 提供友好的错误提示
def check_dependencies():
    """检查必需的依赖包是否已安装"""
    missing = []
    try:
        import openai
    except ImportError:
        missing.append('openai>=1.0.0')
    
    try:
        from unstructured.partition.pdf import partition_pdf
    except ImportError:
        missing.append('unstructured>=0.10.0')
    
    try:
        import pdfminer
    except ImportError:
        missing.append('pdfminer.six>=20221105')
        
    try:
        import ocrmypdf
    except ImportError:
        pass # Optional dependency, don't fail, just warn if used
    
    if missing:
        print("\n" + "="*60)
        print("❌ 缺少必需的Python依赖包！")
        print("="*60)
        print("\n缺少的包:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\n请执行以下命令安装依赖：\n")
        print("  方法1（推荐）: pip install -r requirements.txt")
        print("  方法2（Windows）: 双击运行 install_dependencies.bat")
        print("  方法3（检查）: python check_dependencies.py")
        print("\n" + "="*60 + "\n")
        sys.exit(1)

import qwen_client
from core.pipeline import Pipeline
from config.config_manager import ConfigManager
from utils.logger import get_logger


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog='fall-network-notes',
        description='Fall-Network课程笔记生成Pipeline',
        epilog='示例: python cli.py --input 课件/ --output output/'
    )
    
    # 基本参数
    parser.add_argument(
        '--input', '-i',
        type=str,
        required=False,
        help='输入目录(包含PDF课件文件或笔记文件)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='output',
        help='输出基础目录(默认: output)'
    )
    
    # Pipeline控制
    parser.add_argument(
        '--stage',
        type=str,
        choices=['all', 'parse', 'generate', 'integrate'],
        default='all',
        help='执行阶段: all(全部)/parse(解析)/generate(生成)/integrate(整合)'
    )
    
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        default=True,
        help='跳过已存在的文件(断点续传,默认开启)'
    )
    
    parser.add_argument(
        '--no-skip',
        action='store_true',
        help='不跳过已存在文件,强制重新生成'
    )
    
    # 提示词配置
    parser.add_argument(
        '--prompt-version',
        type=str,
        choices=['v2.0', 'v3.0'],
        default='v3.0',
        help='提示词版本(默认: v3.0应试化版本)'
    )
    
    # 配置文件
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='配置文件路径(默认: config.yaml)'
    )
    
    # 输出控制
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        default=True,
        help='详细输出(默认开启)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='静默模式,只输出错误'
    )
    
    # 日志控制
    parser.add_argument(
        '--log-dir',
        type=str,
        default='logs',
        help='日志目录(默认: logs)'
    )
    
    parser.add_argument(
        '--no-log',
        action='store_true',
        help='禁用日志文件'
    )
    
    # 知识图谱功能
    parser.add_argument(
        '--build-kg',
        action='store_true',
        help='构建知识图谱'
    )
    
    parser.add_argument(
        '--update-kg',
        action='store_true',
        help='更新知识图谱（增量添加）'
    )
    
    parser.add_argument(
        '--subject',
        type=str,
        help='学科/知识库名称（如：Fall-Network）'
    )
    
    parser.add_argument(
        '--new-notes',
        type=str,
        help='要添加到知识库的新笔记文件路径'
    )
    
    parser.add_argument(
        '--qa',
        type=str,
        help='知识库问答（提供问题字符串）'
    )
    
    parser.add_argument(
        '--qa-interactive',
        action='store_true',
        help='启动交互式问答模式'
    )
    
    parser.add_argument(
        '--generate-mindmap',
        action='store_true',
        help='生成思维导图'
    )
    
    parser.add_argument(
        '--level',
        type=str,
        choices=['chapter', 'subject'],
        default='subject',
        help='思维导图级别：chapter(章节)/subject(学科总览)'
    )
    
    parser.add_argument(
        '--mindmap-format',
        type=str,
        choices=['mermaid', 'markmap', 'html'],
        default='markmap',
        help='思维导图格式'
    )
    
    parser.add_argument(
        '--kb-info',
        action='store_true',
        help='查看知识库信息'
    )
    
    # 其他功能
    parser.add_argument(
        '--ocr',
        action='store_true',
        help='启用OCR预处理 (用于纯图片PDF，需安装OCRmyPDF/Tesseract)'
    )
    
    parser.add_argument(
        '--force-ocr',
        action='store_true',
        help='强制执行OCR，即使PDF已包含文本层 (OCRmyPDF --force-ocr)'
    )
    
    parser.add_argument(
        '--validate-config',
        action='store_true',
        help='仅验证配置文件'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser


def validate_inputs(args) -> bool:
    # 解析符号链接，防路径遍历
    real_input = os.path.realpath(args.input)
    sensitive_paths = ['/etc', '/root', '/home', 'C:\\Windows', 'C:\\windows']
    for sp in sensitive_paths:
        if real_input.lower().startswith(sp.lower()):
            print(f"❌ 错误: 不允许访问敏感路径")
            return False

    if not os.path.exists(args.input):
        print(f"❌ 错误: 输入目录不存在 - {args.input}")
        return False

    if not os.path.isdir(args.input):
        print(f"❌ 错误: 输入路径不是目录 - {args.input}")
        return False
    
    # 检查是否有PDF文件
    pdf_files = [f for f in os.listdir(args.input) if f.endswith('.pdf')]
    if not pdf_files:
        print(f"❌ 错误: 输入目录中没有PDF文件 - {args.input}")
        return False
    
    return True


def run_pipeline(args, config: ConfigManager, logger):
    """运行Pipeline"""
    # 创建Pipeline实例
    pipeline = Pipeline(qwen_client, config=config.config)
    
    # 处理skip参数
    skip_existing = not args.no_skip if args.no_skip else args.skip_existing
    
    # 根据stage参数执行
    if args.stage == 'all':
        # 运行完整Pipeline
        logger.info("启动完整Pipeline")
        
        results = pipeline.run_full_pipeline(
            input_dir=args.input,
            output_base=args.output,
            prompt_version=args.prompt_version,
            skip_existing=skip_existing,
            verbose=args.verbose and not args.quiet,
            enable_ocr=args.ocr,
            force_ocr=args.force_ocr
        )
        
        if results['success']:
            logger.info(f"Pipeline执行成功，耗时{results['total_time']:.1f}秒")
            return 0
        else:
            logger.error(f"Pipeline执行失败: {results.get('error', '未知错误')}")
            return 1
    
    elif args.stage == 'parse':
        # 仅PDF解析
        logger.info("执行PDF解析阶段")
        
        output_dir = os.path.join(args.output, "raw_texts")
        os.makedirs(output_dir, exist_ok=True)
        
        results = pipeline.run_stage(
            'parse',
            input_dir=args.input,
            output_dir=output_dir,
            skip_existing=skip_existing,
            verbose=args.verbose and not args.quiet,
            enable_ocr=args.ocr,
            force_ocr=args.force_ocr
        )
        
        logger.info(f"PDF解析完成: {results['success']}/{results['total']}")
        return 0 if results['failed'] == 0 else 1
    
    elif args.stage == 'generate':
        # 仅笔记生成
        logger.info("执行笔记生成阶段")
        
        output_dir = os.path.join(args.output, "notes")
        os.makedirs(output_dir, exist_ok=True)
        
        results = pipeline.run_stage(
            'generate',
            pdf_dir=args.input,
            output_dir=output_dir,
            prompt_version=args.prompt_version,
            skip_existing=skip_existing,
            verbose=args.verbose and not args.quiet
        )
        
        logger.info(f"笔记生成完成: {results['success']}/{results['total']}")
        return 0 if results['failed'] == 0 else 1
    
    elif args.stage == 'integrate':
        # 仅笔记整合
        logger.info("执行笔记整合阶段")
        
        notes_dir = os.path.join(args.output, "notes")
        
        if not os.path.exists(notes_dir):
            logger.error(f"笔记目录不存在: {notes_dir}")
            return 1
        
        results = pipeline.run_stage(
            'integrate',
            notes_dir=notes_dir,
            output_dir=args.output,
            verbose=args.verbose and not args.quiet
        )
        
        logger.info("笔记整合完成")
        return 0


def _build_mindmap_from_notes(notes_dir: str, subject_name: str):
    G = nx.Graph()
    G.add_node(subject_name, type="subject")
    notes_path = os.path.join(notes_dir, '') if not os.path.isdir(notes_dir) else notes_dir
    if not os.path.isdir(notes_path):
        return G
    for md_file in sorted(Path(notes_path).glob("*_笔记.md")):
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        chapter_name = md_file.stem.replace('_笔记', '')
        G.add_node(chapter_name, type="chapter")
        G.add_edge(subject_name, chapter_name)
        sections = re.findall(r'^## (.+)$', content, re.MULTILINE)
        for section in sections[:5]:
            G.add_node(section.strip()[:50], type="section")
            G.add_edge(chapter_name, section.strip()[:50])
    return G


def _cmd_build_kg(args, logger, kb_manager) -> int:
    logger.info(f"开始构建知识图谱: {args.subject}")
    print(f"\n📊 构建知识图谱: {args.subject}")

    notes_dir = args.input if args.input else os.path.join(args.output, "notes")
    if not os.path.exists(notes_dir):
        print(f"❌ 错误: 笔记目录不存在 - {notes_dir}")
        return 1

    try:
        kb_manager.create_kb(
            subject_name=args.subject,
            description=f"Knowledge base for {args.subject}"
        )
        note_files = [f for f in os.listdir(notes_dir) if f.endswith('.md')]
        print(f"找到 {len(note_files)} 个笔记文件")
        kb_manager.update_kb(subject_name=args.subject, notes_dir=notes_dir)

        info = kb_manager.get_kb_info(args.subject)
        print(f"\n✅ 知识图谱构建完成!")
        print(f"  实体数: {info['num_entities']}")
        print(f"  关系数: {info['num_relations']}")
        print(f"  文档数: {info['num_documents']}")
        return 0
    except Exception as e:
        print(f"❌ 构建失败: {e}")
        logger.error(f"知识图谱构建失败: {e}")
        return 1


def _cmd_update_kg(args, logger, kb_manager) -> int:
    logger.info(f"更新知识图谱: {args.subject}")
    print(f"\n🔄 更新知识图谱: {args.subject}")

    if not args.new_notes:
        print("❌ 错误: 需要指定 --new-notes 参数")
        return 1
    if not os.path.exists(args.new_notes):
        print(f"❌ 错误: 笔记文件不存在 - {args.new_notes}")
        return 1

    try:
        notes_dir = os.path.dirname(args.new_notes) if os.path.dirname(args.new_notes) else "."
        kb_manager.update_kb(subject_name=args.subject, notes_dir=notes_dir)
        print(f"✅ 知识图谱更新完成: {args.new_notes}")
        return 0
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        return 1


def _cmd_qa(args, logger, api_key: str = "") -> int:
    from extensions.knowledge_graph.qa_system import QASystem

    logger.info(f"知识库问答: {args.subject}")
    print(f"\n💬 问答模式: {args.subject}")

    try:
        qa_system = QASystem(api_key=api_key)
        print(f"问题: {args.qa}")
        print("正在查询...")
        result = qa_system.ask(question=args.qa, subject=args.subject, use_tool=True)
        print(f"\n📝 答案:")
        print(result['answer'])
        if result.get('sources'):
            print(f"\n📚 来源: {result['sources']}")
        print(f"质量评分: {result['quality_score']:.2f}")
        return 0
    except Exception as e:
        print(f"❌ 问答失败: {e}")
        return 1


def _cmd_qa_interactive(args, logger, api_key: str = "") -> int:
    from extensions.knowledge_graph.qa_system import QASystem

    logger.info(f"启动交互式问答: {args.subject}")
    print(f"\n💬 交互式问答模式: {args.subject}")
    print("输入 'quit' 或 'exit' 退出\n")

    try:
        qa_system = QASystem(api_key=api_key)
        while True:
            question = input("❓ 你的问题: ").strip()
            if question.lower() in ['quit', 'exit', 'q']:
                print("再见! 👋")
                break
            if not question:
                continue
            print("正在查询...")
            result = qa_system.ask(question=question, subject=args.subject, use_tool=True)
            print(f"\n📝 答案:")
            print(result['answer'])
            if result.get('sources'):
                print(f"\n📚 来源: {result['sources']}")
            print(f"质量评分: {result['quality_score']:.2f}\n")
        return 0
    except KeyboardInterrupt:
        print("\n\n再见! 👋")
        return 0
    except Exception as e:
        print(f"❌ 问答失败: {e}")
        return 1


def _cmd_generate_mindmap(args, logger) -> int:
    from extensions.mindmap.mindmap_generator import MindmapGenerator
    from extensions.mindmap.visualizer import MindmapVisualizer

    logger.info(f"生成思维导图: {args.subject}")
    print(f"\n🗺️ 生成思维导图: {args.subject}")

    try:
        notes_dir = args.input if args.input else os.path.join(args.output, "notes")
        G = _build_mindmap_from_notes(notes_dir, args.subject)

        generator = MindmapGenerator()
        output_dir = os.path.join(args.output, "mindmaps")
        os.makedirs(output_dir, exist_ok=True)

        if args.mindmap_format == 'html':
            visualizer = MindmapVisualizer()
            output_path = os.path.join(output_dir, f"{args.subject}_mindmap.html")
            visualizer.render_interactive(G, output_path, title=f"{args.subject} Knowledge Map")
        else:
            content = generator.generate_from_graph(
                G, format=args.mindmap_format, title=f"{args.subject} Knowledge Map"
            )
            output_path = os.path.join(output_dir, f"{args.subject}_mindmap.md")
            generator.save_mindmap(content, output_path, format=args.mindmap_format)

        print(f"✅ 思维导图已生成: {output_path}")
        return 0
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


def _cmd_kb_info(args, logger, kb_manager) -> int:
    logger.info(f"查看知识库信息: {args.subject}")
    print(f"\n📊 知识库信息: {args.subject}\n")

    try:
        info = kb_manager.get_kb_info(args.subject)
        if info and info.get('status') != 'unknown':
            print(f"学科名称: {info['subject_name']}")
            print(f"描述: {info['description']}")
            print(f"实体数: {info.get('num_entities', 'N/A')}")
            print(f"关系数: {info.get('num_relations', 'N/A')}")
            print(f"文档数: {info.get('num_documents', 'N/A')}")
            print(f"创建时间: {info.get('created_at', 'N/A')}")
            print(f"更新时间: {info.get('updated_at', 'N/A')}")
        else:
            print(f"⚠️  知识库不存在或未初始化")
        return 0
    except Exception as e:
        print(f"❌ 获取信息失败: {e}")
        return 1


def run_kg_commands(args, logger, api_key: str = ""):
    from extensions.knowledge_graph.kb_manager import KnowledgeBaseManager

    if not args.subject:
        print("❌ 错误: 知识图谱功能需要指定 --subject 参数")
        return 1

    kb_manager = KnowledgeBaseManager()

    if args.build_kg:
        return _cmd_build_kg(args, logger, kb_manager)
    elif args.update_kg:
        return _cmd_update_kg(args, logger, kb_manager)
    elif args.qa:
        return _cmd_qa(args, logger, api_key)
    elif args.qa_interactive:
        return _cmd_qa_interactive(args, logger, api_key)
    elif args.generate_mindmap:
        return _cmd_generate_mindmap(args, logger)
    elif args.kb_info:
        return _cmd_kb_info(args, logger, kb_manager)
    return 0


def main():
    check_dependencies()
    # 创建解析器
    parser = create_parser()
    args = parser.parse_args()
    
    # 加载配置
    try:
        config = ConfigManager(args.config)
    except Exception as e:
        print(f"❌ 加载配置失败: {e}")
        return 1
    
    # 仅验证配置
    if args.validate_config:
        is_valid, errors = config.validate()
        if is_valid:
            print("✅ 配置验证通过")
            config.display()
            return 0
        else:
            print("❌ 配置验证失败:")
            for error in errors:
                print(f"  • {error}")
            return 1
    
    # 检查是否是知识图谱命令
    kg_commands = ['build_kg', 'update_kg', 'qa', 'qa_interactive', 'generate_mindmap', 'kb_info']
    is_kg_command = any(getattr(args, cmd, False) for cmd in kg_commands)
    
    # 知识图谱命令不需要验证输入目录
    if not is_kg_command:
        # 验证输入
        if not validate_inputs(args):
            return 1
    
    # 初始化日志
    if not args.no_log:
        logger = get_logger(
            name="Pipeline",
            log_dir=args.log_dir,
            console_output=args.verbose and not args.quiet
        )
    else:
        logger = get_logger(console_output=args.verbose and not args.quiet)
    
    # 显示启动信息
    if args.verbose and not args.quiet:
        print("\n" + "="*60)
        print("Fall-Network 课程笔记生成Pipeline v1.0")
        print("="*60)
        print(f"输入目录: {args.input}")
        print(f"输出目录: {args.output}")
        print(f"执行阶段: {args.stage}")
        print(f"提示词版本: {args.prompt_version}")
        print(f"断点续传: {'开启' if (not args.no_skip if args.no_skip else args.skip_existing) else '关闭'}")
        print("="*60 + "\n")
    
    # 运行命令
    try:
        # 如果是知识图谱命令，运行KG命令
        if is_kg_command:
            return_code = run_kg_commands(args, logger, config.get('model.api_key', ''))
        else:
            # 否则运行Pipeline
            return_code = run_pipeline(args, config, logger)
        
        if return_code == 0 and args.verbose and not args.quiet:
            print("\n✨ 任务完成!\n")
        
        return return_code
        
    except KeyboardInterrupt:
        logger.warning("用户中断执行")
        print("\n\n⚠️  执行已中断\n")
        return 130
    
    except Exception as e:
        logger.error(f"发生未预期的错误: {str(e)}")
        print(f"\n❌ 错误: {str(e)}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
