from paddleocr import PaddleOCR


def ocr(img):
    ocr = PaddleOCR(
        lang="en", show_log=False, use_gpu=True, enable_mkdnn=True
    )  # need to run only once to download and load model into memory
    results = ocr.ocr(img, cls=False)
    # print(results)
    # SAMPLE RESULTS #
    # [[[[[33.0, 6.0], [66.0, 6.0], [66.0, 32.0], [33.0, 32.0]], ('10', 0.9976402521133423)]]]
    text_confidences = []
    if results[0]:
        for line in results[0]:
            text, confidence = line[1][0], line[1][1]
            text_confidences.append((text, confidence))

        # Find the text with the highest confidence
        if text_confidences:
            highest_confidence_text = max(text_confidences, key=lambda x: x[1])
            if highest_confidence_text[0].isdigit():
                return highest_confidence_text[0]
            elif highest_confidence_text[0] == "O":
                return "0"
            elif ":" in highest_confidence_text[0]:  # For the timing
                return highest_confidence_text[0]
            else:
                return None
        else:
            return None
