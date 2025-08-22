#!/usr/bin/env python3
import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

SUPPORTED_EXTS = {".txt", ".log", ".md", ".csv", ".json"}

BASIC_STOPWORDS = {
    "the","a","an","and","or","but","if","then","else","when","at","by","for","in",
    "of","on","to","with","is","it","as","that","this","these","those","are","be",
    "was","were","from","so","we","you","he","she","they","them","his","her","our",
    "your","their","i","me","my","mine","us","will","not","no","yes"
}

def discover_files(inputs, recursive=False):
    files = []
    for raw in inputs:
        p = Path(raw)
        if p.is_file():
            if p.suffix.lower() in SUPPORTED_EXTS:
                files.append(p)
        elif p.is_dir():
            if recursive:
                for ext in SUPPORTED_EXTS:
                    files.extend(p.rglob(f"*{ext}"))
            else:
                for ext in SUPPORTED_EXTS:
                    files.extend(p.glob(f"*{ext}"))
        else:
            print(f"[WARN] Skipping non-existent path: {p}")
    # De-duplicate while preserving order
    seen = set()
    unique = []
    for f in files:
        if f.resolve() not in seen:
            seen.add(f.resolve())
            unique.append(f)
    return unique

# ---------- TEXT ----------
WORD_RE = re.compile(r"\b[\w']+\b", re.UNICODE)

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def analyze_text(content: str, top_n: int = 10, use_stopwords: bool = False):
    lines = content.splitlines()
    chars = len(content)
    words = [w.lower() for w in WORD_RE.findall(content)]
    if use_stopwords:
        words = [w for w in words if w not in BASIC_STOPWORDS]
    word_count = len(words)
    unique_words = len(set(words))
    avg_word_len = (sum(len(w) for w in words) / word_count) if word_count else 0.0
    longest_line_len = max((len(line) for line in lines), default=0)
    freqs = Counter(words).most_common(top_n)

    return {
        "type": "text",
        "lines": len(lines),
        "characters": chars,
        "words": word_count,
        "unique_words": unique_words,
        "avg_word_length": round(avg_word_len, 2),
        "longest_line_length": longest_line_len,
        "top_words": [{"word": w, "count": c} for w, c in freqs],
    }

# ---------- CSV ----------
def try_parse_float(x):
    try:
        if x is None:
            return None
        s = str(x).strip()
        if not s:
            return None
        return float(s)
    except Exception:
        return None

def analyze_csv(path: Path):
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        row_count = 0

        col_missing = defaultdict(int)
        col_values_numeric = defaultdict(list)  # floats
        col_values_categorical = defaultdict(list)  # strings (raw)
        col_attempts = defaultdict(int)
        col_numeric_hits = defaultdict(int)

        for row in reader:
            row_count += 1
            for h in headers:
                val = row.get(h)
                if val is None or str(val).strip() == "":
                    col_missing[h] += 1
                    continue
                col_attempts[h] += 1
                num = try_parse_float(val)
                if num is not None and math.isfinite(num):
                    col_numeric_hits[h] += 1
                    col_values_numeric[h].append(num)
                else:
                    col_values_categorical[h].append(str(val).strip())

        column_summaries = []
        for h in headers:
            attempts = col_attempts[h]
            numeric_hits = col_numeric_hits[h]
            # consider numeric if >= 80% of non-missing values are numeric
            is_numeric = (attempts > 0 and numeric_hits / attempts >= 0.8)

            if is_numeric and col_values_numeric[h]:
                vals = col_values_numeric[h]
                col_summary = {
                    "name": h,
                    "type": "numeric",
                    "missing": col_missing[h],
                    "count": len(vals),
                    "min": min(vals),
                    "max": max(vals),
                    "mean": round(mean(vals), 4),
                    "median": round(median(vals), 4),
                }
            else:
                vals = col_values_categorical[h]
                top = Counter(vals).most_common(5)
                col_summary = {
                    "name": h,
                    "type": "categorical",
                    "missing": col_missing[h],
                    "count": attempts,
                    "top_values": [{"value": v, "count": c} for v, c in top],
                }
            column_summaries.append(col_summary)

        return {
            "type": "csv",
            "rows": row_count,
            "columns": len(headers),
            "headers": headers,
            "columns_detail": column_summaries
        }

# ---------- JSON ----------
def analyze_json(path: Path):
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)

    # list of dicts => treat like a table
    if isinstance(data, list) and (len(data) == 0 or isinstance(data[0], dict)):
        # build rows like CSV
        headers = set()
        for item in data:
            if isinstance(item, dict):
                headers.update(item.keys())
        headers = list(headers)
        # simulate CSV-like analysis
        row_count = len(data)

        col_missing = defaultdict(int)
        col_values_numeric = defaultdict(list)
        col_values_categorical = defaultdict(list)
        col_attempts = defaultdict(int)
        col_numeric_hits = defaultdict(int)

        for item in data:
            if not isinstance(item, dict):
                continue
            for h in headers:
                val = item.get(h)
                if val is None or str(val).strip() == "":
                    col_missing[h] += 1
                else:
                    col_attempts[h] += 1
                    num = try_parse_float(val)
                    if num is not None and math.isfinite(num):
                        col_numeric_hits[h] += 1
                        col_values_numeric[h].append(num)
                    else:
                        col_values_categorical[h].append(str(val).strip())

        column_summaries = []
        for h in headers:
            attempts = col_attempts[h]
            numeric_hits = col_numeric_hits[h]
            is_numeric = (attempts > 0 and numeric_hits / attempts >= 0.8)

            if is_numeric and col_values_numeric[h]:
                vals = col_values_numeric[h]
                col_summary = {
                    "name": h,
                    "type": "numeric",
                    "missing": col_missing[h],
                    "count": len(vals),
                    "min": min(vals),
                    "max": max(vals),
                    "mean": round(mean(vals), 4),
                    "median": round(median(vals), 4),
                }
            else:
                vals = col_values_categorical[h]
                top = Counter(vals).most_common(5)
                col_summary = {
                    "name": h,
                    "type": "categorical",
                    "missing": col_missing[h],
                    "count": attempts,
                    "top_values": [{"value": v, "count": c} for v, c in top],
                }
            column_summaries.append(col_summary)

        return {
            "type": "json_table",
            "rows": row_count,
            "columns": len(headers),
            "headers": headers,
            "columns_detail": column_summaries
        }

    # dict (object) => structure summary
    if isinstance(data, dict):
        summary = {}
        for k, v in data.items():
            t = type(v).__name__
            extra = {}
            if isinstance(v, list):
                extra["length"] = len(v)
                if v and not isinstance(v[0], (dict, list)):
                    # show sample primitives
                    extra["sample"] = v[:5]
            elif isinstance(v, dict):
                extra["keys"] = list(v.keys())[:10]
            summary[k] = {"type": t, **extra}
        return {"type": "json_object", "keys": summary}

    # list of primitives
    if isinstance(data, list):
        sample = data[:10]
        types = sorted({type(x).__name__ for x in data[:100]})
        return {"type": "json_list", "length": len(data), "element_types_sample": types, "sample": sample}

    # fallback
    return {"type": "json_other", "python_type": type(data).__name__}

# ---------- REPORTING ----------
def to_markdown(path: Path, analysis: dict, top_n: int):
    title = f"# File Report: {path.name}\n\n"
    base = f"- **Location**: `{path.resolve()}`\n- **Type**: `{analysis.get('type')}`\n\n"

    if analysis["type"] == "text":
        lines = [
            "## Summary\n",
            f"- Lines: **{analysis['lines']}**",
            f"- Characters: **{analysis['characters']}**",
            f"- Words: **{analysis['words']}**",
            f"- Unique Words: **{analysis['unique_words']}**",
            f"- Avg Word Length: **{analysis['avg_word_length']}**",
            f"- Longest Line Length: **{analysis['longest_line_length']}**",
            "\n## Top Words\n",
            "| Rank | Word | Count |",
            "|---:|---|---:|",
        ]
        for i, item in enumerate(analysis["top_words"], start=1):
            lines.append(f"| {i} | {item['word']} | {item['count']} |")
        return title + base + "\n".join(lines) + "\n"

    if analysis["type"] in ("csv", "json_table"):
        lines = [
            "## Summary\n",
            f"- Rows: **{analysis['rows']}**",
            f"- Columns: **{analysis['columns']}**",
            f"- Headers: `{', '.join(analysis['headers'])}`",
            "\n## Column Details\n",
        ]
        for col in analysis["columns_detail"]:
            if col["type"] == "numeric":
                lines += [
                    f"### {col['name']} *(numeric)*",
                    f"- Missing: **{col['missing']}**",
                    f"- Count: **{col['count']}**",
                    f"- Min: **{col['min']}** | Max: **{col['max']}**",
                    f"- Mean: **{col['mean']}** | Median: **{col['median']}**",
                    ""
                ]
            else:
                lines += [
                    f"### {col['name']} *(categorical)*",
                    f"- Missing: **{col['missing']}**",
                    f"- Observed: **{col['count']}**",
                    "",
                    "| Rank | Value | Count |",
                    "|---:|---|---:|",
                ]
                for i, item in enumerate(col.get("top_values", []), start=1):
                    lines.append(f"| {i} | {item['value']} | {item['count']} |")
                lines.append("")
        return title + base + "\n".join(lines)

    if analysis["type"] == "json_object":
        lines = ["## JSON Object Keys\n"]
        for k, v in analysis["keys"].items():
            line = f"- `{k}` → **{v['type']}**"
            if "length" in v:
                line += f" (length: {v['length']})"
            if "keys" in v:
                line += f" (keys: {', '.join(v['keys'])})"
            if "sample" in v:
                line += f" (sample: {v['sample']})"
            lines.append(line)
        return title + base + "\n".join(lines) + "\n"

    if analysis["type"] == "json_list":
        lines = [
            "## JSON List\n",
            f"- Length: **{analysis['length']}**",
            f"- Element types (sample): `{', '.join(analysis['element_types_sample'])}`",
            f"- Sample (up to 10): `{analysis['sample']}`",
        ]
        return title + base + "\n".join(lines) + "\n"

    return title + base + "_No markdown formatter for this type yet._\n"

# ---------- MAIN ----------
def analyze_file(path: Path, top_n: int, stopwords: bool):
    ext = path.suffix.lower()
    if ext in {".txt", ".log", ".md"}:
        content = read_text(path)
        return analyze_text(content, top_n=top_n, use_stopwords=stopwords)
    elif ext == ".csv":
        return analyze_csv(path)
    elif ext == ".json":
        return analyze_json(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def main():
    parser = argparse.ArgumentParser(description="File Reader & Analyzer (Text/CSV/JSON)")
    parser.add_argument("inputs", nargs="+", help="Files or folders to analyze")
    parser.add_argument("-r","--recursive", action="store_true", help="Recurse into subfolders")
    parser.add_argument("--top", type=int, default=10, help="Top N words (text)")
    parser.add_argument("--format", choices=["md","json"], default="md", help="Report format")
    parser.add_argument("-o","--out", default="reports", help="Output directory for reports")
    parser.add_argument("--stopwords", action="store_true", help="Ignore common words in text analysis")
    args = parser.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    files = discover_files(args.inputs, recursive=args.recursive)
    if not files:
        print("No supported files found.")
        return

    for file in files:
        try:
            analysis = analyze_file(file, top_n=args.top, stopwords=args.stopwords)
            if args.format == "md":
                report = to_markdown(file, analysis, top_n=args.top)
                out_path = outdir / f"report_{file.stem}.md"
                out_path.write_text(report, encoding="utf-8")
                print(f"[OK] {file.name} → {out_path}")
            else:
                out_path = outdir / f"report_{file.stem}.json"
                with out_path.open("w", encoding="utf-8") as f:
                    json.dump({
                        "file": str(file.resolve()),
                        "analysis": analysis
                    }, f, ensure_ascii=False, indent=2)
                print(f"[OK] {file.name} → {out_path}")
        except Exception as e:
            print(f"[ERR] {file} → {e}")

if __name__ == "__main__":
    main()
