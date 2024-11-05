from gensim.models import KeyedVectors
import numpy as np
from typing import List
import MeCab
from . import BaseEmbeddingModel

class Word2VecModel(BaseEmbeddingModel):
    """
    Word2Vecモデルを使用したテキスト埋め込み
    """
    
    def __init__(self, model_path: str):
        """
        Args:
            model_path (str): Word2Vecモデルファイルのパス
        """
        self.tagger = MeCab.Tagger("-Owakati")
        super().__init__(model_path)
    
    def load_model(self):
        """Word2Vecモデルの読み込み"""
        try:
            # バイナリ形式で読み込み
            self.model = KeyedVectors.load(self.model_path)
        except Exception as e:
            try:
                # 失敗した場合はword2vec形式で読み込み
                self.model = KeyedVectors.load_word2vec_format(
                    self.model_path,
                    binary=False,
                    encoding='utf-8'
                )
            except Exception as e:
                raise Exception(f"モデルの読み込みに失敗しました: {str(e)}")
        
        self.dimension = self.model.vector_size
    
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
            np.ndarray: 埋め込みベクトル（単語ベクトルの平均）
        """
        words = self.tokenize(text)
        word_vectors = []
        
        for word in words:
            try:
                vector = self.model[word]
                word_vectors.append(vector)
            except KeyError:
                continue
        
        if not word_vectors:
            return np.zeros(self.dimension)
        
        return np.mean(word_vectors, axis=0)
    
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