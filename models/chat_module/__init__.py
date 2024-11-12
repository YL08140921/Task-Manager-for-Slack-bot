from .chat_bot import ChatBot
from .sentiment import SentimentAnalyzer

class ChatModule:
    """チャットモジュールのメインインターフェース"""
    
    def __init__(self):
        self.chat_bot = ChatBot()
        self.sentiment = SentimentAnalyzer()

    def get_response(self, text: str) -> str:
        """最適な応答を生成"""
        candidates = []
        
        # 各種応答を収集
        candidates.extend(self.chat_bot.get_keyword_responses(text))
        candidates.extend(self.chat_bot.get_noun_responses(text))
        candidates.extend(self.chat_bot.get_generic_responses())
        candidates.append(self.sentiment.analyze(text))
        
        # 最高スコアの応答を選択
        best_response = max(candidates, key=lambda x: x.score)
        return best_response.response