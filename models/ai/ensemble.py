from typing import List, Dict
import numpy as np
from .embeddings.word2vec_model import Word2VecModel
from .embeddings.fasttext_model import FastTextModel
from .embeddings.laser_model import LaserModel

class EnsembleModel:
    """
    複数の埋め込みモデルを組み合わせたアンサンブルモデル
    """
    
    def __init__(self, model_paths: Dict[str, str], weights: Dict[str, float] = None):
        """
        Args:
            model_paths (Dict[str, str]): 各モデルのファイルパス
            weights (Dict[str, float], optional): 各モデルの重み
        """
        self.models = {
            'word2vec': Word2VecModel(model_paths['word2vec']),
            'fasttext': FastTextModel(model_paths['fasttext']),
            'laser': LaserModel(model_paths['laser'])
        }
        
        # デフォルトの重み設定
        self.weights = weights or {
            'word2vec': 0.3,
            'fasttext': 0.3,
            'laser': 0.4
        }
    
    def get_weighted_similarity(self, text1: str, text2: str) -> float:
        """
        重み付きの類似度を計算
        
        Args:
            text1 (str): 1つ目のテキスト
            text2 (str): 2つ目のテキスト
            
        Returns:
            float: 重み付き類似度スコア（0-1）
        """
        scores = {}
        for name, model in self.models.items():
            scores[name] = model.get_similarity(text1, text2)
        
        weighted_score = sum(scores[name] * self.weights[name] 
                           for name in scores.keys())
        return weighted_score
    
    def adjust_weights(self, performance_scores: Dict[str, float]):
        """
        モデルの重みを性能に基づいて調整
        
        Args:
            performance_scores (Dict[str, float]): 各モデルの性能スコア
        """
        total_score = sum(performance_scores.values())
        if total_score == 0:
            return
            
        for name in self.weights.keys():
            self.weights[name] = performance_scores[name] / total_score