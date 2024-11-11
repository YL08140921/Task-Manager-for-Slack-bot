import fasttext
import numpy as np
from typing import List
import MeCab
from . import BaseEmbeddingModel

class FastTextModel(BaseEmbeddingModel):
    """
    FastTextモデルを使用したテキスト埋め込み
    """
    
    def __init__(self, model_path: str):
        """
        Args:
            model_path (str): FastTextモデルファイルのパス
        """
        self.tagger = MeCab.Tagger("-Owakati")
        super().__init__(model_path)
    
    def load_model(self):
        """FastTextモデルの読み込み"""
        self.model = fasttext.load_model(self.model_path)
        # FastTextの出力次元は300固定
        self.dimension = 300
    
    def tokenize(self, text: str) -> List[str]:
        """
        テキストを分かち書きする
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            List[str]: 分かち書きされた単語リスト
        """
        return self.tagger.parse(text).strip().split()
    
    def get_embedding(self, text: str) -> np.ndarray:
        """
        テキストの埋め込みベクトルを取得
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            np.ndarray: 埋め込みベクトル
        """
        # FastTextはテキスト全体の埋め込みを直接取得可能
        return self.model.get_sentence_vector(text)
    
    def get_similarity(self, text1: str, text2: str) -> float:
        """
        2つのテキスト間の類似度を計算
        
        Args:
            text1 (str): 1つ目のテキスト
            text2 (str): 2つ目のテキスト
            
        Returns:
            float: 類似度スコア（0-1）
        """
        vec1 = self.get_embedding(text1)
        vec2 = self.get_embedding(text2)
        return self.cosine_similarity(vec1, vec2)