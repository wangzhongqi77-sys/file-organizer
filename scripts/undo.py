# -*- coding: utf-8 -*-
"""undo.py - 按 execute_plan.py 的报告反向撤销移动

用法:
    python undo.py <report.txt> [--dry-run] [--out undo_report.txt]

原理:
    报告里每行 [OK]   原路径 -> 新路径
    倒序（后搬的先撤）把文件搬回原位，(1)(2) 后缀名自动还原

规则:
    - 原位置已被占用 -> 跳过并记录，绝不覆盖
    - [DUP]/[MISS]/[ERROR] 行本来就没移动文件，自动忽略
    - --dry-run 只预览不动文件
"""
import os
import sys
import argparse


def parse_report(path):
    moves = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.startswith("[OK]"):
                continue
            body = line[4:].strip()
            if " -> " not in body:
                continue
            src, dst = body.rsplit(" -> ", 1)
            moves.append((src.strip(), dst.strip()))
    return moves


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default="undo_report.txt")
    args = ap.parse_args()

    moves = parse_report(args.report)
    if not moves:
        msg = f"报告里没有可撤销的移动记录: {args.report}"
        print(msg)
        with open(args.out, "w", encoding="utf-8-sig") as f:
            f.write(msg + "\n")
        return

    undone = skipped = missing = errors = 0
    log = []
    for src, dst in reversed(moves):
        if not os.path.exists(dst):
            log.append(f"[MISS] {dst}")
            missing += 1
            continue
        if os.path.exists(src):
            log.append(f"[SKIP] {src} 已被占用，撤销跳过（不覆盖）")
            skipped += 1
            continue
        parent = os.path.dirname(src)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        if args.dry_run:
            log.append(f"[PLAN] {dst} -> {src}")
            continue
        try:
            os.rename(dst, src)
            log.append(f"[OK]   {dst} -> {src}")
            undone += 1
        except PermissionError:
            try:
                os.chmod(dst, 0o666)
                os.rename(dst, src)
                log.append(f"[OK]   {dst} -> {src}")
                undone += 1
            except OSError as e:
                log.append(f"[ERROR] {dst}: {e}")
                errors += 1
        except OSError as e:
            log.append(f"[ERROR] {dst}: {e}")
            errors += 1

    with open(args.out, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(log) + "\n")
        if not args.dry_run:
            f.write(f"\n撤销 {undone} / 跳过 {skipped} / 缺失 {missing} / 错误 {errors}\n")

    if args.dry_run:
        print(f"预览: {len(moves)} 条可撤销，报告: {args.out}")
    else:
        print(f"撤销 {undone} / 跳过 {skipped} / 缺失 {missing} / 错误 {errors}，报告: {args.out}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    main()
