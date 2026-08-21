"""순수 라우팅 — (method, path, query, body, ctx) -> (status, dict). 소켓 의존 없음."""
from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

from backend import projects, skills_cfg, sessions, pipeline, imagegen, scenes, search, media, tts, manifest, assistant, llm, motion, v3_import, edits, vault, subtitles, chartgen, themes, vectorize, srt
from backend.codex_runner import run_skill
from backend.jobs import run_async

VERSION = "0.2.0-m2"

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"


def _find_scene(data: dict, sn) -> dict | None:
    """씬 번호로 씬을 찾는다. **형을 맞춰서** 찾는다.

    패널이 씬 번호를 문자열로 보내는 자리가 여럿 있다(DOM 속성에서 바로
    꺼내 쓰는 곳). 파이썬에서 "41" == 41 은 거짓이라, 멀쩡한 씬을 눌러도
    「씬 없음」이 떴다. 프런트를 한 군데씩 고치는 것보다 받는 쪽에서
    맞추는 편이 확실하다 — 새 호출이 생겨도 같은 일이 안 난다.

    **다만 소수점 씬 번호를 뭉개면 안 된다.** `int()` 로 맞추면 18.25 가
    18 이 되어 정수 형제 씬을 찾아 준다. 그 씬이 실재하므로 「성공」으로
    보이고, 18.25 에 하려던 일이 18 에 적용된다 — 한 번의 조작으로 두 씬이
    어긋난다. LS 프로젝트의 소수점 씬 19개가 전부 이 경우였다.
    """
    if sn is None:
        return None
    try:
        key = float(sn)
    except (TypeError, ValueError):
        return None
    for s in data.get("scenes") or []:
        try:
            if float(s.get("sceneNumber")) == key:
                return s
        except (TypeError, ValueError):
            continue
    return None


def _codex_status() -> str:
    if shutil.which("codex") is None:
        return "not_installed"
    return "ready" if (Path.home() / ".codex" / "auth.json").exists() else "not_authenticated"



def handle_request(method: str, path: str, query: dict, body: dict | None, ctx: dict):
    try:
        return _dispatch(method, path, query, body, ctx)
    except Exception as e:
        return 500, {"error": f"내부 오류: {e}"}


def _dispatch(method: str, path: str, query: dict, body: dict | None, ctx: dict):
    root: Path = ctx["root"]
    p = path.rstrip("/") or "/"

    if method == "GET" and p == "/health":
        return 200, {"backend_status": "connected", "codex_status": _codex_status(),
                     "version": VERSION, "root": str(root)}

    if method == "GET" and p == "/api/projects":
        return 200, {"projects": projects.scan_projects(root)}

    if method == "POST" and p == "/api/projects/load":
        pid = (body or {}).get("project_id", "")
        try:
            return 200, projects.load_project(root, pid)
        except FileNotFoundError as e:
            return 404, {"error": str(e)}

    if method == "POST" and p == "/api/projects/create":
        b = body or {}
        title = (b.get("title") or "").strip()
        if not title:
            return 400, {"error": "title 필요"}
        info = projects.create_project(
            root, title,
            channel=b.get("channel", "semoji"),
            duration=b.get("duration", "1분"))
        return 200, info

    # 목록에서 빼기 — **지우지 않는다.** `_archive/` 로 옮긴다.
    # 잘못 가져온 프로젝트가 목록에 쌓여 헷갈리는 것이 문제이지, 파일이
    # 아까운 것은 아니다. 되돌리려면 폴더를 도로 꺼내면 된다.
    if method == "POST" and p == "/api/projects/archive":
        pid = ((body or {}).get("project_id") or "").strip()
        proj_dir = root / pid
        if not pid or not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        if proj_dir.resolve().parent != root.resolve():
            return 400, {"error": "잘못된 경로"}
        box = root / "_archive"
        box.mkdir(exist_ok=True)
        dst = box / pid
        i = 2
        while dst.exists():
            dst = box / f"{pid}_{i}"
            i += 1
        shutil.move(str(proj_dir), str(dst))
        return 200, {"ok": True, "moved_to": str(dst)}

    if method == "POST" and p == "/api/projects/import-v3":
        b = body or {}
        path = (b.get("path") or "").strip()
        if not path:
            return 400, {"error": "path 필요(v3 output 프로젝트 전체 경로)"}
        res = v3_import.import_v3(root, path, title=b.get("title"))
        return (200, res) if "error" not in res else (422, res)

    if method == "POST" and p == "/api/skills/run":
        b = body or {}
        pid, skill = b.get("project_id", ""), b.get("skill_name", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": f"project not found: {pid}"}
        try:
            cfg = skills_cfg.load_config(SKILLS_DIR, skill)
        except FileNotFoundError:
            return 404, {"error": f"skill not found: {skill}"}
        miss = skills_cfg.missing_inputs(cfg, proj_dir)
        if miss:
            return 422, {"error": f"입력 누락: {', '.join(miss)}"}
        jobs = ctx["jobs"]
        jid = jobs.create(skill, pid)
        prompt = skills_cfg.build_prompt(SKILLS_DIR, skill, cfg, proj_dir)
        out = proj_dir / cfg["output"]
        out.parent.mkdir(parents=True, exist_ok=True)
        schema = (SKILLS_DIR / skill / cfg["schema"]) if cfg.get("schema") else None
        sid = sessions.load_session(proj_dir)
        result = llm.run_orchestrator(
            prompt, proj_dir,
            session_id=sid,
            output_schema=str(schema) if schema else None,
            output_last=str(out),
            on_line=lambda ln: jobs.append_log(jid, ln),
        )
        if result.get("session_id"):
            sessions.save_session(proj_dir, result["session_id"])
        if result["returncode"] == 0 and out.exists():
            jobs.set_status(jid, "completed", artifact_paths=[str(out)])
        else:
            jobs.set_status(jid, "failed", error=f"rc={result['returncode']}")
        return 200, {"job_id": jid, "status": jobs.get(jid)["status"]}

    if method == "GET" and p == "/api/pipeline/status":
        pid = query.get("project_id", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": f"project not found: {pid}"}
        stages = []
        for name in pipeline.PIPELINE:
            out = skills_cfg.load_config(SKILLS_DIR, name)["output"]
            stages.append({"name": name, "output": out,
                           "done": (proj_dir / out).exists()})
        return 200, {"stages": stages}

    if method == "POST" and p == "/api/pipeline/run-stage":
        b = body or {}
        pid = b.get("project_id", "")
        stage = b.get("stage", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": f"project not found: {pid}"}
        if stage not in pipeline.PIPELINE:
            return 400, {"error": f"unknown stage: {stage}"}
        jobs = ctx["jobs"]
        jid = jobs.create("pipeline-stage", pid)
        def _do_stage(proj_dir=proj_dir, jid=jid, stage=stage):
            r = pipeline.run_one(SKILLS_DIR, proj_dir, stage,
                                 on_line=lambda ln: jobs.append_log(jid, ln))
            if r["status"] != "completed":
                raise RuntimeError(f"{stage}: {r.get('error')}")
            jobs.set_status(jid, "running", artifact_paths=[r["output"]])
            return {"status": "completed", "stage": stage, "output": r["output"]}
        run_async(jobs, jid, _do_stage)
        return 200, {"job_id": jid, "status": "running"}

    if method == "POST" and p == "/api/pipeline/run":
        b = body or {}
        pid = b.get("project_id", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": f"project not found: {pid}"}
        jobs = ctx["jobs"]
        jid = jobs.create("pipeline", pid)
        def _do(proj_dir=proj_dir, jid=jid):
            res = pipeline.run_pipeline(SKILLS_DIR, proj_dir,
                                        on_line=lambda ln: jobs.append_log(jid, ln))
            if res["status"] != "completed":
                raise RuntimeError(f"{res.get('stage')}: {res.get('error')}")
            jobs.set_status(jid, "running", artifact_paths=[res["final"]])
            return {"status": "completed", "completed": res.get("completed", [])}
        run_async(jobs, jid, _do)
        return 200, {"job_id": jid, "status": "running"}

    if method == "POST" and p == "/api/characters/generate":
        b = body or {}
        pid = b.get("project_id", "")
        name = (b.get("name") or "").strip()
        looks = (b.get("looks") or "").strip()
        if not pid or not name or not looks:
            return 400, {"error": "project_id, name, looks 필요"}
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        jobs = ctx["jobs"]
        jid = jobs.create("character", pid)
        res = imagegen.generate_character(
            proj_dir, name, looks,
            on_line=lambda ln: jobs.append_log(jid, ln))
        ok = res.get("status") == "completed"
        jobs.set_status(jid, "completed" if ok else "failed",
                        artifact_paths=[str(proj_dir / "characters")])
        return 200, {"job_id": jid, "status": jobs.get(jid)["status"], "character": res}

    if method == "GET" and p == "/api/characters/list":
        pid = query.get("project_id", "")
        cd = root / pid / "characters"
        if not cd.is_dir():
            return 200, {"images": []}
        names = sorted(f.name for f in cd.glob("*.png"))
        return 200, {"images": names, "dir": str(cd)}

    if method == "GET" and p == "/api/themes":
        return 200, {"themes": themes.list_themes()}

    if method == "POST" and p == "/api/themes/set-project":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        res = scenes.set_project_theme(proj_dir, b.get("theme_id", ""))
        if res.get("ok"):
            vault.log_work(proj_dir, "set_theme", {"theme": b.get("theme_id")})
        return (200, res) if res.get("ok") else (404, res)

    if method == "POST" and p == "/api/themes/set-scene":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        res = scenes.set_scene_theme(proj_dir, b.get("sceneNumber"), b.get("theme_id"))
        return (200, res) if res.get("ok") else (404, res)

    if method == "GET" and p == "/api/tokens":          # 디자인 토큰 — 시트 미리보기가 사용
        tp = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "ae_tokens.json"
        try:
            return 200, json.loads(tp.read_text(encoding="utf-8"))
        except Exception:
            return 200, {}

    if method == "GET" and p == "/api/scenes":
        pid = query.get("project_id", "")
        return 200, scenes.load_scenes(root / pid)

    if method == "POST" and p == "/api/scenes/narration":
        b = body or {}
        pid = b.get("project_id", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        sn = b.get("sceneNumber")
        res = scenes.update_narration(proj_dir, sn, b.get("narration", ""))
        return (200, res) if res.get("ok") else (404, res)

    if method == "POST" and p == "/api/scenes/texts":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        res = scenes.update_texts(proj_dir, b.get("sceneNumber"),
                                  narration_tts=b.get("narration_tts"),
                                  subtitle_text=b.get("subtitle_text"))
        return (200, res) if res.get("ok") else (404, res)

    if method == "POST" and p in ("/api/scenes/add", "/api/scenes/delete",
                                  "/api/scenes/split", "/api/scenes/merge"):
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        if p == "/api/scenes/add":
            return 200, scenes.add_scene(proj_dir, after_number=b.get("after"),
                                         narration=b.get("narration", ""), title=b.get("title", ""))
        if p == "/api/scenes/delete":
            return 200, scenes.remove_scene(proj_dir, b.get("sceneNumber"))
        if p == "/api/scenes/split":
            return 200, scenes.split_scene(proj_dir, b.get("sceneNumber"),
                                           first=b.get("first"), second=b.get("second"))
        return 200, scenes.merge_scenes(proj_dir, b.get("sceneNumber"))

    if method == "POST" and p in ("/api/scenes/tts", "/api/tts/all"):
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        data = scenes.load_scenes(proj_dir)
        jobs = ctx["jobs"]
        voice = b.get("voice")
        if p == "/api/tts/all":
            jid = jobs.create("tts-all", b.get("project_id", ""))
            def _do(proj_dir=proj_dir, data=data, voice=voice, jid=jid):
                results = []
                for s in data["scenes"]:
                    text = scenes.tts_text(s)
                    res = tts.generate_scene_tts(proj_dir, s.get("sceneId"), text, voice=voice)
                    if res.get("status") == "completed":   # 실제 합성 텍스트를 확정 저장
                        scenes.update_texts(proj_dir, s.get("sceneNumber"), narration_tts=text)
                    results.append({"sceneNumber": s.get("sceneNumber"), **res})
                    jobs.append_log(jid, f"S{s.get('sceneNumber')}: {res.get('status')}")
                if not any(x.get("status") == "completed" for x in results):
                    raise RuntimeError("TTS 전체 실패")
                jobs.set_status(jid, "running", artifact_paths=[str(proj_dir / "audio")])
                done = sum(1 for x in results if x.get("status") == "completed")
                vault.log_work(proj_dir, "tts_all", f"TTS {done}/{len(results)}개 생성")
                return {"results": results}
            run_async(jobs, jid, _do)
            return 200, {"job_id": jid, "status": "running"}
        sn = b.get("sceneNumber")
        sc = _find_scene(data, sn)
        if not sc:
            return 404, {"error": "씬 없음"}
        text = b.get("text") if (b.get("text") or "").strip() else scenes.tts_text(sc)
        if not text.strip():
            return 422, {"error": "내레이션 비어있음"}
        jid = jobs.create("tts", b.get("project_id", ""))
        res = tts.generate_scene_tts(proj_dir, sc.get("sceneId"), text, voice=voice)
        if res.get("status") == "completed":               # 실제 합성 텍스트를 확정 저장
            scenes.update_texts(proj_dir, sn, narration_tts=text)
        jobs.set_status(jid, "completed" if res.get("status") == "completed" else "failed",
                        artifact_paths=[str(proj_dir / "audio")])
        return 200, {"job_id": jid, "result": res}

    if method == "POST" and p == "/api/scenes/motion":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        jobs = ctx["jobs"]
        jid = jobs.create("motion", b.get("project_id", ""))
        def _do(proj_dir=proj_dir, sn=b.get("sceneNumber"), jid=jid):
            res = motion.plan_scene_motion(proj_dir, sn,
                                           on_line=lambda ln: jobs.append_log(jid, ln))
            if "error" in res:
                raise RuntimeError(res["error"])
            nmv = sum(len(L.get("moves", [])) for L in res.get("layers", []))
            vault.log_work(proj_dir, "plan_motion",
                           f"씬{sn} 모션 {nmv}개 + 카메라 {(res.get('camera') or {}).get('type')}")
            return {"plan": res}
        run_async(jobs, jid, _do)
        return 200, {"job_id": jid, "status": "running"}

    if method == "POST" and p == "/api/assembly/manifest":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        mres = manifest.build_manifest(proj_dir, only_scene=b.get("sceneNumber"),
                                       only_scenes=b.get("sceneNumbers"))
        scope = b.get("sceneNumbers") or ([b["sceneNumber"]] if b.get("sceneNumber") else None)
        vault.log_work(proj_dir, "assemble",
                       f"매니페스트 빌드(씬 {mres.get('scenes')}개"
                       + (f", 씬 {','.join(str(x) for x in scope)}만" if scope else "") + ")")
        return 200, mres

    if method == "POST" and p == "/api/subtitles/build":
        proj_dir = root / (body or {}).get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        res = subtitles.build_subtitles(proj_dir, only_scenes=(body or {}).get("sceneNumbers"))
        tokens_path = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "ae_tokens.json"
        if tokens_path.is_file():
            res["ae_tokens"] = str(tokens_path)
        vault.log_work(proj_dir, "subtitles", f"말자막 {res['lines']}줄 생성")
        return 200, res

    if p == "/api/tts/settings" and method in ("GET", "POST"):
        pid = (query.get("project_id") if method == "GET" else (body or {}).get("project_id")) or ""
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        if method == "POST":
            b = body or {}
            tts.set_tts_config(proj_dir, style=b.get("style"), voice_id=b.get("voice_id"),
                               model=b.get("model"), voice_settings=b.get("voice_settings"))
        return 200, {"config": tts.effective_voice(proj_dir), "presets": tts.load_voice_presets()}

    if p == "/api/llm/settings" and method in ("GET", "POST"):
        if method == "POST":
            b = body or {}
            llm.set_orchestrator(b.get("orchestrator", ""), claude_model_name=b.get("claude_model"))
        return 200, {"orchestrator": llm.get_orchestrator(), "choices": list(llm.VALID),
                     "claude_model": llm.claude_model()}

    if method == "POST" and p == "/api/assistant":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        instruction = (b.get("instruction") or "").strip()
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        if not instruction:
            return 400, {"error": "instruction 필요"}
        jobs = ctx["jobs"]
        jid = jobs.create("assistant", b.get("project_id", ""))
        def _do(proj_dir=proj_dir, instruction=instruction, jid=jid):
            return assistant.run_assistant(proj_dir, instruction,
                                           on_event=lambda ln: jobs.append_log(jid, ln),
                                           should_cancel=lambda: jobs.is_cancelled(jid))
        run_async(jobs, jid, _do)
        return 200, {"job_id": jid, "status": "running"}

    # 재생성 모달이 고를 수 있는 참조 목록. 인물 시트와 이미 만들어 둔 씬
    # 이미지를 함께 낸다 — 「그 인물로」와 「저 컷과 같은 자리에서」가 둘 다
    # 필요하고, 지금은 전자만 전역 하나로 걸 수 있었다.
    if method == "GET" and p == "/api/scenes/image-refs":
        pid = (query or {}).get("project_id", "")
        proj_dir = root / (pid[0] if isinstance(pid, list) else pid)
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        out = {"characters": [], "scenes": []}
        cdir = proj_dir / "characters"
        if cdir.is_dir():
            for f in sorted(cdir.glob("*.png")):
                out["characters"].append({
                    "name": f.stem.replace("char_", ""),
                    "rel": f.relative_to(proj_dir).as_posix()})
        sdir = proj_dir / "storyboard"
        if sdir.is_dir():
            by_scene = {}
            for s in scenes.load_scenes(proj_dir).get("scenes", []):
                ref = s.get("imageRef") or ""
                if ref and (proj_dir / ref).is_file():
                    by_scene[s.get("sceneNumber")] = ref
            for n in sorted(by_scene, key=lambda x: (x is None, x)):
                out["scenes"].append({"sceneNumber": n, "rel": by_scene[n]})
        return 200, out

    if method == "POST" and p == "/api/scenes/image":
        b = body or {}
        pid = b.get("project_id", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        sn = b.get("sceneNumber")
        data = scenes.load_scenes(proj_dir)
        scene = _find_scene(data, sn)
        if not scene:
            return 404, {"error": f"scene {sn} 없음"}
        sid = scene.get("sceneId")
        char = (b.get("character") or "").strip()
        character_ref = None
        if char:
            cref = proj_dir / "characters" / f"char_{char}.png"
            if cref.exists():
                character_ref = str(cref)
        jobs = ctx["jobs"]
        jid = jobs.create("scene-image", pid)
        name = scenes.new_scene_image_name(sid)
        # 모달에서 고른 참조들. 프로젝트 밖을 가리키는 경로는 받지 않는다.
        extra_refs = []
        for r in (b.get("refs") or []):
            fp = (proj_dir / str(r)).resolve()
            if fp.is_file() and proj_dir.resolve() in fp.parents:
                extra_refs.append(str(fp))
        prompt_in = (b.get("prompt") or "").strip()
        res = imagegen.generate_one(
            proj_dir, name,
            prompt_in or scene.get("image_prompt", "") or scene.get("visual_summary", ""),
            subdir="storyboard", character_ref=character_ref, extra_refs=extra_refs,
            on_line=lambda ln: jobs.append_log(jid, ln))
        # 고쳐 넣은 프롬프트는 남긴다 — 다음에 모달을 열면 이어서 고칠 수 있다.
        if prompt_in and prompt_in != (scene.get("image_prompt") or ""):
            scenes.set_image_prompt(proj_dir, sn, prompt_in)
        if res.get("status") == "completed":
            from pathlib import Path as _P
            rel = _P(res["path"]).relative_to(proj_dir).as_posix()
            scenes.set_image_ref(proj_dir, sn, rel)
        jobs.set_status(jid, "completed" if res.get("status") == "completed" else "failed",
                        artifact_paths=[str(proj_dir / "storyboard")])
        return 200, {"job_id": jid, "result": res}

    if method == "POST" and p == "/api/assets/generate":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        cat = (b.get("category") or "").strip()
        prompt = (b.get("prompt") or "").strip()
        if cat not in ("background", "prop"):
            return 400, {"error": "category는 background 또는 prop"}
        if not prompt:
            return 400, {"error": "prompt 필요"}
        char = (b.get("character") or "").strip()
        char_ref = None
        if char:
            cref = proj_dir / "characters" / f"char_{char}.png"
            if cref.exists():
                char_ref = str(cref)
        jobs = ctx["jobs"]
        jid = jobs.create("asset", b.get("project_id", ""))
        name = f"{cat}_{uuid.uuid4().hex[:6]}.png"
        res = imagegen.generate_asset(
            proj_dir, name, prompt, char_ref=char_ref, subdir="images",
            on_line=lambda ln: jobs.append_log(jid, ln))
        jobs.set_status(jid, "completed" if res.get("status") == "completed" else "failed",
                        artifact_paths=[str(proj_dir / "images")])
        return 200, {"job_id": jid, "result": res}

    if method == "POST" and p == "/api/scenes/map-image":
        # 패널(MapLibre 캔버스 캡처)이 보낸 dataURL PNG 저장 → 씬 이미지로 링크(버전 파일명·무삭제)
        import base64
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        sn = b.get("sceneNumber")
        sid = scenes.scene_id_for(proj_dir, sn)
        if not sid:
            return 404, {"error": f"scene {sn} 없음"}
        du = b.get("dataUrl", "")
        if not du.startswith("data:image/png;base64,"):
            return 400, {"error": "dataUrl 형식 오류(PNG base64 필요)"}
        sb_dir = proj_dir / "storyboard"
        sb_dir.mkdir(exist_ok=True)
        name = f"map_{sid}_{uuid.uuid4().hex[:6]}.png"
        (sb_dir / name).write_bytes(base64.b64decode(du.split(",", 1)[1]))
        geo = b.get("geo")                                  # 마커/경로 픽셀 좌표 — AE 셰이프/텍스트 재료
        if geo:
            (sb_dir / f"{name}.geo.json").write_text(
                json.dumps(geo, ensure_ascii=False, indent=2), encoding="utf-8")
        res = scenes.set_image_ref(proj_dir, sn, f"storyboard/{name}")
        vault.log_work(proj_dir, "map_image", {"scene": sn, "file": name})
        return (200, res) if res.get("ok") else (404, res)

    if method == "POST" and p == "/api/scenes/chart-spec":
        # 차트 디자인 명세서 생성(chartagent) — bar 씬의 패턴/모티프 토큰을 AE에 주입
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        if not chartgen.available():
            return 200, {"error": "chartagent 미설치 — CHARTAGENT_ROOT 환경변수 설정 필요"}
        sn = b.get("sceneNumber")
        data = scenes.load_scenes(proj_dir)
        scene = _find_scene(data, sn)
        if not scene:
            return 404, {"error": f"scene {sn} 없음"}
        try:
            res = chartgen.gen_chart_spec(proj_dir, scene)
        except Exception as e:
            return 200, {"error": f"chartagent 실패: {e}"}
        if res.get("ok"):
            vault.log_work(proj_dir, "chart_spec", {"scene": sn, "theme_set": res.get("theme_set")})
        return 200, res

    if method == "POST" and p == "/api/scenes/unlink-image":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        res = scenes.set_image_ref(proj_dir, b.get("sceneNumber"), "")
        return (200, res) if res.get("ok") else (404, res)

    if method == "POST" and p == "/api/scenes/analyze-layers":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        data = scenes.load_scenes(proj_dir)
        sc = _find_scene(data, b.get("sceneNumber"))
        if not sc:
            return 404, {"error": "씬 없음"}
        if not sc.get("_image"):
            return 422, {"error": "씬 이미지 먼저 생성/링크 필요"}
        jobs = ctx["jobs"]
        jid = jobs.create("analyze-layers", b.get("project_id", ""))
        ctx_str = f"제목: {sc.get('title', '')} / 요약: {sc.get('visual_summary', '')}"
        res = imagegen.analyze_scene_layers(
            proj_dir, str(proj_dir / sc["_image"]),
            narration=sc.get("narration", "") or "", context=ctx_str,
            image_prompt=sc.get("image_prompt", "") or "",
            neighbors=scenes.neighbor_context(data.get("scenes", []), b.get("sceneNumber")),
            briefing=vault.read_context(proj_dir),
            on_line=lambda ln: jobs.append_log(jid, ln))
        jobs.set_status(jid, "completed" if res.get("elements") else "failed")
        return 200, {"job_id": jid, "elements": res.get("elements", []),
                     "dropped": res.get("dropped", []), "error": res.get("error")}

    if method == "POST" and p == "/api/scenes/split-layers":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        data = scenes.load_scenes(proj_dir)
        sc = _find_scene(data, b.get("sceneNumber"))
        if not sc:
            return 404, {"error": "씬 없음"}
        if not sc.get("_image"):
            return 422, {"error": "씬 이미지 없음"}
        elements = b.get("elements") or []
        if not elements:
            return 400, {"error": "elements 필요"}
        jobs = ctx["jobs"]
        jid = jobs.create("split-layers", b.get("project_id", ""))
        def _do(proj_dir=proj_dir, sc=sc, elements=elements, jid=jid):
            res = imagegen.split_scene_to_elements(
                proj_dir, str(proj_dir / sc["_image"]), sc.get("sceneId"), elements,
                on_event=lambda r: jobs.append_log(jid, f"{r['name']}: {r['status']}"))
            layers_res = res.get("layers", [])
            elements_completed = any(l.get("status") == "completed" and l.get("name") != "배경"
                                     for l in layers_res)
            if not elements_completed:
                missing = res.get("missing") or []
                if missing:
                    raise RuntimeError("레이어 분리 실패 — 못 만든 요소: " + ", ".join(missing))
                first_error = next((l.get("error") for l in layers_res if l.get("error")), None)
                if first_error:
                    raise RuntimeError("레이어 분리 전체 실패: " + str(first_error))
                raise RuntimeError("레이어 분리 전체 실패")
            jobs.set_status(jid, "running", artifact_paths=[str(proj_dir / "layers")])
            okn = sum(1 for l in res.get("layers", []) if str(l.get("status", "")).startswith("completed"))
            vault.log_work(proj_dir, "split_layers",
                           f"씬{sc.get('sceneNumber')} 레이어 {okn}개 분리(요소 {len(elements)}+배경)")
            return {"result": res}
        run_async(jobs, jid, _do)
        return 200, {"job_id": jid, "status": "running"}

    if method == "POST" and p == "/api/layers/regenerate":
        b = body or {}
        pid = b.get("project_id", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        data = scenes.load_scenes(proj_dir)
        sc = _find_scene(data, b.get("sceneNumber"))
        if not sc:
            return 404, {"error": "씬 없음"}
        if not sc.get("_image"):
            return 422, {"error": "씬 이미지 없음"}
        layer = (b.get("layer") or "").strip()
        if not layer:
            return 400, {"error": "layer 필요"}
        sid = sc.get("sceneId")
        scene_img = str(proj_dir / sc["_image"])
        jobs = ctx["jobs"]

        jid = jobs.create("layer-regen", pid)
        def _do_regen(proj_dir=proj_dir, scene_img=scene_img, sid=sid, layer=layer, jid=jid):
            res = imagegen.regenerate_layer(
                proj_dir, scene_img, sid, layer,
                on_event=lambda r: jobs.append_log(jid, f"{r.get('name')}: {r.get('status')}"))
            if res.get("error"):
                raise RuntimeError(res["error"])
            if not str((res.get("layer") or {}).get("status", "")).startswith("completed"):
                raise RuntimeError("레이어 재생성 실패")
            jobs.set_status(jid, "running", artifact_paths=[str(proj_dir / "layers")])
            vault.log_work(proj_dir, "layer_regen", f"씬{sc.get('sceneNumber')} 레이어 재생성: {layer}")
            return res
        run_async(jobs, jid, _do_regen)
        return 200, {"job_id": jid, "status": "running"}

    if method == "POST" and p == "/api/layers/state":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        data = scenes.load_scenes(proj_dir)
        sc = _find_scene(data, b.get("sceneNumber"))
        if not sc:
            return 404, {"error": "씬 없음"}
        layer = (b.get("layer") or "").strip()
        if not layer:
            return 400, {"error": "layer 필요"}
        res = imagegen.set_layer_state(
            proj_dir, sc.get("sceneId"), layer,
            hidden=b.get("hidden"), removed=b.get("removed"))
        if res.get("error"):
            return 422, res
        return 200, res

    if method == "POST" and p == "/api/layers/vectorize":
        b = body or {}
        pid = b.get("project_id", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        data = scenes.load_scenes(proj_dir)
        sc = _find_scene(data, b.get("sceneNumber"))
        if not sc:
            return 404, {"error": "씬 없음"}
        stems = [s for s in (b.get("layers") or []) if s]
        if not stems:
            return 400, {"error": "layers 필요"}
        if not vectorize.api_key():
            # 키가 없으면 잡을 시작하지 않는다 — 크레딧도 시간도 쓰지 않는다.
            return 422, {"error": "RECRAFT_API_KEY 없음 — .env 또는 환경변수에 넣어 주세요"}
        sid = sc.get("sceneId")
        force = bool(b.get("force"))
        jobs = ctx["jobs"]
        jid = jobs.create("layer-vectorize", pid)
        def _do_vec(proj_dir=proj_dir, sid=sid, stems=stems, force=force, jid=jid):
            res = vectorize.vectorize_layers(
                proj_dir, sid, stems, force=force,
                on_event=lambda e: jobs.append_log(
                    jid, f"{e['layer']}: {e['status']}" + (f" — {e.get('error','')}"
                                                          if e["status"] == "failed" else "")))
            jobs.set_status(jid, "running", artifact_paths=[str(proj_dir / "layers")])
            vault.log_work(proj_dir, "vectorize",
                           f"씬{sc.get('sceneNumber')} 벡터화 {len(res['ok'])}장"
                           f"(건너뜀 {len(res['skipped'])}, 실패 {len(res['failed'])})")
            return res
        run_async(jobs, jid, _do_vec)
        return 200, {"job_id": jid, "status": "running"}

    if method == "POST" and p == "/api/tools/srt-parse":
        b = body or {}
        cues = srt.parse_srt(b.get("srt") or "")
        if not cues:
            return 422, {"error": "유효한 자막 큐 없음"}
        # 패널은 절대 경로를 모른다 — 빌드가 쓰는 것과 같은 토큰 파일 경로를 실어 준다.
        tokens_path = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "ae_tokens.json"
        out = {"cues": cues}
        if tokens_path.is_file():
            out["tokens_path"] = str(tokens_path)
        return 200, out

    if method == "GET" and p == "/api/media":
        pid = query.get("project_id", "")
        return 200, {"items": media.list_media(root / pid)}

    if method == "GET" and p == "/api/search-images":
        pid = query.get("project_id", "")
        q = (query.get("q") or "").strip()
        if not (root / pid).is_dir():
            return 404, {"error": "프로젝트 없음"}
        if not q:
            return 400, {"error": "검색어 필요"}
        return 200, search.search_images(q, engine=query.get("engine", "serper"))

    if method == "POST" and p == "/api/search-images/save":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        url, name = b.get("url", ""), b.get("name", "")
        if not url or not name:
            return 400, {"error": "url, name 필요"}
        return 200, {"result": search.save_image(proj_dir, url, name)}

    if method == "POST" and p == "/api/scenes/set-image":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        return 200, {"result": media.set_scene_image(proj_dir, b.get("sceneNumber"), b.get("src", ""))}

    if method == "POST" and p == "/api/images/generate":
        b = body or {}
        pid = b.get("project_id", "")
        proj_dir = root / pid
        refs_fp = proj_dir / "references.json"
        if not refs_fp.exists():
            return 422, {"error": "references.json 없음 — reference-list 먼저 실행"}
        import json as _json
        refs = _json.loads(refs_fp.read_text(encoding="utf-8")).get("references", [])
        jobs = ctx["jobs"]
        jid = jobs.create("images", pid)
        # 기본 순차(1) — 같은 프로젝트 폴더에서 codex image_gen 동시 실행 시 출력이 섞이는
        # 충돌 관측됨(요소 A 레이어에 요소 B 그림). AK_LAYER_CONCURRENCY로 조정.
        conc = int(b.get("concurrency") or os.environ.get("AK_LAYER_CONCURRENCY", "1"))
        items = [(f"{ref['id']}.png", ref["image_prompt"]) for ref in refs]
        def _do(proj_dir=proj_dir, items=items, refs=refs, conc=conc, jid=jid):
            results = imagegen.generate_many(
                proj_dir, items, subdir="images", concurrency=conc,
                on_event=lambda rel, res: jobs.append_log(jid, f"{rel}: {res['status']}"))
            done = sum(1 for r in results.values() if r["status"] == "completed")
            if not done:
                raise RuntimeError("이미지 생성 전체 실패")
            jobs.set_status(jid, "running", artifact_paths=[str(proj_dir / "images")])
            return {"generated": done, "total": len(refs)}
        run_async(jobs, jid, _do)
        return 200, {"job_id": jid, "status": "running"}

    if method == "GET" and p == "/api/images/list":
        pid = query.get("project_id", "")
        images_dir = root / pid / "images"
        if not images_dir.is_dir():
            return 200, {"images": []}
        names = sorted(f.name for f in images_dir.glob("*.png"))
        return 200, {"images": names, "dir": str(images_dir)}

    if method == "POST" and p == "/api/storyboard/generate":
        b = body or {}
        pid = b.get("project_id", "")
        proj_dir = root / pid
        scenes_fp = proj_dir / "scenes.json"
        if not scenes_fp.exists():
            return 422, {"error": "scenes.json 없음 — 씬 분해(scene-decompose) 먼저 실행"}
        data = scenes.load_scenes(proj_dir)   # sceneId 보장 + enrich
        scene_list = data["scenes"]
        jobs = ctx["jobs"]
        jid = jobs.create("storyboard", pid)
        # 기본 순차(1) — 같은 프로젝트 폴더에서 codex image_gen 동시 실행 시 출력이 섞이는
        # 충돌 관측됨(요소 A 레이어에 요소 B 그림). AK_LAYER_CONCURRENCY로 조정.
        conc = int(b.get("concurrency") or os.environ.get("AK_LAYER_CONCURRENCY", "1"))
        char = (b.get("character") or "").strip()
        character_ref = None
        if char:
            cref = proj_dir / "characters" / f"char_{char}.png"
            if cref.exists():
                character_ref = str(cref)
        items = []
        for sc in scene_list:
            sid = sc.get("sceneId")
            prompt = sc.get("image_prompt") or sc.get("visual_summary") or sc.get("narration", "")
            items.append((f"sb_{sid}.png", prompt))
        def _do(proj_dir=proj_dir, items=items, scene_list=scene_list,
                conc=conc, character_ref=character_ref, jid=jid):
            results = imagegen.generate_many(
                proj_dir, items, subdir="storyboard", concurrency=conc, character_ref=character_ref,
                on_event=lambda rel, res: jobs.append_log(jid, f"{rel}: {res['status']}"))
            done = sum(1 for r in results.values() if r["status"] == "completed")
            if not done:
                raise RuntimeError("스토리보드 생성 전체 실패")
            jobs.set_status(jid, "running", artifact_paths=[str(proj_dir / "storyboard")])
            return {"generated": done, "total": len(scene_list)}
        run_async(jobs, jid, _do)
        return 200, {"job_id": jid, "status": "running"}

    if method == "GET" and p == "/api/storyboard/list":
        pid = query.get("project_id", "")
        sb_dir = root / pid / "storyboard"
        if not sb_dir.is_dir():
            return 200, {"images": []}
        names = sorted(f.name for f in sb_dir.glob("*.png"))
        return 200, {"images": names, "dir": str(sb_dir)}

    if method == "GET" and p == "/api/layers/list":
        pid = query.get("project_id", "")
        ld = root / pid / "layers"
        if not ld.is_dir():
            return 200, {"images": []}
        names = sorted(f.name for f in ld.glob("*.png"))
        return 200, {"images": names, "dir": str(ld)}

    if method == "GET" and p == "/api/projects/files":
        pid = query.get("project_id", "")
        return 200, {"groups": projects.list_files(root / pid)}

    if method == "GET" and p == "/api/projects/file":
        pid = query.get("project_id", "")
        name = query.get("name", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": f"project not found: {pid}"}
        if not name:
            return 400, {"error": "invalid name"}
        fp = (proj_dir / name).resolve()
        # 경로 탈출 방지: resolve된 경로가 프로젝트 디렉토리 내부여야 함
        if not fp.is_relative_to(proj_dir.resolve()):
            return 400, {"error": "invalid name"}
        if not fp.is_file():
            return 404, {"error": f"file not found: {name}"}
        try:
            content = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return 415, {"error": "binary file not supported"}
        return 200, {"name": name, "content": content}

    if method == "POST" and p == "/api/projects/file/save":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        name = b.get("name") or ""
        if b.get("content") is None:
            return 400, {"error": "content 필요"}
        res = edits.save_file(proj_dir, name, b.get("content"))
        return (200, res) if res.get("ok") else (400, res)

    if method == "POST" and p.startswith("/api/jobs/") and p.endswith("/cancel"):
        jid = p.split("/")[3]
        ok = ctx["jobs"].request_cancel(jid)
        return (200, {"ok": True, "job_id": jid, "status": "cancelling"}) if ok \
            else (404, {"error": f"실행 중인 잡이 아님: {jid}"})

    if method == "GET" and p == "/api/jobs":
        return 200, {"running": ctx["jobs"].running_jobs(query.get("project_id") or None)}

    if method == "GET" and p.startswith("/api/jobs/"):
        jid = p.rsplit("/", 1)[-1]
        j = ctx["jobs"].get(jid)
        if not j:
            return 404, {"error": f"job not found: {jid}"}
        return 200, j

    return 404, {"error": "not found", "path": path}
