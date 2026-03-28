// Flutter Plugin Analysis — detailed 6-card skill logic slide
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 × 5.625"

const slide = pres.addSlide();
slide.background = { color: "FFFFFF" };

// ── COLORS ────────────────────────────────────────────
const DARK  = "111827";
const MED   = "6B7280";
const LIGHT = "9CA3AF";
const TEAL  = "0F766E";
const CBORD = "E5E7EB";
const OUTBG = "F0FDF9";
const OUTLN = "CCECE9";

// ── CARD GEOMETRY ─────────────────────────────────────
// 2 rows × 3 cols, each card 3.08" × 2.14"
const CARD_W   = 3.08;
const CARD_H   = 2.14;
const GAP_X    = 0.12;
const GAP_Y    = 0.10;
const LM       = 0.25;   // left margin

const COL = [
  LM,
  LM + CARD_W + GAP_X,
  LM + 2 * (CARD_W + GAP_X),
];
const ROW = [
  0.92,
  0.92 + CARD_H + GAP_Y,   // = 3.16"
];

// Card internal zones
const CONT_TOP = 0.41;              // header + separator height
const OUT_H    = 0.22;              // output strip height
const CONT_H   = CARD_H - CONT_TOP - OUT_H;  // content area = 1.51"

// ── TITLE ─────────────────────────────────────────────
slide.addText("Flutter 插件智能分析引擎", {
  x: LM, y: 0.15, w: 9.5, h: 0.46,
  fontSize: 19, bold: true, color: DARK, fontFace: "Calibri", margin: 0,
});
slide.addText(
  "opencode  ·  Multi-Skill 自动化流水线  ·  五步独立分析  +  第六步静默交叉修正",
  {
    x: LM, y: 0.61, w: 9.5, h: 0.23,
    fontSize: 8.5, color: LIGHT, margin: 0,
  }
);
slide.addShape(pres.shapes.RECTANGLE, {
  x: 0, y: 0.86, w: 10, h: 0.022,
  fill: { color: TEAL }, line: { color: TEAL },
});

// ── HELPERS ───────────────────────────────────────────

// Draw card shell: border, top bar, step label, title, separator, output strip
function shell(cx, cy, step, title, outText) {
  // Border
  slide.addShape(pres.shapes.RECTANGLE, {
    x: cx, y: cy, w: CARD_W, h: CARD_H,
    fill: { color: "FFFFFF" }, line: { color: CBORD, width: 1 },
  });
  // Teal top accent bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: cx, y: cy, w: CARD_W, h: 0.04,
    fill: { color: TEAL }, line: { color: TEAL },
  });
  // Step number
  slide.addText(step, {
    x: cx + 0.08, y: cy + 0.05, w: 0.28, h: 0.27,
    fontSize: 12, bold: true, color: TEAL,
    align: "center", valign: "middle", margin: 0,
  });
  // Card title
  slide.addText(title, {
    x: cx + 0.38, y: cy + 0.05, w: CARD_W - 0.48, h: 0.27,
    fontSize: 10, bold: true, color: DARK, valign: "middle", margin: 0,
  });
  // Separator
  slide.addShape(pres.shapes.LINE, {
    x: cx + 0.08, y: cy + 0.36, w: CARD_W - 0.16, h: 0,
    line: { color: CBORD, width: 0.75 },
  });
  // Output strip bg
  const outY = cy + CARD_H - OUT_H;
  slide.addShape(pres.shapes.RECTANGLE, {
    x: cx, y: outY, w: CARD_W, h: OUT_H,
    fill: { color: OUTBG }, line: { color: OUTBG },
  });
  slide.addShape(pres.shapes.LINE, {
    x: cx, y: outY, w: CARD_W, h: 0,
    line: { color: OUTLN, width: 0.5 },
  });
  slide.addText(outText, {
    x: cx + 0.10, y: outY, w: CARD_W - 0.20, h: OUT_H,
    fontSize: 6.5, italic: true, color: TEAL, valign: "middle", margin: 0,
  });
}

// Add equally-spaced content items inside the card content area.
// Each item can be a plain string or a rich-text array.
function addItems(cx, cy, list) {
  const iH = CONT_H / list.length;
  list.forEach((item, i) => {
    const iy = cy + CONT_TOP + i * iH;
    const base = {
      x: cx + 0.10, y: iy, w: CARD_W - 0.20, h: iH,
      fontSize: 7, valign: "middle", margin: 0, lineSpacingMultiple: 1.15,
    };
    if (typeof item === "string") {
      slide.addText(item, { ...base, color: DARK });
    } else {
      slide.addText(item, base);
    }
  });
}

// ── CARD ①: 云服务拓扑检测 ───────────────────────────
shell(COL[0], ROW[0], "①", "云服务拓扑检测", "topology · services · evidence");
addItems(COL[0], ROW[0], [
  [
    { text: "三分类：", options: { bold: true, color: TEAL } },
    { text: "pure_edge  ·  centralized  ·  decentralized", options: { color: DARK } },
  ],
  "Step 1a  grep 50+ 厂商关键词（Firebase · JPush · Agora 等）→ centralized",
  "Step 1b  检测可配置端点参数（baseUrl · mqttHost · brokerUrl · endpoint）",
  "Step 1c  扫描硬编码外部 URL（过滤注释和测试文件）",
  "优先级：厂商命中  ›  P2P/可配置协议  ›  无外部调用 = pure_edge",
]);

// ── CARD ②: 付费功能分析 ─────────────────────────────
shell(COL[1], ROW[0], "②", "付费功能分析", "involves_payment · plugin_paid · cloud_paid · payment_type[8种]");
addItems(COL[1], ROW[0], [
  [
    { text: "两维度：", options: { bold: true, color: TEAL } },
    { text: "plugin_paid（商业授权）+  cloud_paid（付费云服务）", options: { color: DARK } },
  ],
  "plugin_paid：grep LICENSE/README → proprietary · All Rights Reserved · purchase",
  "cloud_paid：匹配 pubspec 中 57 个付费 SDK（8 类）",
  [{ text: "  内购 · 支付处理 · 广告 · RTC · IM · 推送 · 归因分析 · APM", options: { color: MED, italic: true } }],
  "补充：iOS Podfile · Android build.gradle · example/ API Key 信号",
]);

// ── CARD ③: 许可证分析 ───────────────────────────────
shell(COL[2], ROW[0], "③", "许可证分析", "type · commercial_friendly · restrictions[]");
addItems(COL[2], ROW[0], [
  [
    { text: "四分类：", options: { bold: true, color: TEAL } },
    { text: "宽松 · 传染性 · 专有 · 未声明", options: { color: DARK } },
  ],
  "读取 LICENSE 文件 + pubspec.yaml license 字段",
  "宽松（MIT · Apache-2.0 · BSD）→ commercial_friendly: true，restrictions: []",
  "传染性：GPL/AGPL 需整体开源；LGPL 动态链接豁免；MPL 文件级传染",
  "专有 → 禁止逆向再分发；未声明 → 默认版权保留，不建议商用",
]);

// ── CARD ④: 厂商平台识别 ─────────────────────────────
shell(COL[0], ROW[1], "④", "厂商平台识别", "label · confidence(high/medium/low) · evidence");
addItems(COL[0], ROW[1], [
  [
    { text: "8标签：", options: { bold: true, color: TEAL } },
    { text: "HMS · GMS · XIAOMI · OPPO · VIVO · HONOR · MEIZU · AGGREGATOR · NONE", options: { color: DARK } },
  ],
  "Step 1  pubspec.yaml 包名前缀（huawei_ · firebase_ · xiaomi_ 等）→ high",
  "Step 2  android/build.gradle gradle 插件 + maven 仓库地址（agcp · play-services）",
  "Step 3  Dart/Kotlin/Java source import 关键类名（HmsInstanceId 等）→ medium",
  "聚合判断：≥2 厂商信号 OR 友盟/极光/个推/融云 → AGGREGATOR_PLATFORM",
]);

// ── CARD ⑤: 功能分类标注 ─────────────────────────────
shell(COL[1], ROW[1], "⑤", "功能分类标注", "feature_list(5–15条) · summary · taxonomy1/2/3");
addItems(COL[1], ROW[1], [
  [
    { text: "5步分析：", options: { bold: true, color: TEAL } },
    { text: "三套分类体系独立输出，互不参考", options: { color: DARK } },
  ],
  "Step 1-2  读 pubspec + README + lib/ 公开 API（Future · Stream · static 方法）",
  "Step 3   按 18 个一级分类分别 grep 关键词，命中文件数决策",
  "Step 4   命中 ≥2 文件的分类深读核心 .dart 文件确认",
  "Step 5   英文 key（18分类）/ 鸿蒙生态（中文）/ SDK字典（中文）独立输出",
]);

// ── CARD ⑥: 静默交叉修正 ─────────────────────────────
shell(COL[2], ROW[1], "⑥", "静默交叉修正", "修正直接体现在主字段 · 六字段合并输出");

// Custom layout: intro line + 3 rule blocks
const c6x = COL[2], c6y = ROW[1];
const tx = c6x + 0.10;
const tw = CARD_W - 0.20;
const cvTop = c6y + CONT_TOP;

// Intro
slide.addText("静默执行，修正结果直接反映在主字段，无修正记录", {
  x: tx, y: cvTop, w: tw, h: 0.22,
  fontSize: 7, bold: true, color: TEAL, valign: "middle", margin: 0,
});

// 3 rule blocks
const CV_RULES = [
  {
    tag:  "C1–C3",
    cond: "topology=pure_edge 且 cloud_paid=true / services非空 / payment_type含云服务",
    fix:  "→ 强制修正为 centralized",
  },
  {
    tag:  "C4",
    cond: "involves_payment  ≠  plugin_paid  OR  cloud_paid",
    fix:  "→ 自动对齐布尔值",
  },
  {
    tag:  "W2",
    cond: "mobile_platform≠NONE 且 services不含对应厂商名",
    fix:  "→ confidence 降为 low",
  },
];

// Rule area: from intro end to output strip top
// = CONT_H - 0.22(intro) - 0.05(gap) = 1.51 - 0.27 = 1.24"
const ruleAreaH = CONT_H - 0.22 - 0.05;
const ruleH     = ruleAreaH / CV_RULES.length;  // 0.413"
const ruleStart = cvTop + 0.22 + 0.05;

CV_RULES.forEach((rule, i) => {
  const ry = ruleStart + i * ruleH;
  // Tag
  slide.addText(rule.tag, {
    x: tx, y: ry, w: 0.46, h: ruleH,
    fontSize: 7.5, bold: true, color: TEAL, valign: "middle", margin: 0,
  });
  // Condition + fix (rich text with line break)
  slide.addText(
    [
      { text: rule.cond + "\n", options: { color: MED } },
      { text: rule.fix, options: { bold: true, color: TEAL } },
    ],
    {
      x: tx + 0.48, y: ry, w: tw - 0.48, h: ruleH,
      fontSize: 6.5, valign: "middle", margin: 0, lineSpacingMultiple: 1.15,
    }
  );
});

// ── BOTTOM JSON STRIP ──────────────────────────────────
// ROW[1] + CARD_H = 3.16 + 2.14 = 5.30"
const JSON_Y = ROW[1] + CARD_H + 0.07;   // 5.37"
const JSON_H = 5.625 - JSON_Y;            // 0.255"

slide.addShape(pres.shapes.RECTANGLE, {
  x: 0, y: JSON_Y, w: 10, h: JSON_H,
  fill: { color: OUTBG }, line: { color: OUTBG },
});
slide.addShape(pres.shapes.LINE, {
  x: 0, y: JSON_Y, w: 10, h: 0,
  line: { color: OUTLN, width: 0.5 },
});
slide.addText(
  "→ JSON 报告    repo_url  ·  analyzed_at  ·  cloud_services  ·  payment  ·  license  ·  mobile_platform  ·  features",
  {
    x: 0.25, y: JSON_Y, w: 9.5, h: JSON_H,
    fontSize: 7.5, color: TEAL, align: "center", valign: "middle", margin: 0,
  }
);

// ── WRITE ─────────────────────────────────────────────
pres.writeFile({ fileName: "flutter_analysis_pipeline.pptx" })
  .then(() => console.log("✓  flutter_analysis_pipeline.pptx"))
  .catch(console.error);
