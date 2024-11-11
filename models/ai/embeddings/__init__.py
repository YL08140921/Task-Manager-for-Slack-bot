from abc import ABC, abstractmethod
import numpy as np

class BaseEmbeddingModel(ABC):
    """
    埋め込みモデルの基底クラス
    全ての埋め込みモデルはこのクラスを継承する
    """
    
    def __init__(self, model_path: str):
        """
        Args:
            model_path (str): モデルファイルのパス
        """
        self.model_path = model_path
        self.model = None
        self.dimension = None
        self.load_model()
    
    @abstractmethod
    def load_model(self):
        """モデルの読み込み"""
        pass
    
    @abstractmethod
    def get_embedding(self, text: str) -> np.ndarray:
        """
        テキストの埋め込みベクトルを取得
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            np.ndarray: 埋め込みベクトル
        """
        pass
    
    @abstractmethod
    def get_similarity(self, text1: str, text2: str) -> float:
        """
        2つのテキスト間の類似度を計算
        
        Args:
            text1 (str): 1つ目のテキスト
            text2 (str): 2つ目のテキスト
            
        Returns:
            float: 類似度スコア（0-1）
        """
        pass
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        2つのベクトル間のコサイン類似度を計算
        
        Args:
            vec1 (np.ndarray): 1つ目のベクトル
            vec2 (np.ndarray): 2つ目のベクトル
            
        Returns:
            float: コサイン類似度
        """
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0
        return np.dot(vec1, vec2) / (norm1 * norm2)