"""
Altary API client for MCP Server
"""

import asyncio
import httpx
import webbrowser
import socket
from urllib.parse import urlparse, parse_qs
from aiohttp import web, web_request
from typing import Dict, List, Any, Optional
from .config import AltaryConfig


class AltaryClient:
    """HTTP client for Altary API"""
    
    def __init__(self, config: AltaryConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def get_user_projects(self) -> List[Dict[str, Any]]:
        """
        ユーザーのプロジェクト一覧を取得
        
        Returns:
            List[Dict]: プロジェクト一覧
        """
        url = f"{self.config.api_base_url}/users/getUserProjects"
        headers = self.config.get_auth_headers()
        
        try:
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            
            # レスポンス内容をデバッグ
            response_data = response.json()
            
            # レスポンスがリスト形式でない場合の対応
            if isinstance(response_data, dict):
                # {"projects": [...]} のような形式の場合
                if "projects" in response_data:
                    return response_data["projects"]
                # エラーレスポンスの場合
                elif "error" in response_data or "message" in response_data:
                    error_msg = response_data.get("message", response_data.get("error", "不明なエラー"))
                    raise Exception(f"APIエラー: {error_msg}")
                # 単一オブジェクトの場合はリストに包む
                else:
                    return [response_data]
            elif isinstance(response_data, list):
                return response_data
            else:
                raise Exception(f"予期しないレスポンス形式: {type(response_data)}")
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise Exception("認証に失敗しました。トークンを確認してください。")
            elif e.response.status_code == 403:
                raise Exception("アクセス権限がありません。")
            else:
                try:
                    error_detail = e.response.json()
                    error_msg = error_detail.get("message", f"HTTP {e.response.status_code}")
                except:
                    error_msg = f"HTTP {e.response.status_code}"
                raise Exception(f"プロジェクト取得に失敗しました: {error_msg}")
        except httpx.RequestError as e:
            raise Exception(f"ネットワークエラー: {e}")
        except Exception as e:
            if "認証に失敗" in str(e) or "アクセス権限" in str(e) or "プロジェクト取得に失敗" in str(e) or "ネットワークエラー" in str(e) or "APIエラー" in str(e):
                raise e
            else:
                raise Exception(f"データ処理エラー: {str(e)}")
    
    async def get_errors(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        エラー一覧を取得
        
        Args:
            project_id: プロジェクトID（省略時はデフォルトプロジェクト使用）
            
        Returns:
            Dict: エラー情報
        """
        if not project_id:
            project_id = self.config.project_id
            if not project_id:
                raise Exception("プロジェクトIDが設定されていません。")
        
        url = f"{self.config.api_base_url}/issues/getError/{project_id}"
        headers = self.config.get_auth_headers()
        
        try:
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception(f"プロジェクトまたはエラーが見つかりません: {project_id}")
            elif e.response.status_code == 401:
                raise Exception("認証に失敗しました。トークンを確認してください。")
            else:
                raise Exception(f"エラー取得に失敗しました: {e.response.status_code}")
        except httpx.RequestError as e:
            raise Exception(f"ネットワークエラー: {e}")
    
    async def complete_error(self, error_id: str) -> Dict[str, Any]:
        """
        エラーを完了状態にする（AI類似性検出付き）
        
        Args:
            error_id: エラーID
            
        Returns:
            Dict: 完了処理結果
        """
        url = f"{self.config.api_base_url}/issues/completeErrorWithSimilar/{error_id}"
        headers = self.config.get_auth_headers()
        
        try:
            response = await self.client.post(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception(f"指定されたエラーが見つかりません: {error_id}")
            elif e.response.status_code == 401:
                raise Exception("認証に失敗しました。トークンを確認してください。")
            else:
                raise Exception(f"エラー完了処理に失敗しました: {e.response.status_code}")
        except httpx.RequestError as e:
            raise Exception(f"ネットワークエラー: {e}")
    
    def open_auth_page(self) -> None:
        """
        認証ページをブラウザで開く（旧方式）
        """
        auth_url = f"{self.config.api_base_url}/users/claude-auth"
        try:
            webbrowser.open(auth_url)
            print(f"🌐 認証ページを開きました: {auth_url}")
            print("ログイン完了後、表示されたトークンをコピーしてください。")
        except Exception as e:
            print(f"ブラウザを開けませんでした: {e}")
            print(f"手動で以下のURLにアクセスしてください: {auth_url}")
    
    def find_free_port(self) -> int:
        """
        使用可能なポート番号を見つける
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    async def start_callback_auth(self) -> str:
        """
        コールバック方式で認証を実行
        
        Returns:
            str: 取得したトークン
        """
        # 使用可能なポートを見つける
        callback_port = self.find_free_port()
        callback_url = f"http://localhost:{callback_port}/callback"
        
        # 認証結果を格納する変数
        auth_result = {"token": None, "error": None}
        
        async def handle_callback(request: web_request.Request):
            """コールバック処理"""
            try:
                # URLパラメータからトークンを取得
                token = request.query.get('token')
                error = request.query.get('error')
                
                if error:
                    auth_result["error"] = error
                    return web.Response(
                        text="""
                        <html><body>
                        <h2>❌ 認証エラー</h2>
                        <p>認証に失敗しました。Claude Codeに戻って再試行してください。</p>
                        <script>window.close();</script>
                        </body></html>
                        """,
                        content_type='text/html'
                    )
                elif token:
                    auth_result["token"] = token
                    return web.Response(
                        text="""
                        <html>
                        <head>
                            <title>認証完了</title>
                            <style>
                                body { 
                                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                                    display: flex; align-items: center; justify-content: center;
                                    min-height: 100vh; margin: 0; text-align: center;
                                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                }
                                .container { 
                                    background: white; padding: 2rem; border-radius: 12px;
                                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
                                }
                                .countdown { color: #667eea; font-weight: 600; }
                            </style>
                        </head>
                        <body>
                        <div class="container">
                            <h2>✅ 認証完了！</h2>
                            <p>Claude Codeで認証が完了しました。</p>
                            <p class="countdown"><span id="countdown">3</span>秒後に自動的にこのタブを閉じます...</p>
                        </div>
                        <script>
                            let countdown = 3;
                            const countdownEl = document.getElementById('countdown');
                            let windowClosed = false;
                            
                            // すぐにタブを閉じる試行
                            function tryCloseWindow() {
                                if (windowClosed) return;
                                
                                try {
                                    // Chrome等のセキュリティ制限を回避する方法
                                    
                                    // 1. window.open()で開かれた場合
                                    if (window.opener) {
                                        window.opener.focus();
                                        window.close();
                                        windowClosed = true;
                                        return;
                                    }
                                    
                                    // 2. 通常のwindow.close()
                                    window.close();
                                    windowClosed = true;
                                    
                                    // 3. location.hrefでabout:blankに移動
                                    setTimeout(() => {
                                        if (!windowClosed) {
                                            window.location.href = 'about:blank';
                                            window.close();
                                        }
                                    }, 100);
                                    
                                } catch(e) {
                                    console.log('Close attempt failed:', e);
                                }
                            }
                            
                            const timer = setInterval(() => {
                                countdown--;
                                countdownEl.textContent = countdown;
                                
                                if (countdown <= 0) {
                                    clearInterval(timer);
                                    
                                    // タブクローズを試行
                                    tryCloseWindow();
                                    
                                    // 閉じられない場合の最終手段
                                    setTimeout(() => {
                                        if (!windowClosed) {
                                            document.body.innerHTML = \`
                                                <div class="container">
                                                    <h2>✅ 認証完了</h2>
                                                    <p><strong>このタブを手動で閉じてください</strong></p>
                                                    <p>Claude Codeに戻って作業を続けてください。</p>
                                                    <button onclick="tryCloseAgain()" style="
                                                        background: #667eea; color: white; border: none; 
                                                        padding: 10px 20px; border-radius: 5px; cursor: pointer;
                                                        font-size: 16px; margin-top: 10px;
                                                    ">再度タブを閉じる</button>
                                                </div>
                                            \`;
                                            
                                            window.tryCloseAgain = function() {
                                                tryCloseWindow();
                                            };
                                        }
                                    }, 1000);
                                }
                            }, 1000);
                            
                            // 様々なタイミングでクローズを試行
                            setTimeout(tryCloseWindow, 500);  // 0.5秒後
                            setTimeout(tryCloseWindow, 1500); // 1.5秒後
                            setTimeout(tryCloseWindow, 3000); // 3秒後
                            
                            // Visibility APIを使用してタブがアクティブでない時にクローズ
                            document.addEventListener('visibilitychange', function() {
                                if (document.visibilityState === 'hidden' && countdown <= 0) {
                                    tryCloseWindow();
                                }
                            });
                        </script>
                        </body></html>
                        """,
                        content_type='text/html'
                    )
                else:
                    auth_result["error"] = "トークンが見つかりません"
                    return web.Response(
                        text="""
                        <html><body>
                        <h2>❌ エラー</h2>
                        <p>認証データが不正です。Claude Codeに戻って再試行してください。</p>
                        <script>window.close();</script>
                        </body></html>
                        """,
                        content_type='text/html'
                    )
            except Exception as e:
                auth_result["error"] = f"コールバック処理エラー: {str(e)}"
                return web.Response(text="エラーが発生しました", status=500)
        
        # Webサーバーを設定
        app = web.Application()
        app.router.add_get('/callback', handle_callback)
        
        # サーバーを起動
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', callback_port)
        await site.start()
        
        try:
            # コールバック付きの認証URLを生成
            auth_url = f"{self.config.api_base_url}/users/claude-auth?callback={callback_url}"
            
            # ブラウザで認証ページを開く
            print(f"🌐 自動認証を開始します...")
            print(f"ブラウザで認証を完了してください。認証後は自動的にトークンが設定されます。")
            
            try:
                webbrowser.open(auth_url)
            except Exception as e:
                print(f"ブラウザを自動で開けませんでした: {e}")
                print(f"手動で以下のURLにアクセスしてください: {auth_url}")
            
            # 認証完了まで待機（最大5分）
            for _ in range(300):  # 5分間待機
                if auth_result["token"] or auth_result["error"]:
                    break
                await asyncio.sleep(1)
            
            if auth_result["error"]:
                raise Exception(f"認証エラー: {auth_result['error']}")
            elif auth_result["token"]:
                # 認証成功時、少し待ってからサーバーを停止（タブクローズを促進）
                await asyncio.sleep(3)  # 3秒待機（カウントダウンと同期）
                print("🔐 認証完了、ローカルサーバーを停止します...")
                return auth_result["token"]
            else:
                raise Exception("認証がタイムアウトしました（5分）。再度お試しください。")
                
        finally:
            # サーバーを停止
            await runner.cleanup()
    
    async def validate_token(self, token: str) -> bool:
        """
        トークンの有効性を検証
        
        Args:
            token: 検証するトークン
            
        Returns:
            bool: トークンが有効かどうか
        """
        # 一時的にトークンを設定して検証
        original_token = self.config.auth_token
        self.config._config["auth"]["token"] = token
        
        try:
            await self.get_user_projects()
            return True
        except Exception:
            return False
        finally:
            # 元のトークンを復元
            self.config._config["auth"]["token"] = original_token