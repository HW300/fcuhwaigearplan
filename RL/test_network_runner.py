#!/usr/bin/env python3
"""
測試 RL 網路版本的啟動腳本
用於驗證 MQTT 連接和基本功能
"""

import time
import json
import logging
from test_RL_network import RLMQTTClient

# 設置詳細日誌
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_mqtt_connection():
    """測試 MQTT 連接"""
    client = RLMQTTClient()
    
    try:
        logger.info("=== 開始測試 RL MQTT 客戶端 ===")
        
        # 設置和連接
        client.setup_client()
        
        if client.connect():
            logger.info("✅ MQTT 連接成功")
            
            # 啟動循環（非阻塞測試）
            import threading
            mqtt_thread = threading.Thread(target=client.start_loop, daemon=True)
            mqtt_thread.start()
            
            # 等待連接穩定
            time.sleep(2)
            
            if client.is_connected:
                logger.info("✅ MQTT 狀態穩定")
                
                # 測試設定更新
                test_settings = {
                    "start_x": 20.0,
                    "start_y": -30.0,
                    "x_min": 15.0,
                    "x_max": 25.0,
                    "y_min": -35.0,
                    "y_max": -25.0,
                    "sig_x_min": 0.001,
                    "sig_y_min": 0.001
                }
                
                logger.info("測試設定更新...")
                client.update_settings(test_settings)
                
                # 檢查設定是否正確更新
                for key, value in test_settings.items():
                    if client.settings.get(key) == value:
                        logger.info(f"✅ 設定 {key} = {value} 更新成功")
                    else:
                        logger.error(f"❌ 設定 {key} 更新失敗")
                
                logger.info("✅ 基本功能測試完成")
                logger.info("💡 客戶端已準備就緒，等待 B-client 的 START 信號...")
                
                # 持續運行等待真實的 MQTT 消息
                try:
                    while True:
                        time.sleep(1)
                        if not client.is_connected:
                            logger.error("❌ MQTT 連接丟失")
                            break
                except KeyboardInterrupt:
                    logger.info("👋 收到中斷信號，正在關閉...")
                    
            else:
                logger.error("❌ MQTT 連接不穩定")
                
        else:
            logger.error("❌ 無法連接到 MQTT Broker")
            
    except Exception as e:
        logger.error(f"❌ 測試過程中發生錯誤: {e}")
        
    finally:
        try:
            client.disconnect()
            logger.info("👋 已斷開 MQTT 連接")
        except:
            pass

def simulate_b_client_messages():
    """提示用戶使用真實的 B-client 模擬器"""
    logger.info("� 請使用真實的 B-client 模擬器:")
    logger.info("   在另一個終端中執行: python simulated_b_client.py")
    logger.info("   然後輸入 's' + Enter 來發送 START 信號")
    logger.info("💡 真實的 B-client 會使用 run_analysis_and_get_time_signal 函數")
    logger.info("   提供真實的振動特徵數據回傳")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--simulate":
        logger.info("🔄 模擬模式提示...")
        simulate_b_client_messages()
        logger.info("⏳ 等待 5 秒後啟動 A-client...")
        time.sleep(5)
    
    # 啟動主要的 RL MQTT 客戶端
    test_mqtt_connection()
