from notion_client import Client
from datetime import datetime, timedelta
from models.task import Task

class NotionService:
    """強化されたNotionサービスクラス"""
    
    def __init__(self, config):
        self.client = Client(auth=config.notion_token)
        self.database_id = config.notion_database_id

    def add_task(self, task):
        """タスクを追加（エラーハンドリング強化）"""
        try:
            # バリデーション
            self._validate_task(task)
            
            # Notionプロパティの構築
            properties = {
                "タスク名": {"title": [{"text": {"content": task.title}}]},
                "ステータス": {"status": {"name": task.status}},
                "優先度": {"select": {"name": task.priority}} if task.priority else None,
                # 複数カテゴリに対応
                "分野": {
                    "multi_select": [
                        {"name": category} 
                        for category in (task.categories or [])
                    ]
                },
                "期限": {"date": {"start": task.due_date}} if task.due_date else None,
                "詳細": {"rich_text": [{"text": {"content": task.description or ""}}]}
            }
            
            # Nullの項目を削除
            properties = {k: v for k, v in properties.items() if v is not None}
            
            # データベースにタスクを追加
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )

            return {
                "success": True,
                "message": f"タスクを追加しました：{task.title}",
                "task": task
            }

        except ValueError as ve:
            return {
                "success": False,
                "message": f"入力値が不正です: {str(ve)}",
                "task": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"エラーが発生しました: {str(e)}",
                "task": None
            }

    def list_tasks(self, filters=None):
        """
        タスク一覧を取得（フィルタリング強化）
        
        Args:
            filters (dict, optional): フィルター条件
            
        Returns:
            dict: 処理結果とタスク一覧
        """
        try:
            # クエリパラメータの構築
            query_params = {
                "database_id": self.database_id,
                "sorts": [
                    {"property": "優先度", "direction": "descending"},
                    {"property": "期限", "direction": "ascending"},
                    {"property": "作成日時", "direction": "descending"}
                ]
            }

            # フィルターの構築
            if filters:
                filter_conditions = []
                
                if "status" in filters:
                    filter_conditions.append({
                        "property": "ステータス",
                        "status": {
                            "equals": filters["status"]
                        }
                    })
                    
                if "priority" in filters:
                    filter_conditions.append({
                        "property": "優先度",
                        "select": {
                            "equals": filters["priority"]
                        }
                    })
                    
                if "category" in filters:
                    filter_conditions.append({
                        "property": "分野",
                        "select": {
                            "equals": filters["category"]
                        }
                    })
                    
                if "overdue" in filters and filters["overdue"]:
                    filter_conditions.append({
                        "property": "期限",
                        "date": {
                            "before": datetime.now().strftime("%Y-%m-%d")
                        }
                    })
                
                if filter_conditions:
                    query_params["filter"] = {
                        "and": filter_conditions
                    }

            # Notionにクエリを実行
            response = self.client.databases.query(**query_params)

            # 結果が空の場合
            if not response.get("results"):
                return {
                    "success": True,
                    "message": "タスクはありません",
                    "tasks": []
                }

            try:
                # 結果を整形
                tasks = []
                for item in response["results"]:
                    task = self._convert_notion_to_task(item)
                    if task:
                        tasks.append(task)
                
                # タスクの分類と整形
                return self._format_task_list(tasks)
                
            except KeyError as ke:
                return {
                    "success": False,
                    "message": f"データの形式が不正です: {str(ke)}",
                    "tasks": None
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"エラーが発生しました: {str(e)}",
                "tasks": None
            }

    def update_task_status(self, task_title, new_status):
        """タスクのステータスを更新（エラーハンドリング強化）"""
        try:
            # ステータスの検証
            if not Task.validate_status(new_status):
                return {
                    "success": False,
                    "message": "無効なステータスです",
                    "task": None
                }
            
            # タスクの検索
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "タスク名",
                    "title": {"equals": task_title}
                }
            )
            
            if not response["results"]:
                return {
                    "success": False,
                    "message": f"タスク「{task_title}」が見つかりません",
                    "task": None
                }
                
            # タスクの更新
            page_id = response["results"][0]["id"]
            self.client.pages.update(
                page_id=page_id,
                properties={
                    "ステータス": {"status": {"name": new_status}},
                    "更新日時": {"date": {"start": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}
                }
            )
            
            return {
                "success": True,
                "message": f"タスク「{task_title}」のステータスを「{new_status}」に更新しました",
                "task": self._convert_notion_to_task(response["results"][0])
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"エラーが発生しました: {str(e)}",
                "task": None
            }

    def _validate_task(self, task):
        """タスクのバリデーション"""
        if not task.title:
            raise ValueError("タスク名は必須です")
            
        if len(task.title) > 100:
            raise ValueError("タスク名は100文字以内にしてください")
            
        if task.description and len(task.description) > 1000:
            raise ValueError("詳細は1000文字以内にしてください")
        
        if task.categories and not isinstance(task.categories, list):
            raise ValueError("categoriesはリスト形式である必要があります")

    def _build_filters(self, filters):
        """フィルター条件の構築"""
        if not filters:
            return None
            
        conditions = []
        
        if "status" in filters:
            conditions.append({"property": "ステータス", "status": {"equals": filters["status"]}})
            
        if "categories" in filters:
            conditions.append({
                "property": "分野",
                "multi_select": {"contains": filters["categories"]}  # multi_selectに変更
            })
            
        if "priority" in filters:
            conditions.append({"property": "優先度", "select": {"equals": filters["priority"]}})
            
        if "due_date" in filters:
            conditions.append({
                "property": "期限",
                "date": {"equals": filters["due_date"]}
            })
            
        if "overdue" in filters and filters["overdue"]:
            conditions.append({
                "property": "期限",
                "date": {"before": datetime.now().strftime('%Y-%m-%d')}
            })
        
        if len(conditions) == 1:
            return conditions[0]
        elif len(conditions) > 1:
            return {"and": conditions}
            
        return None

    def _convert_notion_to_task(self, notion_item):
        """NotionのデータをTaskオブジェクトに変換"""
        props = notion_item["properties"]
        
        title = props["タスク名"]["title"][0]["text"]["content"] if props["タスク名"]["title"] else None
        status = props["ステータス"]["status"]["name"] if "ステータス" in props else Task.STATUS_NOT_STARTED
        priority = props["優先度"]["select"]["name"] if "優先度" in props and props["優先度"]["select"] else None
        due_date = props["期限"]["date"]["start"] if "期限" in props and props["期限"]["date"] else None

        # 複数カテゴリの取得
        categories = []
        if "分野" in props and props["分野"]["multi_select"]:
            categories = [item["name"] for item in props["分野"]["multi_select"]]

        description = props["詳細"]["rich_text"][0]["text"]["content"] if "詳細" in props and props["詳細"]["rich_text"] else None
        
        return Task(
            title=title,
            due_date=due_date,
            priority=priority,
            categories=categories,
            status=status,
            description=description
        )

    def _format_task_list(self, tasks):
        """タスク一覧の整形"""
        if not tasks:
            return {
                "success": True,
                "message": "タスクはありません",
                "tasks": []
            }
            
        # タスクの分類
        overdue_tasks = []
        urgent_tasks = []
        normal_tasks = []
        no_due_tasks = []
        
        for task in tasks:
            if not task.due_date:
                no_due_tasks.append(task)
            elif task.is_overdue():
                overdue_tasks.append(task)
            elif task.days_until_due() <= 3:
                urgent_tasks.append(task)
            else:
                normal_tasks.append(task)
                
        # メッセージの構築
        messages = []
        if overdue_tasks:
            messages.append("⚠️ 期限切れのタスク:")
            messages.extend(str(task) for task in overdue_tasks)
            
        if urgent_tasks:
            messages.append("\n🚨 緊急のタスク:")
            messages.extend(str(task) for task in urgent_tasks)
            
        if normal_tasks:
            messages.append("\n📝 通常のタスク:")
            messages.extend(str(task) for task in normal_tasks)
            
        if no_due_tasks:
            messages.append("\n⏳ 期限未設定のタスク:")
            messages.extend(str(task) for task in no_due_tasks)
            
        return {
            "success": True,
            "message": "\n".join(messages),
            "tasks": tasks
        }
    
    def update_priorities(self):
        """タスクの優先度を期限に基づいて自動更新"""
        try:
            # 未完了タスクの取得
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "and": [
                        {"property": "ステータス", "status": {"does_not_equal": "完了"}},
                        {"property": "期限", "date": {"is_not_empty": True}}
                    ]
                }
            )
            
            updated_count = 0
            for item in response["results"]:
                task = self._convert_notion_to_task(item)
                if task:
                    new_priority = self._calculate_dynamic_priority(task)
                    
                    # 優先度が変更された場合のみ更新
                    if new_priority != task.priority:
                        self.client.pages.update(
                            page_id=item["id"],
                            properties={
                                "優先度": {"select": {"name": new_priority}},
                                "更新日時": {"date": {"start": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}
                            }
                        )
                        updated_count += 1
            
            return {
                "success": True,
                "message": f"{updated_count}件のタスクの優先度を更新しました",
                "updated_count": updated_count
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"優先度の更新中にエラーが発生しました: {str(e)}",
                "updated_count": 0
            }

    def _calculate_dynamic_priority(self, task):
        """期限までの残り日数に基づいて動的に優先度を計算"""
        if not task.due_date:
            return task.priority or "中"
            
        try:
            deadline = datetime.strptime(task.due_date, '%Y-%m-%d')
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            days_until_due = (deadline - today).days
            
            # 期限切れまたは1日以内
            if days_until_due <= 1:
                return "高"
            # 3日以内
            elif days_until_due <= 3:
                return "高"
            # 7日以内
            elif days_until_due <= 7:
                return "高"
            # 14日以内
            elif days_until_due <= 14:
                return "中"
            # それ以上
            else:
                return "低"
                
        except ValueError:
            return task.priority or "中"