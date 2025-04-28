import google.generativeai as genai
from gtts import gTTS
import pygame
import os
import time
import atexit
import speech_recognition as sr


# Hàm phát âm thanh
def speak_text_gtts(text, language="vi"):
    try:
        tts = gTTS(text=text, lang=language, slow=False)
        tts.save("output.mp3")

        pygame.mixer.init()
        pygame.mixer.music.load("output.mp3")
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.quit()
    except Exception as e:
        print(f"Lỗi khi phát âm thanh: {e}")
    finally:
        if os.path.exists("output.mp3"):
            os.remove("output.mp3")


# Hàm nhận giọng nói từ micrô
def listen_to_mic():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Bạn có thể nói câu hỏi của mình...")
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
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


# Dọn dẹp file âm thanh khi chương trình kết thúc
def cleanup():
    if os.path.exists("output.mp3"):
        try:
            os.remove("output.mp3")
        except Exception as e:
            print(f"Lỗi khi dọn dẹp file: {e}")

atexit.register(cleanup)

# Cấu hình Google Generative AI
GOOGLE_API_KEY = "AIzaSyC5lyZNW6PfQCINtP_PLpdhtm1P7hreDMw"  #  API key của bạn

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    chat = model.start_chat()

    print("ChatBot đã sẵn sàng! Gõ 'bye' để kết thúc.")

    while True:
        # Nhận câu hỏi từ mic hoặc bàn phím
        input_mode = input("Nhập 'mic' để nói hoặc 'text' để nhập câu hỏi: ").strip().lower()
        if input_mode == "mic":
            user_input = listen_to_mic()
        elif input_mode == "text":
            user_input = input("You: ")
        else:
            print("Chọn chế độ không hợp lệ!")
            continue
        
        # user_input = listen_to_mic()
        # Kiểm tra đầu vào
        if not user_input:
            continue
        if user_input.lower() == "bye":
            print("ChatBot: Tạm biệt!")
            break

        # Gửi câu hỏi đến chatbot và phát âm thanh trả lời
        try:
            response = chat.send_message(user_input)
            print("ChatBot:", response.text)
            speak_text_gtts(response.text, language="vi")
        except Exception as e:
            print(f"Lỗi khi gửi tin nhắn đến ChatBot: {e}")

except Exception as e:
    print(f"Lỗi khi cấu hình Google Generative AI: {e}")

