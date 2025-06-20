# fcuhwaigearplan
Integration of inspection data and knowledge base with machine learning and generative AI for a smart gearbox inspection production line.

## 📂 靜動態檢驗資料庫說明（PostgreSQL）

本專案使用 PostgreSQL 作為後端資料庫，記錄靜態與動態檢驗資料。

### 🧱 資料庫架構

- **資料庫名稱**：`gear_inspection_data_ai_gear_plan`
- **主要 Schema**：`gear_inspection_data`
- **資料表**：
  - `static_inspection`：靜態檢查資料（齒輪外觀尺寸、幾何公差等）
  - `dynamic_inspection`：動態檢查資料（振動特徵、傳動誤差等）

---

### 🔍 表格結構摘要

#### `gear_inspection_data.static_inspection`

| 欄位名稱                  | 類型        | 說明                   |
|--------------------------|-------------|------------------------|
| id                       | integer     | 主鍵,自動遞增           |
| inspector                | text        | 檢查人員                |
| inspection_date          | timestamp   | 檢查日期                |
| inspection_order_number  | text        | 檢查單號                |
| work_number              | text        | 工單編號                |
| workstation_number       | text        | 作業站編號              |
| part_number              | text        | 品名                    |
| part_name                | text        | 品號                |
| status                   | text        | 狀態                |
| measurement_data         | text        | 靜態尺寸量測數據，包含內孔圓徑、齒厚、外徑、同心度、偏擺等(json格式)   |
| create_time              | timestamp   | 建立時間（預設為 now） |

#### `gear_inspection_data.dynamic_inspection`

| 欄位名稱                  | 類型        | 說明                          |
|--------------------------|-------------|-------------------------------|
| id                       | integer     | 主鍵，自動遞增                 |
| inspection_order_number  | text        | 檢查單號                      |
| part_number              | text        | 品名                          |
| part_name                | text        | 品號                          |
| extra_params             | text        | 齒輪相關參數，包含模數、齒數、壓力角、節圓直徑、螺旋角、齒輪比、中心距(json格式)  |
| vibration_features       | text        | 動態量測振動特徵，包含時/頻域特徵(json格式)  |
| sft_tol                  | text        | 動態量測傳動誤差數據，包含單齒誤差(Fi’)、齒輪跳動誤差 (fi’)、長波誤差(fl’)、短波誤差 (fk’)(json格式)  |
| encode                   | text        |流水號                         |
| create_time              | timestamp   | 建立時間（預設為 now）         |

---

### 🧾 建表 SQL

```sql
CREATE SCHEMA IF NOT EXISTS gear_inspection_data;

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
