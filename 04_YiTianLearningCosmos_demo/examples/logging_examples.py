"""
日志配置示例和使用指南
展示如何在项目中使用统一的日志系统
"""

import os
from pathlib import Path

from .core.logging_config import setup_logging, get_logger
from .core.decorators import handle_exceptions, with_logging_context


# 示例1: 基础日志配置
def configure_basic_logging():
    """基础日志配置示例"""
    # 简单配置
    logger = setup_logging(
        log_level="INFO",
        console_output=True
    )
    return logger


# 示例2: 详细日志配置
def configure_advanced_logging():
    """高级日志配置示例"""
    # 创建日志目录
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    logger = setup_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=str(log_dir / "application.log"),
        log_format="detailed",  # 详细格式包含文件名、行号等
        max_bytes=50 * 1024 * 1024,  # 50MB
        backup_count=10,
        console_output=True
    )
    return logger


# 示例3: JSON格式日志（适合生产环境）
def configure_production_logging():
    """生产环境日志配置"""
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    logger = setup_logging(
        log_level="WARNING",  # 生产环境通常使用WARNING级别
        log_file=str(log_dir / "production.log"),
        log_format="json",  # JSON格式便于日志分析
        max_bytes=100 * 1024 * 1024,  # 100MB
        backup_count=20,
        console_output=False  # 生产环境可能不需要控制台输出
    )
    return logger


# 示例4: 在类中使用日志
class ExampleService:
    def __init__(self):
        self.logger = get_logger(__name__)
    
    @handle_exceptions
    @with_logging_context(service="example_service")
    def process_data(self, data):
        """处理数据的示例方法"""
        self.logger.info(f"开始处理数据: {len(data)} items")
        
        # 模拟一些处理逻辑
        if not data:
            self.logger.warning("收到空数据")
            return []
        
        try:
            # 处理数据
            result = [item.upper() for item in data if isinstance(item, str)]
            self.logger.info(f"数据处理完成: {len(result)} items processed")
            return result
        except Exception as e:
            self.logger.error(f"数据处理失败: {e}")
            raise


# 示例5: 异步函数的日志使用
import asyncio

class AsyncExampleService:
    def __init__(self):
        self.logger = get_logger(__name__)
    
    @handle_exceptions
    @with_logging_context(service="async_example")
    async def async_process(self, items):
        """异步处理示例"""
        self.logger.info(f"开始异步处理 {len(items)} 个项目")
        
        results = []
        for i, item in enumerate(items):
            self.logger.debug(f"处理项目 {i+1}/{len(items)}: {item}")
            # 模拟异步处理
            await asyncio.sleep(0.1)
            results.append(f"processed_{item}")
        
        self.logger.info(f"异步处理完成，共处理 {len(results)} 个项目")
        return results


# 示例6: 自定义日志上下文
def demonstrate_custom_context():
    """演示自定义日志上下文"""
    logger = get_logger(__name__)
    
    # 添加自定义上下文信息
    extra_context = {
        'user_id': 'user_123',
        'session_id': 'sess_456',
        'request_id': 'req_789'
    }
    
    logger.info("用户操作日志", extra={'extra_data': extra_context})


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logger = configure_basic_logging()
    
    # 测试基本日志
    logger.debug("这是调试信息")
    logger.info("这是普通信息")
    logger.warning("这是警告信息")
    logger.error("这是错误信息")
    logger.critical("这是严重错误信息")
    
    # 测试服务类
    service = ExampleService()
    try:
        result = service.process_data(["hello", "world"])
        print(f"处理结果: {result}")
    except Exception as e:
        print(f"服务调用失败: {e}")
    
    # 测试异步服务
    async def test_async():
        async_service = AsyncExampleService()
        result = await async_service.async_process(["item1", "item2", "item3"])
        print(f"异步处理结果: {result}")
    
    asyncio.run(test_async())