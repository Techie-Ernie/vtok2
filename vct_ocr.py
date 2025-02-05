import easyocr

reader = easyocr.Reader(["en"])


def ocr(img):
    scores = []
    if len(reader.readtext(img, detail=0, batch_size=4)) > 0:
        results = reader.readtext(img, detail=0)
        print(results)
        for result in results:
            if len(result) <= 2 and len(scores) < 2:
                # replacement for 4 since '4' is detected as 'R'

                if "R" in result:
                    scores.append("4")
                if result.isdigit():
                    scores.append(result)

        if len(scores) == 2:
            return scores
        else:
            return ["100", "100"]
    return ["100", "100"]


if __name__ == "__main__":
    print(ocr("file2.png"))
