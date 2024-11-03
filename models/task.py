"""
タスクモデルモジュール
タスクの属性と振る舞いを定義
"""

from datetime import datetime, timedelta

class Task:
    """
    タスクの基本情報と状態を管理し、
    Notionとの連携に必要な変換機能を提供
    
    Attributes:
        title (str): タスクのタイトル
        due_date (str): 期限日（YYYY-MM-DD形式）
        priority (str): 優先度（高/中/低）
        category (str): カテゴリ
        status (str): 状態（未着手/進行中/完了）
        description (str): タスクの詳細説明
        created_at (str): 作成日時
        updated_at (str): 更新日時
    """
    
    # ステータス定義
    STATUS_NOT_STARTED = "未着手"
    STATUS_IN_PROGRESS = "進行中"
    STATUS_COMPLETED = "完了"
    
    # 優先度定義
    PRIORITY_HIGH = "高"
    PRIORITY_MEDIUM = "中"
    PRIORITY_LOW = "低"
    
    # 有効なカテゴリ
    VALID_CATEGORIES = ["数学", "統計学", "機械学習", "理論", "プログラミング"]

    def __init__(self, title, due_date=None, priority=None, category=None, status="未着手", description=None):
        """
        タスクの初期化
        
        Args:
            title (str): タスクのタイトル
            due_date (str, optional): 期限日（YYYY-MM-DD形式）
            priority (str, optional): 優先度（高/中/低）
            category (str, optional): カテゴリ
            status (str, optional): 状態（デフォルト: 未着手）
            description (str, optional): タスクの詳細説明
        """
        self.title = title
        self._due_date = None
        self.due_date = due_date  # プロパティを通して設定
        self._priority = None
        self.priority = priority  # プロパティを通して設定
        self._category = None
        self.category = category  # プロパティを通して設定
        self._status = None
        self.status = status  # プロパティを通して設定
        self.description = description
        self.created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.updated_at = self.created_at

    @property
    def due_date(self):
        """
        期限日を取得
        
        Returns:
            str: 期限日（YYYY-MM-DD形式）
        """
        return self._due_date

    @due_date.setter
    def due_date(self, value):
        """
        期限日を設定
        
        Args:
            value (str): 期限日（YYYY-MM-DD形式）

        Raises:
            ValueError: 期限日がYYYY-MM-DD形式でない場合
        """
        if value:
            try:
                # 日付形式の標準化
                if isinstance(value, str):
                    datetime.strptime(value, '%Y-%m-%d')
                self._due_date = value
            except ValueError:
                raise ValueError("期限は'YYYY-MM-DD'形式で指定してください")
        else:
            self._due_date = None

    @property
    def priority(self):
        """
        優先度を取得
        
        Returns:
            str: 優先度（高/中/低）
        """
        return self._priority

    @priority.setter
    def priority(self, value):
        """
        優先度を設定
        有効な優先度値のバリデーションを実施

        Args:
            value (str): 優先度（高/中/低）

        Raises:
            ValueError: 優先度が高/中/低のいずれかでない場合
        """
        if value and value not in [self.PRIORITY_HIGH, self.PRIORITY_MEDIUM, self.PRIORITY_LOW]:
            raise ValueError("優先度は '高'、'中'、'低' のいずれかを指定してください")
        self._priority = value

    @property
    def category(self):
        return self._category

    @category.setter
    def category(self, value):
        if value and value not in self.VALID_CATEGORIES:
            raise ValueError(f"カテゴリは {', '.join(self.VALID_CATEGORIES)} のいずれかを指定してください")
        self._category = value

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if value not in [self.STATUS_NOT_STARTED, self.STATUS_IN_PROGRESS, self.STATUS_COMPLETED]:
            raise ValueError("ステータスは '未着手'、'進行中'、'完了' のいずれかを指定してください")
        self._status = value
        self.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def to_notion_properties(self):
        """
        タスク情報をNotionのプロパティ形式に変換
        
        Returns:
            dict: Notion API用のプロパティ辞書
        """
        properties = {
            "タスク名": {"title": [{"text": {"content": self.title}}]},
            "ステータス": {"status": {"name": self.status}},
            "作成日時": {"date": {"start": self.created_at}},
            "更新日時": {"date": {"start": self.updated_at}}
        }
        
        if self.due_date:
            properties["期限"] = {"date": {"start": self.due_date}}
        
        if self.priority:
            properties["優先度"] = {"select": {"name": self.priority}}
            
        if self.category:
            properties["分野"] = {"select": {"name": self.category}}
            
        if self.description:
            properties["詳細"] = {"rich_text": [{"text": {"content": self.description}}]}
        
        return properties

    def is_overdue(self):
        """
        期限切れかどうかを判定
        
        Returns:
            bool: 期限切れの場合True
        """
        if not self.due_date:
            return False
        return datetime.strptime(self.due_date, '%Y-%m-%d').date() < datetime.now().date()

    def days_until_due(self):
        """
        期限までの残り日数を計算
        
        Returns:
            int: 残り日数（期限なしの場合はNone）
        """
        if not self.due_date:
            return None
        return (datetime.strptime(self.due_date, '%Y-%m-%d').date() - datetime.now().date()).days

    def get_urgency_level(self):
        """
        タスクの緊急度を判定
        
        Returns:
            str: 緊急度レベル（期限切れ/今日まで/明日まで/緊急/要注意/余裕あり/不明）
        """
        if not self.due_date:
            return "不明"
            
        days = self.days_until_due()
        if days < 0:
            return "期限切れ"
        elif days == 0:
            return "今日まで"
        elif days <= 1:
            return "明日まで"
        elif days <= 3:
            return "緊急"
        elif days <= 7:
            return "要注意"
        else:
            return "余裕あり"

    def __str__(self):
        """
        タスクの文字列表現を生成
        
        Returns:
            str: 整形されたタスク情報
        """
        urgency = self.get_urgency_level() if self.due_date else "期限なし"
        base = f"・{self.title}"
        details = []
        
        if self.status:
            details.append(f"状態: {self.status}")
        if self.priority:
            details.append(f"優先度: {self.priority}")
        if self.due_date:
            details.append(f"期限: {self.due_date}({urgency})")
        if self.category:
            details.append(f"分野: {self.category}")
            
        if details:
            base += "\n  " + " | ".join(details)
        
        return base
    
    @staticmethod
    def validate_status(status):
        """
        ステータスの妥当性を検証
        
        Args:
            status (str): 検証するステータス
            
        Returns:
            bool: 妥当な場合はTrue
        """
        return status in [Task.STATUS_NOT_STARTED, Task.STATUS_IN_PROGRESS, Task.STATUS_COMPLETED]