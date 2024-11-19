"""
タスクモデルモジュール
タスクの属性と振る舞いを定義
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class Task:
    """
    タスクの基本情報と状態を管理し、
    Notionとの連携に必要な変換機能を提供
    
    Attributes:
        title (str): タスクのタイトル
        due_date (str): 期限日（YYYY-MM-DD形式）
        priority (str): 優先度（高/中/低）
        categories (str): カテゴリ
        status (str): 状態（未着手/進行中/完了）
        description (str): タスクの詳細説明
        created_at (str): 作成日時
        updated_at (str): 更新日時
    """
    
    # ステータス定義
    STATUS_NOT_STARTED = "未着手"
    STATUS_IN_PROGRESS = "進行中"
    STATUS_COMPLETED = "完了"

    # 優先度の定数
    PRIORITY_HIGH = "高"
    PRIORITY_MEDIUM = "中"
    PRIORITY_LOW = "低"
    
    # 優先度定義
    PRIORITY_KEYWORDS = {
        PRIORITY_HIGH: [
            "重要", "急ぎ", "必須", "絶対", "今すぐ",
            "かなり", "急いで", "やばい", "早く",
            "至急", "即時", "緊急", "すぐ", 
        ],
        PRIORITY_MEDIUM: [
            "なるべく", "できれば", "そろそろ",
            "準備", "確認", "検討"
        ],
        PRIORITY_LOW: [
            "余裕", "ゆっくり", "暇なとき",
            "時間があれば", "後で"
        ]
    }

    # 信頼度の定数定義
    CONFIDENCE = {
        # 基準値（0.5）: キーワードマッチングの基本的な信頼性
        "BASE": 0.5,
        
        # 増分値（0.1）: キーワードマッチごとの信頼度上昇
        "INCREMENT": 0.1,
        
        # 最大値（1.0）: 完全なマッチ
        "MAX": 1.0,
        
        # 最低閾値（0.3）: AI判定で有効とみなす最低ライン
        "THRESHOLD": 0.3,
        
        # タイトルの基本信頼度
        "TITLE": 0.8,

        # AIモデルの重み付け
        "MODEL_WEIGHTS": {
            "LASER": 0.5,    
            "WORD2VEC": 0.3, 
            "FASTTEXT": 0.2
        }
    }

    # 優先度と緊急度の定義を統合
    URGENCY_LEVELS = {
        # 期限切れ: 確実な判定が可能
        "期限切れ": {"days": -1, "priority": PRIORITY_HIGH, "confidence": CONFIDENCE["MAX"]},
        
        # 当日: ほぼ確実だが若干の余地を残す
        "今日まで": {"days": 0, "priority": PRIORITY_HIGH, "confidence": 0.9},
        
        # 翌日: 同様に高い確実性
        "明日まで": {"days": 1, "priority": PRIORITY_HIGH, "confidence": 0.9},
        
        # 3日以内: 高い確実性
        "緊急": {"days": 3, "priority": PRIORITY_HIGH, "confidence": 0.8},
        
        # 1週間以内: やや高い確実性
        "要注意": {"days": 7, "priority": PRIORITY_HIGH, "confidence": 0.7},

        # 2週間以内: 中程度の確実性
        "注意": {"days": 14, "priority": PRIORITY_MEDIUM, "confidence": 0.6},
        
        # それ以降: 控えめな確実性
        "余裕あり": {"days": float('inf'), "priority": PRIORITY_LOW, "confidence": 0.5}
    }

    # カテゴリ定義
    CATEGORY_KEYWORDS = {
        "数学": ["計算", "数式", "証明", "微分", "積分", "線形代数", "確率論"],
        "統計学": ["統計", "確率", "分布", "標本", "検定", "回帰分析", "データ分析"],
        "機械学習": ["ML", "AI", "学習", "モデル", "予測", "ニューラルネットワーク", "深層学習"],
        "データサイエンス": ["データ分析", "可視化", "前処理", "特徴量", "パイプライン"],
        "開発": ["フロントエンド", "バックエンド", "API", "デプロイ", "サーバー", "フレームワーク","コード", "プログラム", "開発", "実装", "デバッグ", "アルゴリズム", "データベース", "DB", "プログラミング"],
        "インフラ": ["クラウド", "AWS", "Docker", "CI/CD", "システム構築"],
        "研究": ["研究", "論文", "実験", "検証", "提案", "論文執筆", "論文校正", "論文投稿", "論文査読", "論文審議", "論文審議意見", "論文審議結果"],
        "インターン": ["業務", "タスク", "報告", "インターン", "勤務"],
        "キャリア": ["就活", "面接", "ES", "企業分析", "イベント"],
        "提出物": ["課題", "レポート", "授業", "演習", "宿題", "提出"],
        "ミーティング": ["MTG", "打ち合わせ", "相談", "報告会", "発表"]
    }

    VALID_CATEGORIES = list(CATEGORY_KEYWORDS.keys())

    def __init__(self, title, due_date=None, priority=None, categories=None, status="未着手", description=None):
        """
        タスクの初期化
        
        Args:
            title (str): タスクのタイトル
            due_date (str, optional): 期限日（YYYY-MM-DD形式）
            priority (str, optional): 優先度（高/中/低）
            categories (list, optional): カテゴリのリスト
            status (str, optional): 状態（デフォルト: 未着手）
            description (str, optional): タスクの詳細説明
        """
        self.title = title
        self._due_date = None
        self.due_date = due_date  
        self._priority = None
        self.priority = priority  
        self._categories = []
        self.categories = categories or []
        self._status = None
        self.status = status  
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
    def categories(self):
        """カテゴリリストを取得"""
        return self._categories

    @categories.setter
    def categories(self, value):
        """
        カテゴリを設定
        
        Args:
            value (str or list): カテゴリまたはカテゴリのリスト
            
        Raises:
            ValueError: 無効なカテゴリが指定された場合
        """
        if value is None:
            self._categories = []
            return

        # 文字列の場合はリストに変換
        if isinstance(value, str):
            value = [value]
            
        # カテゴリの検証
        invalid_categories = [cat for cat in value if cat not in self.VALID_CATEGORIES]
        if invalid_categories:
            raise ValueError(
                f"無効なカテゴリが指定されました: {', '.join(invalid_categories)}\n"
                f"有効なカテゴリ: {', '.join(self.VALID_CATEGORIES)}"
            )
            
        self._categories = value

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
            
        if self.categories:
            # 複数カテゴリに対応
            properties["分野"] = {
                "multi_select": [{"name": category} for category in self.categories]
            }
            
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

    @classmethod
    def get_priority_from_days(cls, days: int) -> Dict[str, Any]:
        """日数から優先度情報を取得"""
        for level, info in cls.URGENCY_LEVELS.items():
            if days <= info["days"]:
                return {
                    "priority": info["priority"],
                    "confidence": info["confidence"],
                    "urgency": level
                }
        return {
            "priority": cls.PRIORITY_LOW,
            "confidence": 0.6,
            "urgency": "余裕あり"
        }

    def get_urgency_level(self) -> str:
        """
        タスクの緊急度を判定
        
        Returns:
            str: 緊急度レベル（期限切れ/今日まで/明日まで/緊急/要注意/余裕あり/不明）
        """
        if not self.due_date:
            return "不明"
            
        days = self.days_until_due()
        return self.get_priority_from_days(days)["urgency"]

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
        if self.categories:
            details.append(f"分野: {', '.join(self.categories)}")
            
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