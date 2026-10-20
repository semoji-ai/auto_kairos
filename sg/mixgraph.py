"""ffmpeg 오디오 믹스 조각: 소스 자르기·지연·볼륨(키프레임 선형)·페이드."""


def volume_expr(gain, keys, key_base, clip_src_in, clip_t):
    """볼륨 표현식(출력 타임라인 t 기준). keys=[[시각, 선형값]]: key_base='clip'이면 조각 시작 기준,
    'media'면 소스 시각(→ 조각이 소스 clip_src_in부터 출력 clip_t에 놓임)."""
    if not keys:
        return f"{gain:g}"
    pts = sorted(((k - clip_src_in if key_base == "media" else k) + clip_t, v) for k, v in keys)
    expr = f"{pts[-1][1]:g}"
    for (t0, v0), (t1, v1) in reversed(list(zip(pts, pts[1:]))):
        lin = f"({v0:g}+({v1:g}-{v0:g})*(t-{t0})/{max(1e-6, t1 - t0)})"
        expr = f"if(between(t,{t0},{t1}),{lin},if(gte(t,{t1}),{expr},{expr}))"
    return f"if(lt(t,{pts[0][0]}),{pts[0][1]:g},{expr})"


def entry(file, t, src_in, dur, gain, keys, key_base, fade_out, k=0):
    """입력 인자(소스 구간)와 필터 체인(48k 스테레오, 지연, 볼륨, 끝 페이드)."""
    args = ["-ss", f"{src_in}", "-t", f"{dur}", "-i", file]
    ms = int(round(t * 1000))
    flt = f"aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}"
    flt += f",volume='{volume_expr(gain, keys, key_base, src_in, t)}':eval=frame"
    if fade_out > 0:
        flt += f",afade=t=out:st={t + dur - fade_out:.3f}:d={fade_out:.3f}"
    return args, flt
