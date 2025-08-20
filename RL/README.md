<<<<<<< HEAD
## fcuhwaigearplan
Integration of inspection data and knowledge base with machine learning and generative AI for a smart gearbox inspection production line.

本專案包含兩大部分：
- 後端資料庫結構與檢驗資料整併（原始遠端 README 內容）
- RL_project：齒輪2D分析與振動模擬模組（本地專案內容）

---

## 📂 靜動態檢驗資料庫說明（PostgreSQL）

本專案使用 PostgreSQL 作為後端資料庫，記錄齒輪之靜態、動態與整併後的檢驗資料，並設有齒輪規格基本資料表供比對與關聯。
![image](https://github.com/user-attachments/assets/29465ff0-51cb-41bf-b3ba-bf2d08fc4ecc)
![image](https://github.com/user-attachments/assets/58f84966-8f1c-441a-a5bd-4b934ee73db1)

### 🧱 資料庫架構

- 資料庫名稱：`gear_inspection_data`
- 主要 Schema：`gear_inspection_data`
- 資料表：
  - `static_inspection`：靜態檢查資料（齒輪外觀尺寸、幾何公差等）
  - `dynamic_inspection`：動態檢查資料（振動特徵、傳動誤差等）
  - `parts_list`：齒輪零件基本資料
  - `merge_inspection_data`：整併靜動態資料的彙總資料表

### 🔍 表格結構摘要

#### gear_inspection_data.parts_list
- id: serial，主鍵
- part_number: text
- part_name: text
- specification: text，齒輪相關規格（json）
- create_time: timestamp，預設 now()

#### gear_inspection_data.static_inspection
- id, inspector, inspection_date, inspection_order_number, work_number, workstation_number, part_number, part_name, status
- measurement_data: text（json，包含鍵槽寬度、鍵槽中心距、鍵槽對稱度、內孔直徑、齒輪厚度、平行度）
- create_time: timestamp

#### gear_inspection_data.dynamic_inspection
- id, inspection_order_number, part_number, part_name
- extra_params: text（json，包含模數、齒數、壓力角、節圓直徑、螺旋角、齒輪比、中心距）
- vibration_features: text（json，時/頻域特徵）
- sft_tol: text（json，Fi’/fi’/fl’/fk’/背隙）
- encode, create_time

#### gear_inspection_data.merge_inspection_data
- 彙整靜/動態檢驗與零件資訊，欄位同上整併

### 🧾 建表 SQL（摘要）

```sql
CREATE SCHEMA IF NOT EXISTS gear_inspection_data;
-- parts_list/static_inspection/dynamic_inspection/merge_inspection_data
-- 詳見資料庫建表腳本
```

---

## RL_project：齒輪2D分析與振動模擬模組

本模組提供齒輪重疊與干涉分析、以及基於嚙合與干涉的振動模擬與頻譜分析。

### 目錄結構（節錄）

```
RL_project/
├── analysis/                      # 分析模組（干涉、振動等）
├── app/                           # App/Notebook 入口
├── data_tools/ data_test_tools/   # 資料處理與測試工具
├── features/                      # 振動特徵擷取
├── geometry/                      # 幾何/齒輪載入與轉換
├── simulation/                    # 振動模擬
├── visualization/                 # 視覺化
├── control_environment.py         # 控制環境腳本
├── config.json / config_manager.py
└── README.md
```

### 功能摘要
- STL 載入與環境檢查（gear_loader.py）
- 齒輪對準與變換（gear_transformer.py）
- 3D 與干涉可視化（gear_visualizer.py）
- 干涉分級與統計（gear_interference_analyzer.py）
- 振動模擬與 FFT（gear_vibration_simulator.py）

### 使用方式
1) Jupyter Notebook：`app/main.ipynb`
2) Python 腳本：`app/main.py` 或 `control_environment.py`

示例（命令列）：
```bash
# 互動模式
python app/main.py --mode interactive

# 單一分析（含振動）
python app/main.py --mode single --x 5 --y -30 --vibration --rpm-pinion 1800

# 批次分析
python app/main.py --mode batch --batch-x-range -20 20 --batch-y-range -40 -20 --batch-step 5
```

### 相依套件（摘要）
- numpy, scipy, plotly, trimesh, ipywidgets 等

### 注意事項
- 高精度/大量點雲分析會耗用記憶體與時間
- STL 檔路徑需正確；建議於 `STL_data/` 放置

---

© 2025 fcuhwaigearplan / RL_project
2. 點擊「📊 振動分析」進行FFT振動模擬
