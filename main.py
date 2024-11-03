from config import Config
from models.task import Task
from services.notion_service import NotionService
from services.slack_service import SlackService
from utils.text_parser import TextParser
from datetime import datetime, timedelta
import logging
import threading
import time

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
        # 優先度更新テスト用
        # self.priority_update_interval = 30
        
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
            
            # 優先度更新用のスレッド初期化
            self.priority_update_thread = threading.Thread(
                target=self._priority_update_loop,
                daemon=True
            )
            
        except Exception as e:
            self.logger.error(f"初期化中にエラーが発生しました: {str(e)}")
            raise

    def start(self):
        """
        Botを起動する
        """
        try:
            self.logger.info("Botを起動しています...")

            # 優先度更新スレッドの開始
            self.priority_update_thread.start()
            self.logger.info("優先度自動更新を開始しました")
            self.slack_service.start(self.config.slack_app_token)
            self.logger.info("Botの起動が完了しました")
        except Exception as e:
            self.logger.error(f"起動中にエラーが発生しました: {str(e)}")
            raise

    def _priority_update_loop(self):
        """
        定期的に優先度を更新するループ処理
        起動時に1回実行し、その後1時間ごとに実行
        """
        while True:
            try:
                self.logger.info("タスクの優先度を更新しています...")
                result = self.notion_service.update_priorities()
                
                if result["success"]:
                    if result["updated_count"] > 0:
                        self.logger.info(result["message"])
                    else:
                        self.logger.info("更新が必要なタスクはありませんでした")
                else:
                    self.logger.error(result["message"])
                    
            except Exception as e:
                self.logger.error(f"優先度更新中にエラーが発生しました: {str(e)}")
            
            # 次の更新まで1時間待機
            self.logger.info("次の優先度更新は1時間後に実行されます")
            time.sleep(3600)

    # def _priority_update_loop(self):
    #     """
    #     定期的に優先度を更新するループ処理
    #     テスト用に短い間隔で実行
    #     """
    #     while True:
    #         try:
    #             self.logger.info("\n=== 優先度更新処理開始 ===")
    #             self.logger.info(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
    #             result = self.notion_service.update_priorities()
                
    #             if result["success"]:
    #                 if result["updated_count"] > 0:
    #                     self.logger.info(f"更新成功: {result['message']}")
    #                 else:
    #                     self.logger.info("更新対象のタスクはありませんでした")
    #             else:
    #                 self.logger.error(f"更新失敗: {result['message']}")
                
    #             self.logger.info("=== 優先度更新処理完了 ===\n")
                    
    #         except Exception as e:
    #             self.logger.error(f"エラー発生: {str(e)}")
            
    #         # 次の更新まで待機
    #         next_update = datetime.now() + timedelta(seconds=self.priority_update_interval)
    #         self.logger.info(f"次回更新予定: {next_update.strftime('%H:%M:%S')}")
    #         time.sleep(self.priority_update_interval)

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