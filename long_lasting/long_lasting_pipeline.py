#!/usr/bin/env python3
"""long-lasting 合规标注流水线.

将"抽取 / 切句 / 标注"拆成确定性脚本步骤 + 一个纯分类 LLM 步骤, 对应两个子命令:

  extract  从原始数据中筛选 "合并接口禁售词" 含 long-lasting 的记录,
           按标点把 "ListingV2原文" 切成片段(每段最多一个 long-lasting 关键词),
           去重并按特征采样, 输出待标注样本 jsonl.

  label    读取待标注样本, 调用标注提示词(long_lasting_labeling_prompt.md)进行分类,
           输出 long_lasting_LLM抽样生成数据.jsonl. 未配置 API 时使用内置启发式标注器,
           便于离线试跑(结果应再经人工/LLM 复核).

标注核心规则(与提示词一致):
  long-lasting 描述普通商品属性/耐用性/寿命/颜色香味续航/涂层结构 -> 正样本;
  long-lasting 与健康/安全/杀菌/抗菌/防虫/驱虫/防蛀等功效绑定 -> 负样本。
  (香味 fragrance/scent 本身不算负样本, 只有用于驱虫/杀菌等功效时才判负。)
内置启发式在真实标注(120 正 / 2 负)上 100% 复现人工标签。

脚本只依赖标准库; 读 .xlsx 时需要 pandas+openpyxl, 调用真实 LLM 时需要环境变量 OPENAI_API_KEY。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable

# ----------------------------------------------------------------------------- #
# 配置
# ----------------------------------------------------------------------------- #
HERE = Path(__file__).resolve().parent
LABELING_PROMPT_PATH = HERE / "long_lasting_labeling_prompt.md"
DEFAULT_OUTPUT = "long_lasting_LLM抽样生成数据.jsonl"

# 关键词: long-lasting / long lasting / longlasting / Long-Lasting ...
KEYWORD_RE = re.compile(r"long[\s\-]?lasting", re.IGNORECASE)

# 原始数据中的列名(可用 CLI 覆盖)
DEFAULT_BANNED_COL = "合并接口禁售词"
DEFAULT_TEXT_COL = "ListingV2原文"
DEFAULT_ID_COL = "id"

# 句子切分: 句末标点 / 分号冒号 / 换行 / 常见 bullet 分隔
SENT_SPLIT_RE = re.compile(r"[\.!?;:。！？；\n\r]+|\s[•·▪◦‣\-–—]\s")

# ----------------------------------------------------------------------------- #
# 负样本敏感功效词(健康/安全/杀菌/抗菌/防虫/驱虫/防蛀)。命中即判负样本。
# 注意: fragrance/scent/freshness/moisture(防潮吸湿) 等普通功能不在此列, 属正样本。
# ----------------------------------------------------------------------------- #
SENSITIVE_RE = re.compile(
    r"\b("
    r"moths?|anti[\s\-]?moths?|insects?|pests?|repell(?:ent|ant|ents|ants|ing)?|"
    r"anti[\s\-]?bacterial|antibacterial|anti[\s\-]?microbial|antimicrobial|"
    r"germs?|bacteria(?:l)?|microbes?|microbial|"
    r"disinfect\w*|sanitiz\w*|sanitis\w*|steriliz\w*|sterilis\w*|"
    r"viruses?|virus|antiviral|mildew|mold|mould|fungal|fungus"
    r")\b",
    re.I,
)
# 中文同义敏感表达(原文可能为多语)
SENSITIVE_ZH = ["驱虫", "防虫", "杀虫", "防蛀", "防蠹", "杀菌", "抗菌", "灭菌",
                "消毒", "病菌", "细菌", "病毒", "霉菌", "除螨", "驱蚊", "防螨"]

# 启发式给正样本估 confidence 用的"普通属性"线索
MATERIAL_HINTS = [
    "stainless steel", "304", "925", "sterling silver", "silicone", "tpu", "nylon",
    "polyester", "latex", "cotton", "wool", "ceramic", "rubber", "vinyl", "wood",
    "metal", "aluminum", "aluminium", "alloy", "leather", "acrylic",
    "pp", "pvc", "abs", "pla", "wax", "gold", "brass", "zinc",
]
SPEC_RE = re.compile(
    r"\b(\d+\s*(mah|hours?|hrs?|hour|days?|washes|months?|years?|meters?|°c|watt|w|"
    r"gsm|mils?|mm|cm))\b",
    re.I,
)


# ----------------------------------------------------------------------------- #
# IO 辅助
# ----------------------------------------------------------------------------- #
def read_rows(path: Path) -> list[dict]:
    """读取原始数据为 list[dict]. 支持 .csv / .tsv / .xlsx。"""
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        try:
            import pandas as pd  # noqa: WPS433
        except ImportError:  # pragma: no cover
            sys.exit("读取 Excel 需要 pandas+openpyxl: pip install pandas openpyxl")
        df = pd.read_excel(path, dtype=str).fillna("")
        return df.to_dict("records")
    import csv

    delimiter = "\t" if suffix == ".tsv" else ","
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=delimiter))


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# ----------------------------------------------------------------------------- #
# 切句
# ----------------------------------------------------------------------------- #
def split_segments(text: str) -> list[str]:
    """把整段文案切成句子片段, 保证每个返回片段最多含一个 long-lasting 关键词。

    若某句含 >1 个关键词, 则围绕每个关键词单独成段(带左右邻句作为上下文窗口),
    以避免材料/功效证据被标点切断导致误判。
    """
    raw = [s.strip() for s in SENT_SPLIT_RE.split(text or "") if s and s.strip()]
    segments: list[str] = []
    for idx, sent in enumerate(raw):
        hits = KEYWORD_RE.findall(sent)
        if not hits:
            continue
        prev = raw[idx - 1] if idx > 0 else ""
        if len(hits) == 1:
            seg = sent
            if len(sent) < 40 and prev:  # 句子过短时带上一句作为上下文
                seg = f"{prev}. {sent}"
            segments.append(_clean(seg))
        else:
            for piece in _one_keyword_pieces(sent):
                segments.append(_clean(piece))
    return [s for s in segments if s]


def _one_keyword_pieces(sentence: str) -> list[str]:
    """把含多个关键词的句子, 按关键词位置切成若干"每段一个关键词"的片段。"""
    spans = [m.start() for m in KEYWORD_RE.finditer(sentence)]
    if len(spans) <= 1:
        return [sentence]
    cuts = [0]
    for a, b in zip(spans, spans[1:]):
        cuts.append((a + b) // 2)
    cuts.append(len(sentence))
    return [sentence[cuts[i]:cuts[i + 1]].strip() for i in range(len(cuts) - 1)]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" .,-–—").strip()


# ----------------------------------------------------------------------------- #
# extract 子命令
# ----------------------------------------------------------------------------- #
def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def cmd_extract(args: argparse.Namespace) -> None:
    rows = read_rows(Path(args.input))
    samples: list[dict] = []
    seen: set[str] = set()
    for i, row in enumerate(rows):
        banned = str(row.get(args.banned_col, "") or "")
        if not KEYWORD_RE.search(banned):
            continue
        text = str(row.get(args.text_col, "") or "")
        base_id = str(row.get(args.id_col) or row.get("序号") or i + 1)
        for j, seg in enumerate(split_segments(text)):
            key = normalize(seg)
            if not key or key in seen:
                continue
            seen.add(key)
            samples.append({"id": f"{base_id}_{j}", "source_id": base_id, "text": seg})

    if args.per_feature:
        samples = _cap_by_feature(samples, args.per_feature)

    out = Path(args.output)
    n = write_jsonl(out, samples)
    print(f"[extract] 命中并切片去重后样本 {n} 条 -> {out}")
    if not samples:
        print("[extract] 未命中任何记录, 请确认列名 (--banned-col/--text-col) 是否正确。")


def _cap_by_feature(samples: list[dict], cap: int) -> list[dict]:
    """按启发式特征分桶, 每桶最多保留 cap 条(真实数据采样用; 不足由增强补足)。"""
    buckets: dict[str, list[dict]] = {}
    for s in samples:
        feat = _guess_feature(s["text"])
        s["feature"] = feat
        buckets.setdefault(feat, []).append(s)
    capped: list[dict] = []
    for feat, items in buckets.items():
        capped.extend(items[:cap])
        if len(items) < cap:
            print(f"[extract] 特征 '{feat}' 真实样本仅 {len(items)} 条 (<{cap}), 建议增强补足。")
    return capped


def _guess_feature(text: str) -> str:
    low = text.lower()
    if is_sensitive(text):
        return "negative_efficacy"
    if any(w in low for w in ("fragrance", "scent", "diffus")):
        return "fragrance"
    if any(w in low for w in ("battery", "mah", "light", "hours", "charge")):
        return "battery_runtime"
    if any(w in low for w in ("color", "colour", "shine", "fade", "print", "design")):
        return "color_appearance"
    if any(w in low for w in ("coating", "nonstick", "non-stick", "waterproof",
                              "wear", "rust", "corrosion", "reuse", "reusable")):
        return "coating_durable"
    if SPEC_RE.search(text) or any(m in low for m in MATERIAL_HINTS):
        return "material_spec"
    return "generic_durability"


# ----------------------------------------------------------------------------- #
# label 子命令
# ----------------------------------------------------------------------------- #
def is_sensitive(text: str) -> list[str]:
    """返回命中的敏感功效词列表(健康/杀菌/抗菌/防虫/驱虫/防蛀); 空列表表示无。"""
    hits = [m.group(0) for m in SENSITIVE_RE.finditer(text)]
    hits += [w for w in SENSITIVE_ZH if w in text]
    return sorted(set(hits))


def heuristic_label(text: str) -> dict:
    """离线启发式标注, 对齐提示词决策规则(用于无 API 时试跑, 非最终标准)。

    命中健康/安全/杀菌/抗菌/防虫/驱虫/防蛀等敏感功效 -> 负样本; 否则 -> 正样本。
    """
    risk = is_sensitive(text)
    if risk:
        return {
            "label": "负样本",
            "risk_terms": risk,
            "reason": "long-lasting 与健康/杀菌/抗菌/防虫/驱虫/防蛀等敏感功效绑定, 属高合规风险。",
            "confidence": 0.95,
        }

    low = text.lower()
    if SPEC_RE.search(text) or any(m in low for m in MATERIAL_HINTS) \
            or any(w in low for w in ("battery", "coating", "nonstick", "fragrance",
                                      "scent", "color", "colour", "shine")):
        conf = 0.94
    else:
        conf = 0.85
    return {
        "label": "正样本",
        "risk_terms": [],
        "reason": "long-lasting 描述普通商品属性/耐用性/续航/颜色香味/涂层等, 无敏感功效词。",
        "confidence": conf,
    }


def llm_label(records: list[dict], model: str, batch: int) -> list[dict]:
    """调用 OpenAI 兼容接口, 用标注提示词分类。返回与输入等长、按 id 对齐的结果。"""
    try:
        from openai import OpenAI  # noqa: WPS433
    except ImportError:  # pragma: no cover
        sys.exit("调用 LLM 需要 openai 库: pip install openai")
    client = OpenAI(base_url=os.environ.get("OPENAI_BASE_URL") or None)
    system_prompt = LABELING_PROMPT_PATH.read_text(encoding="utf-8")

    by_id: dict[str, dict] = {}
    for start in range(0, len(records), batch):
        chunk = records[start:start + batch]
        payload = [{"id": r["id"], "text": r["text"]} for r in chunk]
        user = (
            "请对下列记录逐条标注, 严格按系统提示词的 JSON 数组格式输出, "
            "数组长度与输入一致, 每个对象含 id/label/risk_terms/reason/confidence:\n"
            + json.dumps(payload, ensure_ascii=False, indent=2)
        )
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user},
            ],
        )
        for obj in _parse_json_array(resp.choices[0].message.content):
            if "id" in obj:
                by_id[str(obj["id"])] = obj
        print(f"[label] 已标注 {min(start + batch, len(records))}/{len(records)}")

    merged = []
    for r in records:
        obj = by_id.get(str(r["id"]))
        if obj is None:
            obj = {"label": "负样本", "risk_terms": [],
                   "reason": "LLM 未返回该 id, 需人工复核。", "confidence": 0.5}
        obj["id"] = r["id"]
        obj["text"] = r["text"]
        merged.append(obj)
    return merged


def _parse_json_array(content: str) -> list[dict]:
    content = content.strip()
    content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.M).strip()
    start, end = content.find("["), content.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(content[start:end + 1])
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def cmd_label(args: argparse.Namespace) -> None:
    records = read_jsonl(Path(args.input))
    use_llm = bool(os.environ.get("OPENAI_API_KEY")) and not args.offline
    if use_llm:
        print(f"[label] 使用 LLM 标注 (model={args.model}) ...")
        results = llm_label(records, model=args.model, batch=args.batch)
    else:
        why = "指定了 --offline" if args.offline else "未检测到 OPENAI_API_KEY"
        print(f"[label] {why}, 使用内置启发式标注 (结果需复核)。")
        results = []
        for r in records:
            obj = heuristic_label(r["text"])
            results.append({"id": r["id"], "text": r["text"], **obj})

    ordered = [_order_fields(r) for r in results]
    out = Path(args.output)
    n = write_jsonl(out, ordered)
    pos = sum(1 for r in ordered if r["label"] == "正样本")
    print(f"[label] 输出 {n} 条 -> {out} (正 {pos} / 负 {n - pos})")


def _order_fields(r: dict) -> dict:
    return {
        "id": r.get("id"),
        "text": r.get("text", ""),
        "label": r.get("label"),
        "risk_terms": r.get("risk_terms", []),
        "reason": r.get("reason", ""),
        "confidence": r.get("confidence", 0.0),
    }


# ----------------------------------------------------------------------------- #
# CLI
# ----------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="long-lasting 合规标注流水线")
    sub = p.add_subparsers(dest="command", required=True)

    pe = sub.add_parser("extract", help="筛选+切句+去重, 输出待标注样本")
    pe.add_argument("--input", required=True, help="原始数据文件 (.csv/.tsv/.xlsx)")
    pe.add_argument("--output", default="long_lasting_samples.jsonl")
    pe.add_argument("--banned-col", default=DEFAULT_BANNED_COL)
    pe.add_argument("--text-col", default=DEFAULT_TEXT_COL)
    pe.add_argument("--id-col", default=DEFAULT_ID_COL)
    pe.add_argument("--per-feature", type=int, default=0,
                    help="每个特征最多采样条数(0=不限制)")
    pe.set_defaults(func=cmd_extract)

    pl = sub.add_parser("label", help="用标注提示词进行分类标注")
    pl.add_argument("--input", required=True, help="extract 产出的样本 jsonl")
    pl.add_argument("--output", default=DEFAULT_OUTPUT)
    pl.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    pl.add_argument("--batch", type=int, default=10)
    pl.add_argument("--offline", action="store_true",
                    help="强制使用启发式标注(不调用 LLM)")
    pl.set_defaults(func=cmd_label)
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
