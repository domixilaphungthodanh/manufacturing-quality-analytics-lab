import os
from pathlib import Path
from .db import DEFAULT_DB,connect
def learning_db():
    p=Path(os.environ.get('QUALITY_LAB_DB',DEFAULT_DB)).resolve()
    if not p.exists():raise FileNotFoundError('Chạy python src/prepare_data.py trước. Notebook không tự tạo hoặc thay dữ liệu.')
    return p
def read_sql(sql,params=()):
    import pandas as pd
    with connect(learning_db()) as c:return pd.read_sql_query(sql,c,params=params)
