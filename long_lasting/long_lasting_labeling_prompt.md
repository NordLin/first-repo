# long-lasting 合规标注提示词（标注阶段）

> 用途：对已切片好的英文（或多语）商品文案片段，判断其中 `long-lasting` 的用法属于
> “正样本”还是“负样本”。本提示词只做**分类**，不做数据抽取与增强（抽取/切句由脚本完成，
> 增强见 `long_lasting_augmentation_prompt.md`）。
>
> 标准依据：真实人工标注数据（120 正 / 2 负，内置启发式在该集上 100% 复现）。
> 与 `alta calidad` 不同，`long-lasting` **默认偏宽松**——只要落点是
> **物理耐用性 / 使用寿命 / 性能 / 外观·颜色·香味·光照保持**，即便表述较泛、甚至带
> `extremely / best / guarantee` 等词，只要有真实材料/规格/耐用属性支撑，通常仍是正样本。
> 只有当 `long-lasting` 偏离耐用性落点时才判负。

---

## 任务目标

识别商品文案中 `long-lasting`（含 `long lasting`、`longlasting`、`Long-Lasting` 等写法）的使用，
判断它是“可接受的客观耐用性/寿命/性能描述（正样本）”，还是“功效健康声明、品牌服务承诺、平台敏感内容，或无实质支撑的纯主观夸大（负样本）”。

---

## 标签定义

### 1. 正样本（风险较低，默认倾向）
`long-lasting` 用于描述商品/部件/材料的**物理耐用性、使用寿命、性能、续航、外观/颜色/香味保持**等。
**关键判据：是否有“耐用性实质支撑”**——即文中出现下列任一即可视为有支撑：
- **具体材料**：stainless steel / 304 / 925 sterling silver / PP / PVC / ABS / PLA / silicone / polyester / latex / wood / ceramic / rubber / vinyl / cotton / alloy / metal 等；
- **可验证规格/数字**：1200mAh、8 hours、50000 working hours、800+ meters、28 washes、60-90 days、8-hour burn time、4 mils、°C/Watt/GSM 等；
- **客观耐用属性**：durable / durability、resistant / resistance、waterproof、wear-resistant、fade/rust/corrosion-resistant、breathable、sturdy、reusable、longevity、lifespan、performance 等；
- **外观/颜色/香味/光照/续航的持久**：long-lasting shine / color / fragrance / scent / light / freshness / finish。

> 只要存在上述支撑且落点是耐用性，即便句中带 `extremely durable`、`best choice`、
> `quality guarantee`、`replacement parts`、`provide long-lasting durability` 等措辞，仍判**正样本**。
> 较泛但落点为耐用性的表述（`ensures long-lasting use / performance / reliability`）在无其它风险时也判正。

### 2. 负样本（风险较高）
`long-lasting` **偏离物理耐用性落点**，进入以下任一情形：
- **功效 / 健康 / 防护类声明**：long-lasting 修饰 germ protection、antibacterial / antimicrobial defense、kill 99.9%、disinfect、医疗/疗效、harmful germs 等（平台敏感功效宣称）。
- **品牌 / 商家承诺 / 服务（作为主体）**：long-lasting brand、we provide/offer long-lasting **products**、long-lasting **service / warranty / after-sales**。
  （注意：`guarantee a soft touch`、`provide long-lasting durability` 这类“修饰耐用性”的动词用法**不算**品牌服务承诺。）
- **与售后/联系/评价/优惠等平台敏感内容绑定**：contact us、contact seller、email us、WhatsApp、refund、reembolso、money-back、leave a review、5 stars/estrellas、feedback、coupon/cupón、discount、free gift、free replacement。
- **无实质支撑的纯主观夸大**：句中只有主观吹捧（very rich、amazing…）或最高级（longest-lasting、most long-lasting、best、#1、No.1），且**没有任何材料/规格/耐用属性支撑**，泛化吹捧整体商品/套装。例：`A very rich, long-lasting moth repellent kit`。

---

## 判定流程（请严格按优先级执行）

1. **硬风险扫描（命中即判负）**：
   - 功效/健康/防护：antibacterial、antimicrobial、germ(s)、kill xx%、disinfect、cure、prevent disease、medical/therapeutic
   - 平台敏感/售后：contact us/seller、email us、WhatsApp、refund/reembolso、money-back、leave a review、5 stars、feedback、coupon/cupón、discount、free gift、free replacement / replacement warranty
   - 品牌/服务作为主体：long-lasting brand、we provide/offer long-lasting products、long-lasting service/warranty/after-sales

2. **判断“耐用性实质支撑”是否存在**（材料 / 规格数字 / 客观耐用属性 / 外观持久，任一即算有）。

3. **主观夸大/最高级处理**（very、extremely、amazing、best、longest-lasting、most long-lasting…）：
   - 若**有**实质支撑 → 视为正常营销修饰，**不影响判正**；
   - 若**没有**实质支撑（纯吹捧整体商品/套装）→ **负样本**。

4. **裁决（优先级从高到低）**：
   - 命中第 1 步硬风险 → **负样本**
   - 纯主观夸大且无实质支撑（第 3 步）→ **负样本**
   - 落点为物理耐用性/寿命/性能/外观保持（有支撑，或仅较泛但无风险）→ **正样本**
   - 仍无法判断 → 保守判 **负样本**，并降低 confidence

> 重要：不要仅因为出现 `long-lasting`、`extremely`、`best`、`guarantee` 就判负。
> 绝大多数耐用性描述是正样本；只有功效健康、品牌服务承诺、平台敏感内容，或无实质支撑的纯吹捧才判负。

---

## confidence 锚定标准
- 物理耐用性 + 具体材料/参数齐全：**0.93–0.98**
- 物理耐用性但表述较泛、无材料/参数支撑：**0.82–0.92**
- 明确功效健康 / 品牌服务承诺 / 平台敏感：**0.90–0.98**
- 无实质支撑的纯主观夸大：**0.85–0.92**
- 模棱两可、上下文被切断：**0.60–0.80**

## risk_terms 抽取规则
- 抽取**触发判负的最小完整短语**（如 `Long-Lasting Germ Protection`、`very rich`、`we provide long-lasting products`、`contact us`）。
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

## 人工标注示例（均取自真实标注数据，标准已与之对齐）

示例 1（正）
文本：[Material] -- They are easy to put on and loose and they are made of stainless steel for long lasting durability
输出：{"label": "正样本", "risk_terms": [], "reason": "long-lasting 绑定具体材料 stainless steel，落点为 durability（物理耐用性）。", "confidence": 0.95}

示例 2（正）
文本：Quality Material: Our spacers are made from 304 stainless steel, which provides excellent strength and corrosion resistance, ensuring durability and long-lasting performance
输出：{"label": "正样本", "risk_terms": [], "reason": "明确 304 stainless steel + corrosion resistance/durability，long-lasting 修饰性能。", "confidence": 0.97}

示例 3（正）
文本：RECHARGEABLE & LONG LASTING: Built-in 1200mAh lithium battery, This camping head light has can be last up to 8 hours after full charge
输出：{"label": "正样本", "risk_terms": [], "reason": "long-lasting 绑定可验证规格 1200mAh、8 小时续航，属客观寿命描述。", "confidence": 0.96}

示例 4（正，含 "extremely" 但有材料支撑）
文本：With a zinc alloy construction, the house numbers for outside are extremely long-lasting and will not rust
输出：{"label": "正样本", "risk_terms": [], "reason": "虽有 extremely，但绑定 zinc alloy 材料且 will not rust，耐用性有实质支撑，按宽松标准判正。", "confidence": 0.9}

示例 5（正，含 "best choice" 但落点为耐用性）
文本：It is the best choice for your travel and outdoor activities ... yet ensures long-lasting durability that pairs perfectly with your AirPods 3
输出：{"label": "正样本", "risk_terms": [], "reason": "尽管出现 best choice 营销语，但 long-lasting 落点为 durability，有耐用属性支撑。", "confidence": 0.86}

示例 6（正，含 "guarantee" 动词用法）
文本：High-quality materials guarantee a soft touch and long-lasting durability, and will not cause foot odor when worn for a long time
输出：{"label": "正样本", "risk_terms": [], "reason": "guarantee 为动词修饰属性，非品牌服务承诺；long-lasting 绑定 durability，有材料支撑。", "confidence": 0.9}

示例 7（正，表述较泛）
文本：It ensures long-lasting use, making it the dependable choice
输出：{"label": "正样本", "risk_terms": [], "reason": "表述虽泛，但落点为 use 的耐用性，且无夸大/功效/平台风险，按宽松标准判正。", "confidence": 0.84}

示例 8（正，"provide long-lasting durability" 属耐用性修饰）
文本：This camping backpack is made of ripstop and water-resistant nylon fabric to provide long-lasting durability for everyday use
输出：{"label": "正样本", "risk_terms": [], "reason": "provide long-lasting durability 修饰耐用性，绑定 nylon 材料与 water-resistant 属性，非商家承诺。", "confidence": 0.94}

示例 9（负，主观夸大且无耐用性实质支撑）
文本：A very rich, long-lasting moth repellent kit
输出：{"label": "负样本", "risk_terms": ["very rich"], "reason": "very rich 主观吹捧 + 泛化修饰整套 kit，无材料/规格/耐用属性支撑。", "confidence": 0.9}

示例 10（负，功效/健康声明）
文本：Long-Lasting Germ Protection - Get 12 hours of antibacterial defense to keep harmful germs at bay
输出：{"label": "负样本", "risk_terms": ["Long-Lasting Germ Protection", "antibacterial defense", "harmful germs"], "reason": "long-lasting 修饰杀菌/防护功效（germ protection、antibacterial），属平台敏感功效宣称，非物理耐用性。", "confidence": 0.93}

示例 11（负，标准补充：品牌/服务作为主体）
文本：We are a long-lasting brand and we provide long-lasting products with dedicated after-sales service
输出：{"label": "负样本", "risk_terms": ["long-lasting brand", "we provide long-lasting products", "after-sales service"], "reason": "long-lasting 修饰品牌与商家承诺/服务（作为主体），属主观营销与承诺式表达。", "confidence": 0.95}

示例 12（负，标准补充：平台敏感绑定 + 最高级无支撑）
文本：The longest-lasting case ever — if not satisfied contact us for a full refund
输出：{"label": "负样本", "risk_terms": ["longest-lasting", "contact us", "full refund"], "reason": "最高级 longest-lasting 无实质支撑，且绑定联系卖家、退款等平台敏感售后内容。", "confidence": 0.96}
