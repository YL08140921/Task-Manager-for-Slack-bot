import unittest
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any
import json

# プロジェクトのルートディレクトリをPythonパスに追加
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from models.ai.embeddings.word2vec_model import Word2VecModel
from models.ai.embeddings.fasttext_model import FastTextModel
from models.ai.embeddings.laser_model import LaserModel
from models.ai.ensemble import EnsembleModel
from models.ai.inference import AIInference
from utils.text_parser import TextParser
from scripts.utils.memory_tracker import MemoryTracker

class TestModels(unittest.TestCase):
    """モデルテストクラス"""

    @classmethod
    def setUpClass(cls):
        """テスト環境のセットアップ"""
        # ロガーの設定
        cls.logger = logging.getLogger('TestModels')
        cls.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(ROOT_DIR / 'logs' / 'test_models.log')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        cls.logger.addHandler(handler)

        # メモリトラッカーの初期化
        cls.memory_tracker = MemoryTracker(cls.logger)

        # モデルパスの設定
        cls.model_paths = {
            'word2vec': str(ROOT_DIR / 'models' / 'ai' / 'pretrained' / 'word2vec' / 'japanese.model'),
            'fasttext': str(ROOT_DIR / 'models' / 'ai' / 'pretrained' / 'fasttext' / 'cc.ja.300.bin'),
            'laser': str(ROOT_DIR / 'models' / 'ai' / 'pretrained' / 'laser')
        }

        # テストケースの読み込み
        cls.test_cases = cls._load_test_cases()

    @staticmethod
    def _load_test_cases() -> Dict[str, Any]:
        """テストケースの読み込み"""
        test_data_path = ROOT_DIR / 'data' / 'training' / 'eval.json'
        with open(test_data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def setUp(self):
        """各テストケース実行前の準備"""
        self.memory_tracker.start_tracking()
        self.start_time = time.time()

    def tearDown(self):
        """各テストケース実行後の処理"""
        elapsed_time = time.time() - self.start_time
        current_memory, peak_memory = self.memory_tracker.stop_tracking()
        
        self.logger.info(
            f"テスト実行時間: {elapsed_time:.2f}秒, "
            f"現在のメモリ: {current_memory:.2f}MB, "
            f"ピークメモリ: {peak_memory:.2f}MB"
        )

    def test_individual_models(self):
        """個別モデルのテスト"""
        test_text = "機械学習の研究を行っています。"
        
        # Word2Vecのテスト
        self.logger.info("Word2Vecモデルのテスト開始")
        try:
            model = Word2VecModel(self.model_paths['word2vec'])
            embedding = model.get_embedding(test_text)
            self.assertIsNotNone(embedding)
            self.assertEqual(len(embedding.shape), 1)
        except Exception as e:
            self.logger.error(f"Word2Vecテストエラー: {str(e)}")
            raise

        # FastTextのテスト
        self.logger.info("FastTextモデルのテスト開始")
        try:
            model = FastTextModel(self.model_paths['fasttext'])
            embedding = model.get_embedding(test_text)
            self.assertIsNotNone(embedding)
            self.assertEqual(len(embedding.shape), 1)
        except Exception as e:
            self.logger.error(f"FastTextテストエラー: {str(e)}")
            raise

        # LASERのテスト
        self.logger.info("LASERモデルのテスト開始")
        try:
            model = LaserModel(self.model_paths['laser'])
            embedding = model.get_embedding(test_text)
            self.assertIsNotNone(embedding)
            self.assertEqual(len(embedding.shape), 1)
        except Exception as e:
            self.logger.error(f"LASERテストエラー: {str(e)}")
            raise

    def test_ensemble_model(self):
        """EnsembleModelのテスト"""
        self.logger.info("EnsembleModelのテスト開始")
        
        ensemble = EnsembleModel(self.model_paths)
        test_cases = [
            ("数学の課題を解く", "数学", "高"),
            ("来週までにレポートを提出", "理論", "中"),
            ("プログラミングの演習問題", "プログラミング", "低")
        ]

        for text, expected_category, expected_priority in test_cases:
            category_info = ensemble.estimate_category(text)
            priority_info = ensemble.estimate_priority(text)
            
            self.assertIsNotNone(category_info["category"])
            self.assertIsNotNone(priority_info["priority"])
            self.assertGreater(category_info["confidence"], 0)
            self.assertGreater(priority_info["confidence"], 0)

    def test_ai_inference(self):
        """AIInferenceのテスト"""
        self.logger.info("AIInferenceのテスト開始")
        
        inference = AIInference(self.model_paths)
        test_cases = [
            "明日までに数学のレポートを提出する",
            "来週末までにプログラミングの課題を完了させる",
            "統計学の演習問題を解く"
        ]

        for text in test_cases:
            result = inference.analyze_text(text)
            
            self.assertIsNotNone(result)
            self.assertIn("category", result)
            self.assertIn("priority", result)
            self.assertIn("deadline", result)
            self.assertIn("confidence", result)

    def test_text_parser(self):
        """TextParserのテスト"""
        self.logger.info("TextParserのテスト開始")
        
        parser = TextParser(self.model_paths)
        
        # 基本的なタスク入力のテスト
        text = "明日までに数学のレポートを提出する"
        result = parser.parse_task_info(text)
        self.assertIsNotNone(result)
        self.assertIn("title", result)
        self.assertIn("due_date", result)
        self.assertIn("priority", result)
        self.assertIn("category", result)
        
        # 曖昧な表現のテスト
        text = "そろそろ機械学習の課題をやらないと"
        result = parser.parse_task_info(text)
        self.assertIsNotNone(result)
        
        # 特殊文字を含む入力のテスト
        text = "数学：微分方程式の課題（期限：来週）"
        result = parser.parse_task_info(text)
        self.assertIsNotNone(result)
        
        # エラーケースのテスト
        text = ""
        result = parser.parse_task_info(text)
        self.assertIsNone(result)

    def test_end_to_end(self):
        """エンドツーエンドのテスト"""
        self.logger.info("エンドツーエンドテスト開始")
        
        parser = TextParser(self.model_paths)
        
        for test_case in self.test_cases:
            input_text = test_case["text"]
            expected = test_case["labels"]
            
            try:
                result = parser.parse_task_info(input_text)
                
                self.assertIsNotNone(result)
                if "category" in expected:
                    # カテゴリ予測の詳細をログ出力
                    self.logger.info(f"Input: {input_text}")
                    self.logger.info(f"Expected category: {expected['category']}")
                    self.logger.info(f"Predicted category: {result['category']}")
                    self.assertEqual(result["category"], expected["category"])
                if "priority" in expected:
                    self.assertEqual(result["priority"], expected["priority"])
                
            except Exception as e:
                self.logger.error(f"テストケース失敗: {input_text}")
                self.logger.error(f"エラー: {str(e)}")
                raise

    def test_performance(self):
        """パフォーマンステスト"""
        self.logger.info("パフォーマンステスト開始")
        
        parser = TextParser(self.model_paths)
        test_texts = [
            "明日までに数学のレポートを提出する",
            "来週末までにプログラミングの課題を完了させる",
            "統計学の演習問題を解く"
        ] * 3  # 複数回実行

        start_time = time.time()
        for text in test_texts:
            result = parser.parse_task_info(text)
            self.assertIsNotNone(result)
            
        elapsed_time = time.time() - start_time
        average_time = elapsed_time / len(test_texts)
        
        self.logger.info(f"平均処理時間: {average_time:.3f}秒/テキスト")
        self.assertLess(average_time, 1.5)  # 1テキストあたり1.5秒以内

def main():
    """メインのテスト実行関数"""
    # ロガーの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT_DIR / 'logs' / 'test_models.log')
        ]
    )
    
    # テストの実行
    unittest.main(verbosity=2)

if __name__ == '__main__':
    main()