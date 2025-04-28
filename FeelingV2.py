# Bước 1: Cài đặt
# pip install underthesea

# Bước 2: Kiểm tra chức năng (underthesea có thể không có hàm sentiment analysis trực tiếp)
# Thường underthesea dùng để tiền xử lý (tách từ) trước khi đưa vào mô hình ML khác.
from underthesea import word_tokenize


text_khac = "Tôi rất tiếc khi nghe bạn buồn. Tôi biết cảm giác đó khó chịu như thế nào. Mặc dù tôi không thể hiểu hết được nguyên nhân khiến bạn buồn, nhưng tôi muốn bạn biết rằng bạn không cô đơn.  Có rất nhiều người quan tâm đến bạn và muốn giúp đỡ."

text = "Tôi rất vui khi gặp bạn."
tokens = word_tokenize(text, format="text")
print(f"Văn bản sau khi tách từ: {tokens}")

# Để phân tích cảm xúc, bạn cần kết hợp underthesea (để tách từ)
# với một từ điển cảm xúc tự xây dựng hoặc một mô hình ML (như scikit-learn).
# Ví dụ (ý tưởng với từ điển tự tạo - rất cơ bản):

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
        return "Vui (Dựa trên từ điển)"
    elif neg_score > pos_score:
        return "Buồn (Dựa trên từ điển)"
    else:
        return "Trung tính/Không xác định (Dựa trên từ điển)"


print(f"'{text_khac}' -> {simple_lexicon_sentiment(text_khac)}")