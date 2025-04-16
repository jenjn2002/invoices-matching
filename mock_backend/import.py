import pandas as pd
from sqlalchemy import create_engine

# Thông tin kết nối PostgreSQL
user = 'cr_db_admin'
password = 'cr_db_admin'
host = '209.124.85.88'
port = '5432'
database = 'invoice_db_cr'

# Tạo engine kết nối
engine = create_engine(f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}')

# Đọc file Excel
df = pd.read_excel('DanhSachSanPham.xlsx', sheet_name='Sheet1')  # hoặc thay bằng tên sheet thật

# Đổi tên cột nếu cần
# df.columns = ['id', 'product_name', 'price', 'quantity']

# Import vào bảng product
df.to_sql('cr_product', engine, index=False, if_exists='replace', schema='cr_product')  # hoặc 'append' nếu không muốn xóa bảng cũ