# long-lasting 数据增强提示词（增强阶段）

> 用途：当某一特征的真实样本不足 50 条时，按该特征生成补充样本，**不得同质化**。
> 增强只负责“造数据片段”，标签仍由 `long_lasting_labeling_prompt.md` 统一判定。
>
> 背景：真实标注严重不平衡（120 正 / 2 负）。因此负样本（尤其是“品牌/服务承诺”“最高级绝对化”
> “平台敏感绑定”三类）几乎一定需要增强；正样本各子类一般充足，必要时也可补充。

---

## 生成目标
为指定特征生成 N 条英文（可少量多语混排，贴合真实 listing 风格）商品文案片段，每条满足：
- 每段最多包含**一个** `long-lasting`（含 `long lasting` / `longlasting` / `Long-Lasting` 写法）关键词。
- 长度、句式、品类、材料、卖点表达**尽量多样**，避免雷同模板。
- 真实自然，像电商 bullet point / 标题，不要解释性句子。

## 反同质化要求（必须遵守）
- 覆盖不同**品类**：服饰、首饰、五金、厨具、电子、户外、美妆、宠物、家居、办公等。
- 变化**句式**：标题式、bullet 式、特性短句、带参数的句子等交替。
- 变化**触发要素**：材料 / 参数 / 客观属性 / 外观·颜色·香味 / 续航 等轮换。
- 不重复同一商品或同一措辞；同义改写而非复制粘贴；避免连续使用相同开头词。

---

## 各特征生成要点

### 正样本特征
1. `long-lasting` 绑定具体材料（stainless steel/304/PP/PVC/ABS/PLA/silicone/925 sterling silver/polyester/latex/wood/ceramic/rubber/vinyl/cotton…）。
2. 明确结构 `made of / crafted from / constructed from / built with + 材料`。
3. 绑定客观属性（durable/resistant/waterproof/wear-resistant/fade-resistant/breathable/sturdy/reusable…）。
4. 绑定可验证规格/数字（mAh、hours、working hours、washes、days、burn time、meters…）。
5. 外观/颜色/香味/光照/续航的持久（shine/color/fragrance/scent/light/freshness/finish）。
6. 较泛但落点为耐用性的表述（long-lasting use/performance/durability/reliability）。

### 负样本特征（优先补足）
7. 主观夸大 / 最高级 / 绝对化：very、extremely、amazing + long-lasting；longest-lasting、most long-lasting、best、#1。
8. 泛化吹捧整体商品/套装且带夸大词（如 “a very rich, long-lasting kit”）。
9. 功效 / 健康 / 防护类声明（germ protection、antibacterial、kill 99.9%、医疗疗效…）。
10. 品牌 / 商家承诺 / 服务（long-lasting brand、we provide long-lasting products、long-lasting service/guarantee/warranty）。
11. 与平台敏感内容绑定（contact us、email、WhatsApp、refund/reembolso、replacement、review、feedback、5 stars、coupon、discount、free gift）。

---

## 输出格式（JSON 数组）
```json
[
  {"id": "aug_<特征号>_<序号>", "feature": "特征编号或名称", "text": "生成的文案片段"}
]
```
- `id` 用 `aug_` 前缀以区分真实抽样数据（真实数据保留原始 id）。
- 只输出 JSON 数组，不要输出额外解释。生成后交由标注提示词统一打标签。
