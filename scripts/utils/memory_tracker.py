import psutil
import tracemalloc
import logging
from typing import Tuple, Dict
from datetime import datetime

class MemoryTracker:
    """メモリ使用量を追跡するユーティリティクラス"""
    
    def __init__(self, logger=None):
        """
        Args:
            logger: カスタムロガー（Noneの場合は新規作成）
        """
        self.process = psutil.Process()
        self.initial_memory = self.get_memory_usage()
        self.logger = logger or logging.getLogger(__name__)
        
        if not self.logger.handlers:
            self._setup_logger()
    
    def _setup_logger(self):
        """ロガーの初期設定"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def get_memory_usage(self) -> float:
        """
        現在のメモリ使用量を取得
        
        Returns:
            float: メモリ使用量（MB）
        """
        return self.process.memory_info().rss / 1024 / 1024
    
    def log_memory_usage(self, operation: str):
        """
        メモリ使用量の変化をログに記録
        
        Args:
            operation (str): 実行中の操作の説明
        """
        current_memory = self.get_memory_usage()
        diff = current_memory - self.initial_memory
        self.logger.info(
            f"{operation} - メモリ使用量: {current_memory:.2f}MB "
            f"(変化: {diff:+.2f}MB)"
        )
    
    def start_tracking(self) -> None:
        """メモリ追跡を開始"""
        tracemalloc.start()
    
    def stop_tracking(self) -> Tuple[float, float]:
        """
        メモリ追跡を停止し、使用量を取得
        
        Returns:
            Tuple[float, float]: (現在の使用量MB, ピーク時の使用量MB)
        """
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return current / 1024 / 1024, peak / 1024 / 1024
    
    def get_system_memory_info(self) -> Dict[str, float]:
        """
        システムのメモリ情報を取得
        
        Returns:
            Dict[str, float]: メモリ情報の辞書
        """
        memory = psutil.virtual_memory()
        return {
            "total": memory.total / 1024 / 1024 / 1024,  # GB
            "available": memory.available / 1024 / 1024 / 1024,  # GB
            "used": memory.used / 1024 / 1024 / 1024,  # GB
            "percent": memory.percent
        }
    
    def log_system_info(self):
        """システム情報をログに記録"""
        memory_info = self.get_system_memory_info()
        self.logger.info("\n=== システムメモリ情報 ===")
        self.logger.info(f"全メモリ: {memory_info['total']:.2f}GB")
        self.logger.info(f"使用可能: {memory_info['available']:.2f}GB")
        self.logger.info(f"使用中: {memory_info['used']:.2f}GB")
        self.logger.info(f"使用率: {memory_info['percent']}%")