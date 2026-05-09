"""
日志系统模块
提供统一的日志记录功能
"""
import logging
import os
from datetime import datetime
from typing import Optional


class Logger:
    """日志管理器"""
    
    def __init__(
        self,
        name: str = "Pipeline",
        log_dir: str = "logs",
        log_level: int = logging.INFO,
        console_output: bool = True
    ):
        """
        初始化日志器
        
        Args:
            name: 日志器名称
            log_dir: 日志目录
            log_level: 日志级别
            console_output: 是否输出到控制台
        """
        self.name = name
        self.log_dir = log_dir
        self.logger = self._setup_logger(name, log_dir, log_level, console_output)
    
    def _setup_logger(
        self,
        name: str,
        log_dir: str,
        log_level: int,
        console_output: bool
    ) -> logging.Logger:
        """设置日志器"""
        # 创建日志器
        logger = logging.getLogger(name)
        logger.setLevel(log_level)
        
        # 清除已有处理器
        logger.handlers = []
        
        # 创建日志目录
        os.makedirs(log_dir, exist_ok=True)
        
        # 文件处理器
        log_filename = datetime.now().strftime(f"{name}_%Y%m%d_%H%M%S.log")
        log_path = os.path.join(log_dir, log_filename)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(log_level)
        
        # 控制台处理器
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            logger.addHandler(console_handler)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        if console_output:
            console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
        return logger
    
    def debug(self, message: str):
        """调试级别日志"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """信息级别日志"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """警告级别日志"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """错误级别日志"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """严重错误级别日志"""
        self.logger.critical(message)
    
    def log_stage_start(self, stage_name: str):
        """记录阶段开始"""
        self.info(f"{'='*60}")
        self.info(f"开始阶段: {stage_name}")
        self.info(f"{'='*60}")
    
    def log_stage_end(self, stage_name: str, success: bool = True):
        """记录阶段结束"""
        status = "成功" if success else "失败"
        self.info(f"{'='*60}")
        self.info(f"阶段结束: {stage_name} - {status}")
        self.info(f"{'='*60}")
    
    def log_file_process(
        self,
        file_name: str,
        status: str,
        details: Optional[str] = None
    ):
        """
        记录文件处理
        
        Args:
            file_name: 文件名
            status: 处理状态(success/failed/skipped)
            details: 详细信息
        """
        status_icon = {
            'success': '✅',
            'failed': '❌',
            'skipped': '⏭️'
        }.get(status, '•')
        
        message = f"{status_icon} {file_name}"
        if details:
            message += f" - {details}"
        
        if status == 'failed':
            self.error(message)
        else:
            self.info(message)
    
    def log_statistics(self, stats: dict):
        """记录统计信息"""
        self.info("统计信息:")
        for key, value in stats.items():
            self.info(f"  {key}: {value}")


# 全局日志器实例
_global_logger: Optional[Logger] = None


def get_logger(
    name: str = "Pipeline",
    log_dir: str = "logs",
    log_level: int = logging.INFO,
    console_output: bool = True
) -> Logger:
    """
    获取全局日志器实例
    
    Args:
        name: 日志器名称
        log_dir: 日志目录
        log_level: 日志级别
        console_output: 是否输出到控制台
        
    Returns:
        Logger实例
    """
    global _global_logger
    
    if _global_logger is None:
        _global_logger = Logger(name, log_dir, log_level, console_output)
    
    return _global_logger
