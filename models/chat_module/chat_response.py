class KeywordRule:
    """キーワードと応答のマッチングルール"""
    def __init__(self, keyword: str, response: str):
        self.keyword = keyword
        self.response = response

class ChatResponse:
    """チャット応答候補"""
    def __init__(self, response: str, score: float):
        self.response = response
        self.score = score