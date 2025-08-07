"""
Altary MCP Server implementation
"""

import asyncio
import json
import sys
from typing import Dict, List, Any, Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server

from .config import AltaryConfig
from .client import AltaryClient


# Global instances
config = AltaryConfig()
client = AltaryClient(config)

# Create the server instance
server = Server("altary-mcp")

# サーバー初期化時にログイン状態をチェック
async def check_login_status_on_startup():
    """サーバー起動時にログイン状態をチェックし、必要に応じてログイン画面を表示"""
    try:
        if not config.auth_token:
            print("🔐 Altaryにログインが必要です。認証を開始します...")
            # 自動認証を試行
            auto_token = await client.start_callback_auth()
            
            # 取得したトークンを検証
            is_valid = await client.validate_token(auto_token)
            if is_valid:
                config.auth_token = auto_token
                print("\n" + "="*50)
                print("🎉 ** Altary自動認証に成功しました！** 🎉") 
                print("✅ MCPサーバーが正常に認証されました")
                print("="*50 + "\n")
                
                # プロジェクトが未設定の場合はプロジェクト選択案内
                if not config.project_id:
                    print("📋 デフォルトプロジェクトを設定してください。")
                    print("Claude Codeで `altary_projects` を実行してプロジェクトを選択してください。")
                else:
                    print(f"🎉 設定完了！プロジェクト: {config.project_id}")
            else:
                print("❌ 自動認証に失敗しました。Claude Codeで `altary_auth` を実行してください。")
        else:
            print("✅ Altaryに認証済みです。")
            if config.project_id:
                print(f"📋 デフォルトプロジェクト: {config.project_id}")
            else:
                print("📋 プロジェクト未設定。`altary_projects` でプロジェクトを選択してください。")
                
    except Exception as e:
        print(f"⚠️ ログイン状態チェック中にエラー: {str(e)}")
        print("Claude Codeで `altary_auth` を実行してください。")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    利用可能なツール一覧を返す
    """
    return [
        types.Tool(
            name="altary_projects",
            description="ユーザーのプロジェクト一覧を取得します",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="altary_errors",
            description="指定されたプロジェクトのエラー一覧を取得します",
            inputSchema={
                "type": "object", 
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "プロジェクトID（省略時はデフォルトプロジェクト使用）"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="altary_complete",
            description="エラーを完了状態にします（AI類似性検出で関連エラーも自動完了）",
            inputSchema={
                "type": "object",
                "properties": {
                    "error_id": {
                        "type": "string", 
                        "description": "完了するエラーのID"
                    }
                },
                "required": ["error_id"]
            }
        ),
        types.Tool(
            name="altary_auth",
            description="Altary認証の初期設定を行います",
            inputSchema={
                "type": "object",
                "properties": {
                    "token": {
                        "type": "string",
                        "description": "認証トークン（省略時はブラウザで認証ページを開く）"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="altary_set_project", 
            description="デフォルトプロジェクトを設定します",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "デフォルトに設定するプロジェクトID"
                    }
                },
                "required": ["project_id"]
            }
        ),
        types.Tool(
            name="altary_config",
            description="現在の設定を表示します",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="altary_clear",
            description="設定をクリアします", 
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[types.TextContent]:
    """
    ツール実行のメインハンドラー
    """
    try:
        if name == "altary_projects":
            return await handle_get_user_projects()
        
        elif name == "altary_errors":
            project_id = arguments.get("project_id")
            return await handle_get_errors(project_id)
        
        elif name == "altary_complete":
            error_id = arguments["error_id"]
            return await handle_complete_error(error_id)
        
        elif name == "altary_auth":
            token = arguments.get("token")
            return await handle_setup_auth(token)
        
        elif name == "altary_set_project":
            project_id = arguments["project_id"]
            return await handle_set_default_project(project_id)
        
        elif name == "altary_config":
            return await handle_show_config()
        
        elif name == "altary_clear":
            return await handle_clear_config()
        
        else:
            return [types.TextContent(
                type="text",
                text=f"❌ 未知のツール: {name}"
            )]
    
    except Exception as e:
        return [types.TextContent(
            type="text", 
            text=f"❌ エラーが発生しました: {str(e)}"
        )]


async def handle_get_user_projects() -> list[types.TextContent]:
    """プロジェクト一覧取得の処理"""
    if not config.auth_token:
        return [types.TextContent(
            type="text",
            text="❌ 認証トークンが設定されていません。先に `setup_auth` を実行してください。"
        )]
    
    try:
        projects = await client.get_user_projects()
        
        if not projects:
            return [types.TextContent(
                type="text",
                text="📝 プロジェクトが見つかりませんでした。"
            )]
        
        # プロジェクト一覧を整形
        project_list = "📋 **利用可能なプロジェクト一覧:**\n\n"
        for i, project in enumerate(projects, 1):
            project_name = project.get('name', '無名プロジェクト')
            project_id = project.get('report_rand', project.get('id', ''))
            is_default = project_id == config.project_id
            default_mark = " **(デフォルト)**" if is_default else ""
            
            project_list += f"{i}. **{project_name}**{default_mark}\n"
            project_list += f"   ID: `{project_id}`\n\n"
        
        return [types.TextContent(type="text", text=project_list)]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"❌ プロジェクト取得に失敗しました: {str(e)}"
        )]


async def handle_get_errors(project_id: Optional[str] = None) -> list[types.TextContent]:
    """エラー一覧取得の処理"""
    # 1. 認証チェックと自動認証実行
    if not config.auth_token:
        try:
            # 自動認証を試行
            auto_token = await client.start_callback_auth()
            
            # 取得したトークンを検証
            is_valid = await client.validate_token(auto_token)
            if is_valid:
                config.auth_token = auto_token
                # 認証成功後、プロジェクト設定チェックに進む
                pass
            else:
                return [types.TextContent(
                    type="text",
                    text="❌ 自動取得したトークンが無効です。`altary_auth` で再認証してください。"
                )]
                
        except Exception as e:
            # 自動認証失敗時は手動認証案内
            client.open_auth_page()
            return [types.TextContent(
                type="text",
                text=f"⚠️ **自動認証に失敗しました**\n\n"
                     f"エラー: {str(e)}\n\n"
                     f"🔄 **手動認証モードに切り替えました**\n"
                     f"1. 開いたブラウザでログインを完了してください\n"
                     f"2. 表示されたトークンをコピー\n"
                     f"3. `altary_auth(token=\"コピーしたトークン\")` を実行\n"
                     f"4. その後、再度 `altary_errors` を実行してください\n\n"
                     f"**ログイン URL:** https://altary.web-ts.dev/users/claude-auth"
            )]
    
    # 2. プロジェクト設定チェックと自動設定案内
    if not config.project_id:
        try:
            projects = await client.get_user_projects()
            if not projects:
                return [types.TextContent(
                    type="text",
                    text="❌ プロジェクトが見つかりませんでした。Altaryサービスでプロジェクトを作成してください。"
                )]
            
            # プロジェクト一覧を整形
            project_list = "📋 **デフォルトプロジェクトの設定が必要です**\n\n"
            project_list += "利用可能なプロジェクト:\n\n"
            
            for i, project in enumerate(projects, 1):
                # projectが辞書でない場合の対応
                if not isinstance(project, dict):
                    project_list += f"{i}. **データ形式エラー** (型: {type(project)})\n"
                    project_list += f"   値: {str(project)[:50]}...\n\n"
                    continue
                    
                project_name = project.get('name', '無名プロジェクト')
                project_id_val = project.get('report_rand', project.get('id', ''))
                project_list += f"{i}. **{project_name}**\n"
                project_list += f"   ID: `{project_id_val}`\n\n"
            
            project_list += "**設定方法:**\n"
            project_list += "以下のコマンドでデフォルトプロジェクトを設定してください:\n"
            project_list += "`altary_set_project(project_id=\"上記のID\")`\n\n"
            project_list += "設定完了後、再度 `altary_errors` を実行してください。"
            
            return [types.TextContent(type="text", text=project_list)]
            
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"❌ プロジェクト取得に失敗しました: {str(e)}\n\n"
                     "認証トークンが無効な可能性があります。`altary_auth` で再認証してください。"
            )]
    
    try:
        errors_data = await client.get_errors(project_id)
        
        if errors_data.get('status') != 'success':
            return [types.TextContent(
                type="text",
                text=f"❌ エラー取得に失敗しました: {errors_data.get('message', '不明なエラー')}"
            )]
        
        errors = errors_data.get('errors', [])
        if not errors:
            return [types.TextContent(
                type="text",
                text="✅ 現在エラーはありません。"
            )]
        
        # エラー一覧を短いメッセージに分割して表示（折りたたみ防止）
        result_messages = []
        
        # ヘッダーメッセージ
        header = f"🐛 **エラー一覧** (合計: {len(errors)}件)\n"
        result_messages.append(types.TextContent(type="text", text=header))
        
        # エラーを1つずつ分割表示（最大10件まで）
        for i, error in enumerate(errors[:10]):  # A-J最大10件
            choice_letter = chr(65 + i)  # A, B, C...
            
            message = error.get('message', '不明なエラー')[:150]
            file_path = error.get('file', '不明なファイル')
            line = error.get('line', '?')
            error_id = error.get('rand', error.get('id', ''))
            
            # AI分析結果があれば表示
            ai_summary = error.get('ai_summary', '')
            ai_suggestion = error.get('ai_suggestion', '')
            
            error_text = f"**{choice_letter}. {file_path}:{line}**\n"
            error_text += f"メッセージ: {message}\n"
            error_text += f"ID: `{error_id}`\n"
            
            if ai_summary:
                error_text += f"🤖 AI概要: {ai_summary}\n"
            if ai_suggestion:
                error_text += f"💡 AI修正提案: {ai_suggestion}\n"
            
            result_messages.append(types.TextContent(type="text", text=error_text))
        
        # 残りのエラー件数表示
        if len(errors) > 10:
            footer = f"... 他 {len(errors) - 10} 件のエラーがあります。\n\n**修正したいエラーをアルファベット（A〜J）で選択してください。**"
            result_messages.append(types.TextContent(type="text", text=footer))
        else:
            footer = "**修正したいエラーをアルファベットで選択してください。**"
            result_messages.append(types.TextContent(type="text", text=footer))
        
        return result_messages
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"❌ エラー取得に失敗しました: {str(e)}"
        )]


async def handle_complete_error(error_id: str) -> list[types.TextContent]:
    """エラー完了処理"""
    if not config.auth_token:
        return [types.TextContent(
            type="text",
            text="❌ 認証トークンが設定されていません。先に `setup_auth` を実行してください。"
        )]
    
    try:
        result = await client.complete_error(error_id)
        
        if result.get('status') != 'success':
            return [types.TextContent(
                type="text",
                text=f"❌ エラー完了処理に失敗しました: {result.get('message', '不明なエラー')}"
            )]
        
        target_error = result.get('target_error_rand', error_id)
        similar_count = result.get('similar_completed', 0)
        completed_errors = result.get('completed_errors', [])
        
        response = f"✅ **エラー完了処理が完了しました**\n\n"
        response += f"対象エラー: `{target_error}`\n"
        response += f"類似エラー自動完了: **{similar_count}件**\n\n"
        
        if completed_errors:
            response += "**完了したエラー一覧:**\n"
            for i, completed in enumerate(completed_errors, 1):
                similarity = completed.get('similarity', 0)
                error_msg = completed.get('message', '不明')[:50]
                response += f"{i}. 類似度{similarity:.2f}: {error_msg}...\n"
        
        return [types.TextContent(type="text", text=response)]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"❌ エラー完了処理に失敗しました: {str(e)}"
        )]


async def handle_setup_auth(token: Optional[str] = None) -> list[types.TextContent]:
    """認証設定の処理"""
    if token:
        # トークンが提供された場合、検証して保存
        try:
            is_valid = await client.validate_token(token)
            if is_valid:
                config.auth_token = token
                return [types.TextContent(
                    type="text",
                    text="✅ 認証トークンが正常に設定されました。\n\n次に `altary_errors` を実行してプロジェクト設定を完了してください。"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text="❌ 無効なトークンです。正しいトークンを確認してください。"
                )]
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"❌ トークン検証中にエラーが発生しました: {str(e)}"
            )]
    else:
        # 自動コールバック認証を実行
        try:
            auto_token = await client.start_callback_auth()
            
            # 取得したトークンを検証
            is_valid = await client.validate_token(auto_token)
            if is_valid:
                config.auth_token = auto_token
                return [types.TextContent(
                    type="text",
                    text="🎉 **自動認証が完了しました！**\n\n"
                         "✅ 認証トークンが正常に設定されました。\n"
                         "次に `altary_errors` を実行してプロジェクト設定を完了してください。"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text="❌ 自動取得したトークンが無効です。手動で再認証してください。"
                )]
                
        except Exception as e:
            # 自動認証が失敗した場合は従来方式にフォールバック
            client.open_auth_page()
            return [types.TextContent(
                type="text",
                text=f"⚠️ **自動認証に失敗しました**\n\n"
                     f"エラー: {str(e)}\n\n"
                     f"🔄 **手動認証モードに切り替えました**\n"
                     f"1. 開いたブラウザでログインを完了してください\n"
                     f"2. 表示されたトークンをコピー\n"
                     f"3. `altary_auth(token=\"コピーしたトークン\")` を実行\n\n"
                     f"**ログイン URL:** https://altary.web-ts.dev/users/claude-auth"
            )]


async def handle_set_default_project(project_id: str) -> list[types.TextContent]:
    """デフォルトプロジェクト設定の処理"""
    if not config.auth_token:
        return [types.TextContent(
            type="text",
            text="❌ 認証トークンが設定されていません。先に `setup_auth` を実行してください。"
        )]
    
    # プロジェクトIDの形式検証
    if not project_id.startswith("ALTR-"):
        return [types.TextContent(
            type="text",
            text="❌ 無効なプロジェクトID形式です。'ALTR-'で始まるIDを指定してください。"
        )]
    
    try:
        # プロジェクトの存在確認
        projects = await client.get_user_projects()
        project_exists = any(
            p.get('report_rand') == project_id or p.get('id') == project_id 
            for p in projects
        )
        
        if not project_exists:
            return [types.TextContent(
                type="text",
                text=f"❌ 指定されたプロジェクトが見つかりません: {project_id}\n\n"
                     "`get_user_projects` でプロジェクト一覧を確認してください。"
            )]
        
        config.project_id = project_id
        return [types.TextContent(
            type="text",
            text=f"✅ デフォルトプロジェクトを設定しました: `{project_id}`\n\n"
                 "🎉 設定完了！`altary_errors` でエラー一覧を取得できます。"
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"❌ プロジェクト設定に失敗しました: {str(e)}"
        )]


async def handle_show_config() -> list[types.TextContent]:
    """設定表示の処理"""
    config_info = "⚙️ **現在の設定**\n\n"
    
    if config.auth_token:
        masked_token = config.auth_token[:8] + "..." + config.auth_token[-4:] if len(config.auth_token) > 12 else "***"
        config_info += f"認証トークン: `{masked_token}`\n"
    else:
        config_info += "認証トークン: ❌ 未設定\n"
    
    if config.project_id:
        config_info += f"デフォルトプロジェクト: `{config.project_id}`\n"
    else:
        config_info += "デフォルトプロジェクト: ❌ 未設定\n"
    
    config_info += f"API ベースURL: `{config.api_base_url}`\n\n"
    
    if config.is_configured():
        config_info += "✅ **設定完了** - `altary_errors` でエラー一覧を取得できます"
    else:
        config_info += "⚠️ **設定不完全** - `altary_errors` を実行して設定を完了してください"
    
    return [types.TextContent(type="text", text=config_info)]


async def handle_clear_config() -> list[types.TextContent]:
    """設定クリアの処理"""
    config.clear_config()
    return [types.TextContent(
        type="text",
        text="🗑️ **設定をクリアしました**\n\n"
             "再度利用する場合は `altary_errors` から設定を開始してください。"
    )]


def main():
    """MCP Server のメインエントリーポイント"""
    async def cleanup():
        await client.close()
    
    try:
        # サーバーを実行
        async def run_server():
            # 起動時にログイン状態をチェック
            await check_login_status_on_startup()
            
            async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options()
                )
        
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\n🛑 サーバーを停止しています...")
    finally:
        # クリーンアップ
        try:
            asyncio.run(cleanup())
        except:
            pass


if __name__ == "__main__":
    main()