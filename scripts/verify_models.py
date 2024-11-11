"""
事前学習済みモデルの検証スクリプト
Word2Vec、FastText、LASERモデルの読み込みと基本的な推論をテスト

使用方法:
    python verify_models.py [--debug] [--model MODEL_NAME]

オプション:
    --debug         デバッグモードを有効化
    --model         特定のモデルのみを検証（word2vec, fasttext, laser）
"""

import argparse
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import psutil
import torch
import yaml
from tqdm import tqdm

# プロジェクトのルートディレクトリをPythonパスに追加
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# プロジェクト内のモジュールをインポート
from models.ai.embeddings.word2vec_model import Word2VecModel
from models.ai.embeddings.fasttext_model import FastTextModel
from models.ai.embeddings.laser_model import LaserModel
from scripts.utils.memory_tracker import MemoryTracker

class ModelVerifier:
    """モデル検証クラス"""

    def __init__(self, debug: bool = False):
        """
        初期化
        
        Args:
            debug (bool): デバッグモードフラグ
        """
        self.debug = debug
        self.setup_logging()
        self.memory_tracker = MemoryTracker(self.logger)
        self.pretrained_dir = ROOT_DIR / "models" / "ai" / "pretrained"
        
        # テスト用データ
        self.test_sentences = [
            "機械学習の研究を行っています。",
            "自然言語処理の技術を開発中です。",
            "データ分析の重要性が増しています。",
            "プログラミング言語の学習方法について。",
            "アルゴリズムの最適化に取り組んでいます。"
        ]
        
        self.test_words = [
            "プログラム",
            "コンピュータ",
            "アルゴリズム",
            "データ",
            "学習"
        ]

    def setup_logging(self):
        """ロギングの設定"""
        self.logger = logging.getLogger("ModelVerifier")
        self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        
        # ファイルハンドラ
        log_dir = ROOT_DIR / "logs"
        log_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler(log_dir / "model_verification.log")
        fh.setLevel(logging.DEBUG)
        
        # コンソールハンドラ
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG if self.debug else logging.INFO)
        
        # フォーマッタ
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def verify_word2vec(self) -> bool:
        """
        Word2Vecモデルの検証
        
        Returns:
            bool: 検証成功の場合True
        """
        self.logger.info("=== Word2Vecモデルの検証開始 ===")
        model_path = self.pretrained_dir / "word2vec" / "japanese.model"
        
        try:
            # メモリ使用量の追跡開始
            self.memory_tracker.start_tracking()
            start_time = time.time()
            
            # モデルのロード
            self.logger.info(f"モデルを読み込んでいます: {model_path}")
            model = Word2VecModel(str(model_path))
            
            load_time = time.time() - start_time
            self.logger.info(f"読み込み時間: {load_time:.2f}秒")
            self.memory_tracker.log_memory_usage("Word2Vec読み込み後")
            
            # 基本的な推論テスト
            self.logger.info("基本的な推論テストを実行中...")
            for word in tqdm(self.test_words, desc="単語テスト"):
                embedding = model.get_embedding(word)
                if embedding is not None:
                    if self.debug:
                        self.logger.debug(
                            f"'{word}' の埋め込み - "
                            f"形状: {embedding.shape}, "
                            f"ノルム: {np.linalg.norm(embedding):.2f}"
                        )
                else:
                    self.logger.warning(f"'{word}' の埋め込みに失敗しました")
            
            # 文章の埋め込みテスト
            for sentence in tqdm(self.test_sentences, desc="文章テスト"):
                embedding = model.get_embedding(sentence)
                if embedding is not None and self.debug:
                    self.logger.debug(
                        f"文章の埋め込み - "
                        f"形状: {embedding.shape}, "
                        f"ノルム: {np.linalg.norm(embedding):.2f}"
                    )
            
            # 類似度計算テスト
            if len(self.test_sentences) >= 2:
                similarity = model.get_similarity(
                    self.test_sentences[0],
                    self.test_sentences[1]
                )
                self.logger.info(f"文章間の類似度: {similarity:.4f}")
            
            # メモリ使用状況の記録
            current, peak = self.memory_tracker.stop_tracking()
            self.logger.info(f"現在のメモリ使用量: {current:.2f}MB")
            self.logger.info(f"ピークメモリ使用量: {peak:.2f}MB")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Word2Vecモデルの検証中にエラーが発生しました: {str(e)}")
            if self.debug:
                self.logger.error(traceback.format_exc())
            return False

    def verify_fasttext(self) -> bool:
        """
        FastTextモデルの検証
        
        Returns:
            bool: 検証成功の場合True
        """
        self.logger.info("=== FastTextモデルの検証開始 ===")
        model_path = self.pretrained_dir / "fasttext" / "cc.ja.300.bin"
        
        try:
            # メモリ使用量の追跡開始
            self.memory_tracker.start_tracking()
            start_time = time.time()
            
            # モデルのロード
            self.logger.info(f"モデルを読み込んでいます: {model_path}")
            model = FastTextModel(str(model_path))
            
            load_time = time.time() - start_time
            self.logger.info(f"読み込み時間: {load_time:.2f}秒")
            self.memory_tracker.log_memory_usage("FastText読み込み後")
            
            # 基本的な推論テスト
            self.logger.info("基本的な推論テストを実行中...")
            for sentence in tqdm(self.test_sentences, desc="文章テスト"):
                embedding = model.get_embedding(sentence)
                if embedding is not None and self.debug:
                    self.logger.debug(
                        f"文章の埋め込み - "
                        f"形状: {embedding.shape}, "
                        f"ノルム: {np.linalg.norm(embedding):.2f}"
                    )
            
            # 類似度計算テスト
            if len(self.test_sentences) >= 2:
                similarity = model.get_similarity(
                    self.test_sentences[0],
                    self.test_sentences[1]
                )
                self.logger.info(f"文章間の類似度: {similarity:.4f}")
            
            # メモリ使用状況の記録
            current, peak = self.memory_tracker.stop_tracking()
            self.logger.info(f"現在のメモリ使用量: {current:.2f}MB")
            self.logger.info(f"ピークメモリ使用量: {peak:.2f}MB")
            
            return True
            
        except Exception as e:
            self.logger.error(f"FastTextモデルの検証中にエラーが発生しました: {str(e)}")
            if self.debug:
                self.logger.error(traceback.format_exc())
            return False

    def verify_laser(self) -> bool:
        """
        LASERモデルの検証
        
        Returns:
            bool: 検証成功の場合True
        """
        self.logger.info("=== LASERモデルの検証開始 ===")
        model_dir = self.pretrained_dir / "laser"
        required_files = [
            "93langs.fcodes",
            "93langs.fvocab",
            "bilstm.93langs.2018-12-26.pt"
        ]
        
        try:
            # 必要なファイルの存在確認
            for file in required_files:
                file_path = model_dir / file
                if not file_path.exists():
                    raise FileNotFoundError(f"必要なファイルが見つかりません: {file}")
            
            # メモリ使用量の追跡開始
            self.memory_tracker.start_tracking()
            start_time = time.time()
            
            # モデルのロード
            self.logger.info(f"モデルを読み込んでいます: {model_dir}")
            model = LaserModel(str(model_dir))
            
            load_time = time.time() - start_time
            self.logger.info(f"読み込み時間: {load_time:.2f}秒")
            self.memory_tracker.log_memory_usage("LASER読み込み後")
            
            # 基本的な推論テスト
            self.logger.info("基本的な推論テストを実行中...")
            for sentence in tqdm(self.test_sentences, desc="文章テスト"):
                embedding = model.get_embedding(sentence)
                if embedding is not None and self.debug:
                    self.logger.debug(
                        f"文章の埋め込み - "
                        f"形状: {embedding.shape}, "
                        f"ノルム: {np.linalg.norm(embedding):.2f}"
                    )
            
            # 類似度計算テスト
            if len(self.test_sentences) >= 2:
                similarity = model.get_similarity(
                    self.test_sentences[0],
                    self.test_sentences[1]
                )
                self.logger.info(f"文章間の類似度: {similarity:.4f}")
            
            # メモリ使用状況の記録
            current, peak = self.memory_tracker.stop_tracking()
            self.logger.info(f"現在のメモリ使用量: {current:.2f}MB")
            self.logger.info(f"ピークメモリ使用量: {peak:.2f}MB")
            
            return True
            
        except Exception as e:
            self.logger.error(f"LASERモデルの検証中にエラーが発生しました: {str(e)}")
            if self.debug:
                self.logger.error(traceback.format_exc())
            return False

    def save_verification_results(self, results: Dict[str, bool]):
        """
        検証結果をYAMLファイルに保存
        
        Args:
            results (Dict[str, bool]): モデルごとの検証結果
        """
        output_dir = ROOT_DIR / "logs"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "verification_results.yaml"
        
        # システム情報を追加
        memory_info = self.memory_tracker.get_system_memory_info()
        results_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system_info": {
                "total_memory": f"{memory_info['total']:.2f}GB",
                "available_memory": f"{memory_info['available']:.2f}GB",
                "memory_usage": f"{memory_info['percent']}%",
                "gpu_available": torch.cuda.is_available(),
                "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A",
            },
            "results": {
                model: {
                    "status": "成功" if success else "失敗",
                    "verified_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                for model, success in results.items()
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(results_data, f, allow_unicode=True, default_flow_style=False)
        
        self.logger.info(f"検証結果を保存しました: {output_path}")

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description="事前学習済みモデルの検証")
    parser.add_argument('--debug', action='store_true', help='デバッグモードを有効化')
    parser.add_argument(
        '--model',
        choices=['word2vec', 'fasttext', 'laser'],
        help='特定のモデルのみを検証'
    )
    args = parser.parse_args()
    
    verifier = ModelVerifier(debug=args.debug)
    results = {}
    
    try:
        # システム情報の出力
        verifier.logger.info("=== システム情報 ===")
        verifier.memory_tracker.log_system_info()
        
        if args.model:
            # 特定のモデルのみ検証
            if args.model == 'word2vec':
                results['word2vec'] = verifier.verify_word2vec()
            elif args.model == 'fasttext':
                results['fasttext'] = verifier.verify_fasttext()
            elif args.model == 'laser':
                results['laser'] = verifier.verify_laser()
        else:
            # すべてのモデルを検証
            results['word2vec'] = verifier.verify_word2vec()
            results['fasttext'] = verifier.verify_fasttext()
            results['laser'] = verifier.verify_laser()
        
        # 検証結果の保存
        verifier.save_verification_results(results)
        
    except Exception as e:
        verifier.logger.error(f"検証中にエラーが発生しました: {str(e)}")
        if verifier.debug:
            verifier.logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
