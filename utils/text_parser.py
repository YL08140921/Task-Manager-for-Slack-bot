"""
テキスト解析モジュール
タスク情報の抽出と解析を行う機能を提供
"""

import re
from datetime import datetime, timedelta
import calendar

class TextParser:
    """
    テキスト解析クラス
    
    タスクの説明文から以下の情報を抽出:
    - タイトル
    - 期限
    - 優先度
    - カテゴリ
    
    フォーマット済みテキスト（"|" 区切り）と
    自然言語の両方に対応
    """
    
    def __init__(self):
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

    def parse_task_info(self, text):
        """
        テキストからタスク情報を抽出
        
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
            
        # 基本情報の初期化
        result = {
            "title": None,
            "due_date": None,
            "priority": None,
            "category": None
        }
        
        # 明示的なフォーマット（"|" 区切り）のパース
        if "|" in task_info:
            return self._parse_formatted_text(task_info)
            
        # 自然言語からの解析
        return self._parse_natural_text(task_info)

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
            "due_date": None,
            "priority": None,
            "category": None
        }
        
        components = text.split("|")
        result["title"] = components[0].strip()
        
        for comp in components[1:]:
            comp = comp.strip()
            if "期限:" in comp:
                result["due_date"] = self._parse_date(comp.split("期限:")[1].strip())
            elif "優先度:" in comp:
                result["priority"] = comp.split("優先度:")[1].strip()
            elif "分野:" in comp:
                result["category"] = comp.split("分野:")[1].strip()
                
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
            "due_date": None,
            "priority": None,
            "category": None
        }

        original_text = text
        
        # 日付の抽出
        date_info = self._extract_date(text)
        if date_info:
            result["due_date"] = date_info["date"]
            # 日付部分を除去
            text = date_info["remaining_text"]
        
        # カテゴリの抽出
        category_info = self._extract_category(text)
        if category_info:
            result["category"] = category_info["category"]
            text = category_info["remaining_text"]
        
        # 優先度の抽出
        priority_info = self._extract_priority(original_text)
        if priority_info:
            result["priority"] = priority_info["priority"]
            text = priority_info["remaining_text"]
        
        # タイトル生成のための前処理
        # 不要な助詞・助動詞・動詞の削除
        text = self._clean_title_text(text)
        
        # カテゴリを考慮したタイトル生成
        if result["category"]:
            # カテゴリ名が既にテキストに含まれている場合はそのまま
            if result["category"] in text:
                result["title"] = text
            else:
                # カテゴリ名を先頭に追加
                result["title"] = f"{result['category']}の{text}"
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
            dict: 抽出された日付と残りのテキスト
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
                        return {"date": date_str, "remaining_text": remaining_text.strip()}
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
                    return {"date": date_str, "remaining_text": remaining_text.strip()}
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
            dict: 抽出されたカテゴリと残りのテキスト
            None: カテゴリが見つからない場合
        """
        # 直接カテゴリ名がある場合
        for category in self.category_keywords.keys():
            if category in text:
                return {
                    "category": category,
                    "remaining_text": text.replace(category, "")
                }
        
        # キーワードからカテゴリを推測
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return {
                        "category": category,
                        "remaining_text": text.replace(keyword, "")
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
            dict: 抽出された優先度と残りのテキスト
            None: 優先度が見つからない場合
        """
        print(f"\n=== 優先度抽出開始 ===")
        print(f"入力テキスト: {text}")
        
        original_text = text
        priority_from_keyword = None
        
        # 直接的な優先度表現を最初にチェック
        for priority, keywords in self.priority_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    priority_from_keyword = {
                        "priority": priority,
                        "remaining_text": text.replace(keyword, "")
                    }
                    print(f"キーワード '{keyword}' が見つかりました → 優先度: {priority}")
                    break
            if priority_from_keyword:
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
                
                # キーワードによる優先度がある場合はそれを優先
                if priority_from_keyword:
                    print("キーワードによる優先度が存在するため、それを優先します")
                    return priority_from_keyword
                    
                # 期限に基づく優先度の判定
                if days_until_deadline < 0:  # 期限切れ
                    print("期限切れ → 高優先度")
                    return {"priority": "高", "remaining_text": original_text}
                elif days_until_deadline <= 1:  # 今日または明日
                    print("1日以内 → 高優先度")
                    return {"priority": "高", "remaining_text": original_text}
                elif days_until_deadline <= 7:  # 1週間以内
                    print("7日以内 → 高優先度")
                    return {"priority": "高", "remaining_text": original_text}
                else:  # 1週間以上
                    print("7日超 → 中優先度")
                    return {"priority": "中", "remaining_text": original_text}
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
        return {"priority": "低", "remaining_text": original_text}  # デフォルトを低に設定
    
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
    
