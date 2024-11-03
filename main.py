import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from notion_client import Client

# 環境変数の読み込み
load_dotenv()

# デバッグ用の関数
def debug_env_vars():
    print("環境変数の確認:")
    print(f"NOTION_TOKEN: {'設定されています' if os.getenv('NOTION_TOKEN') else '設定されていません'}")
    print(f"NOTION_DATABASE_ID: {os.getenv('NOTION_DATABASE_ID')}")
    print(f"SLACK_BOT_TOKEN: {'設定されています' if os.getenv('SLACK_BOT_TOKEN') else '設定されていません'}")
    print(f"SLACK_APP_TOKEN: {'設定されています' if os.getenv('SLACK_APP_TOKEN') else '設定されていません'}")

# メイン処理の前にデバッグ関数を呼び出す
debug_env_vars()
# Notionクライアントの初期化
notion = Client(auth=os.environ["NOTION_TOKEN"])
database_id = os.environ["NOTION_DATABASE_ID"]

# Slackアプリの初期化
app = App(token=os.environ["SLACK_BOT_TOKEN"])


def add_task(title, due_date=None, priority=None, category=None):
    """
    タスクを追加する関数
    """
    properties = {
        "タスク名": {"title": [{"text": {"content": title}}]},
        "ステータス": {"status": {"name": "未着手"}},
    }
    
    if due_date:
        properties["期限"] = {"date": {"start": due_date}}
    
    if priority:
        properties["優先度"] = {"select": {"name": priority}}
        
    if category:
        properties["分野"] = {"select": {"name": category}}
    
    try:
        notion.pages.create(
            parent={"database_id": database_id},
            properties=properties
        )
        return f"タスクを追加しました：{title}"
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

def list_tasks(filter_status=None, filter_category=None):
    """
    タスク一覧を取得する関数
    """
    print(f"list_tasks呼び出し - status: {filter_status}, category: {filter_category}")

    # デフォルトのフィルター（全件取得用）
    filter_params = {
        "or": [
            {
                "property": "タスク名",
                "title": {
                    "is_not_empty": True
                }
            }
        ]
    }
    
    # フィルター条件がある場合は上書き
    if filter_status and filter_category:
        filter_params = {
            "and": [
                {"property": "ステータス", "status": {"equals": filter_status}},
                {"property": "分野", "select": {"equals": filter_category}}
            ]
        }
    elif filter_status:
        filter_params = {
            "property": "ステータス",
            "status": {"equals": filter_status}
        }
    elif filter_category:
        filter_params = {
            "property": "分野",
            "select": {"equals": filter_category}
        }

    print(f"Notionクエリパラメータ: {filter_params}")

    try:
        print("Notionクエリ実行前")
        response = notion.databases.query(
            database_id=database_id,
            filter=filter_params,
            sorts=[
                {"property": "期限", "direction": "ascending"},
                {"property": "優先度", "direction": "descending"}
            ]
        )
        print(f"Notionレスポンス: {response}")
        print(f"レスポンスの型: {type(response)}")
        print(f"レスポンスの内容: {response}")

        if not response["results"]:
            print("タスクが見つかりませんでした")
            return "タスクはありません"
            
        task_list = "📚 タスク一覧:\n"
        for item in response["results"]:
            try:
                props = item["properties"]
                title = props["タスク名"]["title"][0]["text"]["content"]
                status = props["ステータス"]["status"]["name"]
                priority = props["優先度"]["select"]["name"] if "優先度" in props else "未設定"
                due_date = props["期限"]["date"]["start"] if "期限" in props and props["期限"]["date"] else "期限なし"
                category = props["分野"]["select"]["name"] if "分野" in props else "未分類"
                
                task_list += f"・{title}\n"
                task_list += f"  状態: {status} | 優先度: {priority} | 期限: {due_date} | 分野: {category}\n"
            except Exception as e:
                print(f"タスク処理中のエラー: {str(e)}")
                print(f"問題のあるitem: {item}")
            
        return task_list
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

def update_task_status(task_title, new_status):
    """
    タスクのステータスを更新する関数
    """
    try:
        # タスクを検索
        response = notion.databases.query(
            database_id=database_id,
            filter={
                "property": "タスク名",
                "title": {"equals": task_title}
            }
        )
        
        if not response["results"]:
            return f"タスク「{task_title}」が見つかりません"
            
        # 最初に見つかったタスクを更新
        page_id = response["results"][0]["id"]
        notion.pages.update(
            page_id=page_id,
            properties={
                "ステータス": {"status": {"name": new_status}}
            }
        )
        return f"タスク「{task_title}」のステータスを「{new_status}」に更新しました"
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

@app.event("app_mention")
def handle_mention(event, say):
    """
    メンションされた時の処理
    """
    # イベントタイプをチェック
    if event.get("type") != "app_mention":
        return

    text = event["text"]
    print(f'受信したイベント: {event}')

    # ボットのメンションを除去
    text = ' '.join(word for word in text.split() if not word.startswith('<@'))
    
    # デバッグ: メンション除去後のテキスト
    print(f"処理するテキスト: {text}")
    
    words = text.split()
    if not words:
        say("使用可能なコマンド:\n- add タスク名 | 期限:YYYY-MM-DD | 優先度:高/中/低 | 分野:カテゴリー\n- list\n- list 状態[未着手/進行中/完了]\n- update タスク名 状態[未着手/進行中/完了]")
        return

    command = words[0].lower()
    print(f"検出したコマンド: {command}")

    # addコマンドの処理
    if command == "add":
        # "add "の後ろの文字列を取得
        task_info = text[text.lower().find("add") + 3:].strip()
        print(f"タスク情報: {task_info}")

        if not task_info:
            say("タスクの情報を入力してください。\n例：add レポート作成 | 期限:2024-03-20 | 優先度:高 | 分野:数学")
            return

        # タスク情報をパース
        components = task_info.split("|")
        print(f"パースされたコンポーネント: {components}")

        title = components[0].strip()
        due_date = None
        priority = None
        category = None

        # オプション情報の解析
        for comp in components[1:]:
            comp = comp.strip()
            print(f"処理中のコンポーネント: {comp}")

            if "期限:" in comp:
                due_date = comp.split("期限:")[1].strip()
                print(f"期限を設定: {due_date}")
            elif "優先度:" in comp:
                priority = comp.split("優先度:")[1].strip()
                print(f"優先度を設定: {priority}")
            elif "分野:" in comp:
                category = comp.split("分野:")[1].strip()
                print(f"分野を設定: {category}")

        print(f"最終的なタスク情報: タイトル={title}, 期限={due_date}, 優先度={priority}, 分野={category}")
        result = add_task(title, due_date, priority, category)
        say(result)
        
    # listコマンドの処理
    elif command == "list":
        if len(words) > 1:
            filter_value = words[1]
            print(f"リストフィルター: {filter_value}")
            if filter_value in ["未着手", "進行中", "完了"]:
                print("ステータスでフィルター")
                result = list_tasks(filter_status=filter_value)
            elif filter_value in ["数学", "統計学", "機械学習", "理論", "プログラミング"]:
                print("分野でフィルター")
                result = list_tasks(filter_category=filter_value)
            else:
                print("フィルターなし")
                result = list_tasks()
        else:
            print("フィルターなしのリスト表示")
            result = list_tasks()
        say(result)
        
    # updateコマンドの処理
    elif command == "update":
        words = text.split()[1:]  # "update"を除いた残りの部分
        print(f"更新用パラメータ: {words}")

        if len(words) >= 2:
            task_title = " ".join(words[:-1])  # 最後の単語以外をタスク名として扱う
            new_status = words[-1]  # 最後の単語をステータスとして扱う
            print(f"更新対象タスク: {task_title}")
            print(f"新しいステータス: {new_status}")

            if new_status in ["未着手", "進行中", "完了"]:
                result = update_task_status(task_title, new_status)
                say(result)
            else:
                say("ステータスは「未着手」「進行中」「完了」のいずれかを指定してください")
        else:
            say("使用方法: update タスク名 ステータス")
            
    else:
        print(f"不明なコマンド: {command}")
        say("使用可能なコマンド:\n- add タスク名 | 期限:YYYY-MM-DD | 優先度:高/中/低 | 分野:カテゴリー\n- list\n- list 状態[未着手/進行中/完了]\n- update タスク名 状態[未着手/進行中/完了]")


# messageイベントを明示的に無視
@app.event("message")
def handle_message(event, logger):
    # app_mentionイベントの場合は処理をスキップ
    if event.get("subtype") == "bot_message" or "bot_id" in event:
        return
    
# アプリの起動
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()

