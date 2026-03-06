/**
 * 시각화 컴포넌트 한국어 문자열 및 아이콘 매칭 패턴
 */

export const VIZ_STRINGS = {
  source_prefix: "출처:",
  table_header_item: "항목",
  table_header_value: "값",
  pie_total: "합계",
  diagram_before: "기존",
  diagram_after: "변경 후",
} as const;

export const ICON_PATTERNS: Array<{ pattern: RegExp; icon: string }> = [
  { pattern: /악재|위험|문제|리스크|risk|danger/i, icon: "\u26A0\uFE0F" },
  { pattern: /교훈|결론|핵심|lesson|key/i, icon: "\uD83D\uDCA1" },
  { pattern: /장점|긍정|성과|advantage|positive/i, icon: "\u2705" },
  { pattern: /단점|부정|실패|disadvantage|negative/i, icon: "\u274C" },
];

export const DEFAULT_ICON = "\u2022";

export function getIconForTitle(title: string): string {
  for (const { pattern, icon } of ICON_PATTERNS) {
    if (pattern.test(title)) return icon;
  }
  return DEFAULT_ICON;
}
