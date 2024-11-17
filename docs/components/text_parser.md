# TextParser - 自然言語解析モジュール

## 目次
1. [概要](#概要)
2. [主要機能](#主要機能)
3. [実装詳細](#実装詳細)
4. [処理フロー](#処理フロー)
5. [使用例](#使用例)

## 概要

TextParserは、ユーザーの自然な入力からタスク情報を抽出するモジュールである。ルールベースの解析とAI推論を組み合わせたハイブリッドアプローチを採用している。

### 特徴
- 自然言語からの情報抽出
- 日付表現の柔軟な解釈
- カテゴリと優先度の自動判定
- AIモデルとの連携による解析

## 主要機能

### 1. タスク情報の抽出
- タイトルの生成
- 期限の解析
- 優先度の推定
- カテゴリの判定

### 2. 日付解析
以下の日付表現に対応
- 絶対日付: `YYYY-MM-DD`, `MM-DD`
- 相対日付: `今日`, `明日`, `N日後`
- 週関連: `今週末`, `来週末`
- 月末関連: `今月末`, `来月末`
- 曜日指定: `今週の月曜日`, `来週の金曜日`

### 3. カテゴリ判定
Task.pyで定義された以下のカテゴリに対応
- 数学
- 統計学
- 機械学習
- データサイエンス
- 開発
- インフラ
- 研究
- インターン
- キャリア
- 提出物
- ミーティング

### 4. 優先度判定
3段階の優先度を判定
- 高: 緊急性・重要性が高いタスク
- 中: 通常の進行タスク
- 低: 余裕のあるタスク

## 実装詳細

### クラス構成

TextParserクラスは、テキスト解析の中核となるクラスである。初期化時にAIモデルのパスを受け取り、必要に応じてAI推論機能を有効化する。Task.pyで定義されたカテゴリやキーワードの定義を利用し、一貫性のある解析を実現している。

```python
class TextParser:
    def __init__(self, model_paths: Optional[Dict[str, str]] = None):
        """
        TextParserの初期化
        
        Args:
            model_paths: AIモデルのファイルパスを含む辞書
                {
                    "word2vec": "path/to/word2vec.model",
                    "fasttext": "path/to/fasttext.model",
                    "laser": "path/to/laser.model"
                }
        """
        self.logger = logging.getLogger(__name__)
        # Task.pyから定義を取得
        self.category_keywords = Task.CATEGORY_KEYWORDS
        self.priority_keywords = Task.PRIORITY_KEYWORDS
        # AIモデルの初期化
        self.ai_inference = AIInference(model_paths) if model_paths else None
```

### 主要メソッド

TextParserクラスは、以下の主要なメソッドを提供している。これらのメソッドは、テキスト解析の異なる側面を担当し、協調して動作する。

#### 1. parse_task_info メソッド

このメソッドは、TextParserの主要なエントリーポイントである。ユーザーの入力テキストを受け取り、タスク情報を構造化されたデータとして返す。処理は4つの段階で行われ、各段階で得られた情報を統合して最終的な結果を生成する。

```python
def parse_task_info(self, text: str) -> Optional[Dict[str, Any]]:
    """
    タスク情報の抽出を行う
    
    処理手順:
    1. テキストの前処理
    2. AI解析の実行（モデルが利用可能な場合）
    3. ルールベース解析の実行
    4. 結果の統合と検証
    
    Args:
        text (str): 入力テキスト
        
    Returns:
        Dict[str, Any]: {
            "title": str,  # タスクのタイトル
            "due_date": Optional[str],  # 期限（YYYY-MM-DD形式）
            "priority": str,  # 優先度（高/中/低）
            "categories": List[str],  # カテゴリのリスト
            "warnings": List[str]  # 警告メッセージのリスト
        }
    """
```

#### 2. _extract_date メソッド

日付情報の抽出を担当するメソッドである。正規表現を使用して様々な日付表現を認識し、標準形式（YYYY-MM-DD）に変換する。期限表現（「まで」「期限」など）との組み合わせを考慮し、より正確な日付抽出を実現している。

```python
def _extract_date(self, text: str) -> Optional[Dict[str, Any]]:
    """
    テキストから日付情報を抽出
    
    処理手順:
    1. 期限表現（まで、期限など）の検索
    2. 日付パターンのマッチング
    3. 相対日付の変換
    4. 信頼度の計算
    
    Returns:
        Optional[Dict[str, Any]]: {
            "date": str,  # YYYY-MM-DD形式の日付
            "confidence": float,  # 信頼度（0.0-1.0）
            "remaining_text": str  # 日付部分を除いたテキスト
        }
    
    Example:
        >>> parser._extract_date("明日までにレポート提出")
        {
            "date": "2024-03-21",
            "confidence": 1.0,
            "remaining_text": "レポート提出"
        }
    """
```

#### 3. _extract_category メソッド

テキストからカテゴリを推定するメソッドである。Task.pyで定義されたカテゴリキーワードとテキストをマッチングし、マッチした数に基づいて信頼度を計算する。複数のカテゴリが検出された場合は、それらをリストとして返す。

```python
def _extract_category(self, text: str) -> Optional[Dict[str, Any]]:
    """
    カテゴリの推定を行う
    
    処理手順:
    1. Task.CATEGORY_KEYWORDSとのマッチング
    2. マッチ数に基づく信頼度の計算
    3. 閾値（0.3）以上の信頼度を持つカテゴリの選択
    
    Returns:
        Optional[Dict[str, Any]]: {
            "categories": List[str],  # カテゴリのリスト
            "confidence": float  # 信頼度（0.0-1.0）
        }
    
    Example:
        >>> parser._extract_category("数学のレポートを提出")
        {
            "categories": ["数学", "提出物"],
            "confidence": 0.7
        }
    """
```

#### 4. _extract_priority メソッド

タスクの優先度を推定するメソッドである。キーワードベースの判定と日付ベースの判定を組み合わせて、最適な優先度を決定する。日付情報がある場合は、期限までの残り日数も考慮に入れる。

```python
def _extract_priority(self, text: str, date_info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    優先度の推定を行う
    
    処理手順:
    1. キーワードベースの優先度判定
    2. 日付ベースの優先度判定（date_infoがある場合）
    3. 両者の結果を統合し、より信頼度の高い方を採用
    
    Args:
        text: 入力テキスト
        date_info: _extract_dateの結果（オプション）
    
    Returns:
        Optional[Dict[str, Any]]: {
            "priority": str,  # "高", "中", "低"
            "confidence": float  # 信頼度（0.5-1.0）
        }
    
    Example:
        >>> parser._extract_priority("急いで提出")
        {
            "priority": "高",
            "confidence": 0.8
        }
    """
```

## TextParserの処理フロー

TextParserの処理フローは、4つの主要なステップで構成されている。各ステップは独立したメソッドとして実装され、順序立てて実行される。

### 1. テキストの前処理 (_preprocess_text)

前処理ステップでは、入力テキストを解析しやすい形式に整形する。全角文字の半角化や不要な空白の削除などの基本的な正規化を行う。日時表現の処理は、後続の解析に影響を与えないよう、オプションで制御可能である。

```python
def _preprocess_text(self, text: str, preserve_datetime: bool = False) -> Optional[str]:
    """
    テキストの前処理を行う
    
    処理内容:
    1. 全角文字の置換
    2. 日時表現の処理（preserve_datetimeがFalseの場合）
    3. 前後の空白削除
    """
    # 全角文字の置換
    text = text.replace('：', ':').replace('、', ',').replace('　', ' ')
    
    if not preserve_datetime:
        # 日時表現を削除
        text = re.sub(r'(今日|明日|明後日|今週|来週)(まで|までに)?', '', text)
    
    return text.strip()
```

### 2. AI解析の実行 (_ai_analysis)

AI解析ステップでは、AIInferenceクラスを使用してテキスト分析を行う。このステップはオプショナルであり、AIモデルが利用可能な場合のみ実行される。エラーが発生した場合は安全にNoneを返し、処理を継続する。

```python
def _ai_analysis(self, text: str) -> Optional[Dict[str, Any]]:
    """
    AIInferenceを使用したテキスト分析
    
    処理内容:
    1. AIモデルによるテキスト分析
    2. 詳細な分析結果の取得
    3. エラー発生時はNoneを返す
    """
    if not self.ai_inference:
        return None
    
    try:
        return self.ai_inference.analyze_text(text, detailed=True)
    except Exception:
        return None
```

### 3. ルールベース解析 (_rule_based_analysis)

ルールベース解析は、定義された規則に基づいてテキストを解析する。日付、カテゴリ、優先度の各要素を順番に抽出し、それぞれに信頼度を付与する。AIの解析結果が利用可能な場合は、それも考慮に入れる。

```python
def _rule_based_analysis(self, text: str, ai_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    ルールベースによる解析
    
    処理手順:
    1. 日付の抽出
    2. カテゴリの推定
    3. 優先度の推定
    4. タイトルの設定
    """
    result = {
        "title": None,
        "due_date": None,
        "priority": None,
        "categories": [],
        "confidence": {}
    }
    
    # 日付の抽出
    date_info = self._extract_date(text)
    if date_info:
        result["due_date"] = date_info["date"]
        result["confidence"]["due_date"] = date_info["confidence"]
        text = date_info["remaining_text"]
    
    # カテゴリの推定
    category_info = self._extract_category(text)
    if category_info:
        result["categories"] = category_info["categories"]
        result["confidence"]["category"] = category_info["confidence"]
    
    # 優先度の推定
    priority_info = self._extract_priority(text, date_info)
    if priority_info:
        result["priority"] = priority_info["priority"]
        result["confidence"]["priority"] = priority_info["confidence"]
    
    # タイトルの設定
    result["title"] = self._clean_title_text(text)
    result["confidence"]["title"] = Task.CONFIDENCE["TITLE"]
    
    return result
```

### 4. 結果の統合と検証 (_integrate_results)

最後のステップでは、ルールベース解析とAI解析の結果を統合する。validator.pyのResultValidatorを使用して結果の整合性を検証し、必要に応じて警告メッセージを生成する。カテゴリの重複を排除し、最終的な結果を構築する。

```python
def _integrate_results(self, rule_based: Dict[str, Any], ai_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    ルールベースとAI分析の結果を統合
    
    処理手順:
    1. ResultValidatorを使用した結果の検証
    2. カテゴリの統合
    3. 警告メッセージの生成
    """
    # ResultValidatorを使用して結果を検証・統合
    validator = ResultValidator()
    validated_result = validator.validate_results(rule_based, ai_result)
    
    # カテゴリの統合
    categories = set()
    if rule_based.get("categories"):
        categories.update(rule_based["categories"])
    if ai_result and "categories" in ai_result:
        ai_categories = [cat for cat in ai_result["categories"] if cat in Task.VALID_CATEGORIES]
        categories.update(ai_categories)
    
    validated_result["categories"] = list(categories)
    
    return validated_result
```

## 使用例

### 基本的な使用方法（ルールベースのみ）
```python
parser = TextParser()
result = parser.parse_task_info("明日までに数学のレポートを提出")
```

### 期待される出力（ルールベース）
```python
{
    "title": "数学レポート提出",
    "due_date": "2024-11-18",  # 明日の日付(11月17日現在)
    "priority": "高",
    "categories": ["数学", "提出物"],
    "warnings": ["⚠️ 期限が近づいています（残り1日）"]
}
```

### AIモデルを使用した場合
```python
# AIモデルのパスを指定して初期化
model_paths = {
    "word2vec": "path/to/word2vec.model",
    "fasttext": "path/to/fasttext.model",
    "laser": "path/to/laser.model"
}
parser = TextParser(model_paths)

# より複雑な入力に対する解析
result = parser.parse_task_info(
    "機械学習の最終課題について、データの前処理とモデルの実装を行う必要がある"
)
```

### 期待される出力（AIモデル使用）
```python
{
    "title": "機械学習最終課題",
    "categories": [
        "機械学習",
        "データサイエンス",
        "開発"  # 「実装」というキーワードから推測
    ],
    "priority": "中",  # 明示的な緊急性が示されていないため
    "confidence": {
        "title": 0.8,
        "categories": {
            "機械学習": 0.9,
            "データサイエンス": 0.7,
            "開発": 0.6
        },
        "priority": 0.5
    },
    "warnings": [
        "ℹ️ 期限が設定されていません",
        "ℹ️ 複数のカテゴリが検出されました"
    ]
}
```

このように、AIモデルを使用することで、より複雑な入力に対しても適切な解析が可能となる。特に以下の点が強化される。

1. 文脈を考慮したタイトル生成
2. 複数カテゴリの検出と信頼度の計算
3. 暗示的な表現からの情報抽出

### エラーハンドリング
```python
try:
    result = parser.parse_task_info(text)
    if result is None:
        print("タスク情報の抽出に失敗しました")
except Exception as e:
    print(f"エラーが発生しました: {str(e)}")
``` 