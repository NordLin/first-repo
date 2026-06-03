# long-lasting 合规标注工具集

针对亚马逊商品文案中 `long-lasting`（含 `long lasting` / `longlasting` / `Long-Lasting`）
的合规标注，提供「抽取 → 切句 → 标注」流水线与配套提示词。设计上把确定性步骤（抽取/切句）
交给脚本，把主观判断（分类）交给单一职责的 LLM 提示词，避免在一个提示词里同时抽样、造数、打标签。

## 目录

| 文件 | 作用 |
| --- | --- |
| `long_lasting_labeling_prompt.md` | **标注提示词**：判定 `long-lasting` 为正样本/负样本（决策树 + 真实示例 + 统一 JSON 输出） |
| `long_lasting_augmentation_prompt.md` | **数据增强提示词**：某特征真实样本不足 50 条时按特征生成补充样本，反同质化 |
| `long_lasting_pipeline.py` | **Python 流水线**：`extract`（筛选+切句+去重+按特征采样）与 `label`（调用提示词标注） |

## 标注标准要点（来自真实人工标注 120 正 / 2 负）

`long-lasting` 默认**偏宽松**。判定核心是：`long-lasting` 是否落在**物理耐用性 / 使用寿命 /
性能 / 外观·颜色·香味·光照保持**上，且是否有“耐用性实质支撑”（材料 / 规格数字 / 客观耐用属性）。

- **正样本**：落点为耐用性，有材料/规格/属性支撑；即便带 `extremely durable`、`best choice`、
  `quality guarantee`、`provide long-lasting durability` 等措辞也判正；较泛的
  `ensures long-lasting use/performance` 在无其它风险时也判正。
- **负样本**：① 功效/健康/防护声明（germ protection、antibacterial…）；② 品牌/商家承诺/服务作为主体
  （long-lasting brand、we provide long-lasting products、long-lasting service/warranty）；
  ③ 平台敏感/售后绑定（contact us、refund、review、coupon、discount…）；
  ④ 无实质支撑的纯主观夸大（`A very rich, long-lasting moth repellent kit`）。

> 校准验证：`long_lasting_pipeline.py` 内置的离线启发式标注器在上述 122 条真实标注上
> **100% 复现人工标签**（含 2 条负样本）。提示词的决策树与该校准保持一致。

## 使用方法

### 1. 抽取 + 切句（确定性，无需 API）
从原始数据中筛选「合并接口禁售词」含 `long-lasting` 的记录，按标点把「ListingV2原文」切成
“每段最多一个关键词”的片段，去重并按特征采样：

```bash
python long_lasting/long_lasting_pipeline.py extract \
  --input docs/01.原始数据/your_data.xlsx \
  --output long_lasting_samples.jsonl \
  --banned-col 合并接口禁售词 \
  --text-col ListingV2原文 \
  --per-feature 50
```

- 支持 `.csv` / `.tsv` / `.xlsx`（读 Excel 需 `pip install pandas openpyxl`）。
- `--per-feature 50`：每个特征最多采样 50 条；不足会打印提示，建议用增强提示词补足。
- 列名与默认不同时用 `--banned-col` / `--text-col` / `--id-col` 覆盖。

### 2. 标注
```bash
# A) 调用 LLM（推荐，最终标准）
export OPENAI_API_KEY=sk-xxx
# 可选: export OPENAI_BASE_URL=...   export OPENAI_MODEL=gpt-4o-mini
python long_lasting/long_lasting_pipeline.py label \
  --input long_lasting_samples.jsonl \
  --output long_lasting_LLM抽样生成数据.jsonl \
  --model gpt-4o-mini

# B) 离线启发式（无 API 时试跑/自检，结果仍需复核）
python long_lasting/long_lasting_pipeline.py label \
  --input long_lasting_samples.jsonl \
  --output long_lasting_LLM抽样生成数据.jsonl \
  --offline
```

调用 LLM 时，脚本会把 `long_lasting_labeling_prompt.md` 作为 system prompt，分批送入记录并解析返回的 JSON 数组。

### 3. 数据增强（可选）
当某特征真实样本不足 50 条时，用 `long_lasting_augmentation_prompt.md` 让 LLM 生成补充样本
（`id` 用 `aug_` 前缀），再合并进 `long_lasting_samples.jsonl` 一起走第 2 步标注。

## 输出格式（`long_lasting_LLM抽样生成数据.jsonl`，每行一条）
```json
{"id": "123_0", "text": "...原文片段...", "label": "正样本", "risk_terms": [], "reason": "...", "confidence": 0.95}
```

## 依赖
- 抽取/切句/离线标注：仅标准库。
- 读 Excel：`pandas`、`openpyxl`。
- 调用 LLM：`openai`，并设置 `OPENAI_API_KEY`（可选 `OPENAI_BASE_URL` / `OPENAI_MODEL`）。

## 备注
- 首个上传文件（`long-lasting________78d0.csv`）为 `%TSD-Header-###%` 加密容器，且约 62% 字节被
  UTF-8 替换字符（U+FFFD）破坏，不可恢复；本工具集依据可读的第二个导出（120 正 / 2 负）构建。
- 负样本在真实数据中极少（仅 2 条），品牌/服务承诺、平台敏感绑定、最高级绝对化等负样本子类
  几乎都需要靠增强提示词补足，且务必反同质化。
