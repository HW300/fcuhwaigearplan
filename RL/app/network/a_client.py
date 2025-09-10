import json
import time
import uuid
import threading
import logging
from typing import Dict, Any, Tuple, Optional
import paho.mqtt.client as mqtt

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MQTT 配置 - 可通過環境變數覆蓋
import os
BROKER_HOST = os.getenv("MQTT_BROKER_IP", "140.134.60.218")
PORT = int(os.getenv("MQTT_PORT", "4883"))              # 標準 MQTT 端口
ID = os.getenv("MQTT_CLIENT_ID", "id1")
CLIENT_ID = f"A-{ID}"
KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "45"))

# Topic 定義
TOP_CTRL_START = f"v1/{ID}/ctrl/start"       # B→A
TOP_CTRL_END   = f"v1/{ID}/ctrl/end"         # A→B
TOP_CMD_POINT  = f"v1/{ID}/cmd/point"        # A→B
TOP_RESULT     = f"v1/{ID}/telemetry/result" # B→A
TOP_SETTING    = f"v1/{ID}/config/setting"   # retained
TOP_STATUS     = f"v1/{ID}/status"

class MQTTClient:
    def __init__(self):
        self.client = None
        self.is_connected = False
        # 等待表：req_id → (Event, result_payload)
        self._pending: Dict[str, Tuple[threading.Event, Any]] = {}
        self._pending_lock = threading.Lock()
        
    def setup_client(self):
        """設置 MQTT 客戶端"""
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID, clean_session=False, protocol=mqtt.MQTTv311)
        
        # 匿名連接，不需要用戶名密碼
        
        # 設置遺囑
        will_payload = json.dumps({
            "online": False, 
            "sender": "A", 
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
            logger.info("A 客戶端連接成功")
            
            # 訂閱主題
            subs = [
                (TOP_CTRL_START, 1), 
                (TOP_RESULT, 1), 
                (TOP_SETTING, 1)
            ]
            client.subscribe(subs)
            
            # 發送上線狀態（retained）
            status_payload = json.dumps({
                "online": True, 
                "sender": "A", 
                "ts": int(time.time()), 
                "state": "idle"
            })
            client.publish(TOP_STATUS, status_payload, qos=1, retain=True)
            logger.info("已發送上線狀態")
        else:
            logger.error(f"A 客戶端連接失敗，錯誤碼：{rc}")
            
    def on_disconnect(self, client, userdata, rc, properties=None):
        """斷線回調"""
        self.is_connected = False
        logger.warning(f"A 客戶端斷線，錯誤碼：{rc}")
        
    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        """接收消息回調"""
        try:
            data = json.loads(msg.payload.decode("utf-8"))
            logger.info(f"收到消息 - Topic: {msg.topic}, Data: {data}")
        except Exception as e:
            logger.error(f"解析消息錯誤: {e}, topic: {msg.topic}")
            return

        # 處理控制開始消息
        if msg.topic == TOP_CTRL_START and data.get("type") == "start":
            logger.info(f"[A] 收到 START 信號: {data}")
            # 在新線程中運行演算法，避免阻塞 MQTT 循環
            threading.Thread(target=self.run_algorithm, daemon=True).start()

        # 處理結果消息
        elif msg.topic == TOP_RESULT and data.get("type") == "result_feature_set":
            req_id = data.get("req_id")
            if not req_id:
                logger.warning("結果消息缺少 req_id")
                return
                
            with self._pending_lock:
                item = self._pending.get(req_id)
                
            if item:
                ev, _ = item
                # 更新結果並喚醒等待線程
                with self._pending_lock:
                    self._pending[req_id] = (ev, data)
                ev.set()
                logger.info(f"[A] 收到結果 req_id={req_id}")
            else:
                logger.warning(f"收到未知 req_id 的結果: {req_id}")

        # 處理設定消息
        elif msg.topic == TOP_SETTING:
            logger.info(f"[A] 收到設定更新: {data}")
            
    def send_point_and_wait(self, x: float, y: float, timeout: float = 5.0, retries: int = 2) -> Optional[Dict]:
        """
        發送 cmd/point，等待對應 req_id 的 telemetry/result。
        逾時重試（使用相同 req_id 以達到幂等）。
        """
        if not self.is_connected:
            logger.error("MQTT 未連接，無法發送點位")
            return None
            
        req_id = str(uuid.uuid4())
        payload = {
            "type": "move_point",
            "point": {"x": x, "y": y},
            "ts": int(time.time()),
            "sender": "A",
            "req_id": req_id
        }
        
        ev = threading.Event()
        with self._pending_lock:
            self._pending[req_id] = (ev, None)

        attempt = 0
        while attempt <= retries:
            attempt += 1
            
            # 發送點位命令
            self.client.publish(TOP_CMD_POINT, json.dumps(payload), qos=1)
            logger.info(f"[A] 發送點位 ({x},{y}), 嘗試 {attempt}, req_id={req_id}")
            
            # 等待結果
            if ev.wait(timeout):
                # 取回結果
                with self._pending_lock:
                    _, result = self._pending.pop(req_id, (None, None))
                logger.info(f"[A] 獲得結果 req_id={req_id}: {result}")
                return result
            else:
                logger.warning(f"[A] 等待結果逾時 (req_id={req_id}), 重試...")

        # 最終失敗，清理等待表
        with self._pending_lock:
            self._pending.pop(req_id, None)
        raise TimeoutError(f"req_id={req_id} 在 {retries+1} 次嘗試後仍未收到結果")

    def run_algorithm(self):
        """示範演算法：順序下兩個點，逐點等待結果，再發 end"""
        logger.info("[A] 開始執行演算法")
        
        # 更新狀態為運行中
        status_payload = json.dumps({
            "online": True, 
            "sender": "A", 
            "ts": int(time.time()), 
            "state": "running"
        })
        self.client.publish(TOP_STATUS, status_payload, qos=1, retain=True)
        
        # 定義要測試的點位
        points = [(10, 5), (12.3, -7.5), (0, 0), (-5.2, 8.1)]
        successful_points = []
        
        for i, (x, y) in enumerate(points):
            try:
                logger.info(f"[A] 處理第 {i+1}/{len(points)} 個點位")
                result = self.send_point_and_wait(x, y, timeout=8.0, retries=2)
                
                if result:
                    successful_points.append((x, y, result))
                    # 這裡可以加入資料分析邏輯
                    features = result.get("features", [])
                    values = result.get("values", [])
                    logger.info(f"[A] 點位 ({x},{y}) 完成，獲得 {len(features)} 個特徵")
                else:
                    logger.error(f"[A] 點位 ({x},{y}) 未獲得結果")
                    
            except TimeoutError as e:
                logger.error(f"[A] 點位 ({x},{y}) 處理失敗: {e}")
                # 根據需求決定是否繼續或中止
                continue
            
            # 點位間的間隔
            time.sleep(1)

        # 發送結束信號
        end_payload = json.dumps({
            "type": "end",
            "ts": int(time.time()),
            "sender": "A",
            "summary": {
                "total_points": len(points),
                "successful_points": len(successful_points),
                "failed_points": len(points) - len(successful_points)
            }
        })
        self.client.publish(TOP_CTRL_END, end_payload, qos=1)
        logger.info("[A] 已發送 END 信號")
        
        # 更新狀態為完成
        status_payload = json.dumps({
            "online": True, 
            "sender": "A", 
            "ts": int(time.time()), 
            "state": "completed"
        })
        self.client.publish(TOP_STATUS, status_payload, qos=1, retain=True)
        
        logger.info(f"[A] 演算法執行完成，成功處理 {len(successful_points)} 個點位")

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
                "sender": "A", 
                "ts": int(time.time()),
                "state": "disconnected"
            })
            self.client.publish(TOP_STATUS, status_payload, qos=1, retain=True)
            self.client.disconnect()

def main():
    """主函數"""
    mqtt_client = MQTTClient()
    
    try:
        # 設置客戶端
        mqtt_client.setup_client()
        
        # 連接
        if mqtt_client.connect():
            logger.info("A 客戶端啟動成功，等待 B 端發送 START 信號...")
            mqtt_client.start_loop()
        else:
            logger.error("無法啟動 A 客戶端")
            
    except KeyboardInterrupt:
        logger.info("收到中斷信號，正在關閉...")
    except Exception as e:
        logger.error(f"運行錯誤: {e}")
    finally:
        mqtt_client.disconnect()

if __name__ == "__main__":
    main()
