from typing import List, Dict, Optional, Any
import numpy as np
import logging
from .embeddings.word2vec_model import Word2VecModel
from .embeddings.fasttext_model import FastTextModel
from .embeddings.laser_model import LaserModel
from utils.text_parser import TextParser

class EnsembleModel:
    """
    複数の埋め込みモデルを組み合わせたアンサンブルモデル
    """
    
    def __init__(self, model_paths: Dict[str, str], weights: Optional[Dict[str, float]] = None):
        """
        Args:
            model_paths (Dict[str, str]): 各モデルのファイルパス
            weights (Dict[str, float], optional): 各モデルの重み
        """
        # ロガーの初期化
        self.logger = logging.getLogger(__name__)
        
        # モデル関連の初期化
        self.models = {}
        self.model_status = {
            'word2vec': False,
            'fasttext': False,
            'laser': False
        }
        
        # デフォルトの重み設定
        self.weights = weights or {
            'word2vec': 0.3,
            'fasttext': 0.3,
            'laser': 0.4
        }

        # 優先度の参照テキストを初期化
        self.priority_references = {
            "高": "緊急 重要 急ぐ 即時 直ちに すぐ",
            "中": "通常 標準 普通",
            "低": "余裕 後回し そのうち いつか"
        }
        
        # カテゴリの参照テキストを初期化
        self.category_references = {
            "数学": "数式 計算 証明 代数 幾何",
            "統計学": "統計 確率 データ分析 回帰 分散",
            "機械学習": "AI 人工知能 深層学習 ニューラル"
        }
        
        # モデルの初期化（遅延ロード）
        self._initialize_models(model_paths)

        # TextParserのインスタンス化を遅延させる
        self._text_parser = None
        self.category_references = {}
        self.priority_references = {}
        
        # TextParserのマッピングを使用して参照テキストを生成
    @property
    def text_parser(self):
        """TextParserの遅延初期化"""
        # TextParserのマッピングを使用して参照テキストを生成
        if self._text_parser is None:
            self._text_parser = TextParser()
            self.category_references = {
                category: " ".join(keywords)
                for category, keywords in self._text_parser.category_keywords.items()
            }
            self.priority_references = {
                priority: " ".join(keywords)
                for priority, keywords in self._text_parser.priority_keywords.items()
            }
        return self._text_parser
    
    def _initialize_models(self, model_paths: Dict[str, str]) -> None:
        """モデルの遅延ロード初期化"""
        self.model_paths = model_paths
        self.models = {}

    def _load_model(self, model_name: str) -> bool:
        """
        指定されたモデルを必要時に読み込む
        
        Args:
            model_name (str): モデル名
            
        Returns:
            bool: 読み込み成功の場合True
        """
        if model_name in self.models:
            return True
            
        try:
            if model_name == 'word2vec':
                self.models[model_name] = Word2VecModel(self.model_paths[model_name])
            elif model_name == 'fasttext':
                self.models[model_name] = FastTextModel(self.model_paths[model_name])
            elif model_name == 'laser':
                self.models[model_name] = LaserModel(self.model_paths[model_name])
                
            self.model_status[model_name] = True
            return True
            
        except Exception as e:
            self.logger.error(f"{model_name}モデルの読み込みに失敗: {str(e)}")
            self.model_status[model_name] = False
            return False
    
    def get_weighted_similarity(self, text1: str, text2: str) -> float:
        """
        重み付きの類似度を計算
        
        Args:
            text1 (str): 1つ目のテキスト
            text2 (str): 2つ目のテキスト
            
        Returns:
            float: 重み付き類似度スコア（0-1）
        """
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
        
        if not similarities:
            return 0.0
            
        return sum(similarities) / total_weight if total_weight > 0 else 0.0

    def estimate_category(self, text: str) -> Dict[str, Any]:
        """
        カテゴリを推定
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            Dict[str, Any]: 推定結果と信頼度
        """
        similarities = {}
        
        for category, reference in self.category_references.items():
            similarity = self.get_weighted_similarity(text, reference)
            similarities[category] = similarity
        
        if not similarities:
            return {"category": None, "confidence": 0.0}
            
        best_category = max(similarities.items(), key=lambda x: x[1])
        return {
            "category": best_category[0],
            "confidence": best_category[1],
            "scores": similarities
        }

    def estimate_priority(self, text: str) -> Dict[str, Any]:
        """
        優先度を推定
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            Dict[str, Any]: 推定結果と信頼度
        """
        similarities = {}
        
        for priority, reference in self.priority_references.items():
            similarity = self.get_weighted_similarity(text, reference)
            similarities[priority] = similarity
        
        if not similarities:
            return {"priority": "中", "confidence": 0.5}
            
        best_priority = max(similarities.items(), key=lambda x: x[1])
        return {
            "priority": best_priority[0],
            "confidence": best_priority[1],
            "scores": similarities
        }

    def estimate_deadline(self, text: str) -> Dict[str, Any]:
        """
        期限を推定
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            Dict[str, Any]: 推定結果と信頼度
        """
        parser = TextParser()
        date_patterns = parser.date_patterns
        
        best_match = None
        max_similarity = 0
        deadline_days = None
        
        for pattern, days in date_patterns.items():
            similarity = self.get_weighted_similarity(text, pattern)
            if similarity > max_similarity:
                max_similarity = similarity
                best_match = pattern
                deadline_days = days
        
        if deadline_days and max_similarity > 0.3:
            deadline_date = datetime.now() + timedelta(days=deadline_days)
            return {
                "deadline": deadline_date.strftime('%Y-%m-%d'),
                "days": deadline_days,
                "confidence": max_similarity,
                "matched_pattern": best_match
            }
        
        return {"deadline": None, "confidence": 0.0}
    
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

    def cleanup(self) -> None:
        """メモリ解放のためのクリーンアップ"""
        for model in self.models.values():
            try:
                del model
            except Exception as e:
                self.logger.warning(f"モデルのクリーンアップ中にエラー: {str(e)}")
        self.models.clear()