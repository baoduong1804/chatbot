
from textblob import TextBlob
import google.generativeai as genai
from gtts import gTTS
import pygame
import os
import time
import atexit
from underthesea import word_tokenize
from datetime import datetime

# Hàm phân tích cảm xúc

positive_words = {'vui', 'thích', 'tuyệt vời', 'tốt', 'hạnh phúc', 'năng lượng'}
negative_words = {'buồn', 'chán', 'tệ', 'tồi tệ', 'mệt mỏi', 'nặng trĩu'}

def simple_lexicon_sentiment(text):
    words = word_tokenize(text.lower()) # Tách từ và chuyển thành chữ thường
    pos_score = 0
    neg_score = 0
    for word in words:
        if word in positive_words:
            pos_score += 1
        elif word in negative_words:
            neg_score += 1

    if pos_score > neg_score:
        return "Vui"
    elif neg_score > pos_score:
        return "Buồn"
    else:
        return "Bình thường"


speaking = True  

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

# Cấu hình API key
GOOGLE_API_KEY = "AIzaSyCDZOzBDFSTRAsC-RrmQ8bO27azloOb02Y"  # <------- REPLACE THIS

try:
    # Cấu hình Google Generative AI
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro-latest')  # Tùy chỉnh mô hình
    chat = model.start_chat()

    print("ChatBot đã sẵn sàng! Gõ 'bye' để kết thúc hoặc 'stop' để dừng phát âm thanh.")
    while True:
        message = input('You: ')    
         
        if message.lower() == 'stop':
            print("Dừng lại.")
            speaking = False  # Đặt cờ thành False
            pygame.mixer.music.stop() # Dừng phát nhạc ngay lập tức
            continue # Tiếp tục vòng lặp mà không phát âm thanh

        try:
            # Gửi câu hỏi và nhận phản hồi
            if "time" in message.lower() or "mấy giờ" in message.lower():
                limited_response = "Bây giờ là: " + datetime.now().strftime("%H:%M:%S  %d/%m/%Y")
            else:
                response = chat.send_message(message + ' .Trả lời ngắn gọn' ) ## ' .Trả lời ngắn gọn'
                limited_response = limit_characters(response.text.replace("*", ""), max_chars=400)  # Giới hạn số ký tự phản hồi
                
            print('ChatBot:', limited_response)
            # Phân tích cảm xúc của câu trả lời
            sentiment = simple_lexicon_sentiment(limited_response)
            print(f"Phản hồi có cảm xúc: {sentiment}")

            # Phát âm thanh phản hồi
            speak_text_gtts(limited_response, language="vi")
        except Exception as e:
            print(f"Lỗi khi gửi tin nhắn đến ChatBot: {e}")

except Exception as e:
    print(f"Lỗi khi cấu hình Google Generative AI: {e}")