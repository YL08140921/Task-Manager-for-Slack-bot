"""
Slackサービスモジュール
Slackとの対話機能とタスク管理機能を提供
"""

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from utils.text_parser import TextParser
from models.task import Task
from typing import Dict, Any, Tuple
import re
import logging
from datetime import datetime, timedelta
from models.chat_module import ChatModule


class SlackService:
    """
    Slackでのコマンド処理とタスク管理機能を提供
    Notionと連携してタスクの永続化を行う
    
    Attributes:
        app: Slackアプリケーションインスタンス
        notion_service: Notionサービスインスタンス
        text_parser: テキスト解析インスタンス
    """
    
    # コマンド定義
    COMMANDS = {
        "add": "タスクを追加",
        "list": "タスク一覧を表示",
        "update": "タスクを更新",
        "help": "ヘルプを表示",
        "search": "タスクを検索",
        "priority": "優先度でフィルター",
        "category": "カテゴリでフィルター",
        "overdue": "期限切れタスクを表示"
    }

    def __init__(self, config, notion_service):
        """
        サービスの初期化
        
        Args:
            config: 設定情報
            notion_service: Notionサービスインスタンス
        """
        self.app = App(token=config.slack_bot_token)
        self.notion_service = notion_service
        self.text_parser = TextParser(config.model_paths)
        self.setup_handlers()

        # 授業で指定されたもの
        self.chat_module = ChatModule()

    def setup_handlers(self):
        """
        Slackイベントハンドラの設定
        メンションとメッセージのイベントを処理
        """
        @self.app.event("app_mention")
        def handle_mention(event, say):
            """
            メンション時の処理
            
            Args:
                event: Slackイベント
                say: メッセージ送信関数
            """
            try:
                text = self._clean_mention(event["text"])
                self._process_command(text, say)
            except Exception as e:
                say(f"申し訳ありません。エラーが発生しました: {str(e)}")

        @self.app.event("message")
        def handle_message(event, say):
            """
            メッセージ受信時の処理
            ボットからのメッセージは無視
            
            Args:
                event: Slackイベント
                say: メッセージ送信関数
            """
            if event.get("subtype") == "bot_message" or "bot_id" in event:
                return

    def start(self, app_token):
        """
        アプリケーションの起動
        
        Args:
            app_token: Slackアプリケーショントークン
        """
        handler = SocketModeHandler(self.app, app_token)
        handler.start()

    def _clean_mention(self, text):
        """
        メンションの除去と文字列の正規化
        
        Args:
            text (str): 入力テキスト
            
        Returns:
            str: 正規化されたテキスト
        """
        # メンションの除去
        text = ' '.join(word for word in text.split() if not word.startswith('<@'))
        
        # 全角文字の正規化
        text = text.replace('：', ':').replace('、', ',').replace('　', ' ')
        
        # 余分な空白の除去
        text = ' '.join(text.split())
        
        return text

    def _process_command(self, text, say):
        """
        コマンドの解析と実行
        
        Args:
            text (str): コマンドテキスト
            say: メッセージ送信関数
        """
        try:
            # タスク管理コマンドの判定
            if text.startswith(tuple(self.COMMANDS.keys())) or any(keyword in text for keyword in ["タスク", "課題", "予定"]):
                # 1. 入力解析
                command, args = self._parse_command(text)
                
                # 2. コマンド処理
                if not command:
                    self._show_help(say)
                    return
            
                handlers = {
                    "add": self._handle_add,
                    "list": self._handle_list,
                    "update": self._handle_update,
                    "help": self._show_help,
                    "search": self._handle_search,
                    "priority": self._handle_priority_filter,
                    "category": self._handle_category_filter,
                    "overdue": self._handle_overdue
                }

                handler = handlers.get(command)
                if handler:
                    handler(args, say)
                else:
                    say(f"申し訳ありません。「{command}」は未知のコマンドです。")
            else:
                # チャットモードの処理
                response = self.chat_module.get_response(text)
                say(response)

        except Exception as e:
            say(f"⚠️ エラーが発生しました: {str(e)}\n処理を中止します。")
            logging.error(f"コマンド処理エラー: {str(e)}", exc_info=True)

    def _parse_command(self, text):
        """
        コマンドとパラメータの解析
        
        Args:
            text (str): コマンドテキスト
            
        Returns:
            tuple: (コマンド, パラメータ)
        """
        if not text:
            return None, None
            
        words = text.lower().split()
        command = words[0]
        
        # コマンドの正規化
        if command in ["追加", "たす", "add"]:
            command = "add"
        elif command in ["一覧", "リスト", "list", "show"]:
            command = "list"
        elif command in ["更新", "変更", "update"]:
            command = "update"
        elif command in ["help", "ヘルプ", "使い方"]:
            command = "help"
        elif command in ["検索", "さがす", "search"]:
            command = "search"
        elif command in ["優先", "priority"]:
            command = "priority"
        elif command in ["分野", "カテゴリ", "category"]:
            command = "category"
        elif command in ["期限切れ", "overdue"]:
            command = "overdue"
            
        args = ' '.join(words[1:])
        return command, args

    def _handle_add(self, args, say):
        """
        タスク追加コマンドの処理
        
        Args:
            args (str): タスク情報
            say: メッセージ送信関数
        """
        if not args:
            say("タスクの情報を入力してください。\n"
                "例1: add レポート作成 | 期限:2024-03-20 | 優先度:高 | 分野:数学\n"
                "例2: add 数学の課題 明日まで")
            return
            
        # タスク情報の解析（AIと検証層を含む）
        task_info = self.text_parser.parse_task_info(args)
        
        if not task_info or not task_info["title"]:
            say("タスクの追加に必要な情報が不足しています。")
            return
            
        # 警告メッセージの確認
        warnings = task_info.get("warnings", [])

        try:
            
            # Taskオブジェクトの作成
            task = Task(
                title=task_info["title"],
                due_date=task_info["due_date"],
                priority=task_info["priority"],
                categories=task_info["categories"]
            )
            
            # タスクの追加
            result = self.notion_service.add_task(task)
            
            # 応答の生成
            if result["success"]:
                response = [
                    f"✅ {result['message']}",
                    "タスクの詳細:",
                    str(task)
                ]
                if task.due_date and task.days_until_due() <= 3:
                    response.append("\n⚠️ このタスクは緊急度が高いです！")
            else:
                response = [f"❌ {result['message']}"]
                
            say("\n".join(response))

        except Exception as e:
            say(f"⚠️ タスクの作成中にエラーが発生しました: {str(e)}")
            logging.error(f"タスク作成エラー: {str(e)}", exc_info=True)

    def _handle_list(self, args, say):
        """
        タスク一覧表示コマンドの処理
        
        Args:
            args (str): フィルター条件
            say: メッセージ送信関数
        """
        filters = {}
        
        if args:
            # フィルター条件の解析
            if args in ["未着手", "進行中", "完了"]:
                filters["status"] = args
            elif args in ["数学", "統計学", "機械学習", "理論", "プログラミング"]:
                filters["category"] = args
                
        # タスク一覧の取得
        result = self.notion_service.list_tasks(filters)
        
        # 応答の生成
        if result["success"]:
            say(result["message"] or "タスクはありません")
        else:
            say(f"❌ {result['message']}")

    def _handle_update(self, args, say):
        """タスク更新の処理"""
        if not args:
            say("使用方法: update タスク名 ステータス\n"
                "例: update レポート作成 完了")
            return
            
        words = args.split()
        if len(words) < 2:
            say("タスク名とステータスを指定してください。")
            return
            
        status = words[-1]
        task_title = ' '.join(words[:-1])
        
        if not Task.validate_status(status):
            say("ステータスは「未着手」「進行中」「完了」のいずれかを指定してください。")
            return
            
        # タスクの更新
        result = self.notion_service.update_task_status(task_title, status)
        
        # 応答の生成
        if result["success"]:
            response = [
                f"✅ {result['message']}",
                "更新後の詳細:",
                str(result["task"])
            ]
            say("\n".join(response))
        else:
            say(f"❌ {result['message']}")

    def _handle_search(self, args, say):
        """タスク検索の処理"""
        if not args:
            say("検索キーワードを入力してください。")
            return
            
        # 検索の実装（今後の課題）
        say("検索機能は現在開発中です。")

    def _handle_priority_filter(self, args, say):
        """優先度フィルターの処理"""
        if not args or args not in ["高", "中", "低"]:
            say("優先度は「高」「中」「低」のいずれかを指定してください。")
            return
            
        filters = {"priority": args}
        result = self.notion_service.list_tasks(filters)
        
        if result["success"]:
            say(result["message"] or f"優先度「{args}」のタスクはありません")
        else:
            say(f"❌ {result['message']}")

    def _handle_category_filter(self, args, say):
        """カテゴリフィルターの処理"""
        if not args or args not in Task.VALID_CATEGORIES:
            say(f"カテゴリは {', '.join(Task.VALID_CATEGORIES)} のいずれかを指定してください。")
            return
            
        filters = {"categories": args}
        result = self.notion_service.list_tasks(filters)
        
        if result["success"]:
            say(result["message"] or f"分野「{args}」のタスクはありません")
        else:
            say(f"❌ {result['message']}")

    def _handle_overdue(self, say):
        """期限切れタスクの処理"""
        filters = {"overdue": True}
        result = self.notion_service.list_tasks(filters)
        
        if result["success"]:
            say(result["message"] or "期限切れのタスクはありません")
        else:
            say(f"❌ {result['message']}")

    def _show_help(self, say):
        """
        ヘルプメッセージの表示
        
        Args:
            say: メッセージ送信関数
        """
        help_text = [
            "🤖 *使用可能なコマンド:*",
            "",
            "*1. タスクの追加*",
            "```add タスク名 | 期限:YYYY-MM-DD | 優先度:高/中/低 | 分野:カテゴリー```",
            "または",
            "```add タスクの説明（自然言語）```",
            "",
            "*2. タスクの一覧表示*",
            "```list [状態/分野]```",
            "- 状態: 未着手/進行中/完了",
            "- 分野: 数学/統計学/機械学習/理論/プログラミング",
            "",
            "*3. タスクの更新*",
            "```update タスク名 状態```",
            "",
            "*4. その他の機能*",
            "- `priority 優先度`: 優先度でフィルター",
            "- `category 分野`: 分野でフィルター",
            "- `overdue`: 期限切れタスクを表示",
            "",
            "*💡 使用例:*",
            "1. `add レポート作成 | 期限:2024-03-20 | 優先度:高 | 分野:数学`",
            "2. `add 明日までに数学のレポートを提出`",
            "3. `list 未着手`",
            "4. `update レポート作成 完了`"
            "5. `こんにちは`（チャット）",
            "6. `今日はいい天気ですね`（チャット）"
        ]
        
        say("\n".join(help_text))