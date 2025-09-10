#!/usr/bin/env python3
"""
模擬 B-client 使用真實的 run_analysis_and_get_time_signal 函數
處理來自 A-client 的位置命令並回傳真實的振動特徵數據
"""

import json
import time
import threading
import logging
from typing import Dict, Any
import paho.mqtt.client as mqtt

# 導入真實的分析函數
from control_environment import run_analysis_and_get_time_signal as run_analysis

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MQTT 配置
import os
BROKER_HOST = os.getenv("MQTT_BROKER_IP", "140.134.60.218")
PORT = int(os.getenv("MQTT_PORT", "4883"))
ID = os.getenv("MQTT_CLIENT_ID", "id1")
CLIENT_ID = f"B-{ID}"
KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "45"))

# Topic 定義
TOP_CTRL_START = f"v1/{ID}/ctrl/start"       # B→A
TOP_CTRL_END   = f"v1/{ID}/ctrl/end"         # A→B
TOP_CTRL_STOP  = f"v1/{ID}/ctrl/stop"        # B→A
TOP_CMD_POINT  = f"v1/{ID}/cmd/point"        # A→B
TOP_RESULT     = f"v1/{ID}/telemetry/result" # B→A
TOP_SETTING    = f"v1/{ID}/config/setting"   # retained
TOP_STATUS     = f"v1/{ID}/status"

class SimulatedBClient:
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.processing_points = False
        
        # 模擬參數（可調整以匹配實際系統）
        self.offset_deg = 10.0
        self.sample_rate = 150
        
    def setup_client(self):
        """設置 MQTT 客戶端"""
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, 
            client_id=CLIENT_ID, 
            clean_session=False, 
            protocol=mqtt.MQTTv311
        )
        
        # 設置遺囑
        will_payload = json.dumps({
            "online": False, 
            "sender": "B", 
            "ts": int(time.time()),
            "state": "disconnected"
        })
        self.client.will_set(TOP_STATUS, will_payload, qos=1, retain=True)
        
        # 設置回調函數
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
    def on_connect(self, client: mqtt.Client, userdata, flags, rc, properties=None):
        """連接成功回調"""
        if rc == 0:
            self.is_connected = True
            logger.info("模擬 B-client 連接成功")
            
            # 訂閱主題
            subs = [
                (TOP_CMD_POINT, 1),  # 監聽 A-client 的點位命令
                (TOP_CTRL_END, 1),   # 監聽 A-client 的結束信號
                (TOP_STATUS, 1)      # 監聽狀態
            ]
            client.subscribe(subs)
            
            # 發送上線狀態
            status_payload = json.dumps({
                "online": True, 
                "sender": "B", 
                "ts": int(time.time()), 
                "state": "ready"
            })
            client.publish(TOP_STATUS, status_payload, qos=1, retain=True)
            
            # 發送初始設定
            self.send_initial_settings()
            logger.info("模擬 B-client 已就緒，等待點位命令...")
            
        else:
            logger.error(f"模擬 B-client 連接失敗，錯誤碼：{rc}")
            
    def on_disconnect(self, client, userdata, rc, properties=None):
        """斷線回調"""
        self.is_connected = False
        logger.warning(f"模擬 B-client 斷線，錯誤碼：{rc}")
        
    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        """接收消息回調"""
        try:
            data = json.loads(msg.payload.decode("utf-8"))
            logger.info(f"B-client 收到消息 - Topic: {msg.topic}")
        except Exception as e:
            logger.error(f"解析消息錯誤: {e}, topic: {msg.topic}")
            return

        # 處理點位移動命令
        if msg.topic == TOP_CMD_POINT and data.get("type") == "move_point":
            self.handle_point_command(data)
            
        # 處理結束信號
        elif msg.topic == TOP_CTRL_END:
            logger.info(f"[B] 收到 A-client 結束信號: {data.get('type', 'unknown')}")
            
    def send_initial_settings(self):
        """發送初始設定參數"""
        settings = {
            "start_x": 22.0,
            "start_y": -28.0,
            "x_min": 17.0,
            "x_max": 27.0,
            "y_min": -33.0,
            "y_max": -23.0,
            "sig_x_min": 0.0008,
            "sig_y_min": 0.0008,
            "timestamp": int(time.time()),
            "sender": "B"
        }
        
        self.client.publish(TOP_SETTING, json.dumps(settings), qos=1, retain=True)
        logger.info(f"[B] 發送初始設定: {settings}")
        
    def handle_point_command(self, data: Dict[str, Any]):
        """處理點位移動命令"""
        if self.processing_points:
            logger.warning("[B] 正在處理其他點位，忽略新命令")
            return
            
        self.processing_points = True
        
        try:
            point = data.get("point", {})
            req_id = data.get("req_id")
            x = point.get("x")
            y = point.get("y")
            
            if req_id is None or x is None or y is None:
                logger.error(f"[B] 點位命令格式錯誤: {data}")
                return
                
            logger.info(f"[B] 處理點位命令: ({x:.3f}, {y:.3f}), req_id={req_id}")
            
            # 在新線程中處理，避免阻塞 MQTT 循環
            threading.Thread(
                target=self.process_point_measurement,
                args=(x, y, req_id),
                daemon=True
            ).start()
            
        except Exception as e:
            logger.error(f"[B] 處理點位命令時發生錯誤: {e}")
            self.processing_points = False
            
    def process_point_measurement(self, x: float, y: float, req_id: str):
        """處理點位測量（在獨立線程中運行）"""
        try:
            start_time = time.time()
            logger.info(f"[B] 開始測量位置 ({x:.3f}, {y:.3f})")
            
            # 使用真實的 run_analysis_and_get_time_signal 函數
            features_dict = run_analysis(
                x_distance=x,
                y_distance=y, 
                offset_deg=self.offset_deg,
                sample_rate=self.sample_rate
            )
            
            # 將 dict 轉換為 features 和 values 列表
            features = list(features_dict.keys())
            values = list(features_dict.values())
            
            measurement_time = time.time() - start_time
            logger.info(f"[B] 位置 ({x:.3f}, {y:.3f}) 測量完成，耗時 {measurement_time:.2f}s")
            logger.debug(f"[B] 獲得 {len(features)} 個特徵")
            
            # 構建回傳消息
            result_payload = {
                "type": "result_feature_set",
                "req_id": req_id,
                "position": {"x": x, "y": y},
                "features": features,
                "values": values,
                "measurement_time": measurement_time,
                "parameters": {
                    "offset_deg": self.offset_deg,
                    "sample_rate": self.sample_rate
                },
                "ts": int(time.time()),
                "sender": "B"
            }
            
            # 發送結果
            self.client.publish(TOP_RESULT, json.dumps(result_payload), qos=1)
            logger.info(f"[B] 已發送測量結果，req_id={req_id}")
            
        except Exception as e:
            logger.error(f"[B] 測量位置 ({x:.3f}, {y:.3f}) 時發生錯誤: {e}")
            
            # 發送錯誤回應
            error_payload = {
                "type": "error",
                "req_id": req_id,
                "position": {"x": x, "y": y},
                "error_message": str(e),
                "ts": int(time.time()),
                "sender": "B"
            }
            self.client.publish(TOP_RESULT, json.dumps(error_payload), qos=1)
            
        finally:
            self.processing_points = False
            
    def send_start_signal(self):
        """發送啟動信號給 A-client"""
        start_payload = {
            "type": "start",
            "ts": int(time.time()),
            "sender": "B",
            "message": "開始 RL 優化"
        }
        
        self.client.publish(TOP_CTRL_START, json.dumps(start_payload), qos=1)
        logger.info("[B] 已發送 START 信號")
        
    def send_stop_signal(self):
        """發送停止信號給 A-client"""
        stop_payload = {
            "type": "stop",
            "ts": int(time.time()),
            "sender": "B",
            "message": "緊急停止 RL 優化"
        }
        
        self.client.publish(TOP_CTRL_STOP, json.dumps(stop_payload), qos=1)
        logger.info("[B] 已發送 STOP 信號")
        
    def connect(self):
        """連接到 MQTT Broker"""
        try:
            logger.info(f"正在連接到 MQTT Broker {BROKER_HOST}:{PORT}")
            self.client.connect(BROKER_HOST, PORT, keepalive=KEEPALIVE)
            return True
        except Exception as e:
            logger.error(f"連接 MQTT Broker 失敗: {e}")
            return False
            
    def start_loop(self):
        """開始 MQTT 循環"""
        self.client.loop_forever()
        
    def disconnect(self):
        """斷開連接"""
        if self.client and self.is_connected:
            # 發送離線狀態
            status_payload = json.dumps({
                "online": False, 
                "sender": "B", 
                "ts": int(time.time()),
                "state": "disconnected"
            })
            self.client.publish(TOP_STATUS, status_payload, qos=1, retain=True)
            self.client.disconnect()

def main():
    """主函數"""
    b_client = SimulatedBClient()
    
    try:
        # 設置客戶端
        b_client.setup_client()
        
        # 連接
        if b_client.connect():
            logger.info("模擬 B-client 啟動成功")
            
            # 在獨立線程中啟動 MQTT 循環
            mqtt_thread = threading.Thread(target=b_client.start_loop, daemon=True)
            mqtt_thread.start()
            
            # 等待連接穩定
            time.sleep(2)
            
            if b_client.is_connected:
                logger.info("✅ 模擬 B-client 就緒")
                logger.info("💡 輸入命令:")
                logger.info("   's' + Enter: 發送 START 信號")
                logger.info("   'stop' + Enter: 發送 STOP 信號") 
                logger.info("   'q' + Enter: 退出")
                
                # 互動式控制
                while True:
                    try:
                        cmd = input().strip().lower()
                        if cmd == 's':
                            b_client.send_start_signal()
                        elif cmd == 'stop':
                            b_client.send_stop_signal()
                        elif cmd == 'q':
                            break
                        else:
                            logger.info("未知命令，請輸入 's' (start), 'stop' 或 'q' (quit)")
                    except KeyboardInterrupt:
                        break
            else:
                logger.error("❌ MQTT 連接不穩定")
        else:
            logger.error("❌ 無法啟動模擬 B-client")
            
    except KeyboardInterrupt:
        logger.info("收到中斷信號，正在關閉...")
    except Exception as e:
        logger.error(f"運行錯誤: {e}")
    finally:
        b_client.disconnect()
        logger.info("👋 模擬 B-client 已關閉")

if __name__ == "__main__":
    main()
