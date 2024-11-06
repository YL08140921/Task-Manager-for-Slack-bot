"""
検証層モジュール
ルールベースとAI推論の結果を検証し、最終的な判断を行う
既存のTask、Ensemble、TextParserの設計を活用
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from models.task import Task

class ResultValidator:
    """
    Task.pyで定義された定数や判定ロジックを活用して
    ルールベースとAI推論の結果を検証する
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.priority_keywords = Task.PRIORITY_KEYWORDS
        self.category_keywords = Task.CATEGORY_KEYWORDS
        self.confidence_settings = Task.CONFIDENCE
        self.urgency_levels = Task.URGENCY_LEVELS
    
    def validate_results(
        self,
        rule_based: Dict[str, Any],
        ai_result: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        ルールベースとAI推論の結果を検証
        
        検証の流れ:
        1. 基本フィールドの検証
        2. 信頼度の高い情報を優先して選択
        3. 期限ベースの優先度調整
        4. 整合性チェックと警告生成

        Args:
            rule_based: ルールベースの解析結果
            ai_result: AI推論の結果（オプション）
            
        Returns:
            Dict: {
                "title": str,
                "due_date": Optional[str],
                "priority": str,
                "category": Optional[str],
                "confidence": float,
                "warnings": List[str]
            }
        """
        # 基本検証
        validated = self._validate_basic_fields(rule_based, ai_result)
        
        # 信頼度の高い情報を優先して選択
        validated = self._select_high_confidence_results(
            validated, rule_based, ai_result
        )
        
        # 期限ベースの優先度調整と警告生成
        deadline_warnings = []
        if validated.get("due_date"):
            priority_info = self._validate_deadline_priority(
                validated["due_date"],
                validated.get("priority", Task.PRIORITY_MEDIUM)
            )
            validated["priority"] = priority_info["priority"]
            deadline_warnings = priority_info["warnings"]
        
        # 整合性チェックと警告の統合
        validated["warnings"] = (
            deadline_warnings +
            self._check_consistency(validated)
        )
        
        return validated
    
    def _validate_basic_fields(
        self,
        rule_based: Dict[str, Any],
        ai_result: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        基本フィールドの検証
        
        検証ステップ:
        1. タイトル（必須）の検証
        2. 期限のフォーマット検証
        3. 優先度の値域検証
        4. カテゴリの値域検証
        """
        result = {}
        
        # タイトルのバリデーション（必須項目）
        if rule_based.get("title"):
            result["title"] = rule_based["title"]
        else:
            self.logger.warning("タイトルが設定されていません")
            result["title"] = "無題のタスク"
        
        # 期限のバリデーション
        due_date_value = None
        if due_date := rule_based.get("due_date"):
          try:
              datetime.strptime(due_date, "%Y-%m-%d")
              due_date_value = due_date
          except ValueError:
              self.logger.warning(f"無効な期限フォーマット: {due_date}")

        result["due_date"] = due_date_value
        
        # 優先度のバリデーション（Task.pyの定義を利用）
        priority = (
            rule_based.get("priority") or
            (ai_result.get("priority") if ai_result else None) or
            Task.PRIORITY_MEDIUM
        )
        result["priority"] = priority if priority in [
            Task.PRIORITY_HIGH,
            Task.PRIORITY_MEDIUM,
            Task.PRIORITY_LOW
        ] else Task.PRIORITY_MEDIUM
        
        # カテゴリのバリデーション（Task.pyの定義を利用）
        category = (
            rule_based.get("category") or
            (ai_result.get("category") if ai_result else None)
        )
        result["category"] = (
            category if category in Task.VALID_CATEGORIES else None
        )
        
        return result
    
    def _select_high_confidence_results(
        self,
        validated: Dict[str, Any],
        rule_based: Dict[str, Any],
        ai_result: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        信頼度に基づく結果の選択
        
        選択ロジック:
        1. タイトルは常にルールベースを優先
        2. 期限はルールベースを優先（_validate_basic_fieldsで検証済み）、なければAIの結果を使用
        3. カテゴリと優先度は信頼度の高い方を採用
        """
        # タイトルは常にルールベースを優先
        validated["title"] = rule_based.get("title", validated["title"])
        
        # カテゴリと優先度は信頼度の高い方を採用
        rule_confidence = rule_based.get("confidence", {})
        ai_confidence = ai_result.get("confidence", 0) if ai_result else 0
        
        for field in ["category", "priority"]:
            rule_value = rule_based.get(field)
            ai_value = ai_result.get(field) if ai_result else None
            
            rule_field_confidence = rule_confidence.get(field, 0)
            
            if rule_field_confidence > ai_confidence and rule_value:
                validated[field] = rule_value
            elif ai_value and ai_confidence > self.confidence_settings["THRESHOLD"]:
                validated[field] = ai_value
        
        return validated
    
    def _validate_deadline_priority(
        self,
        due_date: str,
        current_priority: str
    ) -> Dict[str, Any]:
        """
        期限に基づく優先度の検証と調整
        
        検証ロジック:
        1. 期限までの日数を計算
        2. Task.pyのurgency_levelsに基づいて優先度を判定
        3. 現在の優先度と推奨優先度を比較
        4. 必要に応じて警告を生成
        """
        try:
            deadline = datetime.strptime(due_date, "%Y-%m-%d").date()
            days_until = (deadline - datetime.now().date()).days

            # 期限切れの場合は即座に警告を生成
            if days_until < 0:
              return {
                  "priority": Task.PRIORITY_HIGH,
                  "warnings": [
                      f"⚠️ 期限切れ（{abs(days_until)}日経過）のため、"
                      f"優先度を「{current_priority}」から「{Task.PRIORITY_HIGH}」に変更しました"
                  ]
              }
            
            # Task.pyのurgency_levelsを利用
            for level, info in self.urgency_levels.items():
              if days_until <= info["days"]:
                  suggested_priority = info["priority"]
                  if suggested_priority != current_priority:
                      return {
                          "priority": suggested_priority,
                          "warnings": [
                              f"⚠️ {level}（残り{days_until}日）のため、"
                              f"優先度を「{current_priority}」から「{suggested_priority}」に調整しました"
                          ]
                      }
                  break
            
            return {
                "priority": current_priority,
                "warnings": []
            }
            
        except ValueError:
            return {
                "priority": current_priority,
                "warnings": ["⚠️ 期限の形式が正しくありません"]
            }
    
    def _check_consistency(self, data: Dict[str, Any]) -> List[str]:
        """
        データの整合性チェック
        
        チェック項目:
        1. 必須フィールドの存在確認
        2. 期限と優先度の整合性
        3. カテゴリの設定確認
        """
        warnings = []
        
        # 必須フィールドのチェック
        if not data.get("title"):
            warnings.append("⚠️ タイトルが設定されていません")
        
        # 期限と優先度の整合性
        if due_date := data.get("due_date"):
            try:
                deadline = datetime.strptime(due_date, "%Y-%m-%d").date()
                days_until = (deadline - datetime.now().date()).days

                # 期限切れの場合
                if days_until < 0:
                    warnings.append(
                        f"⚠️ このタスクは期限切れです（{abs(days_until)}日経過）"
                    )
                
                # 期限が近い場合
                elif days_until <= 3:  # 3日以内を期限が近いと定義
                    warnings.append(
                        f"⚠️ 期限が近づいています（残り{days_until}日）"
                    )
                
                # 優先度の整合性チェック
                for level, info in self.urgency_levels.items():
                    if days_until <= info["days"]:
                        if data.get("priority") != info["priority"]:
                            warnings.append(
                                f"⚠️ {level}（残り{days_until}日）ですが、"
                                f"優先度が「{info['priority']}」になっていません"
                            )
                        break
                        
            except ValueError:
                warnings.append("⚠️ 期限の形式が正しくありません")
        else:
            warnings.append("ℹ️ 期限が設定されていません")
        
        # カテゴリのチェック
        if not data.get("category"):
            warnings.append("ℹ️ カテゴリが設定されていません")
        
        return warnings