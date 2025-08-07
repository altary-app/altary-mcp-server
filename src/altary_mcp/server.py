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


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    利用可能なツール一覧を返す
    """
    return [
        types.Tool(
            name="get_user_projects",
            description="ユーザーのプロジェクト一覧を取得します",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_errors",
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
            name="complete_error",
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
            name="setup_auth",
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
            name="set_default_project", 
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
            name="show_config",
            description="現在の設定を表示します",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="clear_config",
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
        if name == "get_user_projects":
            return await handle_get_user_projects()
        
        elif name == "get_errors":
            project_id = arguments.get("project_id")
            return await handle_get_errors(project_id)
        
        elif name == "complete_error":
            error_id = arguments["error_id"]
            return await handle_complete_error(error_id)
        
        elif name == "setup_auth":
            token = arguments.get("token")
            return await handle_setup_auth(token)
        
        elif name == "set_default_project":
            project_id = arguments["project_id"]
            return await handle_set_default_project(project_id)
        
        elif name == "show_config":
            return await handle_show_config()
        
        elif name == "clear_config":
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
    if not config.auth_token:
        return [types.TextContent(
            type="text",
            text="❌ 認証トークンが設定されていません。先に `setup_auth` を実行してください。"
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
        
        # エラー一覧を整形（アルファベット選択形式）
        error_list = f"🐛 **エラー一覧** (合計: {len(errors)}件)\n\n"
        
        for i, error in enumerate(errors[:26]):  # A-Z最大26件
            choice_letter = chr(65 + i)  # A, B, C...
            
            message = error.get('message', '不明なエラー')[:100]
            file_path = error.get('file', '不明なファイル')
            line = error.get('line', '?')
            error_id = error.get('rand', error.get('id', ''))
            
            # AI分析結果があれば表示
            ai_summary = error.get('ai_summary', '')
            ai_suggestion = error.get('ai_suggestion', '')
            
            error_list += f"**{choice_letter}. {file_path}:{line}**\n"
            error_list += f"   メッセージ: {message}\n"
            error_list += f"   ID: `{error_id}`\n"
            
            if ai_summary:
                error_list += f"   🤖 AI概要: {ai_summary}\n"
            if ai_suggestion:
                error_list += f"   💡 AI修正提案: {ai_suggestion}\n"
            
            error_list += "\n"
        
        if len(errors) > 26:
            error_list += f"... 他 {len(errors) - 26} 件のエラーがあります。\n"
        
        return [types.TextContent(type="text", text=error_list)]
        
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
                    text="✅ 認証トークンが正常に設定されました。\n\n次に `set_default_project` でデフォルトプロジェクトを設定してください。"
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
        # ブラウザで認証ページを開く
        client.open_auth_page()
        return [types.TextContent(
            type="text",
            text="🌐 **認証ページを開きました**\n\n"
                 "1. ブラウザでログインを完了してください\n"
                 "2. 表示されたトークンをコピー\n"
                 "3. `setup_auth` をトークン付きで再実行: \n"
                 "   例: `setup_auth` with token parameter\n\n"
                 "**ログイン URL:** https://altary.web-ts.dev/users/claude-auth"
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
                 "これで `get_errors` コマンドでエラー一覧を取得できます。"
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
        config_info += "✅ **設定完了** - 全ての機能を利用できます"
    else:
        config_info += "⚠️ **設定不完全** - `setup_auth` と `set_default_project` を実行してください"
    
    return [TextContent(type="text", text=config_info)]


async def handle_clear_config() -> list[types.TextContent]:
    """設定クリアの処理"""
    config.clear_config()
    return [TextContent(
        type="text",
        text="🗑️ **設定をクリアしました**\n\n"
             "再度利用する場合は `setup_auth` から設定を行ってください。"
    )]


def main():
    """MCP Server のメインエントリーポイント"""
    async def cleanup():
        await client.close()
    
    try:
        # サーバーを実行
        async def run_server():
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