"""
集成测试 - 验证完整Pipeline流程
测试范围:
1. 端到端流程测试
2. 断点续传测试
3. 各阶段输出验证
4. 配置加载测试
"""
import sys
import os
import shutil

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import qwen_client
from core.pipeline import Pipeline
from config.config_manager import ConfigManager
from utils.logger import get_logger


class IntegrationTest:
    """集成测试类"""
    
    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.test_input = os.path.join(self.project_root, "课件")
        self.test_output = os.path.join(self.project_root, "output_test")
        self.logger = get_logger("IntegrationTest", log_dir="logs", console_output=True)
        
    def setup(self):
        """测试前准备"""
        print("\n" + "="*60)
        print("🧪 集成测试准备")
        print("="*60)
        
        # 清理测试输出目录
        if os.path.exists(self.test_output):
            print(f"清理测试目录: {self.test_output}")
            shutil.rmtree(self.test_output)
        
        os.makedirs(self.test_output, exist_ok=True)
        print("✅ 测试环境准备完成\n")
    
    def teardown(self):
        """测试后清理"""
        print("\n" + "="*60)
        print("🧹 清理测试环境")
        print("="*60)
        # 可选：保留测试输出供检查
        # shutil.rmtree(self.test_output)
        print(f"ℹ️  测试输出保留在: {self.test_output}")
        print("✅ 清理完成\n")
    
    def test_full_pipeline(self):
        """测试1: 完整Pipeline流程"""
        print("\n" + "="*60)
        print("📝 测试1: 完整Pipeline流程")
        print("="*60)
        
        try:
            # 加载配置
            config = ConfigManager()
            
            # 创建Pipeline
            pipeline = Pipeline(qwen_client, config=config.config)
            
            # 执行完整流程（使用3个PDF测试）
            results = pipeline.run_full_pipeline(
                input_dir=self.test_input,
                output_base=self.test_output,
                prompt_version="v3.0",
                skip_existing=False,  # 第一次不跳过
                verbose=True
            )
            
            # 验证结果
            assert results['success'], "Pipeline执行失败"
            assert results['pdf_parsed'] > 0, "PDF解析数量为0"
            assert results['notes_generated'] > 0, "笔记生成数量为0"
            
            # 验证输出文件
            raw_texts_dir = os.path.join(self.test_output, "raw_texts")
            notes_dir = os.path.join(self.test_output, "notes")
            
            assert os.path.exists(raw_texts_dir), "raw_texts目录不存在"
            assert os.path.exists(notes_dir), "notes目录不存在"
            assert os.path.exists(os.path.join(self.test_output, "完整复习笔记.md")), "完整笔记文件不存在"
            assert os.path.exists(os.path.join(self.test_output, "笔记索引.md")), "索引文件不存在"
            
            print("\n✅ 测试1通过: 完整Pipeline流程正常")
            return True
            
        except Exception as e:
            print(f"\n❌ 测试1失败: {str(e)}")
            return False
    
    def test_resume_capability(self):
        """测试2: 断点续传功能"""
        print("\n" + "="*60)
        print("📝 测试2: 断点续传功能")
        print("="*60)
        
        try:
            config = ConfigManager()
            pipeline = Pipeline(qwen_client, config=config.config)
            
            # 第二次运行，应该跳过已存在的文件
            print("\n重新运行Pipeline（应跳过已存在文件）...")
            results = pipeline.run_full_pipeline(
                input_dir=self.test_input,
                output_base=self.test_output,
                prompt_version="v3.0",
                skip_existing=True,  # 启用断点续传
                verbose=True
            )
            
            assert results['success'], "断点续传执行失败"
            
            print("\n✅ 测试2通过: 断点续传功能正常")
            return True
            
        except Exception as e:
            print(f"\n❌ 测试2失败: {str(e)}")
            return False
    
    def test_stage_execution(self):
        """测试3: 单阶段执行"""
        print("\n" + "="*60)
        print("📝 测试3: 单阶段执行")
        print("="*60)
        
        try:
            config = ConfigManager()
            pipeline = Pipeline(qwen_client, config=config.config)
            
            # 测试单独执行整合阶段
            print("\n测试整合阶段...")
            results = pipeline.run_stage(
                'integrate',
                notes_dir=os.path.join(self.test_output, "notes"),
                output_dir=self.test_output,
                verbose=True
            )
            
            assert results is not None, "整合阶段执行失败"
            
            print("\n✅ 测试3通过: 单阶段执行正常")
            return True
            
        except Exception as e:
            print(f"\n❌ 测试3失败: {str(e)}")
            return False
    
    def test_config_loading(self):
        """测试4: 配置加载"""
        print("\n" + "="*60)
        print("📝 测试4: 配置加载")
        print("="*60)
        
        try:
            # 测试默认配置
            config = ConfigManager()
            
            assert config.get('model.name') is not None, "模型名称未配置"
            assert config.get('prompt.version') is not None, "提示词版本未配置"
            assert config.get('pipeline.skip_existing') is not None, "Pipeline配置缺失"
            
            # 测试配置验证
            is_valid, errors = config.validate()
            if not is_valid:
                print(f"⚠️  配置验证警告: {errors}")
            
            print("\n✅ 测试4通过: 配置加载正常")
            return True
            
        except Exception as e:
            print(f"\n❌ 测试4失败: {str(e)}")
            return False
    
    def test_output_quality(self):
        """测试5: 输出质量验证"""
        print("\n" + "="*60)
        print("📝 测试5: 输出质量验证")
        print("="*60)
        
        try:
            notes_dir = os.path.join(self.test_output, "notes")
            
            # 检查笔记文件
            note_files = [f for f in os.listdir(notes_dir) if f.endswith('.md') and '笔记' in f]
            
            assert len(note_files) > 0, "没有生成笔记文件"
            
            # 检查第一个笔记文件的内容
            first_note = os.path.join(notes_dir, note_files[0])
            with open(first_note, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 验证v3.0特性
            assert '⭐⭐⭐' in content or '⭐⭐' in content, "缺少重要性标记"
            assert '##' in content, "缺少章节标题"
            assert len(content) > 500, "笔记内容过短"
            
            # 检查是否有质量标记
            has_quality_mark = '<!-- QUALITY_PASSED -->' in content
            
            print(f"\n检查笔记文件: {note_files[0]}")
            print(f"  文件大小: {len(content)} 字符")
            print(f"  质量标记: {'✅ 有' if has_quality_mark else '⚠️  无'}")
            
            print("\n✅ 测试5通过: 输出质量验证正常")
            return True
            
        except Exception as e:
            print(f"\n❌ 测试5失败: {str(e)}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("🚀 开始集成测试")
        print("="*60)
        
        self.setup()
        
        tests = [
            ("完整Pipeline流程", self.test_full_pipeline),
            ("断点续传功能", self.test_resume_capability),
            ("单阶段执行", self.test_stage_execution),
            ("配置加载", self.test_config_loading),
            ("输出质量验证", self.test_output_quality),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"\n❌ 测试异常: {test_name} - {str(e)}")
                results.append((test_name, False))
        
        self.teardown()
        
        # 汇总结果
        print("\n" + "="*60)
        print("📊 测试结果汇总")
        print("="*60)
        
        passed = sum(1 for _, r in results if r)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{status}: {test_name}")
        
        print(f"\n总计: {passed}/{total} 通过")
        print("="*60)
        
        return passed == total


def main():
    """主函数"""
    test = IntegrationTest()
    success = test.run_all_tests()
    
    if success:
        print("\n🎉 所有集成测试通过!\n")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查日志\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
