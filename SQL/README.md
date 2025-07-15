
# merge_inspection_data_csv_to_sql.py

將 CSV 格式的齒輪檢測資料匯入 PostgreSQL 資料庫中 `gear_inspection_data.merge_inspection_data` 資料表。

---

## 功能簡介

提供一個 Python 程式 `merge_inspection_data_csv_to_sql.py`，可將含有 JSON 欄位的檢測資料從 CSV 匯入 PostgreSQL 中指定的資料表。  
適用於齒輪靜/動態檢測整合資料之匯入。

---

## 1. 環境準備

1. 安裝 PostgreSQL
2. 建立一個資料庫與 schema，例如：
   ```sql
   CREATE SCHEMA IF NOT EXISTS gear_inspection_data;
   ```
3. 安裝必要 Python 套件：
   ```bash
   pip install psycopg2-binary pandas python-dotenv
   ```

---

## 2. 建立 `.env` 檔案

請在專案根目錄建立 `.env` 檔案，內容如下：

```env
PG_HOST=your_host
PG_PORT=your_port
PG_USER=your_username
PG_PASSWORD=your_password
PG_DB=your_databasename
```

---

## 3. 設定 CSV 檔案路徑

請在 `merge_inspection_data_csv_to_sql.py` 中設定你欲匯入的 CSV 路徑：

```python
csv_path = "merge_inspection_data_20250715.csv"
```

---

## 4. 執行匯入程式

於終端機執行：

```bash
python merge_inspection_data_csv_to_sql.py
```

若成功，將顯示：

```bash
✅ 成功匯入 merge_inspection_data 資料表！
```

---

## 資料表結構

執行時會自動建立以下資料表（若尚未存在）：

```sql
CREATE TABLE IF NOT EXISTS gear_inspection_data.merge_inspection_data (
    id SERIAL PRIMARY KEY,
    inspection_order_number TEXT,
    part_number TEXT,
    part_name TEXT,
    inspector TEXT,
    inspection_date TIMESTAMP,
    work_number TEXT,
    workstation_number TEXT,
    status NUMERIC,
    measurement_data JSONB,
    extra_params JSONB,
    vibration_features JSONB,
    sft_tol JSONB,
    encode TEXT,
    create_time TIMESTAMP
);
```

---

## ⚠️ 注意事項

- `measurement_data`、`extra_params`、`vibration_features`、`sft_tol` 為 JSON 欄位，CSV 中請確保為有效的 JSON 格式字串。
- 預設不會刪除舊資料，如需重建資料表，請取消程式中的下列註解：

```python
#cur.execute("DROP TABLE IF EXISTS gear_inspection_data.merge_inspection_data CASCADE;")
#conn.commit()
```

---

## 📂 範例 CSV 欄位格式
以下為完整欄位格式與（... 表示省略部分）

| id  | inspection_order_number | part_number         | part_name                                      | inspector | inspection_date     | work_number        | workstation_number | status | measurement_data                                        | extra_params                                     | vibration_features                                         | sft_tol                                              | encode | create_time         |
|-----|--------------------------|---------------------|------------------------------------------------|-----------|----------------------|---------------------|---------------------|--------|---------------------------------------------------------|--------------------------------------------------|-------------------------------------------------------------|-------------------------------------------------------|--------|----------------------|
| 1 | P250617001;P250617002   | 1TH00037;1TH00038   | 一般4級蝸線齒輪M2*20T;一般4級蝸線齒輪M2*20T | 22023     | 2025-06-18 16:06:08 | 5211-20250617001    | F001                | 未判定 | {"S25060000025": [3.9935], "S25060000026": [9.3785], ...} | {"module": "2", "gear_ratio": "1", ...}         | {"Time_rms_x": "0.03806585", "Time_rms_y": "0.0872722", ...} | {"CW_Fi": "9.8", "CW_fi": "5.59", ...}               | 4      | 2025-07-02 10:53:00 |




