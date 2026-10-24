from pyzbar.pyzbar import decode
from PIL import Image
import io

def read_barcode(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'L':
            img = img.convert('L')
        codes = decode(img)
        if not codes:
            img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            codes = decode(img)
        res = []
        for c in codes:
            s = c.data.decode('utf-8', errors='ignore').strip()
            if s and s not in res:
                res.append(s)
        return res
    except:
        return []
