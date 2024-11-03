import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()
        self.notion_token = os.getenv("NOTION_TOKEN")
        self.notion_database_id = os.getenv("NOTION_DATABASE_ID")
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_app_token = os.getenv("SLACK_APP_TOKEN")

    def debug_print(self):
        """設定の状態を確認するデバッグ用メソッド"""
        print("環境変数の確認:")
        print(f"NOTION_TOKEN: {'設定されています' if self.notion_token else '設定されていません'}")
        print(f"NOTION_DATABASE_ID: {self.notion_database_id}")
        print(f"SLACK_BOT_TOKEN: {'設定されています' if self.slack_bot_token else '設定されていません'}")
        print(f"SLACK_APP_TOKEN: {'設定されています' if self.slack_app_token else '設定されていません'}")