"""
Duplicate Check — N-gram 기반 원고 중복 감지

pipeline.json phase_2 step_3: final_manuscript.md 내 반복 문장/구절 탐지
blocking=false이므로 실패해도 파이프라인 계속 진행.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from auto_agent.scripts.project_paths import get_project_dir


def extract_sentences(text: str) -> list:
    """텍스트를 문장 단위로 분리."""
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"#{1,6}\s+.*", "", text)  # 마크다운 헤더 제거
    sentences = re.split(r"[.!?。]\s*", text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def find_ngram_duplicates(sentences: list, n: int = 3) -> list:
    """N-gram 중복 탐지."""
    ngrams = Counter()
    for sent in sentences:
        words = sent.split()
        for i in range(len(words) - n + 1):
            gram = " ".join(words[i:i + n])
            ngrams[gram] += 1

    duplicates = []
    for gram, count in ngrams.items():
        if count >= 3:
            duplicates.append({"ngram": gram, "count": count, "n": n})

    return sorted(duplicates, key=lambda x: x["count"], reverse=True)


def find_sentence_duplicates(sentences: list) -> list:
    """완전 동일 문장 탐지."""
    counter = Counter(sentences)
    return [
        {"sentence": sent, "count": count}
        for sent, count in counter.items()
        if count >= 2
    ]


def main():
    project_dir = get_project_dir()
    manuscript = project_dir / "final_manuscript.md"

    if not manuscript.exists():
        print(f"WARNING: {manuscript} not found — 스킵")
        sys.exit(0)

    print(f"Duplicate Check: {manuscript}")
    text = manuscript.read_text(encoding="utf-8")
    sentences = extract_sentences(text)
    print(f"  문장 수: {len(sentences)}")

    # 1. 완전 동일 문장
    sent_dups = find_sentence_duplicates(sentences)

    # 2. N-gram (3~5)
    ngram_dups = []
    for n in [3, 4, 5]:
        ngram_dups.extend(find_ngram_duplicates(sentences, n))

    # 결과
    result = {
        "total_sentences": len(sentences),
        "sentence_duplicates": sent_dups[:20],
        "ngram_duplicates": ngram_dups[:30],
        "severity": "warning" if (sent_dups or ngram_dups) else "ok",
    }

    output_path = project_dir / "duplicate_check.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if sent_dups:
        print(f"  완전 중복 문장: {len(sent_dups)}개")
        for d in sent_dups[:5]:
            print(f"    [{d['count']}회] {d['sentence'][:60]}...")
    if ngram_dups:
        print(f"  N-gram 반복: {len(ngram_dups)}개")
    if not sent_dups and not ngram_dups:
        print("  중복 없음.")

    print(f"\nOutput: {output_path}")


if __name__ == "__main__":
    main()
