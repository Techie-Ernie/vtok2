from paddleocr import PaddleOCR

_ocr = PaddleOCR(lang="en", show_log=False, use_gpu=True, enable_mkdnn=True, cls=False)


def ocr(img):
    results = _ocr.ocr(img)
    text_confidences = []
    if results[0]:
        for line in results[0]:
            text, confidence = line[1][0], line[1][1]
            text_confidences.append((text, confidence))

        if text_confidences:
            highest_confidence_text = max(text_confidences, key=lambda x: x[1])
            if highest_confidence_text[0].isdigit():
                return highest_confidence_text[0]
            elif highest_confidence_text[0] == "O":
                return "0"
            elif ":" in highest_confidence_text[0]:
                return highest_confidence_text[0]
            else:
                return None
        else:
            return None
