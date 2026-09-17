# -*- coding: utf-8 -*-
# 通用 contact sheet：指定目录按批生成序号标注拼图（序号锚定，避免OCR幻觉）
import os, sys
from PIL import Image, ImageDraw, ImageFont

def font(sz):
    for p in [r"C:\Windows\Fonts\msyhbd.ttf", r"C:\Windows\Fonts\msyh.ttc"]:
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            continue
    return ImageFont.load_default()

def main():
    D = sys.argv[1]
    TAG = sys.argv[2]
    OUT = sys.argv[3]
    PER = int(sys.argv[4]) if len(sys.argv) > 4 else 25
    COLS = int(sys.argv[5]) if len(sys.argv) > 5 else 5
    TH = 210; W = 300; LB = 22
    names = sorted(f for f in os.listdir(D) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp')))
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f'order_{TAG}.txt'), 'w', encoding='utf-8') as fo:
        for i, n in enumerate(names, 1):
            fo.write(f"{i}\t{n}\n")
    chunks = [names[i:i+PER] for i in range(0, len(names), PER)]
    for ci, chunk in enumerate(chunks):
        rows = (len(chunk) + COLS - 1) // COLS
        sheet = Image.new('RGB', (COLS * W, rows * (TH + LB)), (245, 245, 245))
        dr = ImageDraw.Draw(sheet)
        for k, n in enumerate(chunk):
            idx = ci * PER + k + 1
            p = os.path.join(D, n)
            try:
                im = Image.open(p).convert('RGB')
                r = TH / im.height
                w2 = min(W, int(im.width * r))
                im = im.resize((w2, TH), Image.LANCZOS)
            except Exception:
                im = Image.new('RGB', (W, TH), (220, 220, 220))
            rr, c = divmod(k, COLS)
            y = rr * (TH + LB)
            sheet.paste(im, (c * W, y))
            dr.rectangle([c * W + 2, y + TH + 1, c * W + 62, y + TH + LB - 2], fill=(255, 200, 0))
            dr.text((c * W + 8, y + TH + 3), f"#{idx}", fill=(0, 0, 0), font=font(19))
        op = os.path.join(OUT, f'{TAG}_sheet{ci+1}.png')
        sheet.save(op)
        print('saved', op, len(chunk))

if __name__ == '__main__':
    main()