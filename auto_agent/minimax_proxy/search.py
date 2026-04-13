#!/usr/bin/env python3
"""웹 검색 헬퍼 — minimax_proxy에서 subprocess로 호출
날씨 쿼리: Open-Meteo API (무료)
일반 쿼리: Wikipedia API + Naver 뉴스
"""
import sys
import json
import urllib.request
import urllib.parse
import re

CITY_COORDS = {
    "서울": (37.5665, 126.9780),
    "seoul": (37.5665, 126.9780),
    "부산": (35.1796, 129.0756),
    "대구": (35.8722, 128.6018),
    "인천": (37.4563, 126.7052),
    "제주": (33.4996, 126.5312),
    "도쿄": (35.6762, 139.6503),
    "tokyo": (35.6762, 139.6503),
    "뉴욕": (40.7128, -74.0060),
    "베이징": (39.9042, 116.4074),
}

def get_weather(query):
    """날씨 관련 쿼리 처리 — Open-Meteo API"""
    lat, lon, city_name = 37.5665, 126.9780, "서울"
    for city, coords in CITY_COORDS.items():
        if city in query.lower():
            lat, lon = coords
            city_name = city
            break

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,apparent_temperature,precipitation,"
        f"weathercode,windspeed_10m,relativehumidity_2m"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
        f"&timezone=Asia%2FSeoul&forecast_days=3"
    )
    with urllib.request.urlopen(url, timeout=8) as r:
        data = json.loads(r.read())

    c = data["current"]
    d = data["daily"]

    wcode_map = {
        0: "맑음", 1: "대체로 맑음", 2: "부분 구름", 3: "흐림",
        45: "안개", 48: "서리 안개", 51: "이슬비", 53: "이슬비",
        55: "강한 이슬비", 61: "비", 63: "비", 65: "강한 비",
        71: "눈", 73: "눈", 75: "강한 눈", 80: "소나기", 95: "뇌우",
    }
    wcode = c.get("weathercode", 0)
    status = wcode_map.get(wcode, f"코드{wcode}")

    result = f"[{city_name} 현재 날씨]\n"
    result += f"상태: {status}\n"
    result += f"기온: {c['temperature_2m']}°C (체감 {c['apparent_temperature']}°C)\n"
    result += f"습도: {c['relativehumidity_2m']}%\n"
    result += f"강수량: {c['precipitation']}mm\n"
    result += f"풍속: {c['windspeed_10m']}km/h\n\n"
    result += "[3일 예보]\n"
    for i in range(3):
        day = d["time"][i]
        wc = wcode_map.get(d["weathercode"][i], "")
        result += f"{day}: 최고 {d['temperature_2m_max'][i]}°C / 최저 {d['temperature_2m_min'][i]}°C, {wc}, 강수 {d['precipitation_sum'][i]}mm\n"
    return result.strip()


def search_wikipedia(query):
    """Wikipedia 검색"""
    url = "https://ko.wikipedia.org/w/api.php?action=query&list=search&srsearch=" + \
          urllib.parse.quote(query) + "&format=json&srlimit=3"
    req = urllib.request.Request(url, headers={"User-Agent": "KairosBot/1.0 (auto_kairos)"})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read())

    results = []
    for item in data.get("query", {}).get("search", [])[:3]:
        title = item["title"]
        snippet = re.sub(r"<[^>]+>", "", item.get("snippet", "")).strip()
        page_url = "https://ko.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        results.append(f"[Wikipedia] {title}\nURL: {page_url}\n{snippet}")

    return results


def search_naver_news(query):
    """네이버 뉴스 RSS (API 키 불필요)"""
    url = "https://news.naver.com/search/results.naver?query=" + urllib.parse.quote(query)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=8) as r:
        html = r.read().decode("utf-8", errors="ignore")

    titles = re.findall(r'class="news_tit"[^>]*title="([^"]+)"', html)[:5]
    return [f"[뉴스] {t}" for t in titles]


def search(query):
    """쿼리 유형에 따라 적합한 검색 실행"""
    query_lower = query.lower()

    # 날씨 관련
    weather_keywords = ["날씨", "기온", "기상", "비", "눈", "weather", "temperature", "rain"]
    if any(kw in query_lower for kw in weather_keywords):
        return get_weather(query)

    # 일반 검색: Wikipedia + 뉴스
    results = []
    try:
        wiki = search_wikipedia(query)
        results.extend(wiki)
    except Exception as e:
        results.append(f"Wikipedia 오류: {e}")

    if not results:
        return f'"{query}" 검색 결과 없음'

    return "\n\n".join(results)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not query:
        print("사용법: python3 search.py <검색어>")
        sys.exit(1)
    try:
        print(search(query))
    except Exception as e:
        print(f"검색 오류: {e}")
