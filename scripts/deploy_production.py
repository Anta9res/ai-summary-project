"""
生产部署脚本
用于生产环境部署，生成完整的19讲笔记
"""
import sys
import os
import shutil
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

# 执行依赖检查
check_dependencies()

import qwen_client
from core.pipeline import Pipeline
from config.config_manager import ConfigManager
from utils.logger import get_logger


def backup_old_output(output_dir: str):
    """备份旧输出"""
    if not os.path.exists(output_dir):
        print(f"ℹ️  输出目录不存在，无需备份")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"{output_dir}_backup_{timestamp}"
    
    print(f"\n📦 备份旧输出...")
    print(f"源目录: {output_dir}")
    print(f"备份至: {backup_dir}")
    
    try:
        shutil.copytree(output_dir, backup_dir)
        print(f"✅ 备份完成\n")
        return backup_dir
    except Exception as e:
        print(f"⚠️  备份失败: {e}")
        return None


def clean_output_dir(output_dir: str, keep_backup: bool = True):
    """清理输出目录"""
    if not os.path.exists(output_dir):
        return
    
    if keep_backup:
        response = input(f"\n⚠️  即将清空 {output_dir}，是否继续？(y/N): ")
        if response.lower() != 'y':
            print("❌ 取消清理")
            return False
    
    print(f"\n🗑️  清空输出目录...")
    try:
        shutil.rmtree(output_dir)
        print(f"✅ 清理完成\n")
        return True
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        return False


def run_production_pipeline(
    input_dir: str = "课件",
    output_dir: str = "output",
    prompt_version: str = "v3.0",
    backup: bool = True,
    clean: bool = False,
    force_regenerate: bool = False
):
    """运行生产Pipeline"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(project_root, input_dir)
    output_path = os.path.join(project_root, output_dir)
    
    print("\n" + "="*60)
    print("🚀 Fall-Network 生产部署")
    print("="*60)
    print(f"输入目录: {input_path}")
    print(f"输出目录: {output_path}")
    print(f"提示词版本: {prompt_version}")
    print(f"备份旧数据: {'是' if backup else '否'}")
    print(f"清空输出: {'是' if clean else '否'}")
    print(f"断点续传: {'否(强制重新生成)' if force_regenerate else '是(跳过已生成)'}")
    print("="*60)
    
    # 检查输入目录
    if not os.path.exists(input_path):
        print(f"\n❌ 输入目录不存在: {input_path}")
        return False
    
    # 备份
    backup_path = None
    if backup and os.path.exists(output_path):
        backup_path = backup_old_output(output_path)
    
    # 清理
    if clean:
        if not clean_output_dir(output_path, keep_backup=(not backup)):
            return False
    
    # 加载配置
    print("\n📝 加载配置...")
    try:
        config = ConfigManager()
        is_valid, errors = config.validate()
        if not is_valid:
            print("❌ 配置验证失败:")
            for error in errors:
                print(f"  • {error}")
            return False
        print("✅ 配置验证通过\n")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False
    
    # 创建Pipeline
    print("🏗️  初始化Pipeline...")
    pipeline = Pipeline(qwen_client, config=config.config)
    logger = get_logger("ProductionDeploy", log_dir="logs")
    print("✅ Pipeline就绪\n")
    
    # 确认开始
    if force_regenerate:
        print("\n⚠️  警告: 已启用强制重新生成模式，将忽略已生成的笔记！")
    response = input("⚡ 准备开始生成，预计需要10-15分钟。继续？(y/N): ")
    if response.lower() != 'y':
        print("\n❌ 取消部署\n")
        return False
    
    # 运行Pipeline
    print("\n" + "="*60)
    print("🎬 开始生成笔记")
    print("="*60)
    
    try:
        # 关键修复: 默认支持断点续传(skip_existing=True)
        # 只有在force_regenerate=True时才强制重新生成
        results = pipeline.run_full_pipeline(
            input_dir=input_path,
            output_base=output_path,
            prompt_version=prompt_version,
            skip_existing=not force_regenerate,  # 修复: 默认True支持断点续传
            verbose=True
        )
        
        # 结果汇总
        print("\n" + "="*60)
        print("📊 部署结果")
        print("="*60)
        
        if results['success']:
            print(f"✅ 部署成功")
            print(f"\n统计信息:")
            print(f"  PDF解析: {results['pdf_parsed']} 个")
            print(f"  笔记生成: {results['notes_generated']} 个")
            print(f"  质量问题: {results['quality_issues']} 个")
            print(f"  总耗时: {results['total_time']:.1f} 秒")
            
            print(f"\n输出目录: {output_path}")
            if backup_path:
                print(f"备份目录: {backup_path}")
            
            print("\n" + "="*60)
            print("🎉 生产部署完成！")
            print("="*60)
            
            logger.info(f"生产部署成功: {results}")
            return True
        else:
            print(f"❌ 部署失败: {results.get('error', '未知错误')}")
            logger.error(f"生产部署失败: {results}")
            return False
            
    except KeyboardInterrupt:
        print("\n\n⚠️  部署被用户中断")
        logger.warning("生产部署被中断")
        return False
    except Exception as e:
        print(f"\n❌ 部署异常: {str(e)}")
        logger.error(f"生产部署异常: {str(e)}")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fall-Network 生产部署",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 标准部署（默认支持断点续传）
  python deploy_production.py
  
  # 强制重新生成所有笔记
  python deploy_production.py --force-regenerate
  
  # 清空输出并重新生成
  python deploy_production.py --clean --force-regenerate
  
        """
    )
    parser.add_argument("--input", default="课件", help="输入目录")
    parser.add_argument("--output", default="output", help="输出目录")
    parser.add_argument("--version", default="v3.0", choices=['v3.0'], help="提示词版本")
    parser.add_argument("--no-backup", action="store_true", help="不备份旧数据")
    parser.add_argument("--clean", action="store_true", help="清空输出目录（高风险操作）")
    parser.add_argument("--force-regenerate", action="store_true", 
                       help="强制重新生成所有笔记（忽略已生成的文件）")
    
    args = parser.parse_args()
    
    success = run_production_pipeline(
        input_dir=args.input,
        output_dir=args.output,
        prompt_version=args.version,
        backup=not args.no_backup,
        clean=args.clean,
        force_regenerate=args.force_regenerate
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
