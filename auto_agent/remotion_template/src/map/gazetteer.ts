/**
 * 가제터 (Gazetteer) — 지명 → 좌표 매핑 데이터베이스
 *
 * 에이전트가 원고에서 추출한 지명을 좌표로 변환할 때 사용.
 * 초기 데이터: 단종 유배 관련 한반도 주요 지명 (~20개)
 */

export interface GazetteerEntry {
  nameKorean: string;
  nameEnglish?: string;
  nameHistorical?: string;
  coordinates: [number, number]; // [lng, lat]
  defaultZoom: number;
  category:
    | "city"
    | "palace"
    | "landmark"
    | "region"
    | "river"
    | "mountain"
    | "fortress";
}

export const GAZETTEER: GazetteerEntry[] = [
  // ── 수도 / 주요 도시 ──────────────────────────
  {
    nameKorean: "한양",
    nameEnglish: "Hanyang",
    nameHistorical: "漢陽",
    coordinates: [126.977, 37.566],
    defaultZoom: 11,
    category: "city",
  },
  {
    nameKorean: "서울",
    nameEnglish: "Seoul",
    coordinates: [126.977, 37.566],
    defaultZoom: 11,
    category: "city",
  },
  {
    nameKorean: "개성",
    nameEnglish: "Kaesong",
    nameHistorical: "開城",
    coordinates: [126.563, 37.971],
    defaultZoom: 12,
    category: "city",
  },
  {
    nameKorean: "평양",
    nameEnglish: "Pyongyang",
    coordinates: [125.752, 39.019],
    defaultZoom: 11,
    category: "city",
  },

  // ── 단종 유배 관련 ──────────────────────────
  {
    nameKorean: "영월",
    nameEnglish: "Yeongwol",
    coordinates: [128.462, 37.184],
    defaultZoom: 12,
    category: "city",
  },
  {
    nameKorean: "청령포",
    nameEnglish: "Cheongnyeongpo",
    coordinates: [128.456, 37.172],
    defaultZoom: 15,
    category: "landmark",
  },
  {
    nameKorean: "관풍헌",
    nameEnglish: "Gwanpungheon",
    coordinates: [128.461, 37.183],
    defaultZoom: 16,
    category: "landmark",
  },
  {
    nameKorean: "장릉",
    nameEnglish: "Jangneung",
    nameHistorical: "莊陵",
    coordinates: [128.477, 37.188],
    defaultZoom: 15,
    category: "landmark",
  },
  {
    nameKorean: "순흥",
    nameEnglish: "Sunheung",
    coordinates: [128.732, 36.935],
    defaultZoom: 13,
    category: "city",
  },

  // ── 궁궐 ──────────────────────────
  {
    nameKorean: "경복궁",
    nameEnglish: "Gyeongbokgung",
    nameHistorical: "景福宮",
    coordinates: [126.977, 37.579],
    defaultZoom: 15,
    category: "palace",
  },
  {
    nameKorean: "창덕궁",
    nameEnglish: "Changdeokgung",
    nameHistorical: "昌德宮",
    coordinates: [126.991, 37.579],
    defaultZoom: 15,
    category: "palace",
  },
  {
    nameKorean: "창경궁",
    nameEnglish: "Changgyeonggung",
    coordinates: [126.995, 37.579],
    defaultZoom: 15,
    category: "palace",
  },

  // ── 유배 경유지 ──────────────────────────
  {
    nameKorean: "여주",
    nameEnglish: "Yeoju",
    coordinates: [127.636, 37.298],
    defaultZoom: 12,
    category: "city",
  },
  {
    nameKorean: "원주",
    nameEnglish: "Wonju",
    coordinates: [127.920, 37.342],
    defaultZoom: 12,
    category: "city",
  },
  {
    nameKorean: "제천",
    nameEnglish: "Jecheon",
    coordinates: [128.191, 37.133],
    defaultZoom: 12,
    category: "city",
  },

  // ── 기타 주요 지명 ──────────────────────────
  {
    nameKorean: "함흥",
    nameEnglish: "Hamheung",
    coordinates: [127.539, 39.918],
    defaultZoom: 11,
    category: "city",
  },
  {
    nameKorean: "부산",
    nameEnglish: "Busan",
    coordinates: [129.076, 35.180],
    defaultZoom: 11,
    category: "city",
  },
  {
    nameKorean: "강화도",
    nameEnglish: "Ganghwado",
    coordinates: [126.487, 37.747],
    defaultZoom: 12,
    category: "landmark",
  },
  {
    nameKorean: "백두산",
    nameEnglish: "Baekdusan",
    coordinates: [128.056, 42.005],
    defaultZoom: 10,
    category: "mountain",
  },
  {
    nameKorean: "한강",
    nameEnglish: "Han River",
    coordinates: [127.024, 37.528],
    defaultZoom: 11,
    category: "river",
  },
];

/**
 * 한글 지명으로 가제터 항목 검색.
 * 정확 매칭 우선, 없으면 부분 매칭.
 */
export function lookupGazetteer(name: string): GazetteerEntry | undefined {
  // 정확 매칭
  const exact = GAZETTEER.find(
    (e) =>
      e.nameKorean === name ||
      e.nameEnglish === name ||
      e.nameHistorical === name,
  );
  if (exact) return exact;

  // 부분 매칭
  return GAZETTEER.find(
    (e) =>
      e.nameKorean.includes(name) ||
      name.includes(e.nameKorean) ||
      (e.nameEnglish && e.nameEnglish.toLowerCase().includes(name.toLowerCase())),
  );
}
