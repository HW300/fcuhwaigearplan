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
json_cols = ["extra_params", "vibration_features", "sft_tol"]
for col in json_cols:
    df[col] = df[col].apply(lambda x: json.loads(x) if isinstance(x, str) else x)

# 建立資料庫連線
conn = psycopg2.connect(**PG_CONFIG)
cur = conn.cursor()

# 清空資料表 & 重設序號
#cur.execute("DROP TABLE IF EXISTS gear_inspection_data.dynamic_inspection CASCADE;")
#conn.commit()

# 建立資料表
create_table_sql = """
CREATE TABLE gear_inspection_data.dynamic_inspection (
    id SERIAL PRIMARY KEY,
    inspection_order_number TEXT,
    part_number TEXT,
    part_name TEXT,
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
        INSERT INTO gear_inspection_data.dynamic_inspection (
            inspection_order_number, part_number, part_name,
            extra_params, vibration_features, sft_tol,
            encode, create_time
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        row["inspection_order_number"],
        row["part_number"],
        row["part_name"],
        json.dumps(row["extra_params"]),
        json.dumps(row["vibration_features"]),
        json.dumps(row["sft_tol"]),
        row["encode"],
        row["create_time"]
    ))

conn.commit()
cur.close()
conn.close()

print("✅ 成功匯入 dynamic_inspection 資料表！")
