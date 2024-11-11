from laserembeddings import Laser
import numpy as np
from typing import List
import MeCab
from . import BaseEmbeddingModel

class LaserModel(BaseEmbeddingModel):
    """
    LASERモデルを使用したテキスト埋め込み
    """
    
    def __init__(self, model_path: str):
        """
        Args:
            model_path (str): LASERモデルファイルのパス
        """
        self.tagger = MeCab.Tagger("-Owakati")
        super().__init__(model_path)
    
    def load_model(self):
        """LASERモデルの読み込み"""
        self.model = Laser()
        # LASERの出力次元は1024固定
        self.dimension = 1024
    
    def get_embedding(self, text: str) -> np.ndarray:
        """
        テキストの埋め込みベクトルを取得
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            np.ndarray: 埋め込みベクトル
        """
        # LASERは言語を指定して埋め込みを取得
        embeddings = self.model.embed_sentences([text], lang='ja')
        return embeddings[0]
    
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