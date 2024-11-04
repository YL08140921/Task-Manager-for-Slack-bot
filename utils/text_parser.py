"""
テキスト解析モジュール
ルールベースとAI推論を組み合わせたハイブリッド解析
"""

import re
from datetime import datetime, timedelta
import calendar
from typing import Dict, Any, Optional
from models.ai.inference import AIInference

class TextParser:
    """
    テキスト解析クラス
    第1層（ルールベース）と第2層（AI）を組み合わせて
    高精度な情報抽出を行う

    タスクの説明文から以下の情報を抽出:
    - タイトル
    - 期限
    - 優先度
    - カテゴリ
    
    フォーマット済みテキスト（"|" 区切り）と
    自然言語の両方に対応
    """
    
    def __init__(self, model_paths: Optional[Dict[str, str]] = None):
        # カテゴリーのキーワードマッピング
        self.category_keywords = {
            "数学": ["計算", "数式", "証明", "微分", "積分", "代数", "幾何"],
            "統計学": ["統計", "確率", "分布", "標本", "検定", "推定"],
            "機械学習": ["ML", "AI", "学習", "モデル", "予測", "分類"],
            "理論": ["理論", "原理", "定理", "公理", "法則"],
            "プログラミング": ["コード", "プログラム", "開発", "実装", "デバッグ"]
        }
        
        # 優先度のキーワードマッピング
        self.priority_keywords = {
            "高": ["重要", "急ぎ", "必須", "絶対", "今すぐ", "即時"],
            "中": ["なるべく", "できれば", "そろそろ", "近いうち"],
            "低": ["余裕", "時間がある", "ゆっくり"]
        }

        # AI推論ベースの初期化
        self.ai_inference = None
        if model_paths:
            try:
                self.ai_inference = AIInference(model_paths)
            except Exception as e:
                print(f"警告: AI推論ベースの初期化に失敗しました: {e}")
                print("ルールベースのみで動作します")

    def parse_task_info(self, text: str) -> Dict[str, Any]:
        """
        テキストからタスク情報を抽出（ハイブリッドアプローチ）
        
        Args:
            text (str): 解析対象のテキスト
            
        Returns:
            dict: タスク情報を含む辞書（title, due_date, priority, category）
            None: 解析失敗時
        """
        # "add "の後ろの文字列を取得
        task_info = text[text.lower().find("add") + 3:].strip() if "add" in text.lower() else text
        
        if not task_info:
            return None
            
       # 1. ルールベースによる解析
        rule_based_result = None
        if "|" in task_info:
            # フォーマット済みテキストの場合は従来通りの処理
            return self._parse_formatted_text(task_info)
        else:
            # 自然言語の場合はハイブリッド解析
            rule_based_result = self._parse_natural_text(task_info)

        # 2. AI推論による解析（利用可能な場合）
        ai_result = None
        if self.ai_inference and not "|" in task_info:
            try:
                ai_result = self.ai_inference.analyze_text(task_info)
            except Exception as e:
                print(f"AI推論中にエラーが発生しました: {e}")
            
        # 3. 結果の統合
        return self._integrate_results(rule_based_result, ai_result, task_info)
    
    def _integrate_results(
        self,
        rule_based: Dict[str, Any],
        ai_result: Optional[Dict[str, Any]],
        original_text: str
    ) -> Dict[str, Any]:
        """
        ルールベースとAI推論ベースの結果を統合
        
        Args:
            rule_based (Dict[str, Any]): ルールベースの結果
            ai_result (Optional[Dict[str, Any]]): AI推論ベースの結果
            original_text (str): 元のテキスト
            
        Returns:
            Dict[str, Any]: 統合された結果
        """
        # AI結果が利用できない場合はルールベースの結果をそのまま返す
        if not ai_result:
            return rule_based
        
        result = {}
        
        # タイトルの設定（ルールベースを優先）
        result["title"] = rule_based["title"]
        
        # 期限の統合
        if rule_based["due_date"]:
            result["due_date"] = rule_based["due_date"]
        elif ai_result["deadline"]["estimated_days"]:
            estimated_date = datetime.now() + timedelta(days=ai_result["deadline"]["estimated_days"])
            result["due_date"] = estimated_date.strftime('%Y-%m-%d')
        else:
            result["due_date"] = None
        
        # 優先度の統合（ルールベースとAIの信頼度を比較）
        rule_based_priority = rule_based.get("priority")
        ai_priority = ai_result["priority"]["level"]
        ai_confidence = ai_result["priority"]["confidence"]
        
        if rule_based_priority:
            result["priority"] = rule_based_priority
        elif ai_confidence > 0.7:  # 高信頼度の場合のみAIの結果を採用
            result["priority"] = ai_priority
        else:
            result["priority"] = "中"  # デフォルト
        
        # カテゴリの統合
        if rule_based["category"]:
            result["category"] = rule_based["category"]
        elif ai_result["category"]["confidence"] > 0.8:  # 高信頼度の場合のみ
            result["category"] = ai_result["category"]["name"]
        else:
            result["category"] = None
        
        return result

    def _parse_formatted_text(self, text):
        """
        フォーマット済みテキストを解析
        例: タスク名 | 期限:2024-03-20 | 優先度:高 | 分野:数学
        
        Args:
            text (str): パイプ区切りのフォーマット済みテキスト
            
        Returns:
            dict: 解析されたタスク情報
        """
        result = {
            "title": None,
            "due_date": {
                "value": None,
                "confidence": 0.0
            },
            "priority": {
                "value": None,
                "confidence": 0.0
            },
            "category": {
                "value": None,
                "confidence": 0.0
            }
        }
        
        components = text.split("|")
        result["title"] = components[0].strip()
        
        for comp in components[1:]:
            comp = comp.strip()
            if "期限:" in comp:
                date_value = self._parse_date(comp.split("期限:")[1].strip())
                result["due_date"] = {"value": date_value, "confidence": 1.0}
            elif "優先度:" in comp:
                priority_value = comp.split("優先度:")[1].strip()
                result["priority"] = {"value": priority_value, "confidence": 1.0}
            elif "分野:" in comp:
                category_value = comp.split("分野:")[1].strip()
                result["category"] = {"value": category_value, "confidence": 1.0}
                
        return result

    def _parse_natural_text(self, text):
        """
        自然言語テキストを解析
        日付、カテゴリ、優先度を順に抽出し、
        残りをタイトルとして扱う
        
        Args:
            text (str): 自然言語のテキスト
            
        Returns:
            dict: 解析されたタスク情報
        """
        result = {
            "title": None,
            "due_date": {
                "value": None,
                "confidence": 0.0
            },
            "priority": {
                "value": None,
                "confidence": 0.0
            },
            "category": {
                "value": None,
                "confidence": 0.0
            }
        }

        original_text = text
        
        # 日付の抽出
        date_info = self._extract_date(text)
        if date_info:
            result["due_date"] = {
                "value": date_info["date"],
                "confidence": 1.0 if "期限" in text or "締切" in text else 0.8
            }
            # 日付部分を除去
            text = date_info["remaining_text"]
        
        # カテゴリの抽出
        category_info = self._extract_category(text)
        if category_info:
            result["category"] = {
                "value": category_info["category"],
                "confidence": 1.0 if category_info["category"] in text else 0.9
            }
            text = category_info["remaining_text"]
        
        # 優先度の抽出
        priority_info = self._extract_priority(original_text)
        if priority_info:
            result["priority"] = {
                "value": priority_info["priority"],
                "confidence": 1.0 if any(kw in text for kw in self.priority_keywords[priority_info["priority"]]) else 0.8
            }
            text = priority_info["remaining_text"]
        
        # タイトル生成のための前処理
        # 不要な助詞・助動詞・動詞の削除
        text = self._clean_title_text(text)
        
        # カテゴリを考慮したタイトル生成
        if result["category"]["value"]:
            # カテゴリ名が既にテキストに含まれている場合はそのまま
            if result["category"]["value"] in text:
                result["title"] = text
            else:
                # カテゴリ名を先頭に追加
                result["title"] = f"{result['category']['value']}の{text}"
        else:
            result["title"] = text
        
        return result
    
    def _clean_title_text(self, text):
        """
        タイトルテキストから不要な表現を削除
        
        Args:
            text (str): クリーニング対象のテキスト
            
        Returns:
            str: クリーニング後のテキスト
        """
        # 削除対象の表現パターン
        patterns = [
            # 複合助詞
            r'(について|における|に関する|による|に向けて)',
            # 一般的な助詞
            r'(の|を|に|へ|で|から|まで|より)',
            # する系動詞
            r'(する|します|やる|行う|おこなう)',
            # 一般的な動詞
            r'(提出|作成|実施|開始|完了|終了|準備)',
            # 補助的な表現
            r'(必要|要|予定|こと|もの)',
            # 助動詞
            r'(です|だ|である|になる)',
        ]
        
        # 前後の空白を含めてパターンを作成
        for pattern in patterns:
            # 末尾の表現を削除
            text = re.sub(pattern + r'\s*$', '', text)
            # 先頭の表現を削除
            text = re.sub(r'^\s*' + pattern, '', text)
            # 文中の表現を空白に置換
            text = re.sub(pattern, ' ', text)
        
        # 複数の空白を1つに整理
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _extract_date(self, text):
        """
        テキストから日付情報を抽出
        
        対応フォーマット:
        - YYYY-MM-DD
        - YYYY/MM/DD
        - MM-DD
        - MM/DD
        - 今日、明日、明後日
        - N日後
        - 来週、今週末
        
        Args:
            text (str): 日付を含むテキスト
            
        Returns:
            dict: {
                "date": 抽出された日付,
                "remaining_text": 残りのテキスト,
                "confidence": 確信度（0-1）
            }
            None: 日付が見つからない場合
        """

        # 期限を示す表現
        deadline_patterns = r'(まで|期限|締切|締め切り|〆切)'
        
        patterns = {
            # YYYY-MM-DD または YYYY/MM/DD
            r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?': lambda m: (
                f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            ),
            # MM-DD または MM/DD または MM月DD日
            r'(\d{1,2})[-/月](\d{1,2})日?': lambda m: (
                f"{datetime.now().year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
            ),
            
            # 基本的な相対表現
            r'今日': lambda x: datetime.now().strftime('%Y-%m-%d'),
            r'明日': lambda x: (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            r'明後日': lambda x: (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
            r'(\d+)日後': lambda x: (
                datetime.now() + timedelta(days=int(re.search(r'(\d+)', x.group(1)).group(1)))
            ).strftime('%Y-%m-%d'),
            
            # 週に関する表現
            r'今週末': lambda x: (datetime.now() + timedelta(
                days=(5 - datetime.now().weekday())
            )).strftime('%Y-%m-%d'),
            r'来週末': lambda x: (datetime.now() + timedelta(
                days=(12 - datetime.now().weekday())
            )).strftime('%Y-%m-%d'),
            
            # 月末に関する表現
            r'今月末': lambda x: datetime.now().replace(
                day=calendar.monthrange(datetime.now().year, datetime.now().month)[1]
            ).strftime('%Y-%m-%d'),
            r'来月末': lambda x: (datetime.now().replace(day=1) + timedelta(days=32)).replace(
                day=calendar.monthrange(
                    (datetime.now() + timedelta(days=32)).year,
                    (datetime.now() + timedelta(days=32)).month
                )[1]
            ).strftime('%Y-%m-%d'),

            # 曜日に関する表現
            r'今週の(月|火|水|木|金|土|日)曜日': lambda m: (
                datetime.now() + timedelta(days=self._get_days_until_weekday(m.group(1)))
            ).strftime('%Y-%m-%d'),
            r'来週の(月|火|水|木|金|土|日)曜日': lambda m: (
                datetime.now() + timedelta(days=self._get_days_until_weekday(m.group(1)) + 7)
            ).strftime('%Y-%m-%d'),
        }

        # 日付と期限表現の組み合わせを検索
        for pattern, date_func in patterns.items():
            # 期限表現を含むパターンを作成
            combined_pattern = f'({pattern}.*?{deadline_patterns}|{deadline_patterns}.*?{pattern})'
            match = re.search(combined_pattern, text)
            if match:
                date_match = re.search(pattern, match.group())
                if date_match:
                    try:
                        # グループがある場合はそれを使用、ない場合は全体を使用
                        date_str = date_func(date_match)
                        remaining_text = text[:match.start()] + text[match.end():]
                        # 期限表現がある場合は高信頼度
                        return {
                            "date": date_str,
                            "remaining_text": remaining_text.strip(),
                            "confidence": 1.0
                        }
                    except (ValueError, AttributeError) as e:
                        print(f"日付処理エラー: {e}")
                        continue
        
        # 期限表現がない場合は日付のみで検索
        for pattern, date_func in patterns.items():
            match = re.search(pattern, text)
            if match:
                try:
                    date_str = date_func(match)
                    remaining_text = text[:match.start()] + text[match.end():]
                    # 期限表現がない場合は低めの信頼度
                    return {
                        "date": date_str,
                        "remaining_text": remaining_text.strip(),
                        "confidence": 0.8
                    }
                except (ValueError, AttributeError) as e:
                    print(f"日付処理エラー: {e}")
                    continue

        return None
    
    def _get_days_until_weekday(self, weekday_text):
        """
        指定された曜日までの日数を計算
        
        Args:
            weekday_text (str): 曜日を含むテキスト
            
        Returns:
            int: 指定曜日までの日数
        """
        weekdays = {
            '月': 0, '火': 1, '水': 2, '木': 3,
            '金': 4, '土': 5, '日': 6
        }
        
        # weekday_textは既に曜日の文字なので、直接辞書を参照
        target_weekday = weekdays[weekday_text]
        current_weekday = datetime.now().weekday()
        
        # 指定曜日までの日数を計算
        days_ahead = target_weekday - current_weekday

        if days_ahead <= 0:
            # 今週の指定で、既に過ぎている場合は来週の同じ曜日
            days_ahead += 7
            
        return days_ahead

    def _extract_category(self, text):
        """
        テキストからカテゴリを抽出
        
        直接的なカテゴリ名または関連キーワードから
        最適なカテゴリを判定
        
        Args:
            text (str): カテゴリを含むテキスト
            
        Returns:
            dict: {
                "category": 抽出されたカテゴリ,
                "remaining_text": 残りのテキスト,
                "confidence": 確信度（0-1）
            }
            None: カテゴリが見つからない場合
        """
        # 直接カテゴリ名がある場合
        for category in self.category_keywords.keys():
            if category in text:
                return {
                    "category": category,
                    "remaining_text": text.replace(category, ""),
                    "confidence": 1.0  # 完全一致は最高信頼度
                }
        
        # キーワードからカテゴリを推測
        matched_keywords = {}
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    if category not in matched_keywords:
                        matched_keywords[category] = 0
                    matched_keywords[category] += 1
        
        if not matched_keywords:
            # 最も多くのキーワードにマッチしたカテゴリを選択
            best_category = max(matched_keywords.items(), key=lambda x: x[1])[0]
            keyword_count = matched_keywords[best_category]
            # キーワードの数に応じて信頼度を調整
            confidence = min(0.8 + (keyword_count - 1) * 0.1, 0.9)  # 最大0.9
            return {
                "category": best_category,
                "remaining_text": text,
                "confidence": confidence
            }
        return None

    def _extract_priority(self, text):
        """
        テキストから優先度を抽出
        
        優先度キーワードまたは期限の緊急度から
        優先度を判定
        
        Args:
            text (str): 優先度を含むテキスト
            
        Returns:
        dict: {
                "priority": 優先度,
                "remaining_text": 残りのテキスト,
                "confidence": 確信度（0-1）
            }
            None: 優先度が見つからない場合
        """
        print(f"\n=== 優先度抽出開始 ===")
        print(f"入力テキスト: {text}")
        
        original_text = text
        priority_from_keyword = None
        
        # キーワードによる優先度判定
        for priority, keywords in self.priority_keywords.items():
            matched_keywords = []
            for keyword in keywords:
                if keyword in text:
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                confidence = min(0.8 + (len(matched_keywords) - 1) * 0.1, 1.0)  # キーワード数による信頼度調整
                priority_from_keyword = {
                    "priority": priority,
                    "remaining_text": text,
                    "confidence": confidence
                }
                for kw in matched_keywords:
                    print(f"キーワード '{kw}' が見つかりました → 優先度: {priority}")
                break
        
        # 期限による優先度推測
        print("\n期限による優先度判定:")
        date_info = self._extract_date(text)
        print(f"抽出された日付情報: {date_info}")
        
        if date_info and date_info["date"]:
            try:
                deadline = datetime.strptime(date_info["date"], '%Y-%m-%d')
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                days_until_deadline = (deadline - today).days
                
                print(f"期限日: {deadline.date()}")
                print(f"今日: {today.date()}")
                print(f"期限までの日数: {days_until_deadline}日")
                
                 # キーワードによる優先度がある場合はその信頼度を考慮
                if priority_from_keyword and priority_from_keyword["confidence"] > 0.8:
                    return priority_from_keyword
                    
                # 期限に基づく優先度の判定
                # 期限切れ
                if days_until_deadline < 0:
                    return {
                        "priority": "高",
                        "remaining_text": original_text,
                        "confidence": 0.9
                    }
                # 今日または明日
                elif days_until_deadline <= 1:
                    return {
                        "priority": "高",
                        "remaining_text": original_text,
                        "confidence": 0.9
                    }
                # 1週間以内
                elif days_until_deadline <= 7:
                    return {
                        "priority": "高",
                        "remaining_text": original_text,
                        "confidence": 0.85
                    }
                # 1週間以上
                else:
                    return {
                        "priority": "中",
                        "remaining_text": original_text,
                        "confidence": 0.7
                    }
            except ValueError as e:
                print(f"日付処理エラー: {e}")
                if priority_from_keyword:
                    return priority_from_keyword
        else:
            print("日付情報が見つかりませんでした")
        
        # キーワードによる優先度がある場合はそれを返す
        if priority_from_keyword:
            print("キーワードによる優先度を使用")
            return priority_from_keyword
        
        print("デフォルトの優先度（低）を設定")
        # デフォルト値
        return {
            "priority": "低",
            "remaining_text": original_text,
            "confidence": 0.5  # デフォルトは低信頼度
        }
    
    @staticmethod
    def _parse_date(date_str):
        """日付文字列をパース"""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            return date_str

    @staticmethod
    def validate_status(status):
        """
        ステータスの妥当性を検証
        
        Args:
            status (str): 検証するステータス
            
        Returns:
            bool: 妥当な場合はTrue
        """
        valid_statuses = ["未着手", "進行中", "完了"]
        return status in valid_statuses

    @staticmethod
    def validate_priority(priority):
        """
        優先度の妥当性を検証
        
        Args:
            priority (str): 検証する優先度
            
        Returns:
            bool: 妥当な場合はTrue
        """
        valid_priorities = ["高", "中", "低"]
        return priority in valid_priorities
    
