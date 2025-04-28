# combined_chatbot_sender.py

import socket
import time
import sqlite3
from datetime import datetime
import os
import atexit

# Thư viện cho Chatbot
from textblob import TextBlob
import google.generativeai as genai
from gtts import gTTS
import pygame # Pygame cần được cài đặt: pip install pygame
from underthesea import word_tokenize
from playsound import playsound # Import thư viện playsound

import webbrowser #Mở website
import re
import speech_recognition as sr

# --- Cấu hình ---
# Chatbot
GOOGLE_API_KEY = "AIzaSyCDZOzBDFSTRAsC-RrmQ8bO27azloOb02Y" 
# ESP32 Sender
ESP32_IP = "192.168.100.218"  # <<< THAY ĐỔI thành IP của ESP32 của bạn
ESP32_PORT = 8888
DATABASE_FILE = "sent_data_log.db"
# --- Kết thúc cấu hình ---

# --- Các hàm của Chatbot ---
speaking = True # Biến kiểm soát việc phát âm

# --- Cấu hình âm thanh ---
# Lấy thư mục chứa file Python hiện tại
script_directory = os.path.dirname(os.path.abspath(__file__))
# Giả sử thư mục SOUND nằm CÙNG CẤP với file script này
# (Nếu nó nằm trong thư mục con, ví dụ 'assets/SOUND', hãy thay đổi cho phù hợp)
SOUND_FOLDER = os.path.join(script_directory, "SOUND") # <<< Đảm bảo thư mục tên 'SOUND' tồn tại

# Tạo đường dẫn đầy đủ đến các file âm thanh
HAPPY_SOUND_PATH = os.path.join(SOUND_FOLDER, "haha.wav") # <<< Đảm bảo file haha.wav tồn tại
SAD_SOUND_PATH = os.path.join(SOUND_FOLDER, "saddd.wav") # <<< Đảm bảo file saddd.wav tồn tại
# --- Kết thúc cấu hình ---

# --- Khởi tạo Pygame Mixer MỘT LẦN ---
try:
    pygame.mixer.init()
    print("Pygame mixer initialized successfully.")
except pygame.error as e:
    print(f"Fatal Error: Could not initialize pygame mixer: {e}") 

# Hàm nhận giọng nói từ micrô
def listen_to_mic():
    recognizer = sr.Recognizer()
    # Điều chỉnh độ nhạy với tiếng ồn xung quanh
    # recognizer.dynamic_energy_threshold = True # Bật nếu môi trường ồn ào thay đổi
    # recognizer.energy_threshold = 400 # Giảm nếu mic quá nhạy, tăng nếu mic không bắt tiếng
    # recognizer.pause_threshold = 0.8 # Thời gian im lặng trước khi kết thúc câu (giây)
    with sr.Microphone() as source:
        print("Bạn có thể nói câu hỏi của mình...")
        try:
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
            text = recognizer.recognize_google(audio, language="vi-VN")
            print(f"Bạn nói: {text}")
            return text
        except sr.UnknownValueError:
            print("Không nhận diện được giọng nói.")
            return None
        except sr.RequestError as e: 
            print(f"Lỗi kết nối khi nhận diện giọng nói: {e}")
            return None
        except Exception as e:
            print(f"Lỗi khác khi nhận giọng nói: {e}")
            return None

#Hàm phân tích cảm xúc của câu trả lời
positive_words = {'vui', 'thích', 'tuyệt', 'tốt', 'hạnh phúc', 'mừng', "sướng", 
                  "lạc quan","háo hức", 'năng lượng', 'hehe', 'hihi', 'kk'}
negative_words = {'buồn', 'chán', 'tệ', 'tồi tệ', 'mệt mỏi', 'nặng trĩu', "bi quan","huhu",
                  "nản lòng", "ủ rũ", "rầu rĩ", "phiền muộn", "lo lắng" , "tiêu cực", "mất hứng", "nản chí"}

def simple_lexicon_sentiment(text,message):
    words1 = word_tokenize(text.lower()) # Tách từ và chuyển thành chữ thường
    words2 = word_tokenize(message.lower()) # Tách từ và chuyển thành chữ thường
    words = words1 + words2
    pos_score = 0
    neg_score = 0
    for word in words :
        if word in positive_words:
            pos_score += 1
        elif word in negative_words:
            neg_score += 1

    if pos_score > neg_score:
        return "Vui"
    elif neg_score > pos_score:
        return "Buon"
    else:
        return "Binh thuong"


# --- Hàm phát hiệu ứng âm thanh (Sử dụng Pygame) ---
def play_sound_effect(sound_file_path):
    """Phát một file hiệu ứng âm thanh ngắn bằng pygame.mixer.Sound"""
    if not pygame.mixer.get_init():
        print("Warning: Pygame mixer not initialized. Cannot play sound effect.")
        return
    if not os.path.exists(sound_file_path):
        print(f"Warning: Sound effect file not found: {sound_file_path}")
        return
    try:
        sound = pygame.mixer.Sound(sound_file_path)
        sound.play() # Phát trên kênh trống đầu tiên (non-blocking)
    except pygame.error as e:
        print(f"Error playing sound effect {sound_file_path}: {e}")
    except Exception as e:
        print(f"Unexpected error playing sound effect {sound_file_path}: {e}")

# Hàm phát âm thanh
# --- Hàm phát âm thanh TTS (Đã cập nhật để xử lý lỗi khóa file) ---
def speak_text_gtts(text, language="vi"):
    """Phát văn bản bằng gTTS và pygame.mixer.music, xử lý lỗi khóa file."""
    global speaking
    if not pygame.mixer.get_init():
        print("Error: Pygame mixer not initialized. Cannot speak.")
        return

    if not speaking:
        speaking = True
        print("Speak request ignored because speaking flag was False.")
        return

    temp_file = "output.mp3"
    mixer_was_busy = False # Biến để theo dõi nếu nhạc thực sự đã phát

    try:
        # Dừng nhạc có thể đang phát từ lần trước
        if pygame.mixer.get_init(): # Luôn kiểm tra trước khi gọi
            pygame.mixer.music.stop()
            pygame.mixer.music.unload() # Thêm unload ở đây để đảm bảo sạch sẽ trước khi tạo file mới
            time.sleep(0.1) # Chờ một chút xíu

        # print(f"Generating TTS for: '{text}'")
        tts = gTTS(text=text, lang=language, slow=False)
        tts.save(temp_file) # Lỗi [Errno 13] có thể xảy ra ở đây nếu không có quyền ghi
        # print(f"TTS saved to {temp_file}")

        if pygame.mixer.get_init():
            pygame.mixer.music.load(temp_file)
            # print(f"Playing TTS: {temp_file}...")
            pygame.mixer.music.play()
            mixer_was_busy = True # Đánh dấu là nhạc đã bắt đầu phát

            while pygame.mixer.music.get_busy():
                if not speaking:
                    print("TTS playback interrupted by flag.")
                    pygame.mixer.music.stop()
                    # Không unload ở đây vội, để finally xử lý
                    break
                time.sleep(0.1)
        else:
             print("Error: Mixer not initialized before playback attempt.")


    except PermissionError as pe:
        print(f"PermissionError during TTS save/load: {pe}. Check write permissions for the script's directory.")
        # Không cần làm gì thêm ở đây, finally sẽ cố gắng dọn dẹp
    except Exception as e:
        print(f"Error during TTS generation or playback: {e}")
        # Cố gắng dừng nhạc nếu có lỗi xảy ra giữa chừng
        if pygame.mixer.get_init() and mixer_was_busy:
             try:
                 pygame.mixer.music.stop()
             except Exception as stop_err:
                 print(f"Error stopping music after exception: {stop_err}")

    finally:
        # --- Khối dọn dẹp quan trọng ---
        # print("DEBUG: Entering finally block for TTS cleanup.") # Debug
        if pygame.mixer.get_init():
            # print(f"DEBUG: Mixer is initialized. Music was busy: {mixer_was_busy}") # Debug
            # Chỉ unload nếu nhạc đã được load và có thể đã phát
            if mixer_was_busy: # Chỉ unload nếu đã load và play thành công
                try:
                    # print("DEBUG: Attempting to unload music...") # Debug
                    pygame.mixer.music.unload() # <<< GIẢI PHÓNG KHÓA FILE Ở ĐÂY
                    # print("DEBUG: Music unloaded successfully.") # Debug
                except Exception as unload_err:
                    print(f"Error unloading music: {unload_err}")

        # Đợi một chút sau khi unload để hệ thống có thời gian xử lý
        time.sleep(0.3) # Có thể tăng/giảm thời gian này nếu cần

        if os.path.exists(temp_file):
            # print(f"DEBUG: Attempting to remove {temp_file}...") # Debug
            try:
                os.remove(temp_file)
                # print(f"DEBUG: Removed temporary TTS file: {temp_file}") # Debug
            # Bắt lỗi cụ thể hơn
            except PermissionError as pe_remove:
                print(f"PermissionError removing {temp_file}: {pe_remove}. File might STILL be locked or permissions issue.")
                # Ở đây, nếu vẫn lỗi, có thể do antivirus hoặc vấn đề khác
            except FileNotFoundError:
                 print(f"Warning: {temp_file} not found during cleanup (already removed?).")
            except Exception as e_remove:
                print(f"Error removing {temp_file}: {e_remove}")
        # else:
            # print(f"DEBUG: {temp_file} does not exist in finally block.") # Debug

    # print("DEBUG: Exiting speak_text_gtts function.") # Debug
    speaking = True

#Hàm giới hạn kí tự câu trả lời
def limit_characters(text, max_chars=200):
    if len(text) > max_chars:
        truncated = text[:max_chars]
        last_space = truncated.rfind(" ")
        if last_space != -1:
            truncated = truncated[:last_space]
        return truncated + "..."
    return text

# --- Các hàm của ESP32 Sender ---
#Khởi tạo dữ liệu
def initialize_database():
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

# --- Hàm để đọc dữ liệu ---
def read_all_data_from_db():
    """
    Đọc tất cả dữ liệu từ bảng data_log trong database.
    Trả về một danh sách các tuple, mỗi tuple là một hàng dữ liệu.
    """
    conn = None
    all_data = [] # Khởi tạo danh sách rỗng để chứa kết quả
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Thực thi câu lệnh SELECT để lấy tất cả các cột (*) từ bảng data_log
        # Bạn cũng có thể chỉ định các cột cụ thể: SELECT id, timestamp, data_sent FROM data_log
        cursor.execute("SELECT id, timestamp, data_sent, status FROM data_log ORDER BY timestamp DESC") # Sắp xếp theo thời gian mới nhất trước

        # Lấy tất cả các hàng kết quả trả về từ câu lệnh execute
        all_data = cursor.fetchall()

        print(f"Đã đọc thành công {len(all_data)} bản ghi từ database.")

    except sqlite3.Error as e:
        print(f"Lỗi SQLite khi đọc dữ liệu: {e}")
        all_data = [] # Trả về danh sách rỗng nếu có lỗi
    finally:
        # Đảm bảo kết nối luôn được đóng dù có lỗi hay không
        if conn:
            conn.close()

    return all_data

# --- Hàm gửi dữ liệu tới ESP32 ---
# Chúng ta đưa logic gửi vào hàm riêng để dễ gọi và quản lý socket
client_socket = None # Biến toàn cục để giữ kết nối socket

def send_to_esp32(data_to_send):
    global client_socket
    is_sent = False # Biến để biết đã gửi thành công chưa

    # Bước 1: Thử kết nối nếu chưa có hoặc bị mất
    if client_socket is None:
        print("\nĐang thử kết nối tới ESP32...")
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(3) # Timeout ngắn để không chờ quá lâu
            client_socket.connect((ESP32_IP, ESP32_PORT))
            print(f"Đã kết nối tới ESP32 tại {ESP32_IP}:{ESP32_PORT}")
            client_socket.settimeout(None) # Bỏ timeout sau khi kết nối
        except (socket.timeout, socket.error) as conn_err:
            print(f"Lỗi kết nối ESP32: {conn_err}")
            log_data_to_db(f"Connection Error: {conn_err}", status="Error")
            client_socket = None # Đặt lại để thử lại lần sau
            log_data_to_db(data_to_send, status="Failed (No Connection)") # Ghi log dữ liệu không gửi được
            return False # Trả về False nếu không kết nối được

    # Bước 2: Gửi dữ liệu nếu đang có kết nối
    if client_socket:
        try:
            print(f"--> Đang gửi tới ESP32: {data_to_send}")
            client_socket.sendall(data_to_send.encode('utf-8') + b'\n')
            log_data_to_db(data_to_send, status="Sent OK")
            is_sent = True # Đánh dấu đã gửi thành công
        except socket.error as send_err:
            print(f"Lỗi khi gửi tới ESP32: {send_err}. Đang đóng kết nối.")
            log_data_to_db(f"Send Error: {send_err}", status="Error")
            try:
                client_socket.close() # Cố gắng đóng socket cũ
            except:
                pass # Bỏ qua nếu đóng cũng lỗi
            client_socket = None # Đặt lại để thử kết nối lại lần sau
            log_data_to_db(data_to_send, status="Failed (Send Error)") # Ghi log dữ liệu không gửi được
            is_sent = False # Đánh dấu gửi thất bại
        except Exception as e:
             print(f"Lỗi không xác định khi gửi: {e}")
             log_data_to_db(f"Unknown Send Error: {e}", status="Error")
             try:
                client_socket.close()
             except:
                pass
             client_socket = None
             log_data_to_db(data_to_send, status="Failed (Unknown Send Error)")
             is_sent = False

    return is_sent # Trả về True nếu gửi thành công, False nếu thất bại

# --- Dọn dẹp ---
def cleanup():
    global client_socket
    # Dọn dẹp file mp3
    if os.path.exists("output.mp3"):
        try:
            os.remove("output.mp3")
        except Exception as e:
            print(f"Lỗi khi dọn dẹp file mp3: {e}")
    # Đóng socket
    if client_socket:
        print("Đóng kết nối socket khi thoát.")
        try:
            client_socket.close()
        except Exception as e:
             print(f"Lỗi khi đóng socket lúc dọn dẹp: {e}")


#Hàm mở ứng dụng
def open_application(text):
    if "google" in text:
        os.startfile("C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")
        return "Đang mở Google Chrome!!!"
    elif "word" in text:
        os.startfile('C:\Program Files\Microsoft Office\\root\Office16\WINWORD.EXE')
        return "Đang mở Microsoft Word!!!"
    elif "excel" in text:
        os.startfile("C:\Program Files\Microsoft Office\\root\Office16\EXCEL.EXE")
        return "Đang mở Microsoft Excel!!!"
    else:
        print("Ứng dụng chưa được cài đặt. Bạn hãy thử lại!!!")
        
#Hàm mở website
def open_website(text):
    reg_ex = re.search('mở (.+)', text)
    if reg_ex:
        domain = reg_ex.group(1)
        url = 'https://www.' + domain + '.com'
        # url = domain + '.com'
        webbrowser.open(url)
        return "Đang mở "+ domain + "!!!"

atexit.register(cleanup) # Đăng ký hàm cleanup

# --- Khởi tạo và Vòng lặp chính ---
if __name__ == "__main__":
    initialize_database() # Khởi tạo DB
    cleaned_response = ''
    # Cấu hình Google Generative AI
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        chat = model.start_chat()
        print("ChatBot và ESP32 Sender đã sẵn sàng! Gõ 'bye' để kết thúc hoặc 'stop' để dừng nói.")
    except Exception as e:
        print(f"Lỗi nghiêm trọng khi cấu hình Google Generative AI: {e}")
        print("Chương trình không thể tiếp tục.")
        exit() # Thoát nếu không cấu hình được AI

    # Vòng lặp chính của Chatbot
    while True:
        try:
            message = input('You: ') # Nhập bằng tay
            # message = listen_to_mic()# Nói 
            
            
            if message is None:
                # Nếu không nhận diện được giọng nói, hoặc có lỗi,
                # thì bỏ qua lần lặp này và lắng nghe lại.
                print("--------------------")
                continue # Quay lại đầu vòng lặp while
            
            text = message.lower()
            if message.lower() == 'bye':
                print('ChatBot: Tạm biệt!')
                break

            if message.lower() == 'stop' or message.lower() == 'dừng lại':
                print("Dừng lại.")
                speaking = False  # Đặt cờ thành False
                pygame.mixer.music.stop() # Dừng phát nhạc ngay lập tức
                continue # Tiếp tục vòng lặp mà không phát âm thanh

            # Gửi tin nhắn đến Chatbot và xử lý
            try:
                if "tay trái" in text : #điều khiển tay trái
                    if "bỏ" in text :
                        message = "bo tay trai"
                        limited_response = "Đang bỏ tay trái xuống"
                    else:
                        message = "tay trai"
                        limited_response = "Đang dơ tay trái lên"
                elif "tay phải" in text : #điều khiển tay phải
                    if "bỏ" in text :
                        message = "bo tay phai"
                        limited_response = "Đang bỏ tay phải xuống"
                    else:
                        message = "tay phai"
                        limited_response = "Đang dơ tay phải lên"
                elif "hai tay" in text:
                    if "bỏ" in text :
                        message = "bo hai tay"
                        limited_response = "Đang bỏ hai tay xuống"
                    else:
                        message = "hai tay"
                        limited_response = "Đang dơ hai tay lên"
                elif "time" in text or "mấy giờ" in text: # thời gian thực
                    limited_response = "Bây giờ là: " + datetime.now().strftime("%H:%M:%S  %d/%m/%Y")
                elif "mở" in text: #mở app, web
                    if re.search("word|excel|google", text):
                        limited_response = open_application(text)
                    elif re.search("điều khiển", text):
                        webbrowser.open("http://"+ ESP32_IP)
                        limited_response = "Đang mở trang web điều khiển"
                    else:
                        limited_response = open_website(text)
                elif "data" in text: #đọc dữ liệu trên database
                    limited_response = "Dữ liệu từ database"
                    print("\n--- Đọc dữ liệu từ DB ---")
                    retrieved_logs = read_all_data_from_db()
                    # In dữ liệu đã đọc
                    if retrieved_logs:
                        print("\n--- Dữ liệu đã đọc ---")
                        for row in retrieved_logs:
                            # Mỗi 'row' là một tuple chứa các giá trị của một hàng
                            # theo thứ tự các cột trong câu lệnh SELECT
                            # (id, timestamp, data_sent, status)
                            print(f"ID: {row[0]}, Thời gian: {row[1]}, Dữ liệu: {row[2]}, Trạng thái: {row[3]}")
                            # cập nhật dữ liệu tôi tên Bảo sinh năm 2003. học trường tdtu. cao 1m7 khi nào tôi hỏi thì mới trả lời. bây giờ trả lời câu hỏi của tôi với tư cách tôi là người lạ.  Xin chào
                    else:
                        print("Không có dữ liệu nào trong database")
                else:
                    response = chat.send_message(message + ' .Trả lời ngắn gọn') ##' .Trả lời ngắn gọn'
                    limited_response = limit_characters(response.text.replace("*", ""), max_chars=400)
                    cleaned_response = response.text.replace('\n', '')
                    
                print('ChatBot:', limited_response)

                # Phân tích cảm xúc
                sentiment = simple_lexicon_sentiment(limited_response, message) if limited_response else "Binh thuong"    
                print(f"(Cảm xúc: {sentiment})") # In cảm xúc
                
                # Phát hiệu ứng âm thanh dựa trên cảm xúc
                if sentiment == "Vui":
                    play_sound_effect(HAPPY_SOUND_PATH)
                elif sentiment == "Buon":
                    play_sound_effect(SAD_SOUND_PATH)

                # *** Gửi dữ liệu tới ESP32 ***
                if cleaned_response == '':
                    response_to_send = limited_response 
                else:
                    response_to_send = cleaned_response
                    
                delimiter = "|"
                send_to_esp32(f"{message}{delimiter}{response_to_send}{delimiter}{sentiment}") 
                cleaned_response = ''

                # Phát âm thanh (sau khi đã gửi)
                speak_text_gtts(limited_response, language="vi")

            except Exception as e:
                print(f"Lỗi trong quá trình chat hoặc gửi: {e}")
                # Có thể log lỗi này vào DB nếu muốn
                log_data_to_db(f"Chat/Send Process Error: {e}", status="Error")

        except KeyboardInterrupt:
             print("\nNgắt bởi người dùng. Đang thoát...")
             break # Thoát vòng lặp chính
        except EOFError:
            print("\nLỗi đọc input. Đang thoát...")
            break

    print("Chương trình kết thúc.")