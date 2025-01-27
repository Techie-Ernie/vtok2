import easyocr

reader = easyocr.Reader(["en"])


def ocr(img):
    if len(reader.readtext(img, detail=0)) > 0:
        return reader.readtext(img, detail=0)[0]

    return None


if __name__ == "__main__":
    print(ocr("file2.png"))
