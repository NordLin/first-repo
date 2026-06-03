# long-lasting 数据增强提示词（增强阶段）

> 用途：当某一特征的真实样本不足 50 条时，按该特征生成补充样本，**不得同质化**。
> 增强只负责“造数据片段”，标签仍由 `long_lasting_labeling_prompt.md` 统一判定。
>
> 背景：真实标注严重不平衡（120 正 / 2 负）。负样本（健康/杀菌/抗菌/防虫/驱虫/防蛀功效类）
> 几乎一定需要增强；正样本各子类一般充足，必要时也可补充。

---

## 生成目标
为指定特征生成 N 条英文（可少量多语混排，贴合真实 listing 风格）商品文案片段，每条满足：
- 每段最多包含**一个** `long-lasting`（含 `long lasting` / `longlasting` / `Long-Lasting` 写法）关键词。
- 长度、句式、品类、材料、卖点表达**尽量多样**，避免雷同模板。
- 真实自然，像电商 bullet point / 标题，不要解释性句子。

## 反同质化要求（必须遵守）
- 覆盖不同**品类**：服饰、首饰、五金、厨具、电子、户外、美妆、宠物、家居、办公等。
- 变化**句式**：标题式、bullet 式、特性短句、带参数的句子等交替。
- 变化**触发要素**：材料 / 续航参数 / 颜色光泽 / 香味 / 涂层耐磨 / 保鲜密封 等轮换。
- 不重复同一商品或同一措辞；同义改写而非复制粘贴；避免连续使用相同开头词。

---

## 各特征生成要点

### 正样本特征（描述普通商品属性，**不得**出现健康/杀菌/防虫词）
1. **材料耐用、长期使用**：long-lasting durability / use / performance / strength / reliability（绑定 stainless steel、304、PP、PVC、ABS、PLA、silicone、polyester、wood、metal 等）。
2. **颜色、光泽、图案、印刷持久**：long-lasting shine / color / beauty、designs that won't fade over time。
3. **香味、扩香、清新持久（不涉及驱虫/杀菌/治疗）**：long-lasting scents / fragrance、continuous diffusion。
4. **电池、灯光、续航、容量**：long-lasting battery / light、last up to 8 hours、1200mAh、50000 working hours。
5. **涂层、非粘、耐磨、防水、耐腐蚀、可重复使用**：long-lasting nonstick coating / reuse、resists rust and corrosion、wear-resistant。
6. **普通保存/密封**：long-lasting freshness、airtight seal。
7. **普通吸湿/防潮/干燥**：prolonged protection against dampness、absorb moisture。

### 负样本特征（与健康/安全/杀菌/抗菌/防虫/驱虫/防蛀功效绑定，**优先补足**）
8. **驱虫 / 防蛀 / 杀虫 / 驱避害虫**：moth repellent、insect repellent、pest repellent、anti-moth、repellent kit、keep pests away。
9. **抗菌 / 杀菌 / 细菌防护 / 病菌防护**：antibacterial defense、germ protection、harmful germs、kills bacteria、antimicrobial protection。
10. **宣称长效保护健康/安全/免受细菌·害虫侵害**：long-lasting germ protection、long-lasting antibacterial defense、long-lasting insect protection。

> 关键：负样本必须让 `long-lasting` 与上述敏感功效词**真实绑定**；不要只是把香味/普通属性句改个词，
> 否则会被标注为正样本。生成后交由标注提示词统一打标签。

---

## 输出格式（JSON 数组）
```json
[
  {"id": "aug_<特征号>_<序号>", "feature": "特征编号或名称", "text": "生成的文案片段"}
]
```
- `id` 用 `aug_` 前缀以区分真实抽样数据（真实数据保留原始 id）。
- 只输出 JSON 数组，不要输出额外解释。
