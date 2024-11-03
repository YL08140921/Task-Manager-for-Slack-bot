'''
Notionとのやり取りをすべてこのクラスに集約
データベースの操作（追加・一覧・更新）を整理
内部処理（フィルター作成、データ変換）を分離

'''

from notion_client import Client
from models.task import Task

class NotionService:
    """Notionとのやり取りを管理するクラス"""
    
    def __init__(self, config):
        """
        設定を使ってNotionクライアントを初期化
        """
        self.client = Client(auth=config.notion_token)
        self.database_id = config.notion_database_id

    def add_task(self, task):
        """
        タスクを追加する
        """
        try:
            self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=task.to_notion_properties()
            )
            return f"タスクを追加しました：{task.title}"
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"

    def list_tasks(self, status=None, category=None):
        """
        タスク一覧を取得する
        """
        try:
            # フィルターの設定
            filter_params = self._create_filter(status, category)
            
            # Notionにクエリを実行
            response = self.client.databases.query(
                database_id=self.database_id,
                filter=filter_params,
                sorts=[
                    {"property": "期限", "direction": "ascending"},
                    {"property": "優先度", "direction": "descending"}
                ]
            )

            if not response["results"]:
                return "タスクはありません"

            # 結果を整形
            tasks = []
            for item in response["results"]:
                task = self._convert_notion_to_task(item)
                tasks.append(task)

            return self._format_task_list(tasks)

        except Exception as e:
            return f"エラーが発生しました: {str(e)}"

    def update_task_status(self, task_title, new_status):
        """
        タスクのステータスを更新する
        """
        try:
            # タスクを検索
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "タスク名",
                    "title": {"equals": task_title}
                }
            )
            
            if not response["results"]:
                return f"タスク「{task_title}」が見つかりません"
                
            # 最初に見つかったタスクを更新
            page_id = response["results"][0]["id"]
            self.client.pages.update(
                page_id=page_id,
                properties={
                    "ステータス": {"status": {"name": new_status}}
                }
            )
            return f"タスク「{task_title}」のステータスを「{new_status}」に更新しました"
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"

    def _create_filter(self, status=None, category=None):
        """フィルター条件を作成する（内部メソッド）"""
        if status and category:
            return {
                "and": [
                    {"property": "ステータス", "status": {"equals": status}},
                    {"property": "分野", "select": {"equals": category}}
                ]
            }
        elif status:
            return {
                "property": "ステータス",
                "status": {"equals": status}
            }
        elif category:
            return {
                "property": "分野",
                "select": {"equals": category}
            }
        else:
            return {
                "or": [
                    {
                        "property": "タスク名",
                        "title": {
                            "is_not_empty": True
                        }
                    }
                ]
            }

    def _convert_notion_to_task(self, notion_item):
        """NotionのデータをTaskオブジェクトに変換する（内部メソッド）"""
        props = notion_item["properties"]
        
        title = props["タスク名"]["title"][0]["text"]["content"]
        status = props["ステータス"]["status"]["name"]
        priority = props["優先度"]["select"]["name"] if "優先度" in props else None
        due_date = props["期限"]["date"]["start"] if "期限" in props and props["期限"]["date"] else None
        category = props["分野"]["select"]["name"] if "分野" in props else None
        
        return Task(title, due_date, priority, category, status)

    def _format_task_list(self, tasks):
        """タスク一覧を文字列に整形する（内部メソッド）"""
        if not tasks:
            return "タスクはありません"
            
        task_list = "📚 タスク一覧:\n"
        for task in tasks:
            task_list += str(task) + "\n"
        return task_list