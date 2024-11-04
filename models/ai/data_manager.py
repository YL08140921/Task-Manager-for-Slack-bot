"""
学習データの生成と管理を行うモジュール

主な機能:
1. テンプレートベースの学習データ生成
2. 既存タスクからの学習データ追加
3. データの保存と読み込み
4. 学習用・評価用データの分割
"""
import json
import os
from datetime import datetime
import random
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataManager:
    """
    学習データの生成・管理クラス
    
    テンプレートベースのデータ生成と既存タスクからの
    データ収集を組み合わせて、多様な学習データを作成
    """
    
    def __init__(self):
        # データ保存用ディレクトリの設定
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.data_dir = os.path.join(project_root, "data", "training")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Notionから既存タスクを読み込み
        self.existing_tasks = self._load_existing_tasks()
        
        # テンプレートの初期化
        self._init_templates()

    def _init_templates(self):
        """
        学習データ生成用のテンプレートを初期化
        
        設定項目:
        - タスクの種類（レポート、課題など）
        - カテゴリごとのテンプレート（数学、統計学など）
        - 期限の表現（今日、明日など）
        - アクション（終わらせる、提出するなど）
        """
        # タスクの種類
        self.task_types = [
            "レポート", "課題", "宿題", "テスト", "演習",
            "プリント", "問題集", "中間試験", "期末試験"
        ]
        
        # 各カテゴリのテンプレート
        self.templates = {
            # 数学カテゴリ
            "数学": {
                "high": [  # 高優先度
                    "数学の{task}を{deadline}までに急いで{action}",
                    "緊急：{deadline}までの数学の{task}",
                    "{deadline}締切の数学{task}、最優先で{action}"
                ],
                "medium": [  # 中優先度
                    "数学の{task}を{deadline}までに{action}",
                    "{deadline}までの数学{task}",
                    "通常の数学{task}を{deadline}までに"
                ],
                "low": [  # 低優先度
                    "余裕のある数学の{task}、{deadline}まで",
                    "{deadline}の数学{task}、後でいい",
                    "数学{task}、{deadline}が期限"
                ]
            },
            # 統計学カテゴリ（同様のパターン）
            "統計学": {
                "high": [
                    "統計の{task}、{deadline}までに急いで{action}",
                    "優先度高：{deadline}の統計{task}",
                    "統計学の{task}を即急で{action}"
                ],
                "medium": [
                    "統計の{task}を{deadline}までに{action}",
                    "{deadline}の統計{task}",
                    "通常の統計課題、期限{deadline}"
                ],
                "low": [
                    "統計の{task}、{deadline}まで余裕あり",
                    "ゆっくりでいい統計{task}、{deadline}まで",
                    "{deadline}の統計{task}、急ぎではない"
                ]
            },
            # 機械学習カテゴリ
            "機械学習": {
                "high": [
                    "機械学習の{task}を{deadline}までに急いで{action}",
                    "緊急：{deadline}までの機械学習{task}",
                    "機械学習{task}、{deadline}までに最優先で{action}"
                ],
                "medium": [
                    "機械学習の{task}を{deadline}までに{action}",
                    "{deadline}の機械学習{task}",
                    "通常の機械学習課題、期限{deadline}"
                ],
                "low": [
                    "機械学習の{task}、{deadline}まで余裕あり",
                    "{deadline}の機械学習{task}、後でいい",
                    "機械学習{task}、{deadline}が期限"
                ]
            },
            # 理論カテゴリ
            "理論": {
                "high": [
                    "理論の{task}を{deadline}までに急いで{action}",
                    "緊急：{deadline}までの理論{task}",
                    "理論{task}、{deadline}までに最優先で{action}"
                ],
                "medium": [
                    "理論の{task}を{deadline}までに{action}",
                    "{deadline}の理論{task}",
                    "通常の理論課題、期限{deadline}"
                ],
                "low": [
                    "理論の{task}、{deadline}まで余裕あり",
                    "{deadline}の理論{task}、後でいい",
                    "理論{task}、{deadline}が期限"
                ]
            },
            # プログラミングカテゴリ
            "プログラミング": {
                "high": [
                    "プログラミングの{task}を{deadline}までに急いで{action}",
                    "緊急：{deadline}までのプログラミング{task}",
                    "プログラミング{task}、{deadline}までに最優先で{action}"
                ],
                "medium": [
                    "プログラミングの{task}を{deadline}までに{action}",
                    "{deadline}のプログラミング{task}",
                    "通常のプログラミング課題、期限{deadline}"
                ],
                "low": [
                    "プログラミングの{task}、{deadline}まで余裕あり",
                    "{deadline}のプログラミング{task}、後でいい",
                    "プログラミング{task}、{deadline}が期限"
                ]
            }
        }
        
        # 期限の表現
        self.deadlines = [
            "今日", "明日", "明後日", "今週末", "来週",
            "今月末", "３日後", "一週間後", "２週間後"
        ]
        
        # アクション
        self.actions = [
            "終わらせる", "完了する", "提出する",
            "仕上げる", "完成させる", "片付ける"
        ]

    def _load_existing_tasks(self) -> List[Dict[str, Any]]:
        """
        NotionServiceから既存のタスクを読み込む
        
        Returns:
            List[Dict[str, Any]]: 読み込んだタスクのリスト
            失敗時は空リストを返す
        """
        try:
            from services.notion_service import NotionService
            from config import Config
            
            notion_service = NotionService(Config())
            result = notion_service.list_tasks()
            
            if result["success"]:
                logger.info(f"{len(result['tasks'])}件の既存タスクを読み込みました")
                return result["tasks"]
            
        except Exception as e:
            logger.error(f"既存タスクの読み込みに失敗: {e}")
        
        return []

    def generate_training_data(self, num_samples: int = 1000) -> List[Dict[str, Any]]:
        """
        学習データを生成
        
        2つのソースからデータを生成:
        1. テンプレートベースのランダム生成
        2. 既存タスクからの変換
        
        Args:
            num_samples (int): 生成するサンプル数
            
        Returns:
            List[Dict[str, Any]]: 生成された学習データ
        """
        training_data = []

        # テンプレートベースのデータ生成
        for _ in range(num_samples):
            # ランダムな要素の選択
            category = random.choice(list(self.templates.keys()))
            priority = random.choice(["high", "medium", "low"])
            task = random.choice(self.task_types)
            deadline = random.choice(self.deadlines)
            action = random.choice(self.actions)

            # テンプレートの選択と適用
            template = random.choice(self.templates[category][priority])
            text = template.format(
                task=task,
                deadline=deadline,
                action=action
            )

            # データの追加
            training_data.append({
                "text": text,
                "labels": {
                    "category": category,
                    "priority": "高" if priority == "high" else "中" if priority == "medium" else "低",
                    "deadline_type": deadline
                }
            })

        # 既存タスクからのデータ追加
        for task in self.existing_tasks:
            if task.title and task.category:
                text = f"{task.title} {task.due_date if task.due_date else ''}"
                training_data.append({
                    "text": text,
                    "labels": {
                        "category": task.category,
                        "priority": task.priority if task.priority else "中",
                        "deadline_type": "指定日" if task.due_date else "未設定"
                    }
                })

        return training_data

    def save_data(self, data: List[Dict[str, Any]], filename: str):
        """
        データをJSONファイルとして保存
        
        Args:
            data: 保存するデータ
            filename: 保存先のファイル名
        """
        file_path = os.path.join(self.data_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"データを保存しました: {file_path}")

    def load_data(self, filename: str) -> List[Dict[str, Any]]:
        """
        JSONファイルからデータを読み込み
        
        Args:
            filename: 読み込むファイル名
            
        Returns:
            読み込んだデータ（ファイルが存在しない場合は空リスト）
        """
        file_path = os.path.join(self.data_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def prepare_training_data(self):
        """
        学習データの準備を行う
        
        処理の流れ:
        1. 学習データの生成
        2. 全データの保存
        3. 学習用と評価用にデータを分割（8:2）
        4. 分割したデータの保存
        """
        # 生成データの作成と保存
        training_data = self.generate_training_data()
        self.save_data(training_data, "training_data.json")
        
        # データの分割（学習用と評価用）
        random.shuffle(training_data)
        split_point = int(len(training_data) * 0.8)  # 80%を学習用
        
        train_data = training_data[:split_point]
        eval_data = training_data[split_point:]
        
        self.save_data(train_data, "train.json")
        self.save_data(eval_data, "eval.json")
        
        logger.info(f"学習データ: {len(train_data)}件")
        logger.info(f"評価データ: {len(eval_data)}件")

if __name__ == "__main__":
    manager = DataManager()
    manager.prepare_training_data()