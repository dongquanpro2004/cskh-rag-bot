# Dùng bản Python 3.10 siêu nhẹ để Cloud không bị tràn RAM
FROM python:3.11-slim

# Tạo một thư mục làm việc bên trong thùng Container
WORKDIR /app

# Copy danh sách thư viện và ra lệnh cài đặt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code hiện tại vào trong thùng
COPY . .

# Mở cửa số 8000 để giao tiếp với bên ngoài
EXPOSE 8000

# Lệnh khởi động Server khi cái thùng này được cấp điện
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]