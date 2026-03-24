"""
시스템 폰트 매니저 -- macOS / Windows 크로스플랫폼 지원.

사용법:
    from auto_agent.font_manager import FontManager
    fm = FontManager()
    fonts = fm.list_fonts()          # 전체 목록
    fonts = fm.search("Pretendard")  # 검색
"""

import platform
import subprocess
from functools import lru_cache


# Remotion 번들 폰트 (항상 사용 가능)
BUNDLED_FONTS = [
    {"family": "Pretendard", "source": "bundled", "weights": ["400", "700"]},
]

# 기본 폰트
DEFAULT_FONT = "Pretendard"


class FontManager:
    """크로스플랫폼 시스템 폰트 조회."""

    def __init__(self):
        self._system = platform.system()  # "Darwin", "Windows", "Linux"

    @lru_cache(maxsize=1)
    def list_system_fonts(self) -> list[str]:
        """시스템에 설치된 폰트 패밀리 목록 반환 (정렬됨, 중복 제거)."""
        try:
            if self._system == "Darwin":
                return self._list_macos()
            elif self._system == "Windows":
                return self._list_windows()
            else:
                return self._list_linux()
        except Exception:
            return []

    def _list_macos(self) -> list[str]:
        """macOS: system_profiler 또는 fc-list 사용."""
        # 방법 1: fc-list (Homebrew fontconfig 설치 시)
        fonts = self._try_fc_list()
        if fonts:
            return fonts

        # 방법 2: macOS 전용 -- NSFontManager via Python bridge
        try:
            result = subprocess.run(
                [
                    "python3", "-c",
                    "import AppKit; "
                    "fm = AppKit.NSFontManager.sharedFontManager(); "
                    "families = list(fm.availableFontFamilies()); "
                    "print('\\n'.join(sorted(set(families))))"
                ],
                capture_output=True, text=True, encoding="utf-8", timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip():
                return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # 방법 3: 폰트 디렉토리 직접 스캔
        return self._scan_font_dirs_macos()

    def _list_windows(self) -> list[str]:
        """Windows: PowerShell로 레지스트리 조회."""
        try:
            # PowerShell로 설치된 폰트 목록 가져오기
            ps_cmd = (
                "[System.Reflection.Assembly]::LoadWithPartialName('System.Drawing') | Out-Null; "
                "(New-Object System.Drawing.Text.InstalledFontCollection).Families | "
                "ForEach-Object { $_.Name } | Sort-Object -Unique"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, encoding="utf-8", timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # 폴백: 레지스트리 직접 조회
        try:
            reg_cmd = (
                "Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts' | "
                "ForEach-Object { $_.PSObject.Properties } | "
                "Where-Object { $_.Name -ne 'PSPath' -and $_.Name -ne 'PSParentPath' } | "
                "ForEach-Object { ($_.Name -replace '\\s*\\(.*\\)$','').Trim() } | "
                "Sort-Object -Unique"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", reg_cmd],
                capture_output=True, text=True, encoding="utf-8", timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return []

    def _list_linux(self) -> list[str]:
        """Linux: fc-list 사용."""
        return self._try_fc_list() or []

    def _try_fc_list(self) -> list[str] | None:
        """fc-list 커맨드로 폰트 패밀리 목록 추출."""
        try:
            result = subprocess.run(
                ["fc-list", "--format=%{family}\n"],
                capture_output=True, text=True, encoding="utf-8", timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip():
                families = set()
                for line in result.stdout.strip().split("\n"):
                    # fc-list은 "Family1,Family2" 형식으로 출력할 수 있음
                    for name in line.split(","):
                        name = name.strip()
                        if name:
                            families.add(name)
                return sorted(families)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    def _scan_font_dirs_macos(self) -> list[str]:
        """macOS 폰트 디렉토리를 직접 스캔하여 폰트 파일명 추출."""
        from pathlib import Path

        dirs = [
            Path.home() / "Library" / "Fonts",
            Path("/Library/Fonts"),
            Path("/System/Library/Fonts"),
            Path("/System/Library/Fonts/Supplemental"),
        ]
        families = set()
        for d in dirs:
            if not d.exists():
                continue
            for f in d.iterdir():
                if f.suffix.lower() in (".ttf", ".otf", ".ttc", ".dfont"):
                    # 파일명에서 폰트 이름 추출 (정확하진 않지만 폴백용)
                    name = f.stem.replace("-", " ").replace("_", " ")
                    # "Bold", "Italic" 등 weight/style 제거
                    for suffix in ["Bold", "Italic", "Light", "Medium", "Thin",
                                   "Regular", "SemiBold", "ExtraBold", "Black"]:
                        name = name.replace(suffix, "").strip()
                    if name:
                        families.add(name)
        return sorted(families)

    def list_fonts(self) -> list[dict]:
        """번들 + 시스템 폰트 통합 목록 반환.

        Returns:
            [{"family": "Pretendard", "source": "bundled"}, ...]
        """
        result = []

        # 번들 폰트 우선
        bundled_names = set()
        for b in BUNDLED_FONTS:
            result.append({"family": b["family"], "source": "bundled"})
            bundled_names.add(b["family"])

        # 시스템 폰트 (번들과 중복 제거)
        for name in self.list_system_fonts():
            if name not in bundled_names:
                result.append({"family": name, "source": "system"})

        return result

    def search(self, query: str) -> list[dict]:
        """폰트 검색 (대소문자 무시, 부분 매칭)."""
        q = query.lower()
        return [f for f in self.list_fonts() if q in f["family"].lower()]

    def is_available(self, family: str) -> bool:
        """폰트가 사용 가능한지 확인."""
        return any(f["family"] == family for f in self.list_fonts())

    def is_bundled(self, family: str) -> bool:
        """번들 폰트인지 확인."""
        return any(b["family"] == family for b in BUNDLED_FONTS)
