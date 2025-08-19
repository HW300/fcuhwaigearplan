# 齒輪2D分析專案

本專案是一個完整的齒輪分析系統，可以分析兩個齒輪的重疊情況、干涉程度，並模擬相應的FFT振動資料。

## 專案結構

```
gear2D_proj/
├── project/                          # 主專案資料夾
│   ├── main.ipynb                     # 主控制台 Jupyter Notebook
│   ├── main.py                        # 主程式 Python 腳本版本
│   ├── examples.py                    # 使用範例腳本
│   ├── gear_loader.py                 # 齒輪載入與環境設置模組
│   ├── gear_transformer.py            # 齒輪移動與變換模組
│   ├── gear_visualizer.py             # 3D可視化模組
│   ├── gear_interference_analyzer.py  # 干涉分析模組
│   ├── gear_vibration_simulator.py    # FFT振動模擬模組
│   └── __init__.py                     # 專案初始化檢查
├── Gear_1TH00037_v2.0.STL            # 大齒輪STL檔案
├── Pinion_1TH00038_v2.0.STL          # 小齒輪STL檔案
└── README.md                          # 專案說明文件
```

## 功能特色

### 1. 齒輪載入與設置 (`gear_loader.py`)
- STL檔案載入
- 承靠面檢測
- 環境檢查與設置

### 2. 齒輪變換與定位 (`gear_transformer.py`)
- 齒輪中心對準
- 旋轉變換
- 自動對齒功能
- X/Y軸位置調整

### 3. 3D可視化 (`gear_visualizer.py`)
- 齒輪3D顯示
- 干涉點可視化
- 互動式圖表

### 4. 干涉分析 (`gear_interference_analyzer.py`)
- 多層次干涉檢測（嚴重/中度/輕微/接觸/接近）
- 統計分析
- 體積面積計算
- 嚴重程度評分

### 5. FFT振動模擬 (`gear_vibration_simulator.py`)
- 基於干涉程度的振動信號模擬
- 齒輪嚙合頻率計算
- 故障特徵模擬
- FFT頻譜分析
- 多種可視化圖表

## 使用方法

### 方法 1: Jupyter Notebook (推薦)
開啟 `project/main.ipynb` 並執行所有儲存格，使用互動式介面。

### 方法 2: Python 腳本
使用 `main.py` 腳本進行命令列操作或程式化分析。

#### 2.1 互動模式
```bash
python main.py
# 或
python main.py --mode interactive
```

#### 2.2 單一分析模式
```bash
# 基本分析
python main.py --mode single --x 0 --y -31 --offset 10

# 包含振動分析
python main.py --mode single --x 5 --y -30 --vibration --rpm-pinion 1800

# 不顯示圖表（適合自動化）
python main.py --mode single --x 0 --y -31 --no-plots

# 保存圖表到檔案
python main.py --mode single --x 0 --y -31 --save-plots
```

#### 2.3 批次分析模式
```bash
# 基本批次分析
python main.py --mode batch

# 自訂範圍批次分析
python main.py --mode batch --batch-x-range -20 20 --batch-y-range -40 -20 --batch-step 5
```

#### 2.4 查看所有選項
```bash
python main.py --help
```

### 方法 3: 使用範例腳本
```bash
python examples.py
```

### 互動式控制（Jupyter版本）
使用控制面板調整以下參數：
- **X距離**: 控制小齒輪(Pinion)在X軸方向的位置
- **Y距離**: 控制大齒輪(Gear)在Y軸方向的位置
- **旋轉偏移**: 齒輪相對旋轉角度微調
- **分析取樣率**: 干涉分析的精細程度

### 3. 執行分析
1. 點擊「🔍 執行分析」進行齒輪定位和干涉分析
2. 點擊「📊 振動分析」進行FFT振動模擬
3. 點擊「🔄 重置」恢復預設參數

### 4. 批次分析
使用批次分析功能探索最佳齒輪位置：

```python
# 執行批次分析
results = batch_analysis(x_range=(-20, 20), y_range=(-40, -20), step=5)
plot_batch_results(results)
```

## 分析結果說明

### 干涉等級分類
- **嚴重干涉** (< 0.1mm): 紅色點，表示嚴重重疊
- **中度干涉** (< 0.3mm): 橙色點，表示中度重疊
- **輕微干涉** (< 0.5mm): 黃色點，表示輕微重疊
- **接觸區域** (< 1.0mm): 綠色點，表示接觸區域
- **接近接觸** (< 2.0mm): 藍色點，表示接近區域

### 振動分析輸出
- **時域信號**: 基於干涉程度的振動波形
- **FFT頻譜**: 頻率域分析
- **特徵頻率**: 齒輪旋轉頻率、嚙合頻率等
- **相位譜**: 相位資訊
- **功率譜密度**: 功率分佈

### 輸出檔案
- 振動資料會自動匯出為 `.npz` 格式
- 檔名格式: `vibration_x{X距離}_y{Y距離}.npz`

## 技術規格

### 依賴套件
- `trimesh`: STL檔案處理
- `plotly`: 互動式可視化
- `numpy`: 數值計算
- `scipy`: 科學計算
- `ipywidgets`: Jupyter互動元件

### 系統需求
- Python 3.7+
- Jupyter Notebook
- 建議記憶體: 4GB+

## 使用範例

### 程式化使用範例

#### Python腳本程式化使用
```python
from main import GearAnalysisEngine

# 建立分析引擎
engine = GearAnalysisEngine()
engine.initialize()

# 執行分析
result = engine.analyze_gear_position(x_distance=0, y_distance=-31)
print(f"嚴重程度分數: {result['severity_score']:.2f}")

# 振動分析
vibration_data = engine.simulate_vibration(rpm_pinion=1800, rpm_gear=1800)

# 批次分析
results = engine.batch_analysis(x_range=(-10, 10), y_range=(-35, -25), step=5)
```

#### Jupyter Notebook程式化使用
```python
# 執行批次分析
results = batch_analysis(x_range=(-20, 20), y_range=(-40, -20), step=5)
plot_batch_results(results)
```

## 注意事項

1. **STL檔案路徑**: 確保STL檔案位於正確路徑
2. **記憶體使用**: 高精度分析會消耗較多記憶體
3. **計算時間**: 批次分析可能需要較長時間
4. **取樣率設置**: 較低的取樣率會提高分析精度但增加計算時間

## 故障排除

### 常見問題
1. **模組匯入錯誤**: 檢查Python路徑設置
2. **STL載入失敗**: 確認檔案路徑和權限
3. **記憶體不足**: 增加取樣率或減少分析範圍
4. **可視化不顯示**: 檢查Plotly設置

### 效能優化
- 使用適當的取樣率（建議5-10）
- 批次分析時適當設置步長
- 定期清理記憶體

## 開發資訊

本專案由原始的 `test_v3.ipynb` 重構而成，將原本的單一檔案分解為模組化的結構，提供更好的維護性和擴展性。

### 版本資訊
- 版本: 2.0
- 最後更新: 2025年8月
- 作者: Rich

## 授權

本專案僅供學術研究使用。
