# Remotion 규칙

## 양쪽 동기화 필수
- `remotion/src/` 수정 → `auto_agent/remotion_template/src/`에도 반드시 동일 수정
- 대시보드 반영 시 `cd remotion && npx vite build --config vite.thumb.config.ts && npx vite build --config vite.editor.config.ts` 필수
- **절대 한쪽만 수정하고 끝내지 말 것**

## 씬 렌더링 단일 소스 — SceneRenderer.tsx
- **모든 씬 렌더링은 `remotion/src/components/SceneRenderer.tsx`의 `SceneRendererInner`를 사용**
- 스토리보드, 스튜디오, 씬에디터, Remotion Studio 4뷰 모두 동일 렌더러
- **CreativeScene은 순수 텍스트/데이터 렌더링만 담당** — 이미지 처리를 직접 하지 않음
- 레이아웃/이미지 수정 시 **SceneRenderer.tsx 한 곳만 수정**

## 렌더러 규칙
- 씬 렌더링은 **CreativeScene** (`remotion/src/simple/CreativeScene.tsx`)만 수정
- 디자인 토큰은 `artstyle/styles/*.json`의 `design_tokens`에서 관리 (단일 소스)
- `<Img src="">` 빈 src 방지: `if (!src) return null` 가드
- Node 25에서 `npx remotion` 실패 시: `node node_modules/@remotion/cli/remotion-cli.js` 직접 호출
- Thumbnail이 Root.tsx 첫 위치면 crash — Formats/ 폴더 격리
