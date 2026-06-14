import easyocr

reader = easyocr.Reader(["en"])


def ocr_score(img, take="right"):
    """
    Extract a single score digit from a narrow score-region crop.

    take='right'  returns the rightmost digit (use for the left-team crop).
    take='left'   returns the leftmost digit (use for the right-team crop, where
                  the team logo can appear to the right during buy-phase HUD).
    Returns '100' when no valid digit is found.
    """
    results = reader.readtext(img, detail=1, allowlist="0123456789")

    candidates = []
    for bbox, text, _conf in results:
        text = text.strip()
        if text.isdigit() and 1 <= len(text) <= 2:
            x_center = (bbox[0][0] + bbox[2][0]) / 2
            candidates.append((x_center, text))

    if not candidates:
        return "100"

    candidates.sort(key=lambda c: c[0])
    return candidates[0][1] if take == "left" else candidates[-1][1]
