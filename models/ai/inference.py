from typing import Dict, Any, Optional, List, Tuple
import numpy as np
from datetime import datetime, timedelta
from .ensemble import EnsembleModel

class AIInference:
    """
    AI推論を行うためのインターフェースクラス
    テキストからタスクの属性を推定する
    """
    
    def __init__(self, model_paths: Dict[str, str]):
        """
        Args:
            model_paths (Dict[str, str]): 各モデルのファイルパス
        """
        self.ensemble = EnsembleModel(model_paths)
        
        # 各分野のキーワードと参照文
        self.category_references = {
            "数学": "数式 計算 証明 定理 微分 積分 代数 幾何",
            "統計学": "確率 分布 推定 検定 標本 回帰 相関",
            "機械学習": "モデル 学習 予測 分類 特徴量 精度 評価",
            "理論": "概念 定義 公理 法則 命題 証明 理論",
            "プログラミング": "コード 実装 開発 デバッグ アルゴリズム 関数 クラス"
        }
        
        # 優先度の参照文
        self.priority_references = {
            "高": "緊急 重要 即時 必須 急ぎ 期限切迫 絶対",
            "中": "通常 標準 普通 一般的 そろそろ",
            "低": "余裕 後回し 緩い ゆっくり いつでも"
        }
        
        # 期限に関する表現と日数のマッピング
        self.deadline_expressions = {
            "すぐ": 1,
            "急いで": 2,
            "なるべく早く": 3,
            "今週中": 7,
            "来週まで": 14,
            "そのうち": 30
        }

    def estimate_category(self, text: str) -> Dict[str, Any]:
        """
        カテゴリを推定
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            Dict[str, Any]: 推定結果と信頼度
        """
        similarities = {}
        confidence_scores = {}
        
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

    def estimate_priority(self, text: str, deadline_days: Optional[int] = None) -> Dict[str, Any]:
        """
        優先度を推定
        
        Args:
            text (str): 入力テキスト
            deadline_days (Optional[int]): 期限までの日数
            
        Returns:
            Dict[str, Any]: 推定結果と信頼度
        """
        similarities = {}
        
        # テキストと各優先度の参照文との類似度を計算
        for priority, reference in self.priority_references.items():
            similarity = self.ensemble.get_weighted_similarity(text, reference)
            similarities[priority] = similarity
        
        # 期限が設定されている場合、期限に基づいて優先度を調整
        if deadline_days is not None:
            deadline_priority = self._get_priority_from_deadline(deadline_days)
            # テキストベースの類似度と期限ベースの優先度を組み合わせる
            similarities[deadline_priority] += 0.3
        
        # 最も高いスコアの優先度を選択
        max_similarity = max(similarities.values())
        best_priority = max(similarities.items(), key=lambda x: x[1])[0]
        
        # 信頼度スコアの計算
        confidence = max_similarity if max_similarity > 0.3 else 0
        
        return {
            "priority": best_priority,
            "confidence": confidence,
            "similarity_scores": similarities
        }

    def estimate_deadline_expression(self, text: str) -> Dict[str, Any]:
        """
        期限の表現から推定日数を算出
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            Dict[str, Any]: 推定結果と信頼度
        """
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
        
        # 信頼度スコアの計算
        confidence = max_similarity if max_similarity > 0.3 else 0
        
        return {
            "estimated_days": estimated_days,
            "matched_expression": matched_expression,
            "confidence": confidence,
            "similarity_scores": similarities
        }

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        テキストの総合的な分析を実行
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            Dict[str, Any]: 分析結果
        """
        # 期限の推定
        deadline_info = self.estimate_deadline_expression(text)
        estimated_days = deadline_info["estimated_days"]
        
        # カテゴリの推定
        category_info = self.estimate_category(text)
        
        # 優先度の推定
        priority_info = self.estimate_priority(text, estimated_days)
        
        # 総合的な信頼度の計算
        overall_confidence = np.mean([
            deadline_info["confidence"],
            category_info["confidence"],
            priority_info["confidence"]
        ])
        
        return {
            "deadline": {
                "estimated_days": estimated_days,
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

    def get_performance_metrics(self) -> Dict[str, float]:
        """
        各モデルの性能メトリクスを取得
        
        Returns:
            Dict[str, float]: モデルごとの性能スコア
        """
        # 実際の運用では、評価用データセットを使用して
        # 各モデルの性能を計算する
        return {
            'word2vec': 0.85,
            'fasttext': 0.88,
            'laser': 0.92
        }

    def update_model_weights(self):
        """モデルの重みを性能に基づいて更新"""
        performance_scores = self.get_performance_metrics()
        self.ensemble.adjust_weights(performance_scores)