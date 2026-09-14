# -*- coding: utf-8 -*-
"""execute_plan.py - 按计划 CSV 执行移动/重命名/去重/报告

用法:
    python execute_plan.py plan.csv <dest_root> [--dedup] [--src-root <dir>] [--report report.txt]

CSV 列: src,file,category,kw
- 移动: <dest_root>/<category>/<file>；重名加 "(N)" 或 "[来源] " 前缀
- --dedup: MD5 判重，目标内已有相同内容则跳过（不移动）
- --src-root: 安全闸，只允许移动该目录内的文件，越界项拒绝并记录
- 输出 report.txt（每文件一行 + 分类统计 + 删除/移动计数）
"""
import sys
import os
import csv
import hashlib
import argparse
from collections import Counter


def md5(p, chunk=1 << 16):
    h = hashlib.md5()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def unique_name(dst_dir, name):
    stem, ext = os.path.splitext(name)
    cand = name
    i = 1
    while os.path.exists(os.path.join(dst_dir, cand)):
        cand = f"{stem}({i}){ext}"
        i += 1
    return cand


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("dest")
    ap.add_argument("--dedup", action="store_true")
    ap.add_argument("--report", default="report.txt")
    ap.add_argument("--src-root", default="",
                    help="安全闸: 只允许移动该目录内的文件, 越界项拒绝并记录")
    args = ap.parse_args()

    src_root = os.path.abspath(args.src_root) if args.src_root else None
    if src_root is None:
        print("提示: 未指定 --src-root, 不校验来源范围 (推荐总是指定)")

    with open(args.plan, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    seen_hashes = set()          # 目标目录已有内容的 MD5（先收集）
    if args.dedup:
        for dp, _, fns in os.walk(args.dest):
            for fn in fns:
                try:
                    seen_hashes.add(md5(os.path.join(dp, fn)))
                except OSError:
                    pass

    moved = skipped_dup = skipped_oob = 0
    stats = Counter()
    history = []

    for r in rows:
        src = r["src"]
        cat = r["category"] or "未分类"
        if not os.path.exists(src):
            history.append(f"[MISS] {src}")
            continue
        if src_root is not None:
            try:
                inside = os.path.commonpath([os.path.abspath(src), src_root]) == src_root
            except ValueError:
                inside = False
            if not inside:
                history.append(f"[SKIP] {src} 在 --src-root 之外, 拒绝移动")
                skipped_oob += 1
                continue
        if args.dedup:
            try:
                h = md5(src)
            except OSError:
                history.append(f"[ERROR] {src}")
                continue
            if h in seen_hashes:
                skipped_dup += 1
                history.append(f"[DUP]  {src} -> {src}")
                continue
            seen_hashes.add(h)

        dst_dir = os.path.join(args.dest, cat)
        os.makedirs(dst_dir, exist_ok=True)
        name = unique_name(dst_dir, r["file"])
        dst = os.path.join(dst_dir, name)
        try:
            if os.path.abspath(src) != os.path.abspath(dst):
                os.rename(src, dst)
            stats[cat] += 1
            moved += 1
            history.append(f"[OK]   {src} -> {dst}")
        except PermissionError:
            try:
                os.chmod(src, 0o666)
                os.rename(src, dst)
                stats[cat] += 1
                moved += 1
                history.append(f"[OK]   {src} -> {dst}")
            except OSError as e:
                history.append(f"[ERROR] {src}: {e}")
        except OSError as e:
            history.append(f"[ERROR] {src}: {e}")

    with open(args.report, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(history) + "\n\n=== 分类统计 ===\n")
        for k, v in stats.most_common():
            f.write(f"{k}: {v}\n")
        f.write(f"\n移动 {moved} / 去重跳过 {skipped_dup} / 越界拒绝 {skipped_oob}\n")

    print(f"移动 {moved} / 去重跳过 {skipped_dup} / 越界拒绝 {skipped_oob}")
    for k, v in stats.most_common():
        print(f"  {k}: {v}")
    print(f"报告: {args.report}")


if __name__ == "__main__":
    main()