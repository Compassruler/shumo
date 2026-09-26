"""Read the supplied DOCX as ZIP/XML; do not modify the source document."""
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parents[1] / "B题" / "氢燃料电池低温冷启动建模与控制策略研究.docx"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def words(node):
    return "".join(x.text or "" for x in node.findall(".//w:t", NS))


with ZipFile(SOURCE) as source:
    body = ET.fromstring(source.read("word/document.xml")).find("w:body", NS)
lines = ["# 原题第四问与相关约束摘录", "",
         "来源：用户提供的《氢燃料电池低温冷启动建模与控制策略研究.docx》。正文由 ZIP/XML 逐段提取；公式 (4)、(6)–(8) 从文档内嵌 WMF 图像读取并核对。下面将原题文字、既有建模解释和本次求解建议分开。", "",
         "## 1. 原题第四问全文", ""]
inside = False
for node in body:
    text = words(node)
    if text.startswith("问题4："):
        inside = True
    if inside and text.startswith("参考文献"):
        break
    if not inside:
        continue
    if node.tag.endswith("}tbl"):
        rows = [[words(cell) for cell in row.findall("w:tc", NS)]
                for row in node.findall("w:tr", NS)]
        if rows:
            lines.append("| " + " | ".join(rows[0]) + " |")
            lines.append("| " + " | ".join("---" for _ in rows[0]) + " |")
            lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
            lines.append("")
    elif text:
        lines.extend(["> " + text, ""])

lines.extend(["## 2. 相关原题文字", ""])
for start in ("辅助冷启动方式可分为", "（2）分别针对纯预加热启动", "式中，为功率", "将所有单电池同时达到", "式中，Vk (t)"):
    for node in body:
        text = words(node)
        if text.startswith(start):
            lines.extend(["> " + text, ""])

lines.extend([
    "## 3. 经公式原图核对的阈值", "",
    "- 问题二式 (4)：`0 ≤ j(t) ≤ j_max`；`∫₀ᵗˢ j(t)dt ≤ q_max`。其前文给出 `j_max=0.5 A/cm²`、`q_max=20 C/cm²`。",
    "- 式 (6)：`min_{1≤k≤5} T_k(t) > 0 ℃`。",
    "- 式 (7)：`max_{1≤k≤5} ε_ice,k(t) < 0.99`。",
    "- 式 (8)：`min_{1≤k≤5} V_k(t) ≥ 0.30 V`，`0≤t≤t_s`，即电压是整个启动路径的约束。",
    "- 冰体积分数为冰相体积除以对应控制体总体积，不能替换为孔隙冰饱和度。",
    "- 原题第四问只列“最大温差/℃”，未给出具体公式或数值硬上限。本次解释为启动期间五片单电池同一时刻温差的峰值 `max_t[max_k T_k(t)−min_k T_k(t)]`，不把不同时间的升温幅度计为片间不一致性。", "",
    "## 4. 截止时间应采用何种口径", "",
    "**原题的直接措辞：**20 C/cm² 电荷预算出现在问题二。问题三要求满足“问题2规定的电堆冷启动成功条件”，问题四要求在问题三恒功率基础上设计动态控制，并另列功率、冰、电压、及时关热四条约束；问题四本身没有重复明确写出20 C/cm²或96.67 s。故“第四问原题明确规定96.67 s”是不准确的。", "",
    "**用户建模文件的继承口径：**《问题3_建模推导源文件.md》§3.4.1 明文写道：", "",
    "> 因此加载段必须在约 $96.7\\ \\mathrm s$ 内满足成功条件，否则电荷预算耗尽（与问题2同样的预算约束）。", "",
    "其式 (3-30) 及数值实现约束再次要求 `q_L(t_s)≤20`、`t_s≤96.67 s`。问题四建模文件开头声明沿用问题三参数、统一加载、成功判据与约束基础。", "",
    "对题给加载曲线：", "",
    "```text",
    "Q(t) = 0.0025 t²                         (0 ≤ t ≤ 60 s)",
    "     = 9 + 0.3(t−60) = 0.3t−9           (t ≥ 60 s)",
    "Q(60) = 9 C/cm²",
    "Q(t_Q)=20 ⇒ t_Q=60+(20−9)/0.3=96.6666666667 s",
    "Q(180)=45 C/cm²",
    "```", "",
    "**本次主模型建议：**为遵守用户要求的模型继承并使问题三/四比较一致，强制首次成功 `t_s≤96.6666666667 s`，保存实际累计电荷。若搜索延长到180 s，应明确归类为“取消继承电荷预算后的扩展研究”，不能以此替换受预算约束的主优化结果。关热后可另设观察窗口；它属于后验安全验证，主表成本仍截取首次成功，且需说明后验段是否继续消耗超出启动预算的电荷。", "",
    "## 5. 预冷时间与启动时间不可混用", "",
    "20 min、40 min 和10–100 min 是无电流预冷阶段的持续时间；它们不消耗启动电荷，也不计入辅助冷启动成功时间。96.6667 s 是从统一电流开始加载起的预算截止，非预冷截止。", "",
    "若10 min预冷后所有单电池已高于0 ℃且其余初始约束满足，则按原题“最早时刻”的定义应为 `t_s=0、E_aux=0`。", "",
])
(ROOT / "原题第四问摘录.md").write_text("\n".join(lines), encoding="utf-8")
print(ROOT / "原题第四问摘录.md")
