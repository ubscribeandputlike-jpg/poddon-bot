import io
from PIL import Image
import zxingcpp


def read_barcode(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        results = zxingcpp.read_barcodes(img)
        res = []
        for b in results:
            s = (b.text or '').strip()
            if s and s not in res:
                res.append(s)
        return res
    except Exception:
        return []
