"""
ResultValidatorのテストモジュール
基本的なフィールド検証、ルールベース検証、AI結合、期限ベース優先度、警告生成をテスト
エッジケース、統合テストも行う
"""

import unittest
from datetime import datetime, timedelta
from models.ai.validator import ResultValidator
from models.task import Task
import logging

class TestResultValidator(unittest.TestCase):
    """ResultValidatorのテストケース"""
    
    def setUp(self):
        """テストの前準備"""
        # デバッグログの設定
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        self.validator = ResultValidator()
        # 基本的なルールベース結果
        self.base_rule_result = {
            "title": "テストタスク",
            "due_date": None,
            "priority": "中",
            "category": "数学",
            "confidence": {
                "title": 0.8,
                "priority": 0.6,
                "category": 0.7
            }
        }
        # 基本的なAI結果
        self.base_ai_result = {
            "category": "プログラミング",
            "priority": "高",
            "deadline": None,
            "confidence": 0.85
        }

    def test_basic_field_validation(self):
        """基本的なフィールド検証のテスト"""
        # タイトル必須チェック
        result = self.validator.validate_results({}, None)
        self.assertEqual(result["title"], "無題のタスク")
        
        # 優先度のデフォルト値チェック
        result = self.validator.validate_results({"title": "テスト"}, None)
        self.assertEqual(result["priority"], Task.PRIORITY_MEDIUM)
        
        # カテゴリの検証
        invalid_result = self.validator.validate_results({
            "title": "テスト",
            "category": "無効なカテゴリ"
        }, None)
        self.assertIsNone(invalid_result["category"])
        
        # 期限のフォーマット検証
        invalid_date = self.validator.validate_results({
            "title": "テスト",
            "due_date": "不正な日付"
        }, None)
        self.assertIsNone(invalid_date["due_date"])

    def test_rule_based_only(self):
        """ルールベースのみの結果検証"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        rule_result = {
            "title": "数学の課題",
            "due_date": tomorrow,
            "priority": "高",
            "category": "数学",
            "confidence": {
                "title": 0.9,
                "due_date": 0.8,
                "priority": 0.7,
                "category": 0.8
            }
        }
        
        result = self.validator.validate_results(rule_result, None)
        
        # 各フィールドの検証
        self.assertEqual(result["title"], "数学の課題")
        self.assertEqual(result["due_date"], tomorrow)
        self.assertEqual(result["priority"], "高")
        self.assertEqual(result["category"], "数学")
        self.assertTrue("warnings" in result)

    def test_ai_rule_combination(self):
        """AIとルールベースの結合テスト"""
        # ルールベースの信頼度が低く、AIの信頼度が高い場合
        rule_result = {
            "title": "プログラミング課題",
            "priority": "中",
            "category": "プログラミング",
            "confidence": {
                "title": 0.6,
                "priority": 0.5,
                "category": 0.5
            }
        }
        
        ai_result = {
            "priority": "高",
            "category": "プログラミング",
            "confidence": 0.9
        }
        
        result = self.validator.validate_results(rule_result, ai_result)
        
        # AIの高信頼度の結果が採用されているか確認
        self.assertEqual(result["priority"], "高")
        self.assertEqual(result["title"], "プログラミング課題")  # タイトルはルールベース優先

    def test_deadline_priority_adjustment(self):
        """期限ベースの優先度調整テスト"""
        # 期限切れのタスク
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        result = self.validator.validate_results({
            "title": "テスト",
            "due_date": yesterday,
            "priority": "中",
            "confidence": {"priority": 0.6}
        }, None)
        self.assertEqual(result["priority"], "高")  # 期限切れは必ず高優先度
        self.assertTrue(any("期限切れ" in w for w in result["warnings"]))

        # 当日期限のタスク
        today = datetime.now().strftime("%Y-%m-%d")
        result = self.validator.validate_results({
            "title": "テスト",
            "due_date": today,
            "priority": "中",
            "confidence": {"priority": 0.6}
        }, None)
        self.assertEqual(result["priority"], "高")  # 当日も高優先度

        #3日後が期限のタスク（緊急）
        three_days_later = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        result = self.validator.validate_results({
            "title": "テスト",
            "due_date": three_days_later,
            "priority": "中",
            "confidence": {"priority": 0.6}
        }, None)
        self.assertEqual(result["priority"], "高")  # 3日以内は高優先度
        
        # 7日後が期限のタスク（要注意）
        week_later = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        result = self.validator.validate_results({
            "title": "テスト",
            "due_date": week_later,
            "priority": "高",
            "confidence": {"priority": 0.6}
        }, None)
        self.assertEqual(result["priority"], "中")  # 7日以内は中優先度
      
        #8日以降が期限のタスク（余裕あり）
        far_future = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        result = self.validator.validate_results({
            "title": "テスト",
            "due_date": far_future,
            "priority": "高",
            "confidence": {"priority": 0.6}
        }, None)
        self.assertEqual(result["priority"], "低")  # 7日超は低優先度

    def test_warning_message_generation(self):
        """警告メッセージ生成テスト"""
        # 期限切れのタスク
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        result = self.validator.validate_results({
            "title": "テスト",
            "due_date": yesterday,
            "priority": "中",
            "confidence": {}
        }, None)
        
        # 期限切れの警告があるか確認
        self.assertTrue(any("期限切れ" in w for w in result["warnings"]))
        
        # カテゴリなしのタスク
        result = self.validator.validate_results({
            "title": "テスト",
            "priority": "中",
            "confidence": {}
        }, None)
        
        # カテゴリ未設定の警告があるか確認
        self.assertTrue(any("カテゴリ" in w for w in result["warnings"]))
        
        # 期限が近いのに優先度が低いタスク
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        result = self.validator.validate_results({
            "title": "テスト",
            "due_date": tomorrow,
            "priority": "低",
            "confidence": {}
        }, None)
        
        # 優先度に関する警告があるか確認
        self.assertTrue(any("優先度" in w for w in result["warnings"]))

    def test_edge_cases_deadline(self):
        """
        期限に関するエッジケースのテスト

        - 当日期限のタスク
        - 過去の日付のタスク
        - 遠い将来の日付のタスク
        """
        # 今日が期限のタスク
        today = datetime.now().strftime("%Y-%m-%d")
        result = self.validator.validate_results({
            "title": "テスト",
            "due_date": today,
            "priority": "低"
        }, None)
        self.assertEqual(result["priority"], "高")
        self.assertTrue(any("今日まで" in w for w in result["warnings"]))
        
        # 期限が過去の日付（2000年）
        old_date = "2000-01-01"
        result = self.validator.validate_results({
            "title": "テスト",
            "due_date": old_date,
            "priority": "低"
        }, None)
        self.assertEqual(result["priority"], "高")
        self.assertTrue(any("期限切れ" in w for w in result["warnings"]))
        
        # 期限が遠い将来（10年後）
        future_date = (datetime.now() + timedelta(days=3650)).strftime("%Y-%m-%d")
        result = self.validator.validate_results({
            "title": "テスト",
            "due_date": future_date,
            "priority": "高"
        }, None)
        self.assertEqual(result["priority"], "低")

    def test_edge_cases_ai_results(self):
        """
        AI結果のエッジケースのテスト

        - AIの信頼度が閾値ぎりぎり
        - AIの信頼度が閾値未満
        - AIの結果がNone
        """
        # AIの信頼度が閾値ぎりぎり
        rule_result = {
            "title": "テスト",
            "priority": "低",
            "confidence": {"priority": 0.2}
        }
        ai_result = {
            "priority": "高",
            "confidence": Task.CONFIDENCE["THRESHOLD"] + 0.01
        }
        result = self.validator.validate_results(rule_result, ai_result)
        self.assertEqual(result["priority"], "高")
        
        # AIの信頼度が閾値未満
        ai_result["confidence"] = Task.CONFIDENCE["THRESHOLD"] - 0.01
        result = self.validator.validate_results(rule_result, ai_result)
        self.assertEqual(result["priority"], "低")

        # AIの結果がNoneの場合
        result = self.validator.validate_results(rule_result, None)
        self.assertEqual(result["priority"], "低")

    def test_invalid_data(self):
        """
        無効なデータの処理テスト

        - 空のデータ
        - 不正な優先度
        - 不正なカテゴリ
        - 不正な日付を含む完全なタスク
        """
        # 空のデータ
        result = self.validator.validate_results({}, {})
        self.assertEqual(result["title"], "無題のタスク")
        self.assertEqual(result["priority"], "中")
        
        # 不正な優先度
        result = self.validator.validate_results({
            "title": "テスト",
            "priority": "最高"
        }, None)
        self.assertEqual(result["priority"], "中")
        
        # 不正なカテゴリ
        result = self.validator.validate_results({
            "title": "テスト",
            "category": "存在しないカテゴリ"
        }, None)
        self.assertIsNone(result["category"])

        # 不正な日付を含む完全なタスク
        result = self.validator.validate_results({
            "title": "完全なタスク",
            "due_date": "無効な日付",
            "priority": "高",
            "category": "数学",
            "confidence": {"priority": 0.9}
        }, None)
        self.assertIsNone(result["due_date"])
        self.assertEqual(result["priority"], "高")
        self.assertEqual(result["category"], "数学")

    def test_integration_with_text_parser(self):
        """
        TextParserとの統合テスト

        - TextParserとの統合
        - 期限付きのタスク
        - 優先度指定のあるタスク
        """
        from utils.text_parser import TextParser
        
        parser = TextParser()
        
        # 期限付きのタスク
        parsed_result = parser._rule_based_analysis("明日までに数学のレポートを提出")

        parsed_result["category"] = "数学"  # TextParserの結果にカテゴリを追加
        parsed_result["confidence"]["category"] = 0.9  # カテゴリの信頼度も追加
        
        result = self.validator.validate_results(parsed_result, None)
        self.assertIsNotNone(result["due_date"])
        self.assertEqual(result["category"], "数学")
        self.assertEqual(result["priority"], "高")
        
        # 優先度の指定があるタスク
        parsed_result = parser._rule_based_analysis("重要な数学の課題")
        result = self.validator.validate_results(parsed_result, None)
        self.assertEqual(result["priority"], "高")
        self.assertEqual(result["category"], "数学")

    # def test_task_constant_changes(self):
    #     """
    #     Task定数変更への追従テスト

    #     - Task.pyの定数変更への対応確認
    #     - 元の値への復帰確認
    #     """
    #     original_high = Task.PRIORITY_HIGH
    #     original_medium = Task.PRIORITY_MEDIUM
    #     original_low = Task.PRIORITY_LOW

    #     try:
    #         # 一時的に優先度の定数を変更
    #         Task.PRIORITY_HIGH = "緊急"
    #         Task.PRIORITY_MEDIUM = "通常"
    #         Task.PRIORITY_LOW = "低め"
            
    #         # 古い優先度値での入力をテスト
    #         result = self.validator.validate_results({
    #             "title": "テスト",
    #             "priority": original_high,  # 元の"高"を使用
    #             "confidence": {"priority": 0.9}
    #         }, None)
            
    #         # 変更後の定数に対応していることを確認
    #         self.assertEqual(result["priority"], Task.PRIORITY_MEDIUM)  # デフォルトの"普通"になる
            
    #     finally:
    #         # テスト後に元の値に戻す
    #         Task.PRIORITY_HIGH = original_high
    #         Task.PRIORITY_MEDIUM = original_medium
    #         Task.PRIORITY_LOW = original_low

    #     # 定数を戻した後の確認
    #     result = self.validator.validate_results({
    #         "title": "テスト",
    #         "priority": "高",
    #         "confidence": {"priority": 0.9}
    #     }, None)
    #     self.assertEqual(result["priority"], "高")

if __name__ == '__main__':
    unittest.main()