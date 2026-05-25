"""
Recovery - 错误恢复系统

处理错误并尝试恢复
参考 Hermes 的错误分类和智能重试
"""

import time
import random
import logging
from typing import Callable, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """错误类型分类"""
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    AUTH = "auth"
    NETWORK = "network"
    CONTEXT_LENGTH = "context_length"
    SERVER_ERROR = "server_error"
    UNKNOWN = "unknown"


class Recovery:
    """错误恢复 - 智能重试机制"""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """执行函数并在失败时智能重试"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                error_type = self._classify_error(e)
                
                if attempt < self.max_retries:
                    if self._should_retry(error_type, attempt):
                        delay = self._get_delay(error_type, attempt)
                        logger.warning(
                            f"尝试 {attempt + 1}/{self.max_retries} 失败: {error_type.value} - {e}, "
                            f"{delay:.1f}s 后重试"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"错误类型 {error_type.value} 不可重试: {e}")
                        raise
                else:
                    logger.error(f"所有重试失败: {e}")
                    raise
        
        raise last_error
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """分类错误类型"""
        error_str = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        if "rate" in error_str or "429" in error_str or "quota" in error_str:
            return ErrorType.RATE_LIMIT
        
        if "timeout" in error_str or "timed out" in error_str:
            return ErrorType.TIMEOUT
        
        if "auth" in error_str or "401" in error_str or "403" in error_str or "api key" in error_str:
            return ErrorType.AUTH
        
        if "network" in error_str or "connection" in error_str or "unreachable" in error_str:
            return ErrorType.NETWORK
        
        if "context" in error_str or "token" in error_str and "limit" in error_str:
            return ErrorType.CONTEXT_LENGTH
        
        if "500" in error_str or "502" in error_str or "503" in error_str or "504" in error_str:
            return ErrorType.SERVER_ERROR
        
        return ErrorType.UNKNOWN
    
    def _should_retry(self, error_type: ErrorType, attempt: int) -> bool:
        """判断是否应该重试"""
        non_retryable = {ErrorType.AUTH, ErrorType.CONTEXT_LENGTH}
        
        if error_type in non_retryable:
            return False
        
        return True
    
    def _get_delay(self, error_type: ErrorType, attempt: int) -> float:
        """计算延迟时间 - 指数退避 + 抖动"""
        base_delays = {
            ErrorType.RATE_LIMIT: 60.0,
            ErrorType.TIMEOUT: 5.0,
            ErrorType.NETWORK: 3.0,
            ErrorType.SERVER_ERROR: 10.0,
            ErrorType.UNKNOWN: 2.0,
        }
        
        base = base_delays.get(error_type, 2.0)
        
        exponential = base * (2 ** attempt)
        
        jitter = random.uniform(-0.3, 0.3) * exponential
        
        delay = exponential + jitter
        
        max_delays = {
            ErrorType.RATE_LIMIT: 300.0,
            ErrorType.TIMEOUT: 60.0,
            ErrorType.NETWORK: 30.0,
            ErrorType.SERVER_ERROR: 120.0,
            ErrorType.UNKNOWN: 30.0,
        }
        
        max_delay = max_delays.get(error_type, 30.0)
        
        return min(delay, max_delay)
