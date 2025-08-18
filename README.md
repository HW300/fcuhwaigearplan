# fcuhwaigearplan
Test
Integration of inspection data and knowledge base with machine learning and generative AI for a smart gearbox inspection production line.

## 📂 靜動態檢驗資料庫說明（PostgreSQL）

本專案使用 PostgreSQL 作為後端資料庫，記錄齒輪之靜態、動態與整併後的檢驗資料，並設有齒輪規格基本資料表供比對與關聯。
![image](https://github.com/user-attachments/assets/29465ff0-51cb-41bf-b3ba-bf2d08fc4ecc)
![image](https://github.com/user-attachments/assets/58f84966-8f1c-441a-a5bd-4b934ee73db1)

### 🧱 資料庫架構

- **資料庫名稱**：`gear_inspection_data`
- **主要 Schema**：`gear_inspection_data`
- **資料表**：
  - `static_inspection`：靜態檢查資料（齒輪外觀尺寸、幾何公差等）
  - `dynamic_inspection`：動態檢查資料（振動特徵、傳動誤差等）
  - `parts_list`：齒輪零件基本資料
  - `merge_inspection_data`：整併靜動態資料的彙總資料表

---

### 🔍 表格結構摘要

#### `gear_inspection_data.parts_list`

| 欄位名稱       | 類型      | 說明                     |
|----------------|-----------|--------------------------|
| id             | serial    | 主鍵，自動遞增           |
| part_number     | text      | 品號                     |
| part_name       | text      | 品名                     |
| specification   | text      | 齒輪相關規格(json格式) |
| create_time     | timestamp | 建立時間（預設為 now）   |

#### `gear_inspection_data.static_inspection`

| 欄位名稱                 | 類型      | 說明                                  |
|--------------------------|-----------|---------------------------------------|
| id                       | serial    | 主鍵，自動遞增                        |
| inspector                | text      | 檢驗人員                               |
| inspection_date          | timestamp | 檢驗日期                               |
| inspection_order_number  | text      | 檢驗單號                               |
| work_number              | text      | 工單編號                               |
| workstation_number       | text      | 作業站編號                             |
| part_number              | text      | 品號                                   |
| part_name                | text      | 品名                                   |
| status                   | text      | 狀態                                   |
| measurement_data         | text      | 靜態尺寸量測數據，json格式，包含鍵槽寬度、鍵槽中心距、鍵槽對稱度、內孔直徑、齒輪厚度、平行度 |
| create_time              | timestamp | 建立時間（預設為 now）                 |

#### `gear_inspection_data.dynamic_inspection`

| 欄位名稱           | 類型      | 說明                                           |
|--------------------|-----------|------------------------------------------------|
| id                 | serial    | 主鍵，自動遞增                                 |
| inspection_order_number | text      | 檢驗單號                                       |
| part_number         | text      | 品號                                           |
| part_name           | text      | 品名                                           |
| extra_params        | text      | 齒輪相關參數，json格式，包含模數、齒數、壓力角、節圓直徑、螺旋角、齒輪比、中心距   |
| vibration_features  | text      | 動態量測振動特徵，json格式，包含時/頻域特徵       |
| sft_tol             | text      | 動態量測傳動誤差數據，json格式，包含單齒誤差 ( Fi’)、齒輪跳動誤差 (fi’)、長波誤差(fl’)、短波誤差 (fk’)、背隙(B/L)   |
| encode              | text      | 資料流水號                                     |
| create_time         | timestamp | 建立時間（預設為 now）                         |

#### `gear_inspection_data.merge_inspection_data`

| 欄位名稱               | 類型      | 說明                                           |
|------------------------|-----------|------------------------------------------------|
| id                     | serial    | 主鍵，自動遞增                                 |
| inspection_order_number| text      | 檢驗單號                                       |
| part_number            | text      | 品號                                           |
| part_name              | text      | 品名                                           |
| inspector              | text      | 檢驗人員                                       |
| inspection_date        | timestamp | 檢驗日期                                       |
| work_number            | text      | 工單編號                                       |
| workstation_number     | text      | 作業站編號                                     |
| status                 | text      | 狀態                         |
| measurement_data       | text      | 靜態尺寸量測數據，json格式，包含鍵槽寬度、鍵槽中心距、鍵槽對稱度、內孔直徑、齒輪厚度、平行度     |
| extra_params           | text      | 齒輪相關參數，json格式，包含模數、齒數、壓力角、節圓直徑、螺旋角、齒輪比、中心距                |
| vibration_features     | text      | 動態量測振動特徵，json格式，包含時/頻域特徵       |
| sft_tol                | text      | 動態量測傳動誤差數據，json格式，包含單齒誤差 ( Fi’)、齒輪跳動誤差 (fi’)、長波誤差(fl’)、短波誤差 (fk’)、背隙(B/L)   |
| encode                 | text      | 資料流水號                                     |
| create_time            | timestamp | 建立時間（預設為 now）                         |

---

### 🧾 建表 SQL

```sql
CREATE SCHEMA IF NOT EXISTS gear_inspection_data;

CREATE TABLE gear_inspection_data.parts_list(
  "id" serial PRIMARY KEY,
  "part_number" text,
  "part_name" text,
  "specification" text,
  "create_time" TIMESTAMP DEFAULT (now())
);

CREATE TABLE gear_inspection_data.static_inspection (  
  "id" serial PRIMARY KEY,  
  "inspector" text,  
  "inspection_date" TIMESTAMP,  
  "inspection_order_number" text,  
  "work_number" text,  
  "workstation_number" text,  
  "part_number" text,  
  "part_name" text,  
  "status" text,  
  "measurement_data" text,  
  "create_time" TIMESTAMP DEFAULT (now())
);

CREATE TABLE gear_inspection_data.dynamic_inspection(  
  "id" serial PRIMARY KEY,  
  "inspection_order_number" text,  
  "part_number" text,  
  "part_name" text,  
  "extra_params" text,  
  "vibration_features" text,  
  "sft_tol" text,  
  "encode" text,
  "create_time" TIMESTAMP DEFAULT (now())
);

CREATE TABLE gear_inspection_data.merge_inspection_data(
  "id" serial PRIMARY KEY,
  "inspection_order_number" text,
  "part_number" text,
  "part_name" text,
  "inspector" text,
  "inspection_date" TIMESTAMP,
  "work_number" text,
  "workstation_number" text,
  "status" text,
  "measurement_data" text,
  "extra_params" text,
  "vibration_features" text,
  "sft_tol" text,
  "encode" text,
  "create_time" TIMESTAMP DEFAULT (now())
);
```
