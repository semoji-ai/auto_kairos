# Remotion 규칙

## ⚠️ 1순위 체크: 씬 렌더링 3뷰 분기 금지
**스토리보드 / 스튜디오 / 씬에디터가 다르게 보이면 반드시 `SceneRendererInner` 분기가 생긴 것.**

- `SceneEditor.tsx`, `SingleScenePlayer.tsx`, `ThumbComposition.tsx` 는 **모두 `SceneRendererInner` 하나만 호출**해야 함
- 씬 관련 컴포넌트(ImageBackground, SideImageLayout, FadeWrap 등)를 **SceneEditor.tsx에 새로 추가하는 것 절대 금지** — SceneRenderer.tsx에 추가할 것
- `SceneEditor.tsx`를 수정할 때 반드시 확인: `SceneRendererInner`를 거치는가? 직접 `CreativeScene`이나 이미지 컴포넌트를 호출하면 즉시 분기
- `portraitPlacement`와 `imageAsset.placement`는 항상 일치해야 함 — SceneRendererInner가 SideLayout 라우팅 시 동기화하지만, 데이터 생성 시점에도 일치시킬 것
- 폰트(`usePresetFonts`)는 `SceneRendererInner` 안에서 호출 — 진입점마다 따로 호출하지 말 것

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
