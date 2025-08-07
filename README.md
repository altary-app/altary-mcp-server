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

### 🚀 簡単セットアップ（推奨）

```bash
# まずはこれだけ！自動で設定案内が始まります
altary_errors
```

1. 初回実行時にブラウザが開くのでログイン
2. 表示されたトークンで認証: `altary_auth(token="トークン")`
3. 再度 `altary_errors` を実行してプロジェクト選択
4. プロジェクト設定: `altary_set_project(project_id="プロジェクトID")`
5. 再度 `altary_errors` でエラー一覧表示

### 詳細セットアップ（手動）

```bash
# 1. 認証設定
altary_auth                    # ブラウザで認証
altary_auth(token="your-token")  # トークン設定

# 2. プロジェクト設定
altary_projects               # プロジェクト一覧表示
altary_set_project(project_id="ALTR-xxx")  # プロジェクト設定

# 3. エラー管理
altary_errors                 # エラー一覧表示
altary_complete(error_id="error-id")  # エラー完了
```

## 利用可能なツール

| ツール名 | 説明 | パラメータ |
|---------|------|-----------|
| `altary_projects` | プロジェクト一覧取得 | なし |
| `altary_errors` | エラー一覧取得 | `project_id` (省略可) |
| `altary_complete` | エラー完了処理 | `error_id` (必須) |
| `altary_auth` | 認証設定 | `token` (省略可) |
| `altary_set_project` | デフォルトプロジェクト設定 | `project_id` (必須) |
| `altary_config` | 現在の設定表示 | なし |
| `altary_clear` | 設定クリア | なし |

## 使用例

### 基本的なワークフロー

```python
# 🚀 シンプル！まずはこれだけ
await altary_errors()  # 自動で設定案内→エラー表示

# エラー修正後
await altary_complete(error_id="target-error-id")

# 設定確認したい場合
await altary_config()
```

### 従来のワークフロー

```python
# 1. 設定確認
await altary_config()

# 2. 認証（初回のみ）
await altary_auth()

# 3. プロジェクト設定（初回のみ）  
await altary_projects()
await altary_set_project(project_id="ALTR-...")

# 4. エラー確認・修正
await altary_errors()
await altary_complete(error_id="target-error-id")
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
altary_clear
altary_auth
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