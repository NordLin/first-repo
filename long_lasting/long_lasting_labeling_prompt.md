# long-lasting 合规标注提示词（标注阶段）

> 用途：对已切片好的英文（或多语）商品文案片段，判断其中 `long-lasting`（含 `long lasting`、
> `longlasting`、`Long-Lasting` 写法）的使用属于“正样本”还是“负样本”。本提示词只做**分类**，
> 不做数据抽取与增强（抽取/切句由脚本完成，增强见 `long_lasting_augmentation_prompt.md`）。
>
> 核心判据：`long-lasting` 是在描述**普通商品属性 / 耐用性 / 寿命 / 颜色香味续航 / 涂层结构**（正样本），
> 还是与**健康、安全、杀菌、抗菌、防虫、驱虫、防蛀**等功效绑定（负样本）。
> 真实人工标注（120 正 / 2 负）上，该规则 100% 复现人工标签。

---

## 任务目标

识别商品文案中 `long-lasting` 的使用是否属于可接受的普通商品属性/耐用性描述（正样本），
还是与健康/安全/杀菌/抗菌/防虫/驱虫/防蛀等功效绑定的高合规风险表达（负样本）。

---

## 标签定义

### 1. 正样本（风险较低）
表示 `long-lasting` 的使用风险较低，通常是在描述普通商品属性、材料耐用性、使用寿命、颜色保持、香味保持、电池续航、涂层耐用、重复使用、结构稳定等。

常见正样本特征包括：
- **描述材料耐用、长期使用**：
  long-lasting durability、long-lasting use、long-lasting performance、long-lasting strength、long-lasting reliability
- **描述颜色、光泽、图案、印刷效果持久**：
  long-lasting shine、long-lasting color、long-lasting beauty、designs that won't fade over time
- **描述香味、扩香、清新效果持久，但不涉及驱虫、杀菌、治疗**：
  long-lasting scents、long-lasting fragrance、continuous diffusion
- **描述电池、灯光、续航、容量**：
  long-lasting battery、long-lasting light、last up to 8 hours
- **描述涂层、非粘锅、耐磨、防水、耐腐蚀、可重复使用**：
  long-lasting nonstick coating、long-lasting reuse、resists rust and corrosion、wear-resistant
- **描述普通保存或密封效果**：
  long-lasting freshness、airtight seal
- **描述普通吸湿、防潮、干燥环境**：
  prolonged protection against dampness、absorb moisture

### 2. 负样本（合规风险较高）
表示 `long-lasting` 的使用存在较高合规风险，通常与健康、安全、杀菌、抗菌、防虫、驱虫、防蛀等功效绑定。

常见负样本风险包括：
- **与驱虫、防蛀、杀虫、驱避害虫相关**：
  moth repellent、insect repellent、pest repellent、anti-moth、repellent kit
- **与抗菌、杀菌、细菌防护、病菌防护相关**：
  antibacterial defense、germ protection、harmful germs、kills bacteria、antimicrobial protection
- **宣称长效保护人体健康、安全或免受细菌/害虫侵害**：
  long-lasting germ protection、long-lasting antibacterial defense

---

## 判定流程（请严格按优先级执行）

1. **敏感功效扫描（命中即判负，一票否决）**：文案中是否出现与健康/安全/杀菌/防虫绑定的敏感词——
   moth(s)、anti-moth、insect、pest、repellent/repellant、antibacterial、antimicrobial、
   germ(s)、bacteria(l)、microbe/microbial、disinfect、sanitize、sterilize、virus/antiviral、
   mildew/mold/fungal（以及驱虫/防蛀/杀菌/抗菌/病菌等中文同义表达）。
   → 命中任一 → **负样本**。

2. **否则判正**：若 `long-lasting` 只是在描述普通耐用性、性能、颜色、光泽、香味/扩香、续航、
   涂层、结构、重复使用、保鲜密封、吸湿防潮等 → **正样本**。

> 注意：
> - 不要仅因为出现 `long-lasting` 就标为负样本。
> - 如果 `long-lasting` 描述普通耐用性、性能、颜色、香味、续航、涂层、结构、重复使用，通常标为正样本。
> - 如果 `long-lasting` 与 germ、bacteria、antibacterial、antimicrobial、moth、repellent、pest、insect 等敏感词绑定，应优先标为负样本。
> - `fragrance / scent` 本身不一定是负样本；只有当香味用于驱虫、防蛀、驱避害虫等功效时，才倾向负样本。
> - 必须严格输出人工标注标签：“正样本”或“负样本”。

---

## confidence 锚定标准
- 明确普通属性（材料/续航/涂层/颜色/香味等），无敏感词：**0.90–0.98**
- 较泛但落点为普通耐用性，无敏感词：**0.82–0.90**
- 明确命中驱虫/杀菌/抗菌等敏感功效：**0.90–0.98**
- 模棱两可、上下文被切断：**0.60–0.80**

## risk_terms 抽取规则
- 抽取**触发判负的最小完整短语**（如 `moth repellent`、`Long-Lasting Germ Protection`、`antibacterial defense`、`harmful germs`）。
- 正样本输出空数组 `[]`。

---

## 输出格式（唯一标准，必须是 JSON 数组）

对输入的每条记录输出一个对象，字段顺序与示例一致：

```json
[
  {
    "id": "原始 id",
    "label": "正样本/负样本",
    "risk_terms": ["命中的风险词或短语；无风险则为空数组"],
    "reason": "简要说明判断理由",
    "confidence": 0.0
  }
]
```

只输出 JSON 数组，不要输出任何额外解释。

---

## 人工标注示例（均取自真实标注数据）

示例 1（正，材料耐用）
文本：[Material] -- They are easy to put on and loose and they are made of stainless steel for long lasting durability
输出：{"label": "正样本", "risk_terms": [], "reason": "long-lasting 描述 stainless steel 材料耐用性，无敏感功效词。", "confidence": 0.95}

示例 2（正，电池续航）
文本：RECHARGEABLE & LONG LASTING: Built-in 1200mAh lithium battery, This camping head light has can be last up to 8 hours after full charge
输出：{"label": "正样本", "risk_terms": [], "reason": "long-lasting 描述电池续航（1200mAh、8 小时），属普通规格。", "confidence": 0.96}

示例 3（正，颜色/印刷持久）
文本：Vibrant colors: Using UV printing technology, our signs have clear and longlasting designs with vivid and vibrant colors that wont fade over time
输出：{"label": "正样本", "risk_terms": [], "reason": "long-lasting 描述颜色/印刷效果持久（won't fade），无敏感词。", "confidence": 0.94}

示例 4（正，香味持久，未涉及驱虫/杀菌）
文本：Long lasting fragrance for months, Quality Craftmanship Reeds Work With most of the Oil Mix
输出：{"label": "正样本", "risk_terms": [], "reason": "long-lasting 描述普通香味持久（fragrance），未用于驱虫/杀菌，属正样本。", "confidence": 0.9}

示例 5（正，涂层/耐磨）
文本：NON-STICK COATING: ... features a long lasting nonstick coating for easy food release ... making it resistant to high heat
输出：{"label": "正样本", "risk_terms": [], "reason": "long-lasting 描述不粘涂层耐用性，无健康/杀菌功效。", "confidence": 0.94}

示例 6（正，防潮/吸湿，属普通干燥功能）
文本：Long-Lasting Effectiveness: Enjoy prolonged protection against dampness as each sachet works continuously to absorb moisture, ensuring a consistently dry environment
输出：{"label": "正样本", "risk_terms": [], "reason": "long-lasting 描述防潮吸湿/干燥环境，属普通保存功能，非杀菌/驱虫。", "confidence": 0.88}

示例 7（正，保鲜/密封）
文本：Airtight Seal Mess free- easy to close leak proof lids form an airtight seal to ensure long lasting freshness and prevent freezer burn
输出：{"label": "正样本", "risk_terms": [], "reason": "long-lasting 描述保鲜与密封效果，属普通商品功能。", "confidence": 0.9}

示例 8（负，驱虫/防蛀）
文本：A very rich, long-lasting moth repellent kit
输出：{"label": "负样本", "risk_terms": ["moth repellent"], "reason": "long-lasting 与驱虫/防蛀功效（moth repellent）绑定，属高合规风险。", "confidence": 0.95}

示例 9（负，杀菌/抗菌）
文本：Long-Lasting Germ Protection - Get 12 hours of antibacterial defense to keep harmful germs at bay
输出：{"label": "负样本", "risk_terms": ["Long-Lasting Germ Protection", "antibacterial defense", "harmful germs"], "reason": "long-lasting 与杀菌/抗菌、病菌防护功效绑定，属高合规风险。", "confidence": 0.95}

示例 10（负，杀虫/驱避害虫）
文本：This sachet provides long-lasting insect repellent protection to keep pests away from your closet
输出：{"label": "负样本", "risk_terms": ["insect repellent", "pests"], "reason": "long-lasting 与驱虫/驱避害虫功效绑定（insect repellent、pests）。", "confidence": 0.94}

示例 11（负，抗菌防护）
文本：The coating offers long-lasting antimicrobial protection that kills bacteria on contact
输出：{"label": "负样本", "risk_terms": ["antimicrobial protection", "kills bacteria"], "reason": "long-lasting 与抗菌/杀菌功效（antimicrobial、kills bacteria）绑定。", "confidence": 0.96}
