"""
Altary API client for MCP Server
"""

import httpx
import webbrowser
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
        認証ページをブラウザで開く
        """
        auth_url = f"{self.config.api_base_url}/users/claude-auth"
        try:
            webbrowser.open(auth_url)
            print(f"🌐 認証ページを開きました: {auth_url}")
            print("ログイン完了後、表示されたトークンをコピーしてください。")
        except Exception as e:
            print(f"ブラウザを開けませんでした: {e}")
            print(f"手動で以下のURLにアクセスしてください: {auth_url}")
    
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