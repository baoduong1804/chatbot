
import socket
import time
import sqlite3
from datetime import datetime

# --- Cấu hình ---
ESP32_IP = "192.168.100.219"  # <<< THAY ĐỔI thành IP của ESP32 của bạn
ESP32_PORT = 8888
DATABASE_FILE = "sent_data_log.db"
# --- Kết thúc cấu hình ---

# --- Hàm xử lý Database (Giữ nguyên từ ví dụ trước) ---
def initialize_database():
    """Khởi tạo database và bảng nếu chưa tồn tại"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                data_sent TEXT NOT NULL,
                status TEXT
            )
        ''')
        conn.commit()
        print(f"Database '{DATABASE_FILE}' đã được khởi tạo/kết nối.")
    except sqlite3.Error as e:
        print(f"Lỗi SQLite khi khởi tạo: {e}")
    finally:
        if conn:
            conn.close()

def log_data_to_db(data, status="Sent"):
    """Ghi dữ liệu đã gửi hoặc lỗi vào database"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO data_log (timestamp, data_sent, status) VALUES (?, ?, ?)",
                       (timestamp, data, status))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Lỗi SQLite khi ghi log: {e}")
    finally:
        if conn:
            conn.close()

# --- Khởi tạo Database ---
initialize_database()
print(f"Sẵn sàng gửi dữ liệu tới ESP32 tại {ESP32_IP}:{ESP32_PORT}")
print("Nhập 'quit' để thoát chương trình.")

# --- Vòng lặp chính quản lý kết nối và gửi dữ liệu ---
client_socket = None

while True: # Vòng lặp ngoài để thử kết nối lại nếu mất kết nối
    try:
        # --- Bước 1: Thiết lập kết nối (nếu chưa có) ---
        if client_socket is None:
            print("\nĐang thử kết nối tới ESP32...")
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5) # Giảm timeout để phản hồi nhanh hơn nếu ESP32 không có sẵn
            client_socket.connect((ESP32_IP, ESP32_PORT))
            print(f"Đã kết nối thành công! Nhập dữ liệu để gửi:")
            client_socket.settimeout(None) # Bỏ timeout sau khi kết nối thành công

        # --- Bước 2: Nhận input từ người dùng và gửi ---
        try:
            data_to_send = input("> ") # Nhận input từ terminal

            if data_to_send.lower().strip() == 'quit':
                print("Đang thoát...")
                break # Thoát khỏi vòng lặp ngoài cùng

            if not data_to_send: # Bỏ qua nếu người dùng chỉ nhấn Enter
                continue

            # Gửi dữ liệu tới ESP32
            # print(f"[{datetime.now().strftime('%H:%M:%S')}] Gửi: {data_to_send}") # Bỏ comment nếu muốn xem log gửi
            client_socket.sendall(data_to_send.encode('utf-8') + b'\n')

            # Ghi dữ liệu vào Database
            log_data_to_db(data_to_send, status="Sent OK")

            # (Tùy chọn) Nhận phản hồi - bỏ comment nếu ESP32 có gửi lại
            # client_socket.settimeout(1) # Đặt timeout ngắn để chờ phản hồi
            # try:
            #     response = client_socket.recv(1024).decode('utf-8').strip()
            #     if response:
            #         print(f"ESP32 phản hồi: {response}")
            # except socket.timeout:
            #     pass # Không có phản hồi, tiếp tục
            # finally:
            #      client_socket.settimeout(None) # Bỏ timeout

        except socket.error as send_err:
            print(f"\nLỗi khi gửi/nhận dữ liệu: {send_err}")
            print("Kết nối có thể đã bị mất. Đang thử kết nối lại...")
            log_data_to_db(f"Send/Recv Error: {send_err}", status="Error")
            if client_socket:
                client_socket.close()
            client_socket = None # Đặt lại để vòng lặp ngoài thử kết nối lại
            time.sleep(2) # Chờ một chút trước khi thử lại
        except EOFError: # Xảy ra nếu input bị đóng (hiếm gặp trong tương tác thông thường)
             print("\nLỗi đọc input. Đang thoát...")
             break
        except Exception as inner_ex: # Bắt các lỗi khác trong lúc gửi/nhận
             print(f"\nLỗi không xác định trong vòng lặp gửi: {inner_ex}")
             log_data_to_db(f"Inner Loop Error: {inner_ex}", status="Error")
             # Có thể cân nhắc đóng socket và thử lại hoặc thoát tùy mức độ lỗi
             # client_socket.close()
             # client_socket = None
             # time.sleep(2)


    # --- Xử lý lỗi kết nối ban đầu hoặc mất kết nối ---
    except socket.timeout:
        print(f"Lỗi: Không thể kết nối tới {ESP32_IP}:{ESP32_PORT} (Timeout)")
        log_data_to_db(f"Connection attempt failed (Timeout)", status="Error")
        client_socket = None # Đảm bảo thử kết nối lại
        print("Sẽ thử kết nối lại sau 5 giây...")
        time.sleep(5)
    except socket.error as conn_err:
        print(f"Lỗi Socket khi kết nối: {conn_err}")
        log_data_to_db(f"Connection Socket Error: {conn_err}", status="Error")
        client_socket = None # Đảm bảo thử kết nối lại
        print("Sẽ thử kết nối lại sau 5 giây...")
        time.sleep(5)
    except KeyboardInterrupt:
        print("\nNgắt bởi người dùng. Đang thoát...")
        break # Thoát vòng lặp ngoài cùng
    except Exception as outer_ex:
        print(f"\nLỗi không xác định bên ngoài: {outer_ex}")
        log_data_to_db(f"Outer Loop Error: {outer_ex}", status="Error")
        break # Thoát nếu có lỗi nghiêm trọng không lường trước

# --- Dọn dẹp trước khi thoát ---
    finally:
        if client_socket:
            print("Đóng kết nối socket.")
            client_socket.close()
        print("Chương trình Python kết thúc.")