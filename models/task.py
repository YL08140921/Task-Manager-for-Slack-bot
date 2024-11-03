class Task:
    def __init__(self, title, due_date=None, priority=None, category=None, status="未着手"):
        self.title = title
        self.due_date = due_date
        self.priority = priority
        self.category = category
        self.status = status

    def to_notion_properties(self):
        """Notionのプロパティ形式に変換"""
        properties = {
            "タスク名": {"title": [{"text": {"content": self.title}}]},
            "ステータス": {"status": {"name": self.status}},
        }
        
        if self.due_date:
            properties["期限"] = {"date": {"start": self.due_date}}
        
        if self.priority:
            properties["優先度"] = {"select": {"name": self.priority}}
            
        if self.category:
            properties["分野"] = {"select": {"name": self.category}}
        
        return properties

    def __str__(self):
        """タスクの文字列表現"""
        return f"・{self.title}\n  状態: {self.status} | 優先度: {self.priority or '未設定'} | 期限: {self.due_date or '期限なし'} | 分野: {self.category or '未分類'}"