// auto_kairos 데스크톱 앱 — 대시보드를 창으로 감싼다.
//
// 화면을 다시 만들지 않는다. 이미 있는 FastAPI 대시보드를 앱이 직접 띄우고
// 그 주소를 창에 물린다. 웹으로 쓰던 것과 같은 화면이 앱이 된다.
//
// 앱을 닫으면 서버도 함께 내린다 — 창만 닫고 서버가 남으면 다음 실행에서
// 포트가 막힌다.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::path::PathBuf;
use std::fs::File;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::Manager;

const PORT: u16 = 8777; // 손으로 띄우는 8080과 부딪히지 않게 따로 쓴다

struct Server(Mutex<Option<Child>>);

/// 저장소 뿌리 — 개발 중에는 app/src-tauri 에서 두 단계 위, 배포본은 실행 파일 옆.
fn repo_root() -> PathBuf {
    if let Ok(p) = std::env::var("AUTO_KAIROS_ROOT") {
        return PathBuf::from(p);
    }
    let dev = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|p| p.parent())
        .map(PathBuf::from);
    dev.unwrap_or_else(|| PathBuf::from("."))
}

fn up() -> bool {
    TcpStream::connect(("127.0.0.1", PORT)).is_ok()
}

fn spawn_server(root: &PathBuf) -> Option<Child> {
    if up() {
        return None; // 이미 떠 있으면 그대로 쓴다
    }
    let py = root.join(".venv/bin/python");
    let bin = if py.exists() { py } else { PathBuf::from("python3") };
    // Finder로 띄운 앱에는 표준 출력이 없다. 그대로 물려주면 로그를 쓰다
    // 파이프가 막혀 서버가 멈춘다 — 실제로 그래서 8777이 안 열렸다.
    let log = root.join("logs");
    let _ = std::fs::create_dir_all(&log);
    let out = File::create(log.join("app-dashboard.log")).ok();
    let err = out.as_ref().and_then(|f| f.try_clone().ok());

    let mut cmd = Command::new(bin);
    cmd.args([
        "-m", "uvicorn", "app:app",
        "--host", "127.0.0.1",
        "--port", &PORT.to_string(),
    ])
    .current_dir(root);
    match (out, err) {
        (Some(o), Some(e)) => { cmd.stdout(Stdio::from(o)).stderr(Stdio::from(e)); }
        _ => { cmd.stdout(Stdio::null()).stderr(Stdio::null()); }
    }
    cmd.spawn().ok()
}

/// 서버가 응답할 때까지 기다린다. 창이 먼저 뜨면 흰 화면이 보인다.
fn wait_ready(limit: Duration) -> bool {
    let start = Instant::now();
    while start.elapsed() < limit {
        if up() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    false
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(Server(Mutex::new(None)))
        .setup(|app| {
            let root = repo_root();
            let child = spawn_server(&root);
            *app.state::<Server>().0.lock().unwrap() = child;
            wait_ready(Duration::from_secs(30));
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(mut c) = window.state::<Server>().0.lock().unwrap().take() {
                    let _ = c.kill();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("auto_kairos 앱 실행 실패");
}
