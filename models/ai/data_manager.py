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
import calendar

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

        # キーワード辞書
        self.category_keywords = {
            "数学": ["計算", "数式", "証明", "微分", "積分"],
            "統計学": ["統計", "確率", "分布", "標本", "検定"],
            "機械学習": ["ML", "AI", "学習", "モデル", "予測"],
            "理論": ["理論", "原理", "定理", "公理", "法則"],
            "プログラミング": ["コード", "プログラム", "開発", "実装"]
        }
        
        self.priority_keywords = {
            "高": ["重要", "急ぎ", "必須", "絶対", "今すぐ"],
            "中": ["なるべく", "できれば", "そろそろ"],
            "低": ["余裕", "ゆっくり"]
        }
        
        # テンプレートの初期化
        self._init_templates()

        # Notionから既存タスクを読み込み（エラー時は空リスト）
        self.existing_tasks = []
        try:
            self.existing_tasks = self._load_existing_tasks()
        except Exception as e:
            logger.error(f"既存タスクの読み込みに失敗: {e}")

    def _init_templates(self):
        """
        学習データ生成用のテンプレートを初期化
        
        設定項目:
        - タスクの種類（レポート、課題など）
        - カテゴリごとのテンプレート（数学、統計学など）
        - 期限の表現（今日、明日など）
        - アクション（終わらせる、提出するなど）
        """
        # 基本的なタスクの種類（出現確率）
        self.task_types = {
            "レポート": 0.3,
            "課題": 0.25,
            "宿題": 0.15,
            "テスト": 0.1,
            "演習": 0.1,
            "プリント": 0.05,
            "問題集": 0.05
        }
        
        # 期限の表現と日数のマッピング
        self.deadline_patterns = {
            "今日": {"days": 0, "weight": 0.1},
            "明日": {"days": 1, "weight": 0.2},
            "明後日": {"days": 2, "weight": 0.15},
            "今週末": {"days": (5 - datetime.now().weekday()), "weight": 0.15},
            "来週": {"days": 7, "weight": 0.2},
            "再来週": {"days": 14, "weight": 0.1},
            "今月末": {"days": (calendar.monthrange(datetime.now().year, datetime.now().month)[1] - datetime.now().day), "weight": 0.1}
        }

        # アクションと優先度の関連付け
        self.actions = {
            "高": {
                "終わらせる": 0.3,
                "完了する": 0.2,
                "提出する": 0.3,
                "急いで仕上げる": 0.2
            },
            "中": {
                "進める": 0.3,
                "取り組む": 0.3,
                "準備する": 0.2,
                "確認する": 0.2
            },
            "低": {
                "着手する": 0.4,
                "確認しておく": 0.3,
                "目を通す": 0.3
            }
        }

        # 各カテゴリのテンプレート
        self.templates = {
            "数学": self._create_category_templates("数学", ["計算", "証明", "問題"]),
            "統計学": self._create_category_templates("統計", ["分析", "検定", "推定"]),
            "機械学習": self._create_category_templates("機械学習", ["モデル", "学習", "予測"]),
            "理論": self._create_category_templates("理論", ["定理", "公理", "法則"]),
            "プログラミング": self._create_category_templates("プログラミング", ["実装", "開発", "コーディング"])
        }

    def _create_category_templates(self, category: str, keywords: List[str]) -> Dict[str, List[str]]:
        """カテゴリごとのテンプレートを生成"""
        return {
            "高": [
                f"{category}の{{task}}を{{deadline}}までに急いで{{action}}"
            ] + [
                # リスト内包表記を正しい構文で記述
                f"緊急：{{deadline}}までの{category}の{{task}}（{keyword}）" 
                for keyword in keywords
            ] + [
                f"{category}の重要な{{task}}、{{deadline}}までに{{action}}"
            ],
            "中": [
                f"{category}の{{task}}を{{deadline}}までに{{action}}"
            ] + [
                f"{category}の{{task}}（{keyword}）を{{deadline}}までに" 
                for keyword in keywords
            ] + [
                f"通常の{category}{{task}}、期限{{deadline}}"
            ],
            "低": [
                f"{category}の{{task}}、{{deadline}}まで余裕あり",
                f"優先度低：{category}の{{task}}（{{deadline}}まで）",
                f"{category}の{{task}}、ゆっくり{{action}}"
            ]
        }
    
    def _determine_priority_from_deadline(self, days: int) -> str:
        """期限から優先度を決定"""
        if days <= 1:
            return "高"
        elif days <= 3:
            return random.choices(["高", "中"], weights=[0.7, 0.3])[0]
        elif days <= 7:
            return random.choices(["中", "低"], weights=[0.7, 0.3])[0]
        else:
            return "低"

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
                tasks = result["tasks"]
                processed_tasks = self._preprocess_notion_tasks(tasks)
                logger.info(f"{len(processed_tasks)}件の既存タスクを読み込みました")
                return processed_tasks
            
        except Exception as e:
            logger.error(f"既存タスクの読み込みに失敗: {e}")
        
        return []

    def _preprocess_notion_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Notionから取得したタスクデータの前処理
        
        処理内容:
        1. 不完全なデータの補完
        2. 日付情報の標準化
        3. 優先度の推定（ない場合）
        4. カテゴリの推定（ない場合）
        """
        processed_tasks = []
        
        for task in tasks:
            if not task.get("title"):  # タイトルがない場合はスキップ
                continue
                
            processed_task = {
                "title": task["title"],
                "category": task.get("category"),
                "priority": task.get("priority"),
                "due_date": task.get("due_date"),
                "status": task.get("status", "未着手")
            }

            # 日付情報の処理
            if processed_task["due_date"]:
                try:
                    due_date = datetime.strptime(processed_task["due_date"], "%Y-%m-%d")
                    days_until = (due_date.date() - datetime.now().date()).days
                    processed_task["days_until"] = days_until
                    processed_task["deadline_type"] = self._get_deadline_type(days_until)
                except ValueError:
                    processed_task["days_until"] = None
                    processed_task["deadline_type"] = "未設定"
            
            # カテゴリの推定（未設定の場合）
            if not processed_task["category"]:
                processed_task["category"] = self._estimate_category_from_title(task["title"])
            
            # 優先度の推定（未設定の場合）
            if not processed_task["priority"]:
                processed_task["priority"] = self._estimate_priority_from_task(processed_task)
            
            processed_tasks.append(processed_task)
        
        return processed_tasks
    
    def _get_deadline_type(self, days_until: int) -> str:
        """日数から期限タイプを判定"""
        if days_until < 0:
            return "期限切れ"
        elif days_until == 0:
            return "今日"
        elif days_until == 1:
            return "明日"
        elif days_until == 2:
            return "明後日"
        elif days_until <= 7:
            return "今週"
        elif days_until <= 14:
            return "来週"
        else:
            return "長期"
    
    def _estimate_category_from_title(self, title: str) -> str:
        """タイトルからカテゴリを推定"""
        max_matches = 0
        best_category = "その他"
        
        for category, keywords in self.category_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in title)
            if matches > max_matches:
                max_matches = matches
                best_category = category
        
        return best_category

    def _estimate_priority_from_task(self, task: Dict[str, Any]) -> str:
        """
        タスク情報から優先度を推定
        
        推定基準:
        1. 期限までの日数
        2. タイトルのキーワード
        3. ステータス
        """

        # キーワードベースの優先度
        keyword_priority = None
        title = task["title"].lower()
        for priority, keywords in self.priority_keywords.items():
            if any(keyword in title for keyword in keywords):
                keyword_priority = priority
                break

        # 期限ベースの優先度
        if task.get("days_until") is not None:
            deadline_priority = self._determine_priority_from_deadline(task["days_until"])
        else:
            deadline_priority = "中"

        # ステータスベースの優先度調整
        status = task.get("status", "未着手")
        if status == "遅延":
            return "高"
        elif status == "進行中":
            return deadline_priority
        
        # 最終的な優先度の決定
        if keyword_priority:
            # キーワードと期限ベースの優先度を比較して、より高い方を採用
            priority_levels = {"高": 3, "中": 2, "低": 1}
            return max(
                keyword_priority,
                deadline_priority,
                key=lambda x: priority_levels[x]
            )
        
        return deadline_priority

    def _generate_template_based_data(self, num_samples: int) -> List[Dict[str, Any]]:
        """テンプレートベースの学習データを生成"""
        training_data = []
        
        for _ in range(num_samples):
            # 基本情報の生成
            category = random.choice(list(self.templates.keys()))
            task_type = random.choices(
                list(self.task_types.keys()),
                weights=list(self.task_types.values())
            )[0]
            
            # 期限の生成
            deadline_pattern = random.choices(
                list(self.deadline_patterns.keys()),
                weights=[p["weight"] for p in self.deadline_patterns.values()]
            )[0]
            days_until = self.deadline_patterns[deadline_pattern]["days"]
            
            # 優先度の決定
            priority = self._determine_priority_from_deadline(days_until)
            
            # アクションの選択
            action = random.choices(
                list(self.actions[priority].keys()),
                weights=list(self.actions[priority].values())
            )[0]
            
            # テンプレートの選択と文章生成
            template = random.choice(self.templates[category][priority.lower()])
            text = template.format(
                task=task_type,
                deadline=deadline_pattern,
                action=action
            )

            # データの追加
            training_data.append({
                "text": text,
                "labels": {
                    "category": category,
                    "priority": priority,
                    "deadline_type": deadline_pattern,
                    "days_until": days_until
                }
            })
        
        return training_data

    def _generate_existing_based_data(self, num_samples: int) -> List[Dict[str, Any]]:
        """既存タスクベースの学習データを生成"""
        if not self.existing_tasks:
            return []
            
        training_data = []
        for _ in range(num_samples):
            task = random.choice(self.existing_tasks)
            
            # テキストの生成
            text = f"{task['title']}"
            if task.get('due_date'):
                text += f"、期限は{task['due_date']}"
            if task.get('priority'):
                text += f"、優先度{task['priority']}"
                
            # データの追加
            training_data.append({
                "text": text,
                "labels": {
                    "category": task.get("category", "その他"),
                    "priority": task.get("priority", "中"),
                    "deadline_type": task.get("deadline_type"),
                    "days_until": task.get("days_until")
                }
            })
        
        return training_data

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

        # テンプレートベースのデータ生成（80%）
        template_samples = int(num_samples * 0.8)
        training_data.extend(self._generate_template_based_data(template_samples))
        
        # 既存タスクからのデータ生成（20%）
        if self.existing_tasks:
            existing_samples = num_samples - template_samples
            training_data.extend(self._generate_existing_based_data(existing_samples))
        
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