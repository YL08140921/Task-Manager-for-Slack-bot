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
            self.logger.info(f"\n=== テキスト分析開始 ===")
            self.logger.info(f"入力テキスト: {text}")

            # タイトル生成を追加
            self.logger.info("\n--- タイトル生成 ---")
            title_info = self.ensemble.generate_title(text)
            self.logger.info(f"生成タイトル: {title_info['title']}")
            self.logger.info(f"タイトル生成の信頼度: {title_info['confidence']:.3f}")
            
            # カテゴリ推定
            self.logger.info("\n--- カテゴリ推定 ---")
            category_info = self.ensemble.estimate_category(text)
            self.logger.info(f"検出カテゴリ: {category_info['categories']}")
            self.logger.info(f"カテゴリごとの類似度:")
            for category, score in category_info.get("scores", {}).items():
                self.logger.info(f"  - {category}: {score:.3f}")
            self.logger.info(f"カテゴリ推定の信頼度: {category_info['confidence']:.3f}")

            # 優先度推定
            self.logger.info("\n--- 優先度推定 ---")
            priority_info = self.ensemble.estimate_priority(text)
            self.logger.info(f"判定された優先度: {priority_info['priority']}")
            self.logger.info(f"優先度ごとの類似度:")
            for priority, score in priority_info.get("scores", {}).items():
                self.logger.info(f"  - {priority}: {score:.3f}")
            self.logger.info(f"優先度推定の信頼度: {priority_info['confidence']:.3f}")

            # 期限推定
            self.logger.info("\n--- 期限推定 ---")
            deadline_info = self.ensemble.estimate_deadline(text)
            if deadline_info.get("deadline"):
                self.logger.info(f"推定された期限: {deadline_info['deadline']}")
                self.logger.info(f"マッチしたパターン: {deadline_info.get('matched_pattern')}")
                self.logger.info(f"期限までの日数: {deadline_info.get('days')}日")
            else:
                self.logger.info("期限は指定されていません")
            self.logger.info(f"期限推定の信頼度: {deadline_info.get('confidence', 0):.3f}")

            # 総合結果の構築
            confidence = self._calculate_confidence([
                title_info["confidence"],
                category_info["confidence"],
                priority_info["confidence"],
                deadline_info.get("confidence", 0)
            ])
            
            # 結果の構築
            result = {
                "title": title_info["title"],
                "categories": category_info["categories"],
                "priority": priority_info["priority"],
                "deadline": deadline_info.get("deadline"),
                "confidence": confidence
            }
            
            if detailed:
                result["details"] = {
                    "title": title_info,
                    "category": category_info,
                    "priority": priority_info,
                    "deadline": deadline_info
                }

            self.logger.info("\n=== 分析結果 ===")
            self.logger.info(f"タイトル: {result['title']}")
            self.logger.info(f"カテゴリ: {result['categories']}")
            self.logger.info(f"優先度: {result['priority']}")
            self.logger.info(f"期限: {result['deadline'] or '指定なし'}")
            self.logger.info(f"総合信頼度: {confidence:.3f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"テキスト分析エラー")
            self.logger.error(f"エラー内容: {str(e)}")
            return self._get_fallback_result()
    
    def _get_fallback_result(self) -> Dict[str, Any]:
        """エラー時のフォールバック結果"""
        return {
            "title": "",
            "categories": [], 
            "priority": "中",
            "deadline": None,
            "confidence": 0.0,
            "error": True
        }

    def _calculate_confidence(self, scores: list) -> float:
        """信頼度スコアの計算"""
        return round(sum(scores) / len(scores), 3)

    def _get_fallback_result(self) -> Dict[str, Any]:
        """エラー時のフォールバック結果"""
        return {
            "categories": [], 
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