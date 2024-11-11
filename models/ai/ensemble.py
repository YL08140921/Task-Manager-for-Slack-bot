from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import logging
from datetime import datetime, timedelta
from .embeddings.word2vec_model import Word2VecModel
from .embeddings.fasttext_model import FastTextModel
from .embeddings.laser_model import LaserModel
from gensim.models import KeyedVectors
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

    def generate_title(self, text: str) -> Dict[str, Any]:
        """
        テキストからタスクタイトルを生成
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            Dict[str, Any]: タイトル情報
        """
        try:
            # MeCabで形態素解析を実行
            words = self._tokenize_with_pos(text)
            
            # 不要な表現を除去
            filtered_words = []
            for word, pos in words:
                # 時間表現を除去
                if word in ['今日', '明日', '明後日', '今週', '来週', '今月']:
                    continue
                # 助詞・助動詞を除去
                if pos.startswith(('助詞', '助動詞')):
                    continue
                # 動詞の基本形を除去
                if pos.startswith('動詞') and word in ['する', 'やる', '行う', '実施']:
                    continue
                # その他の不要語を除去
                if word in ['必要', '予定', 'こと', 'もの', 'ため']:
                    continue
                    
                filtered_words.append((word, pos))

            # 重要度計算
            word_scores = {}
            for word, pos in filtered_words:
                # 品詞による重み付け
                base_weight = {
                    '名詞': 1.0,
                    '形容詞': 0.8,
                    '副詞': 0.6
                }.get(pos.split('-')[0], 0.4)
                
                # Word2Vecによる類似度計算
                try:
                    similarities = []
                    for other_word, _ in filtered_words:
                        if word != other_word:
                            sim = self.get_similarity(word, other_word)
                            similarities.append(sim)
                    
                    if similarities:
                        avg_similarity = sum(similarities) / len(similarities)
                        # 品詞の重みと類似度を組み合わせる
                        word_scores[word] = avg_similarity * base_weight
                    else:
                        word_scores[word] = base_weight * 0.5
                        
                except KeyError:
                    word_scores[word] = base_weight * 0.5

            if not word_scores:
                return {"title": text[:50], "confidence": 0.3}

            # スコアに基づいて重要な単語を抽出
            max_score = max(word_scores.values())
            threshold = max_score * 0.6  # 閾値を60%に設定
            
            # 重要な単語を位置順に並べ替え
            important_words = []
            for word, _ in filtered_words:
                if word in word_scores and word_scores[word] >= threshold:
                    important_words.append(word)

            # タイトルの生成
            title = "".join(important_words)
            
            # タイトルが空の場合のフォールバック
            if not title:
                return {"title": text[:50], "confidence": 0.3}
                
            # タイトルの長さ制限
            if len(title) > 50:
                title = title[:47] + "..."

            return {
                "title": title,
                "confidence": max_score,
                "word_scores": word_scores
            }

        except Exception as e:
            self.logger.error(f"タイトル生成エラー: {str(e)}")
            return {"title": text[:50], "confidence": 0.3}

    def _tokenize_with_pos(self, text: str) -> List[Tuple[str, str]]:
        """
        テキストを形態素解析し、単語と品詞のペアのリストを返す
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            List[Tuple[str, str]]: (単語, 品詞)のリスト
        """
        try:
            import MeCab
            mecab = MeCab.Tagger("-Ochasen")
            node = mecab.parseToNode(text)
            
            results = []
            while node:
                if node.surface:  # 空文字列でない場合
                    results.append((node.surface, node.feature.split(',')[0]))
                node = node.next
                
            return results
        except Exception as e:
            self.logger.error(f"形態素解析エラー: {str(e)}")
            return [(text, '名詞')]  # フォールバック

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
            
        # テキストに直接含まれるカテゴリを優先的に検出
        explicit_categories = [
            category for category in Task.VALID_CATEGORIES
            if category in text or 
            any(keyword in text for keyword in Task.CATEGORY_KEYWORDS[category])
        ]

        # 明示的なカテゴリがある場合はそれを使用
        if explicit_categories:
            final_categories = explicit_categories[:3]  # 最大3つまで
        else:
            # 明示的なカテゴリがない場合は類似度による推定を使用
            threshold = Task.CONFIDENCE["THRESHOLD"]
            high_similarity_categories = [
                category for category, score in sorted(
                    similarities.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                if score > threshold
            ]
            # 類似度による推定は最大2つまで
            final_categories = high_similarity_categories[:2]
            
            # カテゴリが全く見つからない場合のフォールバック
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