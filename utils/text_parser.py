import re
from datetime import datetime, timedelta
import calendar
from typing import Dict, Any, Optional
from models.ai.inference import AIInference
from models.task import Task

class TextParser:
    """テキスト解析クラス"""
    
    def __init__(self, model_paths: Optional[Dict[str, str]] = None):
        """
        テキストパーサーの初期化

        キーワードベースの基本ルールと、AIモデルを組み合わせたハイブリッドな解析を行う
        Args:
            model_paths (Optional[Dict[str, str]]): AIモデルのファイルパスを含む辞書
        """
        # カテゴリー判定用のキーワード辞書
        self.category_keywords = Task.CATEGORY_KEYWORDS
        self.priority_keywords = Task.PRIORITY_KEYWORDS

        # AI推論の初期化
        self.ai_inference = None
        if model_paths:
            try:
                self.ai_inference = AIInference(model_paths)
            except Exception as e:
                print(f"警告: AI推論の初期化に失敗: {e}")

    def parse_task_info(self, text: str) -> Optional[Dict[str, Any]]:
        """タスク情報の抽出"""
        cleaned_text = self._preprocess_text(text)
        if not cleaned_text:
            return None

        # ルールベース解析
        rule_based_result = self._rule_based_analysis(cleaned_text)
        
        # AI解析
        ai_result = self._ai_analysis(cleaned_text)
        
        # 結果の統合
        return self._integrate_results(rule_based_result, ai_result)

    def _preprocess_text(self, text: str) -> Optional[str]:
        """テキストの前処理"""
        if not text:
            return None
        text = text.replace('：', ':').replace('、', ',').replace('　', ' ')
        return text.strip()

    def _rule_based_analysis(self, text: str) -> Dict[str, Any]:
        """ルールベースによる解析"""
        result = {
            "title": None,
            "due_date": None,
            "priority": None,
            "category": None,
            "confidence": {}
        }

        # 日付の抽出
        date_info = self._extract_date(text)
        if date_info:
            result["due_date"] = date_info["date"]
            result["confidence"]["due_date"] = date_info["confidence"]
            text = date_info["remaining_text"]

        # カテゴリの推定
        category_info = self._extract_category(text)
        if category_info:
            result["category"] = category_info["category"]
            result["confidence"]["category"] = category_info["confidence"]

        # 日付情報を考慮した優先度の推定
        priority_info = self._extract_priority(text, date_info)
        if priority_info:
            result["priority"] = priority_info["priority"]
            result["confidence"]["priority"] = priority_info["confidence"]

        # タイトルの設定
        result["title"] = self._clean_title_text(text)
        result["confidence"]["title"] = Task.CONFIDENCE["TITLE"]  # 基本的な信頼度

        return result

    def _get_days_until_weekday(self, weekday_text: str) -> int:
        """
        指定された曜日までの日数を計算
        """
        weekdays = {
            '月': 0, '火': 1, '水': 2, '木': 3,
            '金': 4, '土': 5, '日': 6
        }
        
        target_weekday = weekdays[weekday_text]
        current_weekday = datetime.now().weekday()
        days_ahead = target_weekday - current_weekday

        if days_ahead <= 0:
            days_ahead += 7
                
        return days_ahead

    def _extract_date(self, text: str) -> Optional[Dict[str, Any]]:
        """
        テキストから日付情報を抽出

        以下の順序で日付を抽出：
        1. 期限表現（まで、期限など）と組み合わさった日付パターン
        2. 単独の日付パターン
        
        日付パターンの種類：
        - 絶対日付（YYYY-MM-DD, MM-DD）
        - 相対日付（今日、明日、N日後）
        - 週関連（今週末、来週末）
        - 月末関連（今月末、来月末）
        - 曜日指定（今週の月曜日、来週の金曜日）
        
        Returns:
            {
                "date": "YYYY-MM-DD",
                "confidence": float,  # 信頼度（0.0-1.0）
                "remaining_text": str  # 日付部分を除いたテキスト
            }
        """
        # 期限を示す表現
        deadline_patterns = r'(まで|期限|締切|締め切り|〆切)'
        
        patterns = {
            # YYYY-MM-DD または YYYY/MM/DD
            r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?': lambda m: (
                f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}", 1.0
            ),
            # MM-DD または MM/DD または MM月DD日
            r'(\d{1,2})[-/月](\d{1,2})日?': lambda m: (
                f"{datetime.now().year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}", 0.9
            ),
            # 基本的な相対表現
            r'今日': lambda x: (datetime.now().strftime('%Y-%m-%d'), 1.0),
            r'明日': lambda x: ((datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'), 1.0),
            r'明後日': lambda x: ((datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'), 1.0),
            r'(\d+)日後': lambda m: (
                (datetime.now() + timedelta(days=int(m.group(1)))).strftime('%Y-%m-%d'), 0.9
            ),
            
            # 週に関する表現
            r'今週末': lambda x: (
                (datetime.now() + timedelta(days=(5 - datetime.now().weekday()))).strftime('%Y-%m-%d'), 0.8
            ),
            r'来週末': lambda x: (
                (datetime.now() + timedelta(days=(12 - datetime.now().weekday()))).strftime('%Y-%m-%d'), 0.8
            ),
            
            # 月末に関する表現
            r'今月末': lambda x: (
                datetime.now().replace(
                    day=calendar.monthrange(datetime.now().year, datetime.now().month)[1]
                ).strftime('%Y-%m-%d'), 0.9
            ),
            r'来月末': lambda x: (
                (datetime.now().replace(day=1) + timedelta(days=32)).replace(
                    day=calendar.monthrange(
                        (datetime.now() + timedelta(days=32)).year,
                        (datetime.now() + timedelta(days=32)).month
                    )[1]
                ).strftime('%Y-%m-%d'), 0.9
            ),
            
            # 曜日に関する表現
            r'今週の(月|火|水|木|金|土|日)曜日': lambda m: (
                (datetime.now() + timedelta(days=self._get_days_until_weekday(m.group(1)))).strftime('%Y-%m-%d'), 0.9
            ),
            r'来週の(月|火|水|木|金|土|日)曜日': lambda m: (
                (datetime.now() + timedelta(days=self._get_days_until_weekday(m.group(1)) + 7)).strftime('%Y-%m-%d'), 0.9
            )
        }

        def try_pattern_match(pattern: str, text: str, handler: callable) -> Optional[Dict[str, Any]]:
            """パターンマッチを試行"""
            match = re.search(pattern, text)
            if match:
                try:
                    date_str, base_confidence = handler(match)
                    return {
                        "date": date_str,
                        "confidence": base_confidence,
                        "remaining_text": text[:match.start()] + text[match.end():]
                    }
                except ValueError:
                    return None
            return None

        # まず期限表現を検索
        deadline_match = re.search(deadline_patterns, text)
        if deadline_match:
            # 期限表現がある場合、各パターンを試行
            for pattern, handler in patterns.items():
                result = try_pattern_match(pattern, text, handler)
                if result:
                    # 期限表現があれば信頼度を上昇
                    result["confidence"] = min(result["confidence"] + 0.1, 1.0)
                    return result

        # 期限表現がない場合は通常のパターンマッチング
        for pattern, handler in patterns.items():
            result = try_pattern_match(pattern, text, handler)
            if result:
                return result

        return None

    def _extract_category(self, text: str) -> Optional[Dict[str, Any]]:
        """カテゴリの推定"""
        best_category = None
        max_confidence = Task.CONFIDENCE["BASE"]
        
        for category, keywords in self.category_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches:
                confidence = min(
                    Task.CONFIDENCE["BASE"] + matches * Task.CONFIDENCE["INCREMENT"],
                    Task.CONFIDENCE["MAX"]
                )
                if confidence > max_confidence:
                    max_confidence = confidence
                    best_category = category

        if best_category:
            return {
                "category": best_category,
                "confidence": max_confidence
            }
        return None

    def _extract_priority(self, text: str, date_info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        テキストと日付情報から優先度を推定
        
        アルゴリズム：
        1. 各優先度レベルのキーワードとテキストをマッチング
        2. マッチ数に基づいて信頼度を計算（0.5 + マッチ数 * 0.1）
        3. 最も高い信頼度の優先度を選択
        4. マッチがない場合は「低」優先度をデフォルトとして返す
        
        Returns:
            {
                "priority": str,  # "高", "中", "低"
                "confidence": float  # 信頼度（0.5-1.0）
            }
        """
        # 基本的な優先度キーワードチェック
        best_priority = None
        max_confidence = Task.CONFIDENCE["BASE"]

        # 日付ベースの優先度判定
        date_based_priority = None
        if date_info:
            date_based_priority = self._get_date_based_priority(date_info)
        
        # キーワードベースの優先度判定
        for priority, keywords in self.priority_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches:
                # キーワードマッチングベースの信頼度計算（カテゴリと優先度で共通）
                # 基準値0.5 + マッチ数×0.1（上限1.0）
                confidence = min(
                    Task.CONFIDENCE["BASE"] + matches * Task.CONFIDENCE["INCREMENT"],
                    Task.CONFIDENCE["MAX"]
                )
                if confidence > max_confidence:
                    max_confidence = confidence
                    best_priority = priority

        # 日付ベースの優先度と通常の優先度を統合
        if date_based_priority and (not best_priority or date_based_priority["confidence"] > max_confidence):
            return date_based_priority
        elif best_priority:
            return {
                "priority": best_priority,
                "confidence": max_confidence
            }
        return {"priority": "低", "confidence": Task.CONFIDENCE["BASE"]}  # デフォルト

    def _get_date_based_priority(self, date_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        日付情報から優先度を判定
        
        Args:
            date_info (Dict[str, Any]): 日付情報を含む辞書
            
        Returns:
            Optional[Dict[str, Any]]: 優先度情報。日付が無効な場合はNone
        """
        if not isinstance(date_info.get("date"), str):
            return None
            
        try:
            target_date = datetime.strptime(date_info["date"], "%Y-%m-%d").date()
            days_until = (target_date - datetime.now().date()).days
            
            priority_info = Task.get_priority_from_days(days_until)
            # reasonフィールドを追加
            priority_info["reason"] = priority_info.pop("urgency")
            return priority_info
            
        except ValueError:
            return None

    def _clean_title_text(self, text: str) -> str:
        """タイトルテキストのクリーニング"""
        # 不要な表現の削除
        patterns = [
            r'(について|における|に関する)',
            r'(の|を|に|へ|で|から|まで)',
            r'(する|します|やる|行う)',
            r'(必要|予定|こと)',
            r'(です|ます|である)'
        ]
        
        cleaned_text = text
        for pattern in patterns:
            cleaned_text = re.sub(pattern, ' ', cleaned_text)
        
        # 複数の空白を1つに整理
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        return cleaned_text.strip()

    def _ai_analysis(self, text: str) -> Optional[Dict[str, Any]]:
        """AI分析の実行"""
        if not self.ai_inference:
            return None
            
        try:
            return self.ai_inference.analyze_text(text, detailed=True)
        except Exception:
            return None

    def _integrate_results(
        self,
        rule_based: Dict[str, Any],
        ai_result: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        ルールベースとAI分析の結果を統合
        validator.pyの検証層を使用して結果を検証・統合する
        
        Args:
        rule_based: ルールベースの解析結果
        ai_result: AI推論の結果（オプション）
        
        Returns:
            Dict[str, Any]: {
                "title": str,
                "due_date": str,
                "priority": str,
                "category": str,
                "confidence": float,
                "warnings": List[str]  # 警告メッセージのリスト
            }
        """
        # ResultValidatorを使用して結果を検証・統合
        validator = ResultValidator()
        validated_result = validator.validate_results(rule_based, ai_result)
        
        # 検証結果のログ（デバッグ用）
        if validated_result.get("warnings"):
            self.logger.debug(
                "検証による警告:\n%s",
                "\n".join(validated_result["warnings"])
            )
        
        return validated_result

    def cleanup(self):
        """リソースの解放"""
        if self.ai_inference:
            self.ai_inference.cleanup()