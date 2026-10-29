"""번역 파일(l10n/<lang>.json) 갱신: 쓰기 직전에 다시 읽어 자기 섹션의 해당 항목만 바꿈 —
여러 단계(TTS 재번역·그림 문구 번역)가 동시에 돌아도 서로의 수정을 덮어쓰지 않게."""
import fcntl
import json
import os


def update_entries(path, section, entries, replace=False):
    """section의 entries(키→값)를 반영. replace=True면 값을 통째로, 아니면 dict끼리 합침."""
    lock = open(path + ".lock", "w")
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        d = json.load(open(path)) if os.path.exists(path) else {}
        sec = d.setdefault(section, {})
        for k, v in entries.items():
            if replace or not isinstance(sec.get(k), dict) or not isinstance(v, dict):
                sec[k] = v
            else:
                sec[k].update(v)
        tmp = path + ".tmp"
        json.dump(d, open(tmp, "w"), ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        return d
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN); lock.close()
