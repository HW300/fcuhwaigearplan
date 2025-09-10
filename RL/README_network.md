# RL 網路版本使用說明

## 概述

`test_RL_network.py` 是將 RL 優化演算法與 MQTT 網路通訊整合的版本，可以通過網路與 B-client 進行協作，實現分散式的振動優化控制。

## 功能特色

### 1. MQTT 網路通訊
- 自動連接到 MQTT Broker (預設: 140.134.60.218:4883)
- 支援多種 Topic 訂閱和發布
- 具備連線狀態監控和自動重連

### 2. 參數動態配置
通過 MQTT `TOP_SETTING` 主題接收以下參數：
- `start_x`, `start_y`: 起始位置
- `x_min`, `x_max`: X 軸範圍限制
- `y_min`, `y_max`: Y 軸範圍限制
- `sig_x_min`, `sig_y_min`: 最小步長設定

### 3. 遠端控制功能
- **啟動**: 接收 `TOP_CTRL_START` 消息啟動 RL 優化
- **停止**: 接收 `TOP_CTRL_STOP` 消息安全停止優化過程
- **狀態回報**: 即時回報運行狀態 (idle/running/completed/stopped/error)

### 4. 智慧振動分析
- 利用 `send_point_and_wait()` 與 B-client 協作
- 自動重試機制和超時處理
- 支援多軸振動特徵分析

## 主要類別和方法

### RLMQTTClient 類別

#### 核心方法
- `run_control(x, y)`: 新的控制函式，替代原始的 `run_analysis`
- `send_point_and_wait()`: 發送位置命令並等待 B-client 回應
- `run_rl_optimization()`: 執行完整的 RL 優化流程
- `run_optimization_with_stop_check()`: 支援中途停止的優化執行

#### MQTT 回調方法
- `on_connect()`: 連接成功處理
- `on_message()`: 消息接收和路由
- `update_settings()`: 動態更新參數設定

## 使用方法

### 1. 直接執行 A-client (需要手動啟動 B-client)
```bash
python test_RL_network.py
```

### 2. 使用測試腳本
```bash
# 基本測試（需要真實的 B-client）
python test_network_runner.py

# 提示模擬模式（會提醒啟動 simulated_b_client.py）
python test_network_runner.py --simulate
```

### 3. 使用真實 B-client 模擬器（推薦）
```bash
# 在一個終端中啟動 B-client 模擬器
python simulated_b_client.py

# 在另一個終端中啟動 A-client
python test_RL_network.py

# 在 B-client 終端中輸入 's' + Enter 開始優化
```

### 4. 使用整合測試腳本（最簡單）
```bash
# 自動啟動並管理兩個客戶端
python integrated_test_runner.py

# 然後輸入 'start' 或 's' 開始優化
```

## MQTT Topic 結構

| Topic | 方向 | 說明 | 格式 |
|-------|------|------|------|
| `v1/{ID}/ctrl/start` | B→A | 啟動 RL 優化 | `{"type": "start", "ts": timestamp, "sender": "B"}` |
| `v1/{ID}/ctrl/stop` | B→A | 停止 RL 優化 | `{"type": "stop", "ts": timestamp, "sender": "B"}` |
| `v1/{ID}/ctrl/end` | A→B | RL 完成通知 | `{"type": "end", "optimization_result": {...}}` |
| `v1/{ID}/cmd/point` | A→B | 位置移動命令 | `{"type": "move_point", "point": {"x": x, "y": y}, "req_id": "..."}` |
| `v1/{ID}/telemetry/result` | B→A | 振動測量結果 | `{"type": "result_feature_set", "features": [...], "values": [...], "req_id": "..."}` |
| `v1/{ID}/config/setting` | B→A | 參數配置 | `{"start_x": x, "start_y": y, "x_min": x1, ...}` |
| `v1/{ID}/status` | A→B | 狀態回報 | `{"online": true, "state": "idle/running/completed", "ts": timestamp}` |

## 環境變數配置

可通過環境變數自定義 MQTT 連接參數：

```bash
export MQTT_BROKER_IP="your.broker.ip"
export MQTT_PORT="1883"
export MQTT_CLIENT_ID="custom_id"
export MQTT_KEEPALIVE="60"
```

## 錯誤處理

### 1. 網路異常
- 自動重試機制（預設 3 次）
- 連線狀態監控
- 優雅的斷線處理

### 2. 數據驗證
- 檢查振動特徵數據完整性
- 自動補充缺失的特徵值
- 安全門檻檢查

### 3. 優化過程異常
- 支援中途停止
- 異常狀態回報
- 完整的日誌記錄

## 依賴套件

```bash
pip install paho-mqtt numpy
```

## B-client 模擬器

### simulated_b_client.py 特色
- **真實數據**: 使用 `run_analysis_and_get_time_signal` 函數產生真實振動特徵
- **自動回應**: 接收 A-client 的位置命令並自動回傳測量結果
- **參數配置**: 自動發送初始設定給 A-client
- **互動控制**: 支援手動發送 START/STOP 信號

### 模擬器控制命令
- `s` + Enter: 發送 START 信號給 A-client
- `stop` + Enter: 發送 STOP 信號給 A-client  
- `q` + Enter: 退出模擬器

## 注意事項

1. **網路連接**: 確保能夠訪問 MQTT Broker
2. **B-client 協作**: 使用 `simulated_b_client.py` 或真實的 B-client
3. **真實數據**: B-client 模擬器會調用真實的齒輪分析函數
4. **參數調整**: 根據實際機械系統調整限位和步長參數
5. **安全考量**: 優化過程中會監控安全門檻，超過限制會停止
6. **計算時間**: 真實的振動分析可能需要較長時間，請耐心等待

## 測試與除錯

### 日誌等級調整
```python
logging.basicConfig(level=logging.DEBUG)  # 詳細日誌
logging.basicConfig(level=logging.INFO)   # 一般資訊
logging.basicConfig(level=logging.WARNING) # 僅警告和錯誤
```

### 常見問題排除

1. **連接失敗**: 檢查 MQTT Broker 地址和端口
2. **無法收到消息**: 確認 Topic 名稱和 QoS 設定
3. **優化不收斂**: 調整步長參數和收斂條件
4. **振動數據異常**: 檢查 B-client 的數據格式

## 檔案說明

### 核心檔案
- `test_RL_network.py`: 主要的 A-client RL 優化系統
- `simulated_b_client.py`: 使用真實分析函數的 B-client 模擬器

### 測試工具
- `test_network_runner.py`: A-client 測試腳本
- `integrated_test_runner.py`: 整合測試管理工具

### 文檔
- `README_network.md`: 完整使用說明

## 擴展功能

- 支援多軸優化
- 歷史數據保存
- 視覺化結果輸出
- 自適應參數調整
- 真實振動數據分析

## 版本更新

- v1.0: 基本 MQTT 整合
- v1.1: 增加停止控制功能
- v1.2: 改進錯誤處理和重試機制
- v1.3: 加入參數動態配置
- v1.4: 整合真實 B-client 模擬器
- v1.5: 加入整合測試管理工具
