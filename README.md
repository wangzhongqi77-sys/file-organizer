# file-organizer

**Plan-first file organizer for AI agents** — scan → review → move. Never deletes, never overwrites, fully undoable.

[English](#english) | [中文](#中文)

---

<a id="english"></a>
## English

### What it does

Sorts thousands of scattered files (images / videos / audio / PDFs) into category folders by filename keywords, deduplicates by MD5, renames gibberish PDFs by their actual content, and cleans up empty dirs. Designed to be driven by an AI agent (Claude Code, WorkBuddy, Trea...) but works fine from a plain terminal.

### Why this one

Most "file organizer" agent skills are pure prompts: they tell the model to improvise shell commands at runtime — slow, token-hungry, and unreliable. This skill ships **three deterministic scripts** instead:

| | Pure-prompt skills | file-organizer |
|---|---|---|
| Classification rules | Model improvises each run | Fixed JSON rules, repeatable |
| The actual moving | Ad-hoc shell commands | `execute_plan.py`, logged line by line |
| Rollback | None | `undo.py`, reverses any run |
| Scope safety | Hopes the model behaves | `--src-root` hard boundary |
| Network access | — | **Zero. No network code at all** |

### The workflow

```
scan_plan.py  →  plan.csv  →  HUMAN REVIEW  →  execute_plan.py  →  report.txt
   (read-only)     (proposal)    (you approve)     (moves files)      (the ledger)
                                                                      ↓
                                                            undo.py  (reverses it)
```

1. **Scan** — `python scan_plan.py <folder> --out plan.csv --ext png,jpg,pdf,mp4 --rules rules.json [--match-dir]`
   Lists matching files and proposes a category for each. **Touches nothing.**
   Filename matching only by default; add `--match-dir` to fall back to the containing folder name when the filename misses. The `match_on` column in the CSV records which one hit, so you can spot low-confidence rows during review.
2. **Review** — open `plan.csv`, fix wrong rows. The CSV is the single source of truth.
   For image batches, eyeball each file first via `contact_sheet.py`: it renders a numbered thumbnail grid (`#N`) plus `order_<tag>.txt` mapping index → real filename. Never put real filenames in the grid — AI mis-reads CJK filenames. Thumbnail reads are screening only: zoom into any doubtful index for a final call.
3. **Execute** — `python execute_plan.py plan.csv <dest> --src-root <folder> --dedup`
   Moves files to `<dest>/<category>/`. Renames on collision with `(1) (2)` suffixes — **never overwrites**. Duplicates (same MD5) are skipped, not deleted. Refuses any path outside `--src-root`.
4. **Undo** — `python undo.py report.txt` (or `--dry-run` first)
   Replays the ledger in reverse. Occupied destinations are skipped, never overwritten.
5. **PDF renaming** (optional) — `python rename_pdf.py <folder>`
   Extracts text from the first pages; falls back to OCR for scans. Rebuilds names like `2024-05-15_购销合同_甲方_乙方_车型.pdf`. Keeps the original name if nothing readable is found.

### Safety design

- **No network** — zero network code in any script; filenames and contents never leave the machine
- **No deletion** — duplicates are skipped, never removed; empty-dir cleanup is a manual step
- **No overwrite** — collisions get `(N)` suffixes, on execute and on undo alike
- **Plan-first** — `scan_plan.py` is strictly read-only; `execute_plan.py` does nothing without a plan you approved
- **Hard boundary** — `--src-root` rejects any source path outside the folder you designated
- **Fully logged** — every move is written to `report.txt`; undo replays it backwards

### Rules format

```json
{
  "Invoices": ["invoice", "PI", "回单"],
  "Contracts": ["contract", "协议", "购销"],
  "Screenshots": ["screenshot", "截图"]
}
```

Array order = priority; first keyword hit wins. See `rules.example.json`. Categories differ per industry — review the plan before executing.

### Install

Core scripts are Python 3 standard library only. PDF renaming needs optional deps:

```bash
pip install -r requirements.txt
```

Tested on Windows 10/11 (mixing `/` and `\` in paths is handled) and should run anywhere Python runs.

### Use as an agent skill

The folder is a drop-in agent skill (`SKILL.md` with `name`/`description` frontmatter). Copy it into your agent's skills directory — e.g. `~/.claude/skills/`, `~/.workbuddy/skills/`, or `.trae/skills/` inside a project — and the agent picks it up when you ask it to organize files.

### Lessons baked in (from sorting 4,000+ real files)

- **Keyword priority matters**: match person names before equipment, product names before function words — otherwise a parameter like "clearing width" drags a tricycle photo into "sweepers".
- **File-name scanning alone is not enough**: do one pass on filenames, one on folder names, then eyeball the stragglers.
- **AI-generated files (hash names) can't be auto-classified** — flag them for manual review instead of forcing a guess.
- **OCR fixes belong in a mapping table** (`OCR_FIXES` in `rename_pdf.py`): scanned Chinese contracts produce predictable misreads (甲方 read as 申方, etc.).
- **Windows**: save scripts with UTF-8 BOM or Chinese filenames garble; filter surrogate pairs from extracted text or `os.rename` crashes.

### License

[MIT](LICENSE)

---

<a id="中文"></a>
## 中文

### 它做什么

把散落的图片 / 视频 / 音频 / PDF 按文件名关键词分类进文件夹，MD5 去重，乱码 PDF 按内容识别改名。为 AI 编程助手（Claude Code、WorkBuddy、Trea 等）设计，纯终端也能用。

### 为什么是它

市面上大部分"文件整理" agent skill 是**纯提示词**：让模型现场发挥敲命令——慢、费 token、不可复现。这个 skill 直接给你三个确定性脚本：

| | 纯提示词 skill | file-organizer |
|---|---|---|
| 分类规则 | 每次现场发挥 | 固定 JSON 规则，可复现 |
| 实际搬文件 | 临时拼 shell 命令 | `execute_plan.py`，逐行记日志 |
| 反悔 | 无 | `undo.py`，任意一次执行可整单撤销 |
| 范围安全 | 祈祷模型守规矩 | `--src-root` 硬边界 |
| 联网 | — | **零联网代码** |

### 工作流

```
scan_plan.py  →  plan.csv  →  人工确认  →  execute_plan.py  →  report.txt
   (只扫描)       (计划书)     (你点头)      (才动手搬)         (流水账)
                                                                  ↓
                                                        undo.py  (照账本倒着撤)
```

1. **扫描**：`python scan_plan.py <文件夹> --out plan.csv --ext png,jpg,pdf,mp4 --rules rules.json [--match-dir]` —— 只出清单，一个文件不动。默认只匹配文件名；加 `--match-dir` 后文件名没命中才用所在目录名兜底，CSV 的 `match_on` 列会标注命中的是「文件名」还是「目录名」，复核时好抓低置信行。
2. **确认**：打开 plan.csv 检查分错的行，改完保存。图片量大时先用 `contact_sheet.py` 出编号拼图逐张过目（黄底 #N 标签 + `order_<tag>.txt` 映射，禁止在图上写真实文件名——AI 会把中文名 OCR 认错）；缩略图存疑的编号必须放大原图再定，不能凭小图下结论
3. **执行**：`python execute_plan.py plan.csv <目标目录> --src-root <源目录> --dedup` —— 重名加 `(1)(2)` 后缀不覆盖；内容相同（MD5）跳过不删；越界路径拒绝
4. **撤销**：`python undo.py report.txt`（可先 `--dry-run` 预览）—— 倒序还原，原位被占跳过
5. **PDF 改名**（可选）：`python rename_pdf.py <文件夹>` —— 文本层优先、OCR 兜底，按内容重建文件名；识别不出就保留原名

### 安全设计（六条）

不联网 · 不删除 · 不覆盖 · 先确认再动手 · `--src-root` 范围硬闸 · 全程留痕可撤销

### 规则文件

```json
{
  "合同": ["购销合同", "协议"],
  "单据": ["发票", "回单", "报价单", "PI"],
  "证件": ["营业执照", "开户"]
}
```

数组顺序即优先级，先命中先得。示例见 `rules.example.json`，类别按你的行业自定。

### 安装

核心脚本只用 Python 标准库。PDF 改名需要可选依赖：

```bash
pip install -r requirements.txt
```

Windows 10/11 实测通过（正反斜杠混用已处理），其他有 Python 的平台理论通用。

### 踩坑经验（来自 4000+ 真实文件整理）

- **关键词要排优先级**：人物词先于设备词、产品名先于功能词——否则"清扫宽度"这种参数词会把三轮车图误分进扫地车
- **只按文件名扫会漏**：文件名扫一轮 + 目录名扫一轮 + 剩余散图逐张看，三轮才收敛
- **AI 生成的 hash 名文件无法自动分类**：标记出来人工看，别硬猜
- **OCR 错别字走映射表**（`rename_pdf.py` 的 `OCR_FIXES`）：扫描合同的错法是可预测的（"甲方"识别成"申方"之类）
- **Windows**：脚本存 UTF-8 带 BOM，否则中文文件名乱码误判；提取文本要过滤代理对字符，否则 `os.rename` 直接崩

### 许可证

[MIT](LICENSE)
