# long-lasting 合规标注工具集

针对亚马逊商品文案中 `long-lasting`（含 `long lasting` / `longlasting` / `Long-Lasting`）
的合规标注，提供「抽取 → 切句 → 标注」流水线与配套提示词。设计上把确定性步骤（抽取/切句）
交给脚本，把主观判断（分类）交给单一职责的 LLM 提示词，避免在一个提示词里同时抽样、造数、打标签。

## 目录

| 文件 | 作用 |
| --- | --- |
| `long_lasting_labeling_prompt.md` | **标注提示词**：判定 `long-lasting` 为正样本/负样本（决策规则 + 真实示例 + 统一 JSON 输出） |
| `long_lasting_augmentation_prompt.md` | **数据增强提示词**：某特征真实样本不足 50 条时按特征生成补充样本，反同质化 |
| `long_lasting_pipeline.py` | **Python 流水线**：`extract`（筛选+切句+去重+按特征采样）与 `label`（调用提示词标注） |

## 标注标准（来自人工标注 120 正 / 2 负）

核心是一条二分规则：

- **正样本**：`long-lasting` 描述**普通商品属性**——材料耐用 / 使用寿命 / 性能、颜色光泽印刷持久、
  香味·扩香·清新持久（不涉及驱虫杀菌）、电池灯光续航、涂层·非粘·耐磨·防水·耐腐蚀·可重复使用、
  保鲜密封、普通吸湿防潮。
- **负样本**：`long-lasting` 与**健康/安全/杀菌/抗菌/防虫/驱虫/防蛀**等功效绑定，例如
  moth/insect/pest repellent、anti-moth、antibacterial、antimicrobial、germ protection、
  harmful germs、kills bacteria 等。

注意：
- 不要仅因为出现 `long-lasting` 就判负。
- `fragrance / scent` 本身不是负样本；只有用于驱虫/防蛀/驱避害虫等功效时才判负。
- 与 germ、bacteria、antibacterial、antimicrobial、moth、repellent、pest、insect 等敏感词绑定时，优先判负。

> 校准验证：`long_lasting_pipeline.py` 内置离线启发式标注器在上述 122 条真实标注上
> **100% 复现人工标签**（含 2 条负样本）。提示词决策规则与该校准一致。

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
负样本（健康/杀菌/抗菌/防虫/驱虫/防蛀功效类）在真实数据中仅 2 条，几乎一定需要增强。

## 输出格式（`long_lasting_LLM抽样生成数据.jsonl`，每行一条）
```json
{"id": "123_0", "text": "...原文片段...", "label": "正样本", "risk_terms": [], "reason": "...", "confidence": 0.94}
```

## 依赖
- 抽取/切句/离线标注：仅标准库。
- 读 Excel：`pandas`、`openpyxl`。
- 调用 LLM：`openai`，并设置 `OPENAI_API_KEY`（可选 `OPENAI_BASE_URL` / `OPENAI_MODEL`）。

## 备注
- 首个上传文件（`long-lasting________78d0.csv`）为 `%TSD-Header-###%` 加密容器，且约 62% 字节被
  UTF-8 替换字符（U+FFFD）破坏，不可恢复；本工具集依据可读的第二个导出（120 正 / 2 负）构建。
