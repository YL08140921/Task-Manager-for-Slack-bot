class TextParser:
    """テキストを解析してタスク情報を抽出するクラス"""
    
    @staticmethod
    def parse_task_info(text):
        """
        テキストからタスク情報を抽出する
        
        例: "add レポート作成 | 期限:2024-03-20 | 優先度:高 | 分野:数学"
        →　{
            "title": "レポート作成",
            "due_date": "2024-03-20",
            "priority": "高",
            "category": "数学"
        }
        """
        # "add "の後ろの文字列を取得
        task_info = text[text.lower().find("add") + 3:].strip()
        
        if not task_info:
            return None
            
        # 基本の情報を初期化
        result = {
            "title": None,
            "due_date": None,
            "priority": None,
            "category": None
        }
        
        # タスク情報を "|" で分割
        components = task_info.split("|")
        
        # タイトルは最初の部分
        result["title"] = components[0].strip()
        
        # 残りの部分を解析
        for comp in components[1:]:
            comp = comp.strip()
            
            if "期限:" in comp:
                result["due_date"] = comp.split("期限:")[1].strip()
            elif "優先度:" in comp:
                result["priority"] = comp.split("優先度:")[1].strip()
            elif "分野:" in comp:
                result["category"] = comp.split("分野:")[1].strip()
                
        return result

    @staticmethod
    def validate_status(status):
        """ステータスが有効かチェック"""
        valid_statuses = ["未着手", "進行中", "完了"]
        return status in valid_statuses

    @staticmethod
    def validate_priority(priority):
        """優先度が有効かチェック"""
        valid_priorities = ["高", "中", "低"]
        return priority in valid_priorities