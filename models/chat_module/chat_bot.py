import random
import MeCab
from pathlib import Path
from typing import List
from .chat_response import KeywordRule, ChatResponse

class ChatBot:
    """基本的なチャットボット機能"""
    
    def __init__(self):
        self.mecab = MeCab.Tagger()
        self.rules = []
        self._load_rules()

    def _load_rules(self):
        """キーワードルールの読み込み"""
        rule_path = Path(__file__).parent.parent.parent / "data" / "rules" / "kw_matching_rule.txt"
        try:
            with open(rule_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if ',' in line:
                        keyword, response = line.strip().split(',', 1)
                        self.rules.append(KeywordRule(keyword, response))
        except Exception as e:
            print(f"ルール読み込みエラー: {e}")

    def get_keyword_responses(self, text: str) -> List[ChatResponse]:
        """キーワードマッチングによる応答生成"""
        responses = []
        for rule in self.rules:
            if rule.keyword in text:
                responses.append(
                    ChatResponse(rule.response, 1.0 + random.random())
                )
        return responses

    def get_noun_responses(self, text: str) -> List[ChatResponse]:
        """名詞を使用した応答生成"""
        responses = []
        suffixes = ["は好きですか？", "って何ですか？"]
        
        words = self.mecab.parse(text).split('\n')
        for word in words:
            if ',' in word:
                info = word.split('\t')
                if info[1].startswith('名詞'):
                    response = info[0] + random.choice(suffixes)
                    responses.append(
                        ChatResponse(response, 0.7 + random.random())
                    )
        return responses

    def get_generic_responses(self) -> List[ChatResponse]:
        """一般的な応答生成"""
        generic = ["なるほど", "それで？", "興味深いですね"]
        return [ChatResponse(
            random.choice(generic), 
            0.5 + random.random()
        )]