# Altary MCP Server

Claude Code用のAltary エラー管理統合MCPサーバーです。

## 概要

このMCPサーバーは、Claude CodeとAltary エラー管理サービス（https://altary.web-ts.dev）を統合し、エラーの取得・分析・完了処理をClaude Code内で直接実行できるようにします。

## 主な機能

- **プロジェクト管理**: ユーザープロジェクトの一覧取得
- **エラー取得**: プロジェクト別エラー一覧の表示（ChatGPT分析付き）
- **エラー完了**: AI類似性検出による関連エラーの一括完了
- **認証管理**: ブラウザ認証とトークン管理
- **設定管理**: デフォルトプロジェクトと認証情報の永続化

## インストール

### Claude Code MCP統合（推奨）

```bash
claude mcp add altary -- uvx --from git+https://github.com/altary-app/altary-mcp-server altary-mcp-server
```

### 手動インストール

```bash
# 1. リポジトリクローン
git clone https://github.com/altary-app/altary-mcp-server.git
cd altary-mcp-server

# 2. 依存関係インストール
pip install -e .

# 3. Claude Code設定
# ~/.config/claude-desktop/config.json に追加:
{
  "mcpServers": {
    "altary": {
      "command": "altary-mcp-server"
    }
  }
}
```

## セットアップ手順

### 1. 初期認証

```bash
# ブラウザで認証ページを開く
mcp__altary__setup_auth

# トークン取得後、設定
mcp__altary__setup_auth(token="your-auth-token")
```

### 2. プロジェクト選択

```bash
# プロジェクト一覧を取得
mcp__altary__get_user_projects

# デフォルトプロジェクトを設定
mcp__altary__set_default_project(project_id="ALTR-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
```

### 3. エラー管理

```bash
# エラー一覧を表示（A、B、C選択形式）
mcp__altary__get_errors

# 特定プロジェクトのエラー取得
mcp__altary__get_errors(project_id="ALTR-specific-project-id")

# エラー完了（類似エラーも自動完了）
mcp__altary__complete_error(error_id="error-rand-id")
```

## 利用可能なツール

| ツール名 | 説明 | パラメータ |
|---------|------|-----------|
| `get_user_projects` | プロジェクト一覧取得 | なし |
| `get_errors` | エラー一覧取得 | `project_id` (省略可) |
| `complete_error` | エラー完了処理 | `error_id` (必須) |
| `setup_auth` | 認証設定 | `token` (省略可) |
| `set_default_project` | デフォルトプロジェクト設定 | `project_id` (必須) |
| `show_config` | 現在の設定表示 | なし |
| `clear_config` | 設定クリア | なし |

## 使用例

### 基本的なワークフロー

```python
# 1. 設定確認
await mcp__altary__show_config()

# 2. 認証（初回のみ）
await mcp__altary__setup_auth()

# 3. プロジェクト設定（初回のみ）  
projects = await mcp__altary__get_user_projects()
await mcp__altary__set_default_project(project_id="ALTR-...")

# 4. エラー確認・修正
errors = await mcp__altary__get_errors()
# コード修正...
await mcp__altary__complete_error(error_id="target-error-id")
```

### ChatGPT分析付きエラー表示

エラー一覧には自動的にChatGPT分析結果が含まれます：

```
A. UsersController.php:978
   メッセージ: compact()未定義変数エラー
   🤖 AI概要: compact()で未定義の変数$usernameが使用されています
   💡 AI修正提案: compact()の前に$usernameを定義するか、set()で直接設定してください
```

## 設定ファイル

設定は `~/.altary/config.json` に保存されます：

```json
{
  "api_base_url": "https://altary.web-ts.dev",
  "auth": {
    "token": "your-auth-token",
    "project_id": "ALTR-default-project-id"
  }
}
```

## トラブルシューティング

### 認証エラー

```bash
# トークンの再設定
mcp__altary__clear_config
mcp__altary__setup_auth
```

### ネットワークエラー

- インターネット接続を確認
- https://altary.web-ts.dev の稼働状況を確認

### MCPサーバーが認識されない

```bash
# Claude Codeを再起動
# 設定ファイル確認: ~/.config/claude-desktop/config.json
```

## 開発・貢献

### 開発環境セットアップ

```bash
git clone https://github.com/altary-app/altary-mcp-server.git
cd altary-mcp-server
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### テスト実行

```bash
# ユニットテスト
python -m pytest

# MCPサーバーテスト
python -m altary_mcp.server
```

## ライセンス

MIT License

## サポート

- 公式サイト: https://altary.web-ts.dev
- ドキュメント: https://altary.web-ts.dev/document
- GitHub Issues: https://github.com/altary-app/altary-mcp-server/issues