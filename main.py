from config import Config
from models.task import Task
from services.notion_service import NotionService
from services.slack_service import SlackService
from utils.text_parser import TextParser
import logging

class TaskBot:
    """タスク管理Botのメインクラス"""
    
    def __init__(self):
        """
        Botの初期化
        設定の読み込みと各サービスの初期化を行う
        """
        # ログ設定
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        try:
            # 設定の読み込み
            self.logger.info("設定を読み込んでいます...")
            self.config = Config()
            self.config.debug_print()
            
            # Notionサービスの初期化
            self.logger.info("Notionサービスを初期化しています...")
            self.notion_service = NotionService(self.config)
            
            # Slackサービスの初期化
            self.logger.info("Slackサービスを初期化しています...")
            self.slack_service = SlackService(self.config, self.notion_service)
            
            # テキストパーサーの準備
            self.text_parser = TextParser()
            
        except Exception as e:
            self.logger.error(f"初期化中にエラーが発生しました: {str(e)}")
            raise

    def start(self):
        """
        Botを起動する
        """
        try:
            self.logger.info("Botを起動しています...")
            self.slack_service.start(self.config.slack_app_token)
            self.logger.info("Botの起動が完了しました")
        except Exception as e:
            self.logger.error(f"起動中にエラーが発生しました: {str(e)}")
            raise

def main():
    """
    メイン処理
    Botの初期化と起動を行う
    """
    try:
        bot = TaskBot()
        bot.start()
    except Exception as e:
        logging.error(f"プログラムの実行中にエラーが発生しました: {str(e)}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())