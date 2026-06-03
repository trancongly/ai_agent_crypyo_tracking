import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier

print("--- ĐANG KHỞI TẠO DỮ LIỆU HUẤN LUYỆN GIẢ LẬP ---")

# Định dạng đặc trưng đầu vào: [close_diff, rsi_diff, min_rsi, max_rsi]
# Nhãn phân loại: 0 = Bullish Divergence, 1 = Bearish Divergence, 2 = Không phân kỳ
np.random.seed(42)
X_train = []
y_train = []

# Giả lập 100 mẫu Bullish Divergence (Giá giảm, RSI tăng)
for _ in range(100):
    X_train.append([np.random.uniform(-50, -5), np.random.uniform(5, 25), np.random.uniform(15, 30), np.random.uniform(35, 55)])
    y_train.append(0)

# Giả lập 100 mẫu Bearish Divergence (Giá tăng, RSI giảm)
for _ in range(100):
    X_train.append([np.random.uniform(5, 50), np.random.uniform(-25, -5), np.random.uniform(45, 65), np.random.uniform(70, 85)])
    y_train.append(1)

# Giả lập 200 mẫu Không phân kỳ (Giá và RSI đi cùng hướng)
for _ in range(100):
    X_train.append([np.random.uniform(5, 40), np.random.uniform(5, 20), np.random.uniform(30, 50), np.random.uniform(55, 75)])
    y_train.append(2)
    X_train.append([np.random.uniform(-40, -5), np.random.uniform(-20, -5), np.random.uniform(20, 40), np.random.uniform(45, 65)])
    y_train.append(2)

X_train = np.array(X_train)
y_train = np.array(y_train)

print("--- ĐANG HUẤN LUYỆN MÔ HÌNH RANDOM FOREST ---")
# Sử dụng mô hình Random Forest Classifier (Rất nhẹ và tối ưu cho CPU điện thoại)
model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
model.fit(X_train, y_train)

# Xuất mô hình thành tệp .pkl
joblib.dump(model, "divergence_model.pkl")
print(" THÀNH CÔNG: Đã tạo xong file 'divergence_model.pkl' trong thư mục hiện tại!")

