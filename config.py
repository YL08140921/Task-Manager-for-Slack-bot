import os
from dotenv import load_dotenv
from pathlib import Path


class Config:
    def __init__(self):
        load_dotenv()
        self.root_dir = Path(__file__).parent
        self.notion_token = os.getenv("NOTION_TOKEN")
        self.notion_database_id = os.getenv("NOTION_DATABASE_ID")
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_app_token = os.getenv("SLACK_APP_TOKEN")

        self.data_dir = self.root_dir / "data"
        self.models_dir = self.root_dir / "models"
        self.pretrained_dir = self.models_dir / "ai" / "pretrained"

        # AIモデルのパス設定
        self.model_paths = self._setup_model_paths()
        
        # 学習設定
        self.training_config = self._setup_training_config()

    def _setup_model_paths(self):
        """AIモデルのパス設定を初期化"""
        # デフォルトのモデルパス
        default_paths = {
            'word2vec': str(self.pretrained_dir / "word2vec" / "japanese.model"),
            'fasttext': str(self.pretrained_dir / "fasttext" / "japanese.bin"),
            'laser': str(self.pretrained_dir / "laser")
        }
        
        # 環境変数が設定されている場合は優先
        return {
            'word2vec': os.getenv("WORD2VEC_MODEL_PATH", default_paths['word2vec']),
            'fasttext': os.getenv("FASTTEXT_MODEL_PATH", default_paths['fasttext']),
            'laser': os.getenv("LASER_MODEL_PATH", default_paths['laser'])
        }

    def _setup_training_config(self):
        """学習設定を初期化"""
        return {
            'batch_size': int(os.getenv("TRAINING_BATCH_SIZE", "32")),
            'epochs': int(os.getenv("TRAINING_EPOCHS", "10")),
            'learning_rate': float(os.getenv("TRAINING_LEARNING_RATE", "0.001"))
        }

    def ensure_model_directories(self):
        """必要なディレクトリ構造を作成"""
        # pretrainedディレクトリとサブディレクトリを作成
        for model_type in ['word2vec', 'fasttext', 'laser']:
            model_dir = self.pretrained_dir / model_type
            model_dir.mkdir(parents=True, exist_ok=True)

    def verify_model_paths(self):
        """モデルパスの存在確認"""
        missing_models = []
        for model_type, path in self.model_paths.items():
            if not Path(path).exists():
                missing_models.append(model_type)
        return missing_models

    def debug_print(self):
        """設定の状態を確認するデバッグ用メソッド"""
        print("\n=== 設定状態 ===")

        print("\nディレクトリ構造:")
        print(f"ルートディレクトリ: {self.root_dir}")
        print(f"データディレクトリ: {self.data_dir}")
        print(f"モデルディレクトリ: {self.models_dir}")
        print(f"事前学習済みモデルディレクトリ: {self.pretrained_dir}")

        print("環境変数の確認:")
        print(f"NOTION_TOKEN: {'設定されています' if self.notion_token else '設定されていません'}")
        print(f"NOTION_DATABASE_ID: {self.notion_database_id}")
        print(f"SLACK_BOT_TOKEN: {'設定されています' if self.slack_bot_token else '設定されていません'}")
        print(f"SLACK_APP_TOKEN: {'設定されています' if self.slack_app_token else '設定されていません'}")

        print("\nAIモデルのパス:")
        for model_name, path in self.model_paths.items():
            exists = Path(path).exists()
            status = '存在します' if exists else '見つかりません'
            print(f"{model_name}: {path} ({status})")
        
        print("\n学習設定:")
        for key, value in self.training_config.items():
            print(f"{key}: {value}")