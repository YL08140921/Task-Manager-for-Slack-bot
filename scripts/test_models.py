import unittest
import numpy as np
from datetime import datetime, timedelta
from models.ai.embeddings.word2vec_model import Word2VecModel
from models.ai.embeddings.fasttext_model import FastTextModel
from models.ai.embeddings.laser_model import LaserModel
from models.ai.ensemble import EnsembleModel
from models.ai.inference import AIInference
from utils.text_parser import TextParser
from scripts.utils.memory_tracker import MemoryTracker

class TestEmbeddingModels(unittest.TestCase):
    """埋め込みモデルの単体テスト"""
    
    def setUp(self):
        self.memory_tracker = MemoryTracker()
        self.test_texts = [
            "数学の課題を完了する",
            "統計学のレポートを提出",
            "機械学習の実装を行う"
        ]
        self.model_paths = {
            'word2vec': 'models/ai/pretrained/word2vec/japanese.model',
            'fasttext': 'models/ai/pretrained/fasttext/cc.ja.300.bin',
            'laser': 'models/ai/pretrained/laser/bilstm.93langs.2018-12-26.pt'
        }
        
    def test_word2vec_model(self):
        self.memory_tracker.start_tracking()
        self.memory_tracker.log_memory_usage("Word2Vecモデルのテスト開始")
        
        try:
            model = Word2VecModel(self.model_paths['word2vec'])
            for text in self.test_texts:
                embedding = model.get_embedding(text)
                self.assertEqual(len(embedding), model.dimension)
                self.assertTrue(isinstance(embedding, np.ndarray))
        finally:
            current, peak = self.memory_tracker.stop_tracking()
            self.memory_tracker.log_memory_usage(
                f"Word2Vecテスト完了 (ピーク時使用量: {peak:.2f}MB)"
            )
                
    def test_fasttext_model(self):
        self.memory_tracker.start_tracking()
        self.memory_tracker.log_memory_usage("FastTextモデルのテスト開始")
        
        model = FastTextModel(self.model_paths['fasttext'])
        for text in self.test_texts:
            embedding = model.get_embedding(text)
            self.assertEqual(len(embedding), 300)
            
        current, peak = self.memory_tracker.stop_tracking()
        self.memory_tracker.log_memory_usage(
            f"FastTextテスト完了 (ピーク時使用量: {peak:.2f}MB)"
        )
                
    def test_laser_model(self):
        self.memory_tracker.start_tracking()
        self.memory_tracker.log_memory_usage("LASERモデルのテスト開始")
        
        model = LaserModel(self.model_paths['laser'])
        for text in self.test_texts:
            embedding = model.get_embedding(text)
            self.assertEqual(len(embedding), 1024)
            
        current, peak = self.memory_tracker.stop_tracking()
        self.memory_tracker.log_memory_usage(
            f"LASERテスト完了 (ピーク時使用量: {peak:.2f}MB)"
        )

class TestEnsembleModel(unittest.TestCase):
    """EnsembleModelの単体テスト"""
    
    def setUp(self):
        self.model_paths = {
            'word2vec': 'models/ai/pretrained/word2vec/japanese.model',
            'fasttext': 'models/ai/pretrained/fasttext/cc.ja.300.bin',
            'laser': 'models/ai/pretrained/laser/bilstm.93langs.2018-12-26.pt'
        }
        self.ensemble = EnsembleModel(self.model_paths)
        
    def test_priority_estimation(self):
        test_cases = [
            ("急いで完了させる必要がある", "高"),
            ("そのうち対応する", "低"),
            ("来週までに終わらせる", "中")
        ]
        
        for text, expected in test_cases:
            result = self.ensemble.estimate_priority(text)
            self.assertEqual(result["priority"], expected)
            
    def test_category_estimation(self):
        test_cases = [
            ("数式の証明問題", "数学"),
            ("機械学習モデルの実装", "機械学習"),
            ("統計データの分析", "統計学")
        ]
        
        for text, expected in test_cases:
            result = self.ensemble.estimate_category(text)
            self.assertEqual(result["category"], expected)

class TestTextParser(unittest.TestCase):
    """TextParserの単体テスト"""
    
    def setUp(self):
        self.parser = TextParser()
        
    def test_basic_input(self):
        test_cases = [
            {
                "input": "明日までに数学の課題を完了する",
                "expected": {
                    "title": "数学の課題",
                    "category": "数学",
                    "priority": "高",
                    "due_date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                }
            },
            {
                "input": "統計学のレポートを来週までに提出",
                "expected": {
                    "title": "統計学のレポート",
                    "category": "統計学",
                    "priority": "中",
                    "due_date": (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                }
            }
        ]
        
        for case in test_cases:
            result = self.parser.parse_task_info(case["input"])
            self.assertIsNotNone(result)
            for key, value in case["expected"].items():
                self.assertEqual(result[key], value)
        
    def test_ambiguous_input(self):
        text = "そのうち統計の勉強をする"
        result = self.parser.parse_task_info(text)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "統計学")
        self.assertIsNone(result["due_date"])
        self.assertEqual(result["priority"], "低")
        
    def test_error_cases(self):
        test_cases = [
            "",  # 空文字
            "a" * 1001,  # 文字数制限超過
            "invalid|format|text"  # 不正なフォーマット
        ]
        
        for text in test_cases:
            result = self.parser.parse_task_info(text)
            self.assertFalse(result["success"])

class TestIntegration(unittest.TestCase):
    """統合テスト"""
    
    def setUp(self):
        self.model_paths = {
            'word2vec': 'models/ai/pretrained/word2vec/japanese.model',
            'fasttext': 'models/ai/pretrained/fasttext/cc.ja.300.bin',
            'laser': 'models/ai/pretrained/laser/bilstm.93langs.2018-12-26.pt'
        }
        self.parser = TextParser(self.model_paths)
        self.memory_tracker = MemoryTracker()
        
    def test_end_to_end(self):
        test_cases = [
            {
                "input": "明日までに数学の課題を完了する！優先度：高",
                "expected": {
                    "category": "数学",
                    "priority": "高",
                    "due_date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                }
            },
            {
                "input": "機械学習の実装をそのうちやる",
                "expected": {
                    "category": "機械学習",
                    "priority": "低",
                    "due_date": None
                }
            }
        ]

        self.memory_tracker.start_tracking()
        self.memory_tracker.log_memory_usage("統合テスト開始")
        
        for case in test_cases:
            with self.memory_tracker:
                result = self.parser.parse_task_info(case["input"])
                self.assertIsNotNone(result)
                for key, value in case["expected"].items():
                    self.assertEqual(result[key], value)

        current, peak = self.memory_tracker.stop_tracking()
        self.memory_tracker.log_memory_usage(
            f"統合テスト完了 (ピーク時使用量: {peak:.2f}MB)"
        )
                
    def test_performance(self):
        """パフォーマンステスト"""
        long_text = "数学の課題 " * 10
        
        self.memory_tracker.start_tracking()
        self.memory_tracker.log_memory_usage("パフォーマンステスト開始")
        
        start_time = datetime.now()
        result = self.parser.parse_task_info(long_text)
        duration = (datetime.now() - start_time).total_seconds()
        
        current, peak = self.memory_tracker.stop_tracking()
        self.memory_tracker.log_memory_usage(
            f"パフォーマンステスト完了 (実行時間: {duration:.2f}秒, "
            f"ピーク時使用量: {peak:.2f}MB)"
        )
        
        self.assertTrue(duration < 5.0)  # 5秒以内に処理が完了することが条件

if __name__ == '__main__':
    unittest.main(verbosity=2)