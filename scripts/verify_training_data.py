"""
学習データの生成と検証を行うスクリプト
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.ai.data_manager import DataManager

def main():
    # データマネージャーの初期化
    manager = DataManager()

    # 学習データの準備
    print("学習データを生成しています...")
    manager.prepare_training_data()

    # データの確認
    train_data = manager.load_data("train.json")
    print(f"\n学習データの件数: {len(train_data)}")
    print("\nサンプルデータ:")
    for i in range(3):  # 最初の3件を表示
        print(f"\nサンプル {i+1}:")
        print(f"テキスト: {train_data[i]['text']}")
        print(f"ラベル: {train_data[i]['labels']}")

if __name__ == "__main__":
    main()