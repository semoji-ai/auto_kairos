import wave

from auto_agent.scripts.build_manifest import _probe_mp3_duration_local


def test_manifest_reads_exact_pcm_duration(tmp_path):
    path = tmp_path / 'timing.wav'
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(44100)
        audio.writeframes(b'\0\0' * 44100)
    assert _probe_mp3_duration_local(path) == 1.0
