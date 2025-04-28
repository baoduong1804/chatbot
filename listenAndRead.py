
from textblob import TextBlob
import google.generativeai as genai
from gtts import gTTS
import pygame
import os
import time
import atexit
import speech_recognition as sr

# Hàm phân tích cảm xúc
def analyze_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # Trả về giá trị từ -1 (negative) đến 1 (positive)
    
    if polarity > 0.1:
        return "vui"
    elif polarity < -0.1:
        return "buồn"
    else:
        return "trung tính"

speaking = True  # Khởi tạo cờ

# Hàm phát âm thanh
def speak_text_gtts(text, language="vi"):
    global speaking  # Sử dụng biến global
    try:
        # Chuyển văn bản thành file âm thanh
        tts = gTTS(text=text, lang=language, slow=False)
        tts.save("output.mp3")

        # Khởi tạo pygame chỉ khi có âm thanh để phát
        try:
            pygame.mixer.init()
        except pygame.error as e:
            print(f"Lỗi khi khởi tạo pygame: {e}")
            return  # Dừng hàm nếu pygame không khởi tạo được

        # Phát âm thanh
        pygame.mixer.music.load("output.mp3")
        pygame.mixer.music.play()

        # Đợi cho đến khi âm thanh phát xong
        while pygame.mixer.music.get_busy() and speaking:  # Kiểm tra cờ
            time.sleep(0.1)

        pygame.mixer.quit()  # Giải phóng tài nguyên
    except Exception as e:
        print(f"Lỗi khi phát âm thanh: {e}")
    finally:
        # Xóa file âm thanh sau khi phát xong
        time.sleep(0.5)
        if os.path.exists("output.mp3"):
            try:
                os.remove("output.mp3")
            except Exception as e:
                print(f"Lỗi khi xóa file: {e}")

    speaking = True  # Reset cờ

# Đảm bảo xóa file khi chương trình kết thúc
def cleanup():
    if os.path.exists("output.mp3"):
        try:
            os.remove("output.mp3")
        except Exception as e:
            print(f"Lỗi khi dọn dẹp file: {e}")

atexit.register(cleanup)  # Đăng ký dọn dẹp khi thoát

# Hàm giới hạn số ký tự
def limit_characters(text, max_chars=200):
    if len(text) > max_chars:
        truncated = text[:max_chars]
        # Tìm khoảng trắng cuối cùng trong phần truncated
        last_space = truncated.rfind(" ")
        if last_space != -1:
            truncated = truncated[:last_space]
        return truncated + "..."  # Cắt bớt và thêm "..."
    return text

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

# Cấu hình API key
GOOGLE_API_KEY = "AIzaSyCDZOzBDFSTRAsC-RrmQ8bO27azloOb02Y"  # <------- REPLACE THIS

try:
    # Cấu hình Google Generative AI
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro-latest')  # Tùy chỉnh mô hình
    chat = model.start_chat()

    print("ChatBot đã sẵn sàng! Đọc 'bye' để kết thúc hoặc 'stop' để dừng phát âm thanh.")
    while True:
        message = listen_to_mic() #nhận giọng nói từ mic
        if message is None:
            # Nếu không nhận diện được giọng nói, hoặc có lỗi,
            # thì bỏ qua lần lặp này và lắng nghe lại.
            print("--------------------")
            continue # Quay lại đầu vòng lặp while
        
        if message.lower() == 'bye':
            print('ChatBot: Tạm biệt!')
            break

        if message.lower() == 'stop' or message.lower() == 'dừng lại':
            print("Dừng lại.")
            speaking = False  # Đặt cờ thành False
            pygame.mixer.music.stop() # Dừng phát nhạc ngay lập tức
            continue # Tiếp tục vòng lặp mà không phát âm thanh

        try:
            # Gửi câu hỏi và nhận phản hồi
            response = chat.send_message(message + ' .Trả lời ngắn gọn') ## ' .Trả lời ngắn gọn'
            limited_response = limit_characters(response.text.replace("*", ""), max_chars=400)  # Giới hạn số ký tự phản hồi
            print('ChatBot:', limited_response)
            # Phân tích cảm xúc của câu trả lời
            sentiment = analyze_sentiment(limited_response)
            print(f"Phản hồi có cảm xúc: {sentiment}")

            # Phát âm thanh phản hồi
            speak_text_gtts(limited_response, language="vi")
        except Exception as e:
            print(f"Lỗi khi gửi tin nhắn đến ChatBot: {e}")

except Exception as e:
    print(f"Lỗi khi cấu hình Google Generative AI: {e}")