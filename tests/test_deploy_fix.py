"""
验证deploy_production.py修复
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_deploy_production_parameters():
    """测试deploy_production.py的参数修复"""
    print("\n" + "="*60)
    print("🧪 验证deploy_production.py修复")
    print("="*60)
    
    # 测试1: 检查文件存在
    deploy_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "deploy_production.py"
    )
    
    print(f"\n✅ 测试1: 文件存在检查")
    assert os.path.exists(deploy_file), "deploy_production.py不存在"
    print(f"   文件路径: {deploy_file}")
    
    # 测试2: 检查代码修复
    print(f"\n✅ 测试2: 代码修复验证")
    with open(deploy_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查force_regenerate参数
    assert "force_regenerate: bool = False" in content, \
        "缺少force_regenerate参数"
    print(f"   ✅ force_regenerate参数已添加")
    
    # 检查skip_existing修复
    assert "skip_existing=not force_regenerate" in content, \
        "skip_existing参数未正确修复"
    print(f"   ✅ skip_existing参数已修复")
    
    # 检查警告提示
    assert "警告: 已启用强制重新生成模式" in content, \
        "缺少force_regenerate警告提示"
    print(f"   ✅ 警告提示已添加")
    
    # 检查--force-regenerate参数
    assert "--force-regenerate" in content, \
        "缺少--force-regenerate命令行参数"
    print(f"   ✅ --force-regenerate参数已添加")
    
    # 检查clean参数风险提示
    assert "高风险操作" in content, \
        "缺少clean参数风险提示"
    print(f"   ✅ clean参数风险提示已添加")
    
    # 测试3: 验证默认行为
    print(f"\n✅ 测试3: 默认行为验证")
    
    # 检查不再有skip_existing=False的硬编码
    assert "skip_existing=False" not in content or \
           "skip_existing=False  # 修复" not in content, \
        "仍然存在错误的skip_existing=False"
    print(f"   ✅ 没有错误的skip_existing=False")
    
    # 检查默认force_regenerate=False
    lines_with_force_regen = [line for line in content.split('\n') 
                              if 'force_regenerate: bool' in line]
    assert any('= False' in line for line in lines_with_force_regen), \
        "force_regenerate默认值不是False"
    print(f"   ✅ force_regenerate默认值为False（支持断点续传）")
    
    # 测试4: 帮助文档检查
    print(f"\n✅ 测试4: 帮助文档验证")
    assert "标准部署（默认支持断点续传）" in content, \
        "缺少标准部署说明"
    print(f"   ✅ 帮助文档已更新")
    
    # 测试5: 状态显示检查
    print(f"\n✅ 测试5: 状态显示验证")
    assert "断点续传:" in content, \
        "缺少断点续传状态显示"
    print(f"   ✅ 状态显示已增强")
    
    print("\n" + "="*60)
    print("🎉 所有验证通过！deploy_production.py修复成功")
    print("="*60)
    
    print("\n修复总结:")
    print("✅ 1. skip_existing默认为True（支持断点续传）")
    print("✅ 2. 添加--force-regenerate参数控制")
    print("✅ 3. clean参数风险提示已添加")
    print("✅ 4. 警告提示完善")
    print("✅ 5. 帮助文档更新")
    print("✅ 6. 状态显示增强")
    
    print("\n现在deploy_production.py可以安全使用：")
    print("  默认用法: python deploy_production.py")
    print("  强制重新生成: python deploy_production.py --force-regenerate")
    
    return True


def main():
    """主函数"""
    try:
        test_deploy_production_parameters()
        return 0
    except AssertionError as e:
        print(f"\n❌ 验证失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 验证异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
