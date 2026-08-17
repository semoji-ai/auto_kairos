# 다른 컴퓨터를 5.0으로 옮기기

> **`git pull` 한 번이면 코드는 다 옵니다.** adobe까지 저장소 안에 들어와
> 있으므로 따로 받을 것이 없습니다. 손이 가는 것은 딱 두 가지입니다.

---

## 먼저 — 주소는 그대로입니다

저장소는 처음부터 `semoji-ai/auto_kairos`였습니다. 로컬 폴더 이름만
`auto_kairos_v3`였을 뿐입니다. **원격 주소를 건드릴 필요가 없습니다.**

```bash
git remote -v      # semoji-ai/auto_kairos 가 나오면 그대로 두면 됩니다
```

---

## ① 받기

```bash
cd <auto_kairos_v3 또는 auto_kairos 폴더>
git pull origin main
```

이것으로 `adobe/`·새 스크립트·문서가 전부 들어옵니다.

---

## ② 한 번만 — 훅 켜기

```bash
./install.sh
```

`post-merge` 훅은 `core.hooksPath` 설정이 있어야 도는데, 이 설정은 저장소가
아니라 **각 컴퓨터의 `.git/config`**에 있습니다. 그래서 pull 로는 따라오지
않고 한 번은 켜 줘야 합니다.

한 번 켜고 나면 **그다음부터는 `git pull`만으로 끝납니다** — 파이썬 패키지·
npm·Remotion 번들·adobe 패키지·공유 규격을 훅이 알아서 맞춥니다.

---

## ③ adobe를 쓰는 컴퓨터라면 — CEP 심링크

AE는 정해진 폴더에서만 확장을 읽습니다. 경로가 저장소 안으로 옮겨졌으니
다시 걸어야 합니다.

```bash
cd <auto_kairos 폴더>/adobe
rm -f ~/Library/Application\ Support/Adobe/CEP/extensions/com.autokairos.pd
ln -s "$PWD/cep/com.autokairos.pd" \
      ~/Library/Application\ Support/Adobe/CEP/extensions/com.autokairos.pd
```

옛 `auto_kairos_adobe` 저장소는 아직 살아 있지만 **거기서 새 커밋은 하지
마세요.** 내용은 이력까지 전부 `auto_kairos/adobe/`로 넘어와 있습니다.
자세한 것은 `adobe/HANDOFF-5.0-monorepo.md`에 있습니다.

---

## 폴더 이름 (선택)

`auto_kairos_v3`인 채로 둬도 아무 문제 없습니다. 맞추고 싶으면 옛 이름으로
심링크를 남기세요 — 여기 컴퓨터가 그렇게 되어 있습니다.

```bash
mv auto_kairos_v3 auto_kairos && ln -s auto_kairos auto_kairos_v3
```

---

## 잘 됐는지 확인

```bash
git log --oneline -1
git config core.hooksPath      # .githooks 가 나와야 함
ls adobe/backend               # adobe가 안에 들어와 있음
python3 adobe/scripts/spec_check.py   # 공유 규격이 v3 판과 같은지
```

---

## 새 컴퓨터라면

```bash
git clone https://github.com/semoji-ai/auto_kairos.git
cd auto_kairos && ./install.sh
```
