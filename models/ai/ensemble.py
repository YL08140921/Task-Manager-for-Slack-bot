from typing import Dict, Any, Optional
import numpy as np
import logging
from datetime import datetime, timedelta
from .embeddings.word2vec_model import Word2VecModel
from .embeddings.fasttext_model import FastTextModel
from .embeddings.laser_model import LaserModel

class EnsembleModel:
    """複数の埋め込みモデルを組み合わせたアンサンブルモデル"""
    
    def __init__(self, model_paths: Dict[str, str], weights: Optional[Dict[str, float]] = None):
        """
        Args:
            model_paths (Dict[str, str]): 各モデルのファイルパス
            weights (Optional[Dict[str, float]]): モデルの重み
        """
        self.logger = logging.getLogger(__name__)
        self.models = {}
        self.model_status = {}
        
        # デフォルトの重み設定
        self.weights = weights or {
            'word2vec': 0.3,
            'fasttext': 0.3,
            'laser': 0.4
        }
        
        # モデルの初期化（遅延ロード）
        self.model_paths = model_paths
        self.model_status = {name: False for name in ['word2vec', 'fasttext', 'laser']}
        
        # 参照テキストの定義
        self.category_references = {
            "数学": "数式 計算 証明 定理 微分 積分",
            "統計学": "確率 分布 推定 検定 標本",
            "機械学習": "モデル 学習 予測 分類",
            "理論": "概念 定義 公理 法則",
            "プログラミング": "コード 実装 開発 デバッグ"
        }
        
        self.priority_references = {
            "高": "緊急 重要 即時 必須",
            "中": "通常 標準 普通",
            "低": "余裕 後回し 緩い"
        }

    def _load_model(self, model_name: str) -> bool:
        """モデルの遅延ロード"""
        if model_name in self.models:
            return True
            
        try:
            model_classes = {
                'word2vec': Word2VecModel,
                'fasttext': FastTextModel,
                'laser': LaserModel
            }
            self.models[model_name] = model_classes[model_name](self.model_paths[model_name])
            self.model_status[model_name] = True
            return True
        except Exception as e:
            self.logger.error(f"{model_name}モデルの読み込みに失敗: {str(e)}")
            return False

    def get_similarity(self, text1: str, text2: str) -> float:
        """テキスト間の類似度を計算"""
        similarities = []
        total_weight = 0
        
        for model_name, weight in self.weights.items():
            if self._load_model(model_name):
                try:
                    similarity = self.models[model_name].get_similarity(text1, text2)
                    similarities.append(similarity * weight)
                    total_weight += weight
                except Exception as e:
                    self.logger.warning(f"{model_name}での類似度計算エラー: {str(e)}")
        
        return sum(similarities) / total_weight if similarities else 0.0

    def estimate_category(self, text: str) -> Dict[str, Any]:
        """カテゴリを推定"""
        similarities = {
            category: self.get_similarity(text, reference)
            for category, reference in self.category_references.items()
        }
        
        if not similarities:
            return {"category": None, "confidence": 0.0}
            
        best_category = max(similarities.items(), key=lambda x: x[1])
        return {
            "category": best_category[0],
            "confidence": best_category[1],
            "scores": similarities
        }

    def estimate_priority(self, text: str) -> Dict[str, Any]:
        """優先度を推定"""
        similarities = {
            priority: self.get_similarity(text, reference)
            for priority, reference in self.priority_references.items()
        }
        
        if not similarities:
            return {"priority": "中", "confidence": 0.0}
            
        best_priority = max(similarities.items(), key=lambda x: x[1])
        return {
            "priority": best_priority[0],
            "confidence": best_priority[1],
            "scores": similarities
        }

    def estimate_deadline(self, text: str) -> Dict[str, Any]:
        """期限を推定"""
        date_patterns = {
            "明日": 1,
            "明後日": 2,
            "今週中": 7,
            "来週": 7,
            "今月中": 30
        }
        
        best_pattern = max(
            date_patterns.items(),
            key=lambda x: self.get_similarity(text, x[0])
        )
        similarity = self.get_similarity(text, best_pattern[0])
        
        if similarity > 0.3:
            deadline_date = datetime.now() + timedelta(days=best_pattern[1])
            return {
                "deadline": deadline_date.strftime('%Y-%m-%d'),
                "days": best_pattern[1],
                "confidence": similarity,
                "matched_pattern": best_pattern[0]
            }
        
        return {"deadline": None, "confidence": 0.0}

    def cleanup(self) -> None:
        """メモリ解放"""
        for model in self.models.values():
            del model
        self.models.clear()