import os
import psycopg2
import pandas as pd
import json
from dotenv import load_dotenv

# 載入 .env 檔
load_dotenv()

# PostgreSQL 連線設定
PG_CONFIG = {
    "host": os.getenv("PG_HOST"),
    "port": os.getenv("PG_PORT"),
    "dbname": os.getenv("PG_DB"),
    "user": os.getenv("PG_USER"),
    "password": os.getenv("PG_PASSWORD")
}

# 讀取 CSV 檔
csv_path = "merge_inspection_data_20250715.csv"  # 請依實際路徑調整
df = pd.read_csv(csv_path)

# 若 JSON 欄位為字串格式，轉為 dict
json_cols = ["measurement_data", "extra_params", "vibration_features", "sft_tol"]
for col in json_cols:
    df[col] = df[col].apply(lambda x: json.loads(x) if isinstance(x, str) else x)

# 建立資料庫連線
conn = psycopg2.connect(**PG_CONFIG)
cur = conn.cursor()

# 清空資料表 & 重設序號
# cur.execute("DROP TABLE IF EXISTS gear_inspection_data.merge_inspection_data CASCADE;")
# conn.commit()

# 建立資料表（如果尚未存在）
create_table_sql = """
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
"""
cur.execute(create_table_sql)
conn.commit()

# 匯入資料
for _, row in df.iterrows():
    cur.execute("""
        INSERT INTO gear_inspection_data.merge_inspection_data (
            inspection_order_number, part_number, part_name,inspector,
            inspection_date, work_number, workstation_number, status,
            measurement_data,extra_params, vibration_features, sft_tol,
            encode, create_time
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        row["inspection_order_number"],
        row["part_number"],
        row["part_name"],
        row["inspector"],
        row["inspection_date"],
        row["work_number"],
        row["workstation_number"],
        row["status"],
        json.dumps(row["measurement_data"]),
        json.dumps(row["extra_params"]),
        json.dumps(row["vibration_features"]),
        json.dumps(row["sft_tol"]),
        row["encode"],
        row["create_time"]
    ))

conn.commit()
cur.close()
conn.close()

print("✅ 成功匯入 merge_inspection_data 資料表！")
