'''
Slackとのやり取りを管理
メッセージの処理を整理
コマンドごとの処理を分離
'''

# services/slack_service.py の更新版

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from utils.text_parser import TextParser
from models.task import Task

class SlackService:
    """Slackとのやり取りを管理するクラス"""
    
    def __init__(self, config, notion_service):
        """
        設定を使ってSlackアプリを初期化
        """
        self.app = App(token=config.slack_bot_token)
        self.notion_service = notion_service
        self.text_parser = TextParser()
        self.setup_handlers()

    def setup_handlers(self):
        """
        Slackのイベントハンドラを設定
        """
        @self.app.event("app_mention")
        def handle_mention(event, say):
            text = self._clean_mention(event["text"])
            self._process_command(text, say)

        @self.app.event("message")
        def handle_message(event, logger):
            if event.get("subtype") == "bot_message" or "bot_id" in event:
                return

    def start(self, app_token):
        """
        Slackアプリを起動
        """
        handler = SocketModeHandler(self.app, app_token)
        handler.start()

    def _clean_mention(self, text):
        """メンションを除去（内部メソッド）"""
        return ' '.join(word for word in text.split() if not word.startswith('<@'))

    def _process_command(self, text, say):
        """コマンドを処理（内部メソッド）"""
        words = text.split()
        if not words:
            self._show_help(say)
            return

        command = words[0].lower()
        
        if command == "add":
            self._handle_add(text, say)
        elif command == "list":
            self._handle_list(words, say)
        elif command == "update":
            self._handle_update(words, say)
        else:
            self._show_help(say)

    def _handle_add(self, text, say):
        """addコマンドの処理"""
        # タスク情報を解析
        task_info = self.text_parser.parse_task_info(text)
        
        if not task_info:
            say("タスクの情報を入力してください。\n例：add レポート作成 | 期限:2024-03-20 | 優先度:高 | 分野:数学")
            return
            
        # Taskオブジェクトを作成
        task = Task(
            title=task_info["title"],
            due_date=task_info["due_date"],
            priority=task_info["priority"],
            category=task_info["category"]
        )
        
        # NotionServiceを使ってタスクを追加
        result = self.notion_service.add_task(task)
        say(result)

    def _handle_list(self, words, say):
        """listコマンドの処理"""
        if len(words) > 1:
            filter_value = words[1]
            if TextParser.validate_status(filter_value):
                result = self.notion_service.list_tasks(status=filter_value)
            elif filter_value in ["数学", "統計学", "機械学習", "理論", "プログラミング"]:
                result = self.notion_service.list_tasks(category=filter_value)
            else:
                result = self.notion_service.list_tasks()
        else:
            result = self.notion_service.list_tasks()
        say(result)

    def _handle_update(self, words, say):
        """updateコマンドの処理"""
        if len(words) >= 3:
            task_title = " ".join(words[1:-1])  # 最後の単語以外をタスク名として扱う
            new_status = words[-1]  # 最後の単語をステータスとして扱う
            
            if TextParser.validate_status(new_status):
                result = self.notion_service.update_task_status(task_title, new_status)
                say(result)
            else:
                say("ステータスは「未着手」「進行中」「完了」のいずれかを指定してください")
        else:
            say("使用方法: update タスク名 ステータス")

    def _show_help(self, say):
        """ヘルプメッセージを表示（内部メソッド）"""
        say("使用可能なコマンド:\n"
            "- add タスク名 | 期限:YYYY-MM-DD | 優先度:高/中/低 | 分野:カテゴリー\n"
            "- list\n"
            "- list 状態[未着手/進行中/完了]\n"
            "- update タスク名 状態[未着手/進行中/完了]")