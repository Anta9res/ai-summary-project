"""
配置管理器模块
统一管理Pipeline配置
"""
import os
import copy
import yaml
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv

load_dotenv()


class ConfigManager:
    """配置管理器"""
    
    DEFAULT_CONFIG = {
        'model': {
            'name': 'kimi-k2.6',
            'api_key': '',  # 从环境变量或配置文件读取
            'base_url': 'https://opencode.ai/zen/go/v1',
            'temperature': 0.7,
            'max_tokens': 8192,  # kimi-k2.6 推理模型需更大 token 空间
            'top_p': 1.0,
        },
        'prompt': {
            'version': 'v3.0',
        },
        'pipeline': {
            'skip_existing': True,
            'verbose': True,
            'parallel': False,
            'max_workers': 3
        },
        'output': {
            'base_dir': 'output',
            'raw_texts_dir': 'raw_texts',
            'notes_dir': 'notes',
            'backup_enabled': True
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or "config.yaml"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        config = copy.deepcopy(self.DEFAULT_CONFIG)

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f) or {}
                config = self._merge_config(config, file_config)
            except Exception as e:
                print(f"⚠️  加载配置文件失败: {e}，使用默认配置")
        else:
            print("ℹ️  未找到 config.yaml，请复制 config.yaml.example 并编辑")
            print("   或设置环境变量 OPENCODE_API_KEY（默认 kimi-k2.6）或 DASHSCOPE_API_KEY（回退 qwen-long）")

        # 环境变量优先于配置文件 (env > .env > config.yaml)
        # 优先匹配 opencode 端点 (kimi-k2.6 等) 的密钥
        base_url = config['model'].get('base_url', '')
        if 'OPENCODE_API_KEY' in os.environ:
            config['model']['api_key'] = os.environ['OPENCODE_API_KEY']
        elif 'DASHSCOPE_API_KEY' in os.environ:
            config['model']['api_key'] = os.environ['DASHSCOPE_API_KEY']
            # 智能回退: 配置为 opencode 但无 OPENCODE_API_KEY → 回退 DashScope
            if base_url and 'opencode' in base_url:
                print("ℹ️  未检测到 OPENCODE_API_KEY，回退到 DashScope (qwen-long)")
                config['model']['name'] = 'qwen-long'
                config['model']['base_url'] = ''
                config['model']['max_tokens'] = 4096
        elif 'API_KEY' in os.environ:
            config['model']['api_key'] = os.environ['API_KEY']

        return config
    
    def _merge_config(self, base: Dict, override: Dict) -> Dict:
        """合并配置字典"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key: str, default=None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置键(支持点号分隔的路径,如'model.name')
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def set(self, key: str, value: Any):
        """
        设置配置项
        
        Args:
            key: 配置键(支持点号分隔的路径)
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        # 导航到最后一层
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
    
    def save(self, path: Optional[str] = None):
        """
        保存配置到文件
        
        Args:
            path: 保存路径(默认使用初始化时的路径)
        """
        save_path = path or self.config_path
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            return False
    
    def get_model_config(self) -> Dict[str, Any]:
        """获取模型配置"""
        return self.config.get('model', {})
    
    def get_prompt_config(self) -> Dict[str, Any]:
        """获取提示词配置"""
        return self.config.get('prompt', {})
    
    def get_pipeline_config(self) -> Dict[str, Any]:
        """获取Pipeline配置"""
        return self.config.get('pipeline', {})
    
    def get_output_config(self) -> Dict[str, Any]:
        """获取输出配置"""
        return self.config.get('output', {})
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证配置完整性
        
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        # 检查必需配置
        if not self.get('model.api_key'):
            errors.append("缺少API密钥(model.api_key或环境变量 OPENCODE_API_KEY / DASHSCOPE_API_KEY)")
        
        if not self.get('model.name'):
            errors.append("缺少模型名称(model.name)")
        
        if not self.get('prompt.version'):
            errors.append("缺少提示词版本(prompt.version)")
        
        return (len(errors) == 0, errors)
    
    def display(self):
        """显示当前配置"""
        print("\n当前配置:")
        print("="*60)
        print(yaml.dump(self.config, allow_unicode=True, default_flow_style=False))
        print("="*60)
