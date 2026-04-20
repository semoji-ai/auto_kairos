# Signal Feed Sources

Stage 0 and Stage 4 use three classes of signal source.

## 1. Direct RSS or Atom feeds

These can be added to `.collector/signal_feeds.json` and collected automatically with:

```bash
auto-agent collect --signals
```

Recommended direct feeds:

- Google News KR Top  
  `https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko`
- Google News KR Business  
  `https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko`
- Google News KR Entertainment  
  `https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=ko&gl=KR&ceid=KR:ko`
- Daum News Home  
  `https://news.daum.net`
- Reddit Popular Hot  
  `https://www.reddit.com/r/popular/.rss`
- Reddit r/todayilearned Hot  
  `https://www.reddit.com/r/todayilearned/hot/.rss`
- Hacker News Frontpage  
  `https://news.ycombinator.com/rss`

Use these when you want:
- broad trend detection
- community-level hot-post signals
- knowledge/explainer topic seeds

Notes:
- `https://news.daum.net` works as an HTML source for popular-news style signals.
- `https://www.daum.net` main page is not a good default source for this workflow. It returns too much navigation noise.

## 2. Social feeds through a proxy or self-hosted adapter

X and Threads do not provide a stable direct RSS path for this workflow.

Recommended approach:
- use a self-hosted RSSHub or another trusted feed proxy
- keep those feeds disabled by default in `signal_feeds.json`
- write snapshots into `market/social/`

Examples:
- X keyword or watch-account feeds
- Threads watch-account feeds

If the proxy path is unstable, do not auto-collect it. Use snapshot import instead.

## 3. Korean community hot-post aggregators

For Korean communities, stable RSS is often unavailable or inconsistent.

Practical sources to watch:
- 다음 카페 인기글  
  `https://m.cafe.daum.net`
- 글토끼모아  
  `https://gttgg.co.kr/ko`
- 다모앙  
  `https://damoang.net/free`

Recommended operating mode:
- use these sites to discover hot topics
- export or summarize the hot-post set
- import it with:

```bash
auto-agent collect --signals-import <file> --target market/communities
```

or fetch the page directly and store a bounded snapshot with:

```bash
auto-agent collect --signals-import-url <url> --target market/communities --name <snapshot-name>
```

Example:

```bash
auto-agent collect --signals-import-url https://damoang.net/free --target market/communities --name damoang-free
```

```bash
auto-agent collect --signals-import-url https://m.cafe.daum.net --target market/communities --name daum-cafe-popular-mobile
```

`damoang-free` is safe enough to keep in `signal_feeds.json` as an enabled HTML source.
`daum-cafe-popular-mobile` is also usable as an enabled HTML source.
For the rest of the Korean community ecosystem, keep using snapshot import unless a source proves stable enough for automatic collection.

## Channel-specific community buckets

Use separate placeholder feeds in `.collector/signal_feeds.json` when the channel needs a narrower signal mix.

- `finance-community-signals`
  - intended for `이로미즘`
  - prefer economic, tax, investing, market-structure, and policy communities
  - practical Korean starter source: `https://www.ppomppu.co.kr/zboard/zboard.php?id=money`
- `ai-community-signals`
  - intended for `ai백과사전`
  - prefer AI developer, model, GPU, benchmark, and agent communities
  - practical Korean starter source: `https://news.hada.io/`

These starter sources are not meant to be the final answer.
They are simply stable public feeds that can be collected immediately while you decide which Korean communities deserve dedicated import or parser support.

These are disabled by default. Fill them with:
- a stable RSS/Atom source, or
- a manual snapshot import, or
- a URL import from a bounded list page

This is the preferred path for:
- 클리앙
- 더쿠
- FM코리아
- 루리웹
- 인벤
- 뽐뿌
- 다모앙
- community aggregators that do not expose stable feeds

## Selection rule

Prefer this order:

1. Direct RSS or Atom
2. Stable self-hosted proxy feed
3. Manual snapshot import

Do not rely on brittle HTML scraping in the default collector unless a source becomes operationally important and stable enough to justify a dedicated parser.
