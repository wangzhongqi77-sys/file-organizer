# -*- coding: utf-8 -*-
"""rename_pdf.py - PDF 内容识别重命名（文本层优先 + RapidOCR 兜底）

用法:
    python rename_pdf.py <dir> [--recursive] [--out report.txt]

流程: 文本层提取(<20字或无) -> PyMuPDF渲染首页(3x) -> RapidOCR -> 建名
依赖: pypdf, PyMuPDF, rapidocr (pip install "numpy<2")
OCR 错别字映射表写在 OCR_FIXES，按需扩展。
"""
import os
import re
import sys
import argparse

OCR_FIXES = {  # OCR 常见错别字映射（按你行业/客户的真实错法扩展）
    "申方": "甲方",
    "数址": "数量",
}

ILLEGAL = re.compile(r'[\\/:*?"<>|]')
SURROGATES = re.compile(r"[\ud800-\udfff]")


def clean(s):
    s = SURROGATES.sub("", s or "")
    s = ILLEGAL.sub("_", s).strip()
    s = re.sub(r"\s+", "", s)
    return s[:70]


def extract_text(path):
    try:
        from pypdf import PdfReader
        text = ""
        for page in PdfReader(path).pages[:3]:
            text += (page.extract_text() or "")
        return text
    except Exception:
        return ""


def ocr_first_page(path):
    try:
        import fitz
        doc = fitz.open(path)
        if doc.page_count == 0:
            return ""
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(3, 3))
        img = f"{path}.tmp.png"
        pix.save(img)
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        res, _ = engine(img)
        os.remove(img)
        text = "".join(x[1] for x in (res or []))
        for k, v in OCR_FIXES.items():
            text = text.replace(k, v)
        return text
    except Exception as e:
        return f"[OCR失败:{e}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--recursive", action="store_true")
    ap.add_argument("--out", default="rename_report.txt")
    args = ap.parse_args()

    files = []
    if args.recursive:
        for dp, _, fns in os.walk(args.dir):
            for fn in fns:
                if fn.lower().endswith(".pdf"):
                    files.append(os.path.join(dp, fn))
    else:
        files = [os.path.join(args.dir, f) for f in os.listdir(args.dir) if f.lower().endswith(".pdf")]

    plan = []  # (src, new_name)
    for p in files:
        name = os.path.basename(p)
        stem = os.path.splitext(name)[0]
        # 可读名（含汉字或已知前缀）跳过
        if re.search(r"[\u4e00-\u9fff]", stem) and not re.match(r"^(PDF_?|图片|文字|文档|扫描文稿|扫描|QQ|微信)", stem):
            continue
        text = extract_text(p)
        if len(text.strip()) < 20:
            text = ocr_first_page(p)
        cand = clean(text)
        if len(cand) < 8:
            continue  # 识别不出有意义内容，保留原名
        plan.append((p, cand + ".pdf"))

    report = []
    for src, new in plan:
        dst = os.path.join(os.path.dirname(src), new)
        n = 1
        while os.path.exists(dst):
            stem, ext = os.path.splitext(new)
            dst = os.path.join(os.path.dirname(src), f"{stem}({n}){ext}")
            n += 1
        try:
            os.rename(src, dst)
            report.append(f"{os.path.basename(src)} -> {new}")
        except PermissionError:
            try:
                os.chmod(src, 0o666)
                os.rename(src, dst)
                report.append(f"{os.path.basename(src)} -> {new}")
            except OSError as e:
                report.append(f"[ERROR] {src}: {e}")
        except OSError as e:
            report.append(f"[ERROR] {src}: {e}")

    with open(args.out, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(report) + f"\n\n共重命名 {len(report)} 个\n")
    print(f"重命名 {len(report)} 个，报告: {args.out}")


if __name__ == "__main__":
    main()