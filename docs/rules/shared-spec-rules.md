# 공유 규격 — 두 저장소가 같은 파일을 볼 때

> v3와 adobe가 같은 데이터를 쓴다. 사본을 각자 고치기 시작하면 어느 쪽이 맞는지
> 알 수 없게 된다. 실제로 `verify_voice.py`가 양쪽에서 따로 자라 문턱값이
> 갈릴 뻔했다 — 한쪽은 하드코딩, 한쪽은 밴드 파일 읽기였다.

---

## 규칙 하나 — 소유자는 v3다

**고치는 곳은 v3 한 곳이고 adobe는 받아 쓴다.**

```
v3    auto_agent/data/artstyle/semoji-voice-bands.json    ← 여기서 고친다
adobe data/artstyle/semoji-voice-bands.json               ← 사본. 고치지 않는다
```

왜 v3가 소유자인가 — 원고와 그림체를 만드는 쪽이기 때문이다. adobe는 완성된
것을 받아 화면으로 옮긴다. **만드는 쪽이 기준을 갖는다.**

---

## 목록과 잠금

공유 파일 목록은 `auto_agent/data/spec/shared.json`에 있다.
현재 해시는 `shared.lock.json`에 굳어 있고, 두 저장소가 같은 잠금 파일을 본다.

```bash
python3 scripts/spec_sync.py --check    # 어긋난 것이 있는지 (종료코드 1)
python3 scripts/spec_sync.py --push     # 소유자 사본을 밀어 넣고 잠금 갱신
```

adobe 쪽에서는 v3가 없어도 확인할 수 있다.

```bash
python3 scripts/spec_check.py           # 잠금 해시와 대조
```

---

## 언제 돌리나

| 시점 | 명령 |
|---|---|
| 공유 파일을 고친 직후 | `spec_sync.py --push` (v3에서) |
| adobe 작업을 시작할 때 | `spec_check.py` (adobe에서) |
| 커밋 전 | `spec_sync.py --check` |

**고친 뒤 push를 잊으면 다음 사람이 옛 기준으로 작업한다.** 그래서 검사가
종료코드로 실패한다 — 조용히 넘어가지 않는다.

---

## 새 파일을 공유 목록에 넣을 때

`shared.json`에 항목을 더하고 `--push`를 돌린다.

```json
{
 "id": "이름",
 "why": "무엇에 쓰는 파일인지 한 줄",
 "source": "v3에서의 경로",
 "consumers": {"auto_kairos_adobe": "adobe에서의 경로"}
}
```

adobe의 `scripts/spec_check.py`의 `PATHS`에도 같은 id를 더한다.

**아무 파일이나 넣지 않는다.** 공유 대상은 **양쪽이 판단 근거로 쓰는 데이터**다 —
실측 밴드, 그림체 문법 같은 것. 코드나 프로젝트별 산출물은 공유하지 않는다.

---

## 지금 공유 중인 것

| id | 무엇 |
|---|---|
| `semoji-voice-bands` | 세모지 문체 실측 밴드(47편) — 원고 게이트의 문턱 |
| `semoji-drawing-style` | 세모지 그림체 문법 — 실측 등신·외곽선·명암 계단 |
