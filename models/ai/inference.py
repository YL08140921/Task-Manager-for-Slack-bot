from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import logging
from datetime import datetime, timedelta
from .ensemble import EnsembleModel
from utils.text_parser import TextParser

class AIInference:
    """
    AI推論を行うためのインターフェースクラス
    テキストからタスクの属性を推定する
    """
    
    def __init__(self, model_paths: Dict[str, str], weights: Optional[Dict[str, float]] = None):
        """
        Args:
            model_paths (Dict[str, str]): 各モデルのファイルパス
            weights (Optional[Dict[str, float]]): モデルの重み
        """
        # ロガーの設定
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # EnsembleModelの初期化
        try:
            self.ensemble = EnsembleModel(model_paths, weights)
            # TextParserのインスタンス化
            self.text_parser = TextParser()
            
            # 各分野のキーワードと参照文
            self.category_references = {
                category: " ".join(keywords)
                for category, keywords in self.text_parser.category_keywords.items()
            }
            # 優先度の参照文
            self.priority_references = {
                priority: " ".join(keywords)
                for priority, keywords in self.text_parser.priority_keywords.items()
            }
            
            # 期限表現
            self.deadline_expressions = self.text_parser.date_patterns
            
            self.logger.info("AIInference初期化完了")
        except Exception as e:
            self.logger.error(f"AIInference初期化エラー: {str(e)}")
            raise

    def estimate_category(self, text: str) -> Dict[str, Any]:
        """
        カテゴリを推定
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            Dict[str, Any]: 推定結果と信頼度
        """
        try:
            similarities = {}
            
            # 各カテゴリとの類似度を計算
            for category, reference in self.category_references.items():
                similarity = self.ensemble.get_weighted_similarity(text, reference)
                similarities[category] = similarity
                
            # 最も類似度が高いカテゴリを選択
            max_similarity = max(similarities.values())
            best_category = max(similarities.items(), key=lambda x: x[1])[0]
            
            # 信頼度スコアの計算
            confidence = max_similarity if max_similarity > 0.3 else 0
            
            return {
                "category": best_category,
                "confidence": confidence,
                "similarity_scores": similarities
            }
        except Exception as e:
            self.logger.error(f"カテゴリ推定エラー: {str(e)}")
            return {"category": None, "confidence": 0.0}

    def estimate_priority(self, text: str, deadline_days: Optional[int] = None) -> Dict[str, Any]:
        """
        優先度を推定
        
        優先度の判定基準：
        1. 期限ベース
            - 3日以内: 高
            - 7日以内: 中
            - それ以上: 低
        2. キーワードベース
            - 高: "緊急", "重要", "急ぐ", "即時"
            - 中: "通常", "標準"
            - 低: "余裕", "後回し"
        3. AIモデルによる類似度計算
        
        Args:
            text (str): 入力テキスト
            deadline_days (Optional[int]): 期限までの日数
            
        Returns:
            Dict[str, Any]: 推定結果と信頼度
        """
        try:
            # 優先度スコアの初期化
            priority_scores = {
                "高": 0.0,
                "中": 0.3,  # デフォルト値
                "低": 0.0
            }
            
            # 1. 期限による優先度
            if deadline_days is not None:
                deadline_priority = self._get_priority_from_deadline(deadline_days)
                priority_scores[deadline_priority] += 0.5
            
            # 2. キーワードによる優先度
            for priority, reference in self.priority_references.items():
                if any(keyword in text for keyword in reference.split()):
                    priority_scores[priority] += 0.4
            
            # 3. AIモデルによる類似度
            for priority, reference in self.priority_references.items():
                similarity = self.ensemble.get_weighted_similarity(text, reference)
                priority_scores[priority] += similarity * 0.3
            
            # 最終的な優先度を決定
            best_priority = max(priority_scores.items(), key=lambda x: x[1])
            max_score = best_priority[1]
            
            return {
                "priority": best_priority[0],
                "confidence": max_score if max_score > 0.3 else 0.3,
                "similarity_scores": priority_scores
            }
        except Exception as e:
            self.logger.error(f"優先度推定エラー: {str(e)}")
            return {"priority": "中", "confidence": 0.0}

    def estimate_deadline_expression(self, text: str) -> Dict[str, Any]:
        """
        期限の表現から推定日数を算出
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            Dict[str, Any]: 推定結果と信頼度
        """
        try:
            similarities = {}
            estimated_days = None
            max_similarity = 0
            matched_expression = None
            
            # 各期限表現との類似度を計算
            for expression, days in self.deadline_expressions.items():
                similarity = self.ensemble.get_weighted_similarity(text, expression)
                similarities[expression] = similarity
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    estimated_days = days
                    matched_expression = expression
            
            return {
                "estimated_days": estimated_days,
                "matched_expression": matched_expression,
                "confidence": max_similarity if max_similarity > 0.3 else 0,
                "similarity_scores": similarities
            }
        except Exception as e:
            self.logger.error(f"期限推定エラー: {str(e)}")
            return {"estimated_days": None, "confidence": 0.0}

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        テキストの総合的な分析を実行
        
        Args:
            text (str): 入力テキスト
            detailed (bool): 詳細な類似度スコアを含めるかどうか
            
        Returns:
            Dict[str, Any]: 分析結果
        """
        try:
            self.logger.info(f"テキスト分析開始: {text}")

            # テキストの長さチェック
            if len(text) > 1000:
                text = text[:1000]
                self.logger.warning("テキストが長すぎるため切り詰めました")
            
            # 各要素の推定
            deadline_info = self.estimate_deadline_expression(text)
            category_info = self.estimate_category(text)
            priority_info = self.estimate_priority(text, deadline_info["estimated_days"])
            
            # 総合的な信頼度の計算
            overall_confidence = self._calculate_overall_confidence(
                category_info["confidence"],
                priority_info["confidence"],
                deadline_info["confidence"]
            )
            
            result = {
                "deadline": {
                    "estimated_days": deadline_info["estimated_days"],
                    "expression": deadline_info["matched_expression"],
                    "confidence": deadline_info["confidence"]
                },
                "category": {
                    "name": category_info["category"],
                    "confidence": category_info["confidence"]
                },
                "priority": {
                    "level": priority_info["priority"],
                    "confidence": priority_info["confidence"]
                },
                "overall_confidence": overall_confidence
            }
            
            if detailed:
                result["details"] = {
                    "deadline": deadline_info.get("similarity_scores", {}),
                    "category": category_info.get("similarity_scores", {}),
                    "priority": priority_info.get("similarity_scores", {})
                }
            
            self.logger.info("テキスト分析完了")
            return result
            
        except Exception as e:
            self.logger.error(f"テキスト分析エラー: {str(e)}")
            return self._get_fallback_result()

    def _calculate_overall_confidence(
        self,
        category_confidence: float,
        priority_confidence: float,
        deadline_confidence: float
    ) -> float:
        """総合的な信頼度を計算"""
        weights = {'category': 0.4, 'priority': 0.3, 'deadline': 0.3}
        weighted_sum = (
            category_confidence * weights['category'] +
            priority_confidence * weights['priority'] +
            deadline_confidence * weights['deadline']
        )
        return round(weighted_sum, 3)

    def _get_priority_from_deadline(self, days: int) -> str:
        """
        期限までの日数から優先度を判定
        
        Args:
            days (int): 期限までの日数
            
        Returns:
            str: 優先度（高/中/低）
        """
        if days <= 3:
            return "高"
        elif days <= 7:
            return "中"
        else:
            return "低"

    def _get_fallback_result(self) -> Dict[str, Any]:
        """エラー時のフォールバック結果を生成"""
        return {
            "category": None,
            "priority": "中",
            "deadline": None,
            "confidence": 0.0,
            "error": True
        }

    def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        try:
            self.ensemble.cleanup()
            self.logger.info("リソースのクリーンアップ完了")
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {str(e)}")

    def __enter__(self):
        """コンテキストマネージャのエントリーポイント"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """コンテキストマネージャの終了処理"""
        self.cleanup()