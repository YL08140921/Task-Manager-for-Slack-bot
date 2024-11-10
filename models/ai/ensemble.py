from typing import Dict, Any, Optional
import numpy as np
import logging
from datetime import datetime, timedelta
from .embeddings.word2vec_model import Word2VecModel
from .embeddings.fasttext_model import FastTextModel
from .embeddings.laser_model import LaserModel
from models.task import Task

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
        default_weights = {k.lower(): v for k, v in Task.CONFIDENCE["MODEL_WEIGHTS"].items()}
        self.weights = weights or default_weights
        
        # モデルの初期化（遅延ロード）
        self.model_paths = model_paths
        self.model_status = {name: False for name in ['word2vec', 'fasttext', 'laser']}

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
        
        if not total_weight:
            self.logger.warning("有効なモデルがありません。フォールバック値を返します。")
            return 0.5  # デフォルトの信頼度を返す
        
        return sum(similarities) / total_weight if similarities else 0.0 # 0.0 ~ 1.0の範囲

    def estimate_category(self, text: str) -> Dict[str, Any]:
        """
        カテゴリを推定
        
        Returns:
            Dict[str, Any]: {
                "categories": List[str],  # 検出されたカテゴリのリスト
                "confidence": float,      # 全体の信頼度
                "scores": Dict[str, float] # 各カテゴリの類似度スコア
            }
        """
        # 既存のカテゴリとの類似度計算
        similarities = {
            category: self.get_similarity(text, " ".join(keywords))
            for category, keywords in Task.CATEGORY_KEYWORDS.items()
        }
        
        if not similarities:
            return {
                "categories": [],
                "confidence": 0.0,
                "scores": {}
            }
            
        # 信頼度閾値を超えるカテゴリを全て抽出
        threshold = Task.CONFIDENCE["THRESHOLD"]
        matched_categories = [
            category for category, score in similarities.items()
            if score > threshold
        ]

        # テキストに直接含まれるカテゴリを検出
        explicit_categories = [
            category for category in Task.VALID_CATEGORIES
            if category in text or 
            any(keyword in text for keyword in Task.CATEGORY_KEYWORDS[category])
        ]
        
        # 新しいカテゴリの検出（既存カテゴリに含まれない単語）
        words = set(text.split())
        known_words = set()
        for keywords in Task.CATEGORY_KEYWORDS.values():
            known_words.update(keywords)
        
        new_categories = [
            word for word in words
            if (len(word) > 1 and  # 1文字の単語は除外
                word not in known_words and
                not any(word in keywords for keywords in Task.CATEGORY_KEYWORDS.values()))
        ]
        
        # 全ての結果をマージ
        final_categories = list(set(matched_categories + explicit_categories))
        
        # 新しいカテゴリを追加（既存のカテゴリが見つかった場合のみ）
        if final_categories and new_categories:
            final_categories.extend(new_categories)

        # 7. カテゴリが全く見つからない場合のフォールバック
        if not final_categories:
            best_category = max(similarities.items(), key=lambda x: x[1])[0]
            final_categories = [best_category]
        
        return {
            "categories": final_categories,
            "confidence": max(similarities.values()) if similarities else 0.0,
            "scores": similarities
        }

    def estimate_priority(self, text: str) -> Dict[str, Any]:
        """優先度を推定"""
        similarities = {
            Task.PRIORITY_HIGH: self.get_similarity(text, " ".join(Task.PRIORITY_KEYWORDS[Task.PRIORITY_HIGH])),
            Task.PRIORITY_MEDIUM: self.get_similarity(text, " ".join(Task.PRIORITY_KEYWORDS[Task.PRIORITY_MEDIUM])),
            Task.PRIORITY_LOW: self.get_similarity(text, " ".join(Task.PRIORITY_KEYWORDS[Task.PRIORITY_LOW]))
        }
        
        if not similarities:
            return {"priority": "低", "confidence": 0.0}
            
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
        
        if similarity > Task.CONFIDENCE["THRESHOLD"]:
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