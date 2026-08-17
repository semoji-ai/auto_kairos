# 다른 컴퓨터를 5.0으로 옮기기

> **깃 풀만으로는 안 됩니다.** 저장소 주소가 바뀌었고, 훅은 한 번 켜 줘야
> 돌기 시작합니다. 아래 두 가지를 각 컴퓨터에서 한 번씩만 하면 됩니다.

---

## 왜 자동이 아닌가

세 가지가 걸립니다.

| | 사정 |
|---|---|
| 주소 | 옛 이름(`auto_kairos_v3`)은 **응답하지 않습니다.** 리다이렉트가 없어 `git pull`이 「Repository not found」로 끝납니다 |
| 훅 | `post-merge` 훅은 `core.hooksPath`가 켜져 있어야 돕니다. 그 설정은 저장소가 아니라 **각 컴퓨터의 로컬 설정**이라 따라가지 않습니다 |
| adobe | 옛 저장소(`auto_kairos_adobe`)는 아직 살아 있습니다. 그대로 두면 두 곳에서 갈라집니다 |

---

## ① v3가 깔린 컴퓨터

```bash
cd <auto_kairos_v3 가 있는 경로>

# 주소를 새 저장소로 돌린다
git remote set-url origin https://github.com/semoji-ai/auto_kairos.git

git pull origin main
./install.sh            # 훅 활성화 + 패키지·CEP 심링크·공유 규격까지 한 번에
```

`install.sh`를 한 번 돌리고 나면 **그다음부터는 `git pull`만으로 따라옵니다** —
파이썬 패키지·npm·Remotion 번들·adobe 패키지·공유 규격을 훅이 알아서 맞춥니다.

폴더 이름은 `auto_kairos_v3`인 채로 둬도 됩니다. 신경 쓰이면 바꾸고 옛 이름으로
심링크를 걸어 두면 됩니다(이 컴퓨터가 그렇게 되어 있습니다).

```bash
mv auto_kairos_v3 auto_kairos && ln -s auto_kairos auto_kairos_v3
```

---

## ② adobe가 깔린 컴퓨터

**옛 저장소에서 새로 작업하지 마세요.** 내용은 이미 `auto_kairos/adobe/`로
전부 넘어와 있고 커밋 이력도 보존돼 있습니다.

```bash
# 새 자리에서 이어서 한다
cd <auto_kairos 경로>/adobe

# CEP 확장 심링크를 새 경로로 다시 건다 (AE는 정해진 폴더만 읽는다)
rm -f ~/Library/Application\ Support/Adobe/CEP/extensions/com.autokairos.pd
ln -s "$PWD/cep/com.autokairos.pd" \
      ~/Library/Application\ Support/Adobe/CEP/extensions/com.autokairos.pd
```

옛 저장소 폴더는 지우지 말고 당분간 두되, **새 커밋은 하지 않습니다.**
자세한 것은 `adobe/HANDOFF-5.0-monorepo.md`에 있습니다.

---

## 잘 옮겨졌는지 확인

```bash
git log --oneline -1              # 5.0 이후 커밋이 보이면 됨
git config core.hooksPath         # .githooks 가 나와야 함
ls adobe/backend                  # adobe가 안에 들어와 있음
python3 adobe/scripts/spec_check.py   # 공유 규격이 v3 판과 같은지
```

---

## 새 컴퓨터라면

```bash
git clone https://github.com/semoji-ai/auto_kairos.git
cd auto_kairos && ./install.sh
```

이 경우는 한 줄로 끝납니다.
