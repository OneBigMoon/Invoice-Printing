#!/usr/bin/env python3
import cgi
import json
import os
import re
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


HOST = os.environ.get("OCR_HOST", "127.0.0.1")
PORT = int(os.environ.get("OCR_PORT", "8765"))
OCR_ENGINE = None


def get_ocr_engine():
    global OCR_ENGINE
    if OCR_ENGINE is not None:
        return OCR_ENGINE

    from paddleocr import PaddleOCR

    for kwargs in (
        {"use_angle_cls": True, "lang": "ch", "show_log": False},
        {"use_angle_cls": True, "lang": "ch"},
        {"lang": "ch"},
    ):
        try:
            OCR_ENGINE = PaddleOCR(**kwargs)
            return OCR_ENGINE
        except Exception:
            continue
    OCR_ENGINE = PaddleOCR()
    return OCR_ENGINE


def run_ocr(file_path):
    if file_path.suffix.lower() == ".pdf":
        return run_pdf_ocr(file_path)

    engine = get_ocr_engine()
    try:
        result = engine.ocr(str(file_path), cls=True)
    except TypeError:
        result = engine.ocr(str(file_path))
    return extract_text_lines(result)


def run_pdf_ocr(file_path):
    import fitz

    lines = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        doc = fitz.open(file_path)
        try:
            for page_index, page in enumerate(doc):
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image_path = Path(tmp_dir) / f"page-{page_index + 1}.png"
                pixmap.save(image_path)
                lines.extend(run_ocr(image_path))
        finally:
            doc.close()
    return unique_lines(lines)


def extract_text_lines(result):
    lines = []

    def walk(value):
        if isinstance(value, str):
            text = value.strip()
            if text:
                lines.append(text)
            return
        if isinstance(value, tuple) and value and isinstance(value[0], str):
            text = value[0].strip()
            if text:
                lines.append(text)
            return
        if isinstance(value, dict):
            for key in ("text", "rec_text", "transcription"):
                text = value.get(key)
                if isinstance(text, str) and text.strip():
                    lines.append(text.strip())
            for item in value.values():
                walk(item)
            return
        if isinstance(value, list):
            for item in value:
                walk(item)

    walk(result)
    seen = set()
    unique_lines = []
    for line in lines:
        if line not in seen:
            unique_lines.append(line)
            seen.add(line)
    return unique_lines


def unique_lines(lines):
    seen = set()
    result = []
    for line in lines:
        text = line.strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def parse_fields(lines, invoice_type):
    text = "\n".join(lines)
    return {
        "amount": parse_amount(text),
        "date": parse_date(lines, invoice_type),
        "place": parse_place(lines, invoice_type),
    }


def parse_amount(text):
    amount_patterns = [
        r"(?:合计|金额|票价|实付|支付|价税合计|小写)[:：]?\s*[¥￥]?\s*(\d+(?:\.\d{1,2})?)",
        r"[¥￥]\s*(\d+(?:\.\d{1,2})?)",
    ]
    amounts = []
    for pattern in amount_patterns:
        amounts.extend(float(match) for match in re.findall(pattern, text))
    if not amounts:
        amounts.extend(float(match) for match in re.findall(r"(?<!\d)(\d+\.\d{2})(?!\d)", text))
    if not amounts:
        return ""
    return f"{max(amounts):.2f}"


def parse_date(lines, invoice_type):
    if invoice_type == "taxi":
        for line in lines:
            if "行程时间" in line or "上车时间" in line:
                date = parse_first_date(line)
                if date:
                    return date
        for line in lines:
            if "申请时间" in line or "开票日期" in line:
                continue
            date = parse_first_date(line)
            if date:
                return date

    return parse_first_date("\n".join(lines))


def parse_first_date(text):
    patterns = [
        r"(20\d{2})[年./-]\s*(\d{1,2})[月./-]\s*(\d{1,2})",
        r"(?<!\d)(\d{1,2})[月/-]\s*(\d{1,2})日?(?!\d)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        groups = match.groups()
        if len(groups) == 3:
            month = int(groups[1])
            day = int(groups[2])
        else:
            month = int(groups[0])
            day = int(groups[1])
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{month}/{day}"
    return ""


def parse_place(lines, invoice_type):
    cleaned = [line.strip() for line in lines if 2 <= len(line.strip()) <= 24]
    if invoice_type == "taxi":
        itinerary_place = parse_taxi_itinerary_place(cleaned)
        if itinerary_place:
            return itinerary_place

    if invoice_type == "train":
        route_parts = [
            line for line in cleaned
            if not re.search(r"\d|票|价|检|号|车|座|身份证|发票|电子|时间|金额", line)
        ]
        if len(route_parts) >= 2:
            return f"{route_parts[0]}-{route_parts[1]}"

    keywords = ("起点", "终点", "上车", "下车", "出发", "到达", "地点", "地址")
    places = []
    for line in cleaned:
        if any(keyword in line for keyword in keywords):
            place = re.sub(r"^(起点|终点|上车地点|下车地点|出发地|到达地|地点|地址)[:：]?", "", line)
            place = place.strip()
            if place:
                places.append(place)
    if len(places) >= 2:
        return f"{places[0]}-{places[1]}"
    if places:
        return places[0]
    return ""


def parse_taxi_itinerary_place(lines):
    if not any("行程单" in line or "AMAPITINERARY" in line for line in lines):
        return ""

    label_places = []
    for line in lines:
        for label in ("起点", "终点", "上车地点", "下车地点", "出发地", "到达地"):
            if line.startswith(label):
                place = re.sub(rf"^{label}[:：]?", "", line).strip()
                if place and place != label:
                    label_places.append(place)
    if len(label_places) >= 2:
        return f"{label_places[0]}-{label_places[1]}"

    try:
        amount_index = lines.index("金额")
    except ValueError:
        return ""

    candidates = []
    for line in lines[amount_index + 1:]:
        if is_taxi_table_noise(line):
            continue
        candidates.append(line)
        if len(candidates) >= 3:
            break

    if len(candidates) >= 3:
        return f"{candidates[0]}{candidates[2]}-{candidates[1]}"
    if len(candidates) >= 2:
        return f"{candidates[0]}-{candidates[1]}"
    return ""


def is_taxi_table_noise(line):
    if re.search(r"\d", line):
        return True
    if re.search(r"(元|页码|服务商|车型|城市|起点|终点|金额|上车时间)", line):
        return True
    if re.search(r"(高德|地图|打车|行程单|AMAP|出行|经济型|舒适型|快车|专车)", line):
        return True
    if re.fullmatch(r"[\u4e00-\u9fa5]{2,4}市", line):
        return True
    return False


class OcrHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path != "/ocr":
            self.send_json({"error": "not found"}, status=404)
            return

        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type"),
                },
            )
            upload = form["file"]
            invoice_type = form.getfirst("type", "other")
            suffix = Path(upload.filename or "upload.png").suffix or ".png"

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(upload.file.read())
                tmp_path = Path(tmp.name)

            try:
                lines = run_ocr(tmp_path)
                self.send_json({
                    "text": "\n".join(lines),
                    "lines": lines,
                    "fields": parse_fields(lines, invoice_type),
                })
            finally:
                tmp_path.unlink(missing_ok=True)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


if __name__ == "__main__":
    print(f"OCR server listening on http://{HOST}:{PORT}/ocr")
    HTTPServer((HOST, PORT), OcrHandler).serve_forever()
