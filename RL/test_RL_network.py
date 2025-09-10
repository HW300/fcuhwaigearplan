import json
import time
import uuid
import threading
import logging
from typing import Dict, Any, Tuple, Optional
import paho.mqtt.client as mqtt
from Control.control_test import *

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
TOP_CTRL_STOP  = f"v1/{ID}/ctrl/stop"        # B→A (緊急停止)
TOP_CMD_POINT  = f"v1/{ID}/cmd/point"        # A→B
TOP_RESULT     = f"v1/{ID}/telemetry/result" # B→A
TOP_SETTING    = f"v1/{ID}/config/setting"   # retained
TOP_STATUS     = f"v1/{ID}/status"

class RLMQTTClient:
    def __init__(self):
        self.client = None
        self.is_connected = False
        # 等待表：req_id → (Event, result_payload)
        self._pending: Dict[str, Tuple[threading.Event, Any]] = {}
        self._pending_lock = threading.Lock()
        
        # RL 優化器實例
        self.optimizer = None
        self.is_running = False
        self.stop_requested = False
        
        # 從 MQTT 接收的參數設定
        self.settings = {
            "start_x": 16,
            "start_y": -26,
            "x_min": 18.5,
            "x_max": 29.5,
            "y_min": -36.5,
            "y_max": -25.5,
            "sig_x_min": 0.0005,
            "sig_y_min": 0.0005
        }
        
    def setup_client(self):
        """設置 MQTT 客戶端"""
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID, clean_session=False, protocol=mqtt.MQTTv311)
        
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
            logger.info("RL-A 客戶端連接成功")
            
            # 訂閱主題
            subs = [
                (TOP_CTRL_START, 1), 
                (TOP_CTRL_STOP, 1),
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
            logger.error(f"RL-A 客戶端連接失敗，錯誤碼：{rc}")
            
    def on_disconnect(self, client, userdata, rc, properties=None):
        """斷線回調"""
        self.is_connected = False
        logger.warning(f"RL-A 客戶端斷線，錯誤碼：{rc}")
        
    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        """接收消息回調"""
        try:
            data = json.loads(msg.payload.decode("utf-8"))
            logger.info(f"收到消息 - Topic: {msg.topic}, Data: {data}")
        except Exception as e:
            logger.error(f"解析消息錯誤: {e}, topic: {msg.topic}")
            return

        # 處理參數設定消息
        if msg.topic == TOP_SETTING:
            logger.info(f"[A] 收到設定更新: {data}")
            self.update_settings(data)

        # 處理控制開始消息
        elif msg.topic == TOP_CTRL_START and data.get("type") == "start":
            if self.is_running:
                logger.warning("[A] RL 優化已在運行中，忽略新的 START 信號")
                # 回復狀態消息告知正在運行
                status_payload = json.dumps({
                    "online": True, 
                    "sender": "A", 
                    "ts": int(time.time()), 
                    "state": "running",
                    "message": "RL optimization already in progress"
                })
                self.client.publish(TOP_STATUS, status_payload, qos=1, retain=True)
                return
                
            logger.info(f"[A] 收到 START 信號: {data}")
            # 重置停止標誌
            self.stop_requested = False
            # 在新線程中運行 RL 演算法，避免阻塞 MQTT 循環
            threading.Thread(target=self.run_rl_optimization, daemon=True).start()

        # 處理停止消息
        elif msg.topic == TOP_CTRL_STOP and data.get("type") == "stop":
            logger.info(f"[A] 收到 STOP 信號: {data}")
            self.stop_requested = True
            if self.is_running:
                logger.info("[A] 請求停止 RL 優化")
                # 更新狀態為停止中
                status_payload = json.dumps({
                    "online": True, 
                    "sender": "A", 
                    "ts": int(time.time()), 
                    "state": "stopping"
                })
                self.client.publish(TOP_STATUS, status_payload, qos=1, retain=True)

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

    def update_settings(self, data: Dict[str, Any]):
        """更新設定參數"""
        setting_keys = ["start_x", "start_y", "x_min", "x_max", "y_min", "y_max", "sig_x_min", "sig_y_min"]
        
        for key in setting_keys:
            if key in data:
                self.settings[key] = data[key]
                logger.info(f"更新設定: {key} = {data[key]}")

    def run_control(self, x: float, y: float) -> Dict[str, float]:
        """
        新的 run_control 函式：利用 send_point_and_wait 對接 B-client
        替代原本的 run_analysis 函式
        """
        if not self.is_connected:
            logger.error("MQTT 未連接，無法發送點位")
            raise ConnectionError("MQTT 未連接")
            
        try:
            result = self.send_point_and_wait(x, y, timeout=10.0, retries=3)
            if result and "features" in result and "values" in result:
                # 將 B-client 回傳的 features 和 values 轉換成符合 REQUIRED_KEYS 格式的 dict
                features = result["features"]
                values = result["values"]
                
                if len(features) != len(values):
                    logger.error(f"特徵名稱數量 ({len(features)}) 與數值數量 ({len(values)}) 不匹配")
                    raise ValueError("特徵數據格式錯誤")
                
                # 建立特徵字典
                feature_dict = dict(zip(features, values))
                logger.debug(f"位置 ({x:.3f}, {y:.3f}) 的特徵: {feature_dict}")
                
                # 檢查是否包含所有必要的特徵
                missing_keys = [key for key in REQUIRED_KEYS if key not in feature_dict]
                if missing_keys:
                    logger.warning(f"缺少必要特徵: {missing_keys}")
                    # 為缺少的特徵設置預設值（可根據實際情況調整）
                    for key in missing_keys:
                        feature_dict[key] = 0.0
                
                return feature_dict
            else:
                logger.error(f"位置 ({x}, {y}) 未收到有效結果")
                raise ValueError("未收到有效的振動特徵數據")
                
        except Exception as e:
            logger.error(f"位置 ({x}, {y}) 控制失敗: {e}")
            raise

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
            logger.info(f"[A] 發送點位 ({x:.3f},{y:.3f}), 嘗試 {attempt}, req_id={req_id}")
            
            # 等待結果
            if ev.wait(timeout):
                # 取回結果
                with self._pending_lock:
                    _, result = self._pending.pop(req_id, (None, None))
                logger.info(f"[A] 獲得結果 req_id={req_id}")
                return result
            else:
                logger.warning(f"[A] 等待結果逾時 (req_id={req_id}), 重試...")

        # 最終失敗，清理等待表
        with self._pending_lock:
            self._pending.pop(req_id, None)
        raise TimeoutError(f"req_id={req_id} 在 {retries+1} 次嘗試後仍未收到結果")

    def run_rl_optimization(self):
        """執行 RL 優化演算法"""
        if self.is_running:
            logger.warning("[A] RL 優化已在運行中")
            return
            
        self.is_running = True
        logger.info("[A] 開始執行 RL 優化演算法")
        
        try:
            # 更新狀態為運行中
            status_payload = json.dumps({
                "online": True, 
                "sender": "A", 
                "ts": int(time.time()), 
                "state": "running"
            })
            self.client.publish(TOP_STATUS, status_payload, qos=1, retain=True)
            
            # 從設定中讀取參數
            start_x = self.settings["start_x"]
            start_y = self.settings["start_y"]
            
            # 建立限位
            limits = Limits(
                x_min=self.settings["x_min"], 
                x_max=self.settings["x_max"],
                y_min=self.settings["y_min"], 
                y_max=self.settings["y_max"]
            )

            # 權重設定（使用預設值）
            weights = CVIWeights(
                w_trms=1.0,   # 時域 RMS（主要目標：整體振動大小）
                w_tcf=0.5,    # 時域 Crest Factor（尖峰比，抑制突發衝擊）
                w_frms=0.6,   # 頻譜 RMS（頻域能量）
                w_fsk=0.2,    # 頻譜偏度（分布偏斜）
                w_fkurt=0.3   # 頻譜峰度（異常尖銳能量峰）
            )

            # 安全門檻設定（使用預設值）
            safety = SafetyThresholds(
                time_rms_max=5.0,   # 時域 RMS 上限
                time_cf_max=10.0    # Crest Factor 上限
            )

            # 步長控制
            steps = StepConfig(
                sig_x=2,       # 初始 X 步長
                sig_y=2,       # 初始 Y 步長
                sig_x_min=self.settings["sig_x_min"], # X 最小步長
                sig_y_min=self.settings["sig_y_min"], # Y 最小步長
                sig_x_max=2.5,     # X 最大步長
                sig_y_max=2.5,     # Y 最大步長
                up_scale=1.2,    # 若找到更好點 → 步長放大 20%
                down_scale=0.8   # 若沒改善 → 步長縮小 20%
            )

            # RL 控制參數（使用預設值）
            cfg = RLConfig(
                alpha=0.3,           # 位置更新時的低通濾波係數
                K=1,                 # 每個候選點量測次數
                epsilon=1e-3,        # reward 提升門檻
                lambda_move=0.0,     # 動作代價
                max_iters=50,        # 最多迭代次數
                no_improve_patience=10# 連續沒改善的容忍次數
            )

            # 建立 RL 最佳化器
            self.optimizer = Top1of3WithRunAnalysis(
                run_fn=self.run_control,   # 使用新的 run_control 函式
                start_xy=(start_x, start_y), 
                limits=limits,         
                steps=steps,           
                cfg=cfg,               
                w=weights,             
                thr=safety             
            )

            # 優化前的振動數據
            logger.info(f"[A] 開始位置: ({start_x}, {start_y})")
            before_features = self.run_control(start_x, start_y)
            logger.info(f"[A] 優化前振動特徵: {before_features}")

            # 執行優化（加入停止檢查）
            best_x, best_y, best_r = self.run_optimization_with_stop_check()
            
            if self.stop_requested:
                logger.info(f"[A] 優化被中止於: ({best_x:.6f}, {best_y:.6f}), 當前 reward={best_r:.6f}")
                # 發送中止信號
                end_payload = json.dumps({
                    "type": "stopped",
                    "ts": int(time.time()),
                    "sender": "A",
                    "message": "RL optimization stopped by request"
                })
                self.client.publish(TOP_CTRL_END, end_payload, qos=1)
                
                # 更新狀態為已停止
                status_payload = json.dumps({
                    "online": True, 
                    "sender": "A", 
                    "ts": int(time.time()), 
                    "state": "stopped"
                })
                self.client.publish(TOP_STATUS, status_payload, qos=1, retain=True)
                return
            else:
                logger.info(f"[A] 優化完成: ({best_x:.6f}, {best_y:.6f}), 最佳 reward={best_r:.6f}")

            # 優化後的振動數據
            after_features = self.run_control(best_x, best_y)
            logger.info(f"[A] 優化後振動特徵: {after_features}")

            # 發送結束信號
            end_payload = json.dumps({
                "type": "end",
                "ts": int(time.time()),
                "sender": "A",
                "optimization_result": {
                    "start_position": {"x": start_x, "y": start_y},
                    "best_position": {"x": best_x, "y": best_y},
                    "best_reward": best_r,
                    "total_iterations": len(self.optimizer.history) if self.optimizer.history else 0,
                    "before_features": before_features,
                    "after_features": after_features
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

            # 嘗試視覺化
            try:
                from visualization.rl_visualization import plot_rl_history, plot_vibration_comparison
                plot_rl_history(self.optimizer.history, show=True, save_prefix="rl_network_iter")

                # 比較振動特徵（只顯示 X 軸）
                axes_selection = [1, 0, 0]  
                plot_vibration_comparison(
                    before_features, after_features,
                    axes_selection=axes_selection,
                    show=True, save_path="network_feature_comparison.png"
                )
            except Exception as e:
                logger.warning(f"[A] 視覺化失敗：{e}")
            
            logger.info(f"[A] RL 優化演算法執行完成")
            
        except Exception as e:
            logger.error(f"[A] RL 優化過程發生錯誤: {e}")
            # 發送錯誤狀態
            status_payload = json.dumps({
                "online": True, 
                "sender": "A", 
                "ts": int(time.time()), 
                "state": "error",
                "error_message": str(e)
            })
            self.client.publish(TOP_STATUS, status_payload, qos=1, retain=True)
            
        finally:
            self.is_running = False

    def run_optimization_with_stop_check(self):
        """執行優化，但會定期檢查停止請求"""
        # 覆寫 optimizer 的 run 方法以加入停止檢查
        original_run_method = self.optimizer.run
        
        def run_with_stop_check():
            for i in range(self.optimizer.cfg.max_iters):
                if self.stop_requested:
                    logger.info(f"[A] 在第 {i} 次迭代時收到停止請求")
                    break
                    
                # 執行一次迭代
                try:
                    self.optimizer.x, self.optimizer.y, reward, info = self.optimizer.iterate()
                    
                    # 更新歷史記錄
                    self.optimizer.history.append({
                        'iteration': i,
                        'position': (self.optimizer.x, self.optimizer.y),
                        'reward': reward,
                        'info': info
                    })
                    
                    # 檢查是否有改善
                    if reward > self.optimizer.best_reward + self.optimizer.cfg.epsilon:
                        self.optimizer.best_reward = reward
                        self.optimizer.no_improve_cnt = 0
                        logger.info(f"[A] 第 {i+1} 次迭代: 找到更好位置 ({self.optimizer.x:.3f}, {self.optimizer.y:.3f}), reward={reward:.6f}")
                    else:
                        self.optimizer.no_improve_cnt += 1
                        logger.info(f"[A] 第 {i+1} 次迭代: 無改善 ({self.optimizer.no_improve_cnt}/{self.optimizer.cfg.no_improve_patience})")
                    
                    # 檢查是否達到停止條件
                    if self.optimizer.no_improve_cnt >= self.optimizer.cfg.no_improve_patience:
                        logger.info(f"[A] 連續 {self.optimizer.no_improve_cnt} 次迭代無改善，停止優化")
                        break
                        
                except Exception as e:
                    logger.error(f"[A] 第 {i+1} 次迭代出錯: {e}")
                    break
                    
            return self.optimizer.x, self.optimizer.y, self.optimizer.best_reward
        
        return run_with_stop_check()

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
    rl_mqtt_client = RLMQTTClient()
    
    try:
        # 設置客戶端
        rl_mqtt_client.setup_client()
        
        # 連接
        if rl_mqtt_client.connect():
            logger.info("RL-A 客戶端啟動成功，等待設定參數和 START 信號...")
            rl_mqtt_client.start_loop()
        else:
            logger.error("無法啟動 RL-A 客戶端")
            
    except KeyboardInterrupt:
        logger.info("收到中斷信號，正在關閉...")
    except Exception as e:
        logger.error(f"運行錯誤: {e}")
    finally:
        rl_mqtt_client.disconnect()

if __name__ == "__main__":
    main()
