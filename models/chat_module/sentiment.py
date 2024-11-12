import pickle
from pathlib import Path
import random
import MeCab
from collections import Counter
from .chat_response import ChatResponse

class SentimentAnalyzer:
    """ネガポジ判定機能"""
    
    def __init__(self):
        self.mecab = MeCab.Tagger()
        self._load_model()

    def _load_model(self):
        """SVMモデルと単語リストの読み込み"""
        try:
            model_dir = Path(__file__).parent.parent.parent / "data" / "models" / "svm"
            
            with open(model_dir / "svmclassifier.pkl", 'rb') as f:
                self.classifier = pickle.load(f)
            
            self.word_list = []
            with open(model_dir / "basicFormList.txt", 'r', encoding='utf-8') as f:
                self.word_list = [line.strip() for line in f]
                
        except Exception as e:
            print(f"モデル読み込みエラー: {e}")
            self.classifier = None
            self.word_list = []

    def analyze(self, text: str) -> ChatResponse:
        """感情分析の実行"""
        if not self.classifier or not self.word_list:
            return ChatResponse("申し訳ありません", 0.1)

        words = self._tokenize(text)
        vector = self._vectorize(words)
        prediction = self.classifier.predict([vector])[0]
        
        response = "よかったね" if prediction == "1" else "ざんねん"
        return ChatResponse(response, 0.7 + random.random())