import json

from auto_agent import cli


def test_format_autoresearch_summary_includes_top_candidates():
    text = cli._format_autoresearch_summary(
        "이로미즘",
        [
            {
                "title": "트럼프 관세가 다시 오면, 투자자는 어디로 이동해야 하나",
                "topic_score": 720,
                "hook": "관세는 뉴스가 아니라 자산 재배치 신호다.",
                "timing_window": "지금 바로",
                "bridge_reason": "관세 뉴스에서 바로 자산 재배치로 넘어가야 한다.",
            },
            {
                "title": "중동 전쟁이 내 자산을 흔드는 진짜 경로",
                "topic_score": 504,
            },
        ],
    )
    assert "[720점]" in text
    assert "트럼프 관세가 다시 오면" in text
    assert "타이밍: 지금 바로" in text
    assert "브리지:" in text


def test_notify_plan_result_sends_completion_and_summary(monkeypatch, tmp_path):
    vault_dir = tmp_path / "vault"
    planning_dir = vault_dir / "insights" / "planning"
    planning_dir.mkdir(parents=True)
    today = "2026-04-12"
    (planning_dir / f"{today}-이로미즘-autoresearch.json").write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "title": "상여금 10억이면 실제 세금은 얼마일까",
                        "topic_score": 600,
                        "hook": "10억을 받아도 내 통장에 안 남는다.",
                        "timing_window": "지금 바로",
                        "bridge_reason": "보너스 뉴스에서 실수령 구조 설명으로 넘어간다.",
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    sent_messages = []

    class FakeNotifier:
        def __init__(self, webhook_url: str):
            self.webhook_url = webhook_url

        def send(self, message: str):
            sent_messages.append(message)
            return True

    import auto_agent.modules.data_collector.discord_notifier as discord_notifier

    monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.com/webhook")
    monkeypatch.delenv("DISCORD_STAGE0_CHANNEL_ID", raising=False)
    monkeypatch.setattr(discord_notifier, "DiscordNotifier", FakeNotifier)
    cli._notify_plan_result("이로미즘", "AutoResearch (2라운드)")

    assert len(sent_messages) == 2
    assert "기획안 생성 완료" in sent_messages[0]
    assert "[600점]" in sent_messages[1]
