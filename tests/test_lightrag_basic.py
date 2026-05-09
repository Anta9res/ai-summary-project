"""
LightRAG基础功能测试
测试LightRAG的安装和基本功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_lightrag_import():
    """测试LightRAG是否可以正常导入"""
    try:
        from lightrag import LightRAG
        print("✅ LightRAG导入成功")
        return True
    except ImportError as e:
        print(f"❌ LightRAG导入失败: {e}")
        return False


def test_dependencies():
    """测试相关依赖是否安装"""
    dependencies = [
        ("chromadb", "向量数据库"),
        ("networkx", "图计算库"),
        ("numpy", "数值计算库"),
        ("nano_vectordb", "nano向量数据库")
    ]
    
    all_ok = True
    for module_name, desc in dependencies:
        try:
            __import__(module_name)
            print(f"✅ {desc} ({module_name}) 已安装")
        except ImportError:
            print(f"❌ {desc} ({module_name}) 未安装")
            all_ok = False
    
    return all_ok


def test_lightrag_basic_setup():
    """测试LightRAG基本初始化"""
    try:
        from lightrag import LightRAG, QueryParam
        
        # 创建临时工作目录
        test_dir = project_root / "tests" / "temp_lightrag"
        test_dir.mkdir(exist_ok=True)
        
        print("\n正在测试LightRAG类和QueryParam...")
        print(f"✅ LightRAG类导入成功: {LightRAG}")
        print(f"✅ QueryParam类导入成功: {QueryParam}")
        
        # 检查LightRAG的基本属性
        print("\n检查LightRAG可用方法:")
        methods = [m for m in dir(LightRAG) if not m.startswith('_')]
        for method in methods[:10]:  # 显示前10个方法
            print(f"  - {method}")
        
        print("\n✅ LightRAG基本结构测试通过")
        print("⚠️  注意：完整功能需要配置LLM模型（通义千问）")
        
        # 清理临时目录
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir)
        
        return True
        
    except Exception as e:
        print(f"❌ LightRAG初始化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_qwen_client_available():
    """测试通义千问客户端是否可用"""
    try:
        import qwen_client
        print("\n✅ qwen_client模块可用")
        
        # 检查可用函数
        functions = [f for f in dir(qwen_client) if not f.startswith('_')]
        print("可用函数:")
        for func in functions[:5]:  # 显示前5个
            print(f"  - {func}")
        
        # 检查API密钥配置
        import yaml
        config_path = project_root / "config.yaml"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                api_key = config.get('model', {}).get('api_key', '')
                if api_key:
                    print("✅ API密钥已配置")
                else:
                    print("⚠️  API密钥未配置（可能从环境变量读取）")
        
        return True
    except Exception as e:
        print(f"❌ 通义千问客户端测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("LightRAG环境测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: LightRAG导入
    print("\n【测试1】LightRAG导入测试")
    results.append(test_lightrag_import())
    
    # 测试2: 依赖检查
    print("\n【测试2】依赖库检查")
    results.append(test_dependencies())
    
    # 测试3: 通义千问客户端
    print("\n【测试3】通义千问客户端检查")
    results.append(test_qwen_client_available())
    
    # 测试4: LightRAG基本功能
    print("\n【测试4】LightRAG基本初始化测试")
    results.append(test_lightrag_basic_setup())
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")
    
    if all(results):
        print("\n✅ 所有测试通过！环境准备就绪。")
        print("\n下一步:")
        print("1. 配置通义千问API用于LightRAG")
        print("2. 开发知识图谱构建器")
        print("3. 实现LightRAG适配器")
    else:
        print("\n⚠️  部分测试未通过，请检查依赖安装。")
    
    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
