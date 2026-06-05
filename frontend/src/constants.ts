import type { Game, Language } from "./types";

export const GAMES: Game[] = [
  { displayName: "Splendor", apiKey: "splendor" },
  { displayName: "Catan", apiKey: "catan" },
  { displayName: "Speakeasy", apiKey: "speakeasy" },
  { displayName: "Food Chain Magnate", apiKey: "fcm" },
  { displayName: "Feed the Kraken", apiKey: "ftk" },
];

export const LANGUAGES: { code: Language; label: string }[] = [
  { code: "en", label: "EN" },
  { code: "zh", label: "中文" },
];

export const EXAMPLE_QUESTIONS: Record<string, Record<Language, string[]>> = {
  splendor: {
    en: [
      "Can I take 2 gems of the same color?",
      "How do nobles work?",
      "When does the game end?",
    ],
    zh: [
      "我可以拿两个同色的宝石吗？",
      "贵族（nobles）是如何运作的？",
      "游戏在什么时候结束？",
    ],
  },
  catan: {
    en: [
      "What happens when I roll a 7?",
      "How does the Longest Road work?",
      "Can I trade with other players on their turn?",
    ],
    zh: [
      "掷出 7 的时候会发生什么事？",
      "最长道路（Longest Road）是如何计算的？",
      "我可以在别人的回合和他们交易吗？",
    ],
  },
  speakeasy: {
    en: [
      "What does the Contractor do?",
      "How do I protect my buildings?",
      "When is a building considered Operating?",
    ],
    zh: [
      "承包商（Contractor）有什么作用？",
      "我要如何保护我的建筑？",
      "建筑在什么情况下算是运营中（Operating）？",
    ],
  },
  fcm: {
    en: [
      "How does the Dinnertime phase work?",
      "What does the 'First billboard placed' milestone do?",
      "Can I train an employee I just hired?",
    ],
    zh: [
      "晚餐时间（Dinnertime）阶段是如何运作的？",
      "“第一个放置广告看板”里程碑有什么效果？",
      "我可以训练刚雇用的员工吗？",
    ],
  },
  ftk: {
    en: [
      "How do the Sailors win?",
      "How many guns are needed for a successful mutiny?",
      "What does Feed the Kraken do?",
    ],
    zh: [
      "水手（Sailors）要如何获胜？",
      "成功发动叛变（mutiny）需要几把枪？",
      "“喂食克拉肯”（Feed the Kraken）有什么作用？",
    ],
  },
};

export const TIER_CONFIG = {
  1: { label: "Direct Answer", color: "bg-tier1", textColor: "text-white" },
  2: { label: "Multi-Step Reasoning", color: "bg-tier2", textColor: "text-white" },
  3: { label: "Uncertain", color: "bg-tier3", textColor: "text-white" },
} as const;

// Minimal UI-chrome localization. English strings are byte-identical to the
// previous hardcoded values so existing behavior and tests are unchanged.
export interface UIStrings {
  askPlaceholder: string;
  sources: string;
  emptyHeading: string;
  emptySubtitle: string;
  tryAsking: string;
  consulting: string;
  tierLabels: Record<1 | 2 | 3, string>;
  tier2Note: string;
  tier3Note: string;
  errorGeneric: string;
  errorUnavailable: string;
}

export const UI_STRINGS: Record<Language, UIStrings> = {
  en: {
    askPlaceholder: "Ask a rules question...",
    sources: "Sources",
    emptyHeading: "Ask the Oracle",
    emptySubtitle:
      "Ask any rules question and get answers with citations from the official rule book.",
    tryAsking: "Try asking",
    consulting: "Consulting the rule book...",
    tierLabels: { 1: "Direct Answer", 2: "Multi-Step Reasoning", 3: "Uncertain" },
    tier2Note: "Synthesized from multiple rules",
    tier3Note: "Suggested interpretation — not authoritative",
    errorGeneric: "Something went wrong. Please try again.",
    errorUnavailable: "This game isn't available right now. Try a different game.",
  },
  zh: {
    askPlaceholder: "输入规则问题……",
    sources: "资料来源",
    emptyHeading: "询问神谕",
    emptySubtitle: "提出任何规则问题，即可获得引用自官方规则书的解答。",
    tryAsking: "试着问问看",
    consulting: "正在查阅规则书……",
    tierLabels: { 1: "直接解答", 2: "多步推理", 3: "不确定" },
    tier2Note: "综合多条规则得出",
    tier3Note: "建议的解读——并非权威答案",
    errorGeneric: "发生错误，请再试一次。",
    errorUnavailable: "这个游戏目前无法使用，请改试其他游戏。",
  },
};
