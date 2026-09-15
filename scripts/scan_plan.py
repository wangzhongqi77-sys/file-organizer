# -*- coding: utf-8 -*-
"""scan_plan.py - 扫描目录生成分类移动计划（只分析不移动）

用法:
    python scan_plan.py <root> --out plan.csv [--ext png,jpg,pdf,mp4] [--rules rules.json] [--exclude dir1,dir2] [--match-dir]

输出 CSV: src,file,category,kw,match_on   -- 人工确认后再交给 execute_plan.py
match_on: 文件名 / 目录名 / 空(未分类)。默认只匹配文件名；加 --match-dir 后，
          文件名未命中才用所在目录名兜底，并在 match_on 列标注来源便于人工复核。

规则 JSON ~/rules.json:
{
  "类别A": ["关键词1", "关键词2"],
  "类别B": ["关键词3"]
}
按文件名字典序匹配，命中第一个类（数组顺序即优先级）。
```
"""
import sys
import os
import csv
import argparse
import json


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
MEDIA_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv", ".flv", ".m4v", ".mp3", ".wav"}
PDF_EXTS = {".pdf"}

# 通常要排除的目录片段（系统/程序/缓存，避免被图标和聊天图淹没）
DEFAULT_EXCLUDE = ("Windows", "Program Files", "Program Files (x86)", "AppData",
                   "WindowsApps", "node_modules", "$Recycle.Bin", "System Volume")


def scan(root, exts, exclude):
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        if dirnames:
            dirnames[:] = [d for d in dirnames if not any(x.lower() in (d or "").lower() for x in exclude)]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in exts:
                hits.append(os.path.join(dirpath, fn))
    return hits


def load_rules(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def match_rules(fn, rules, dirname=None):
    """返回 (类别, 关键词, 匹配来源)。数组顺序即优先级。

    先按文件名匹配；未命中且传入 dirname 时，再按所在目录名兜底匹配。
    """
    if not rules:
        return ("未分类", "", "")
    for cat, kws in rules.items():
        for kw in kws:
            if kw in fn:
                return (cat, kw, "文件名")
    if dirname:
        for cat, kws in rules.items():
            for kw in kws:
                if kw in dirname:
                    return (cat, kw, "目录名")
    return ("未分类", "", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out", default="plan.csv")
    ap.add_argument("--ext", default="png,jpg,jpeg,gif,webp,bmp,pdf,mp4,mov,avi,mkv,webm,wmv,flv,m4v,mp3,wav")
    ap.add_argument("--rules", default="")
    ap.add_argument("--match-dir", action="store_true",
                    help="文件名未命中时，用所在目录名兜底匹配（默认关闭，行为不变）")
    ap.add_argument("--exclude", default=",".join(DEFAULT_EXCLUDE))
    args = ap.parse_args()

    exts = {"." + e.strip().lstrip(".").lower() for e in args.ext.split(",") if e.strip()}
    rules = load_rules(args.rules)
    exclude = [x.strip() for x in args.exclude.split(",") if x.strip()]

    files = scan(args.root, exts, exclude)
    print(f"扫描到 {len(files)} 个文件")

    rows = []
    for p in files:
        fn = os.path.basename(p)
        dirname = os.path.basename(os.path.dirname(p)) if args.match_dir else None
        cat, kw, match_on = match_rules(fn, rules, dirname)
        rows.append({"src": p, "file": fn, "category": cat, "kw": kw, "match_on": match_on})
    rows.sort(key=lambda r: r["src"])

    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["src", "file", "category", "kw", "match_on"])
        w.writeheader()
        w.writerows(rows)

    if rules:
        from collections import Counter
        c = Counter(r["category"] for r in rows)
        print("分类分布:")
        for k, v in c.most_common():
            print(f"  {k}: {v}")
    print(f"计划已写入 {args.out}，请人工确认后交给 execute_plan.py")


if __name__ == "__main__":
    main()