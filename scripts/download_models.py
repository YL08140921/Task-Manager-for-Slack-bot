"""
必要な学習済みモデルを自動的にダウンロードして配置
"""

import os
import urllib.request
import gzip
import shutil
from pathlib import Path
import subprocess
from tqdm import tqdm
import sys

class ModelDownloader:
    def __init__(self):
        self.base_dir = Path("/home/ubuntu/execution/Task-Manager-for-Slack-bot/models/ai/pretrained")
        
        # 各モデルのディレクトリ
        self.word2vec_dir = self.base_dir / "word2vec"
        self.fasttext_dir = self.base_dir / "fasttext"
        self.laser_dir = self.base_dir / "laser"
        
        # モデルファイルのパス
        self.word2vec_path = self.word2vec_dir / "japanese.model"
        self.fasttext_path = self.fasttext_dir / "cc.ja.300.bin"
        self.laser_path = self.laser_dir / "japanese"

    def create_directories(self):
        """必要なディレクトリを作成"""
        for dir_path in [self.word2vec_dir, self.fasttext_dir, self.laser_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def download_with_progress(self, url, filepath):
        """プログレスバー付きでファイルをダウンロード"""
        try:
            with urllib.request.urlopen(url) as response:
                total_size = int(response.headers['Content-Length'])
                with open(filepath, 'wb') as f, tqdm(
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    desc=f"Downloading {filepath.name}"
                ) as pbar:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        pbar.update(len(chunk))
            return True
        except Exception as e:
            print(f"ダウンロード中にエラーが発生しました: {e}")
            return False

    def download_word2vec(self):
        """Word2Vecモデルのダウンロード"""
        if self.word2vec_path.exists():
            print("Word2Vecモデルは既に存在します")
            return True

        print("Word2Vecモデルをダウンロードしています...")
        url = "https://github.com/singletongue/WikiEntVec/releases/download/20190520/jawiki.word_vectors.300d.txt.bz2"
        bz2_path = self.word2vec_dir / "jawiki.word_vectors.300d.txt.bz2"
        txt_path = self.word2vec_dir / "japanese.txt"
        
        success = self.download_with_progress(url, bz2_path)
        if success:
            # BZ2ファイルを解凍
            try:
                import bz2
                print("ファイルを解凍しています...")
                with bz2.open(bz2_path, 'rb') as f_in:
                    with open(txt_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                bz2_path.unlink()  # BZ2ファイルを削除

                # テキストファイルをWord2Vecモデルに変換
                print("モデルを変換しています...")
                from gensim.models import KeyedVectors
                model = KeyedVectors.load_word2vec_format(str(txt_path), binary=False)
                model.save(str(self.word2vec_path))

                # 中間ファイルを削除
                txt_path.unlink()
                return True

            except Exception as e:
                print(f"解凍中にエラーが発生しました: {e}")
                return False
        return False

    def download_fasttext(self):
        """FastTextモデルのダウンロード"""
        if self.fasttext_path.exists():
            print("FastTextモデルは既に存在します")
            return True

        print("FastTextモデルをダウンロードしています...")
        url = "https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.ja.300.bin.gz"
        gz_path = self.fasttext_path.with_suffix('.bin.gz')
        
        success = self.download_with_progress(url, gz_path)
        if success:
            print("ファイルを解凍しています...")
            try:
                with gzip.open(gz_path, 'rb') as f_in:
                    with open(self.fasttext_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                gz_path.unlink()  # GZファイルを削除
                return True
            except Exception as e:
                print(f"解凍中にエラーが発生しました: {e}")
                return False
        return False

    def download_laser(self):
        """LASERモデルのダウンロード"""
        if self.laser_path.exists():
            print("LASERモデルは既に存在します")
            return True

        print("LASERモデルをダウンロードしています...")
        try:
            subprocess.run([
                sys.executable,
                "-m",
                "pip",
                "install",
                "laserembeddings"
            ])
            subprocess.run([
                sys.executable,
                "-m",
                "laserembeddings",
                "download-models"
            ])
            return True
        except Exception as e:
            print(f"LASERモデルのダウンロード中にエラーが発生しました: {e}")
            return False

    def verify_downloads(self):
        """ダウンロードの検証"""
        missing = []
        # if not self.word2vec_path.exists():
            # missing.append("Word2Vec")
        if not self.fasttext_path.exists():
            missing.append("FastText")
        # if not self.laser_path.exists():
            # missing.append("LASER")
        return missing

    def download_all(self):
        """全モデルのダウンロード"""
        self.create_directories()
        
        results = {
            # "Word2Vec": self.download_word2vec(),
            "FastText": self.download_fasttext(),
            # "LASER": self.download_laser()
        }
        
        print("\nダウンロード結果:")
        for model, success in results.items():
            status = "成功" if success else "失敗"
            print(f"{model}: {status}")
        
        # 検証
        missing = self.verify_downloads()
        if missing:
            print(f"\n警告: 以下のモデルのダウンロードに失敗した可能性があります: {', '.join(missing)}")
        else:
            print("\n全てのモデルが正常にダウンロードされました")

if __name__ == "__main__":
    downloader = ModelDownloader()
    downloader.download_all()