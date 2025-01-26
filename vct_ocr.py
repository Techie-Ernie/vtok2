import easyocr

reader = easyocr.Reader(["en"])


def ocr(img):
    if len(reader.readtext(img, detail=0)) > 0:
        return reader.readtext(img, detail=0)[0]

    return None
