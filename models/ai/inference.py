from typing import Dict, Any, Optional
import logging
from datetime import datetime
from .ensemble import EnsembleModel

class AIInference:
    """AIモデルを使用したテキスト解析インターフェース"""
    
    def __init__(self, model_paths: Dict[str, str], weights: Optional[Dict[str, float]] = None):
        """
        Args:
            model_paths (Dict[str, str]): モデルファイルパス
            weights (Optional[Dict[str, float]]): モデルの重み
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        try:
            self.ensemble = EnsembleModel(model_paths, weights)
            self.logger.info("AIInference初期化完了")
        except Exception as e:
            self.logger.error(f"AIInference初期化エラー: {str(e)}")
            raise

    def analyze_text(self, text: str, detailed: bool = False) -> Dict[str, Any]:
        """テキストの総合的な分析を実行"""
        try:
            self.logger.info(f"テキスト分析開始: {text}")
            
            # 各要素の推定
            category_info = self.ensemble.estimate_category(text)
            priority_info = self.ensemble.estimate_priority(text)
            deadline_info = self.ensemble.estimate_deadline(text)
            
            # 結果の構築
            result = {
                "category": category_info["category"],
                "priority": priority_info["priority"],
                "deadline": deadline_info.get("deadline"),
                "confidence": self._calculate_confidence([
                    category_info["confidence"],
                    priority_info["confidence"],
                    deadline_info.get("confidence", 0)
                ])
            }
            
            if detailed:
                result["details"] = {
                    "category": category_info,
                    "priority": priority_info,
                    "deadline": deadline_info
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"テキスト分析エラー: {str(e)}")
            return self._get_fallback_result()

    def _calculate_confidence(self, scores: list) -> float:
        """信頼度スコアの計算"""
        return round(sum(scores) / len(scores), 3)

    def _get_fallback_result(self) -> Dict[str, Any]:
        """エラー時のフォールバック結果"""
        return {
            "category": None,
            "priority": "中",
            "deadline": None,
            "confidence": 0.0,
            "error": True
        }

    def cleanup(self) -> None:
        """リソース解放"""
        try:
            self.ensemble.cleanup()
            self.logger.info("リソースのクリーンアップ完了")
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {str(e)}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()