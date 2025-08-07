"""
Configuration management for Altary MCP Server
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


class AltaryConfig:
    """Manages Altary MCP Server configuration"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".altary"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(exist_ok=True)
        
        # Default configuration
        self.default_config = {
            "api_base_url": "https://altary.web-ts.dev",
            "auth": {
                "token": None,
                "project_id": None
            }
        }
        
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return {**self.default_config, **config}
            except (json.JSONDecodeError, IOError):
                return self.default_config.copy()
        else:
            return self.default_config.copy()
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise Exception(f"設定ファイルの保存に失敗しました: {e}")
    
    @property
    def api_base_url(self) -> str:
        """Get API base URL"""
        return self._config["api_base_url"]
    
    @property
    def auth_token(self) -> Optional[str]:
        """Get authentication token"""
        return self._config["auth"]["token"]
    
    @auth_token.setter
    def auth_token(self, token: str) -> None:
        """Set authentication token"""
        self._config["auth"]["token"] = token
        self.save_config()
    
    @property
    def project_id(self) -> Optional[str]:
        """Get default project ID"""
        return self._config["auth"]["project_id"]
    
    @project_id.setter
    def project_id(self, project_id: str) -> None:
        """Set default project ID"""
        self._config["auth"]["project_id"] = project_id
        self.save_config()
    
    def is_configured(self) -> bool:
        """Check if minimum configuration is available"""
        return bool(self.auth_token and self.project_id)
    
    def clear_config(self) -> None:
        """Clear all configuration"""
        self._config = self.default_config.copy()
        self.save_config()
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        if not self.auth_token:
            raise Exception("認証トークンが設定されていません")
        
        return {
            "X-Claude-Token": self.auth_token,
            "Content-Type": "application/json",
            "User-Agent": "Altary-MCP-Server/1.0.0"
        }