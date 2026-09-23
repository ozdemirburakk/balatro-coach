"""Install official Lovely and Steamodded releases, then Balatro Coach bridge.

Downloads only from the maintainers' GitHub repositories. Does not launch code.
Existing installs are left in place; use --game-dir for a nondefault Steam library.
"""
from __future__ import annotations

import argparse
import io
import json
import platform
import re
import shlex
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

LOVELY_RELEASE = "https://api.github.com/repos/ethangreen-dev/lovely-injector/releases/latest"
SMODS_RELEASE = "https://api.github.com/repos/Steamodded/smods/releases/latest"
MAX_DOWNLOAD = 120 * 1024 * 1024


def download(url: str) -> bytes:
    if not url.startswith(("https://api.github.com/", "https://github.com/")):
        raise RuntimeError("Beklenmeyen indirme adresi.")
    request = urllib.request.Request(url, headers={
        "User-Agent": "balatro-coach-installer",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(request, timeout=45) as response:
        if response.geturl().split("/")[2] not in (
            "api.github.com", "github.com", "codeload.github.com",
            "release-assets.githubusercontent.com", "objects.githubusercontent.com",
        ):
            raise RuntimeError("Beklenmeyen yönlendirme adresi.")
        data = response.read(MAX_DOWNLOAD + 1)
    if len(data) > MAX_DOWNLOAD:
        raise RuntimeError("İndirilen arşiv beklenenden büyük.")
    return data


def release(url: str) -> dict:
    return json.loads(download(url))


def install_lovely(game_dir: Path) -> None:
    if (game_dir / "liblovely.dylib").exists() and (game_dir / "run_lovely_macos.sh").exists():
        print("Lovely zaten oyun klasöründe; mevcut sürüme dokunulmadı.")
        return
    info = release(LOVELY_RELEASE)
    machine = platform.machine()
    if machine not in ("arm64", "x86_64"):
        raise RuntimeError(f"Desteklenmeyen Mac işlemcisi: {machine}")
    target_name = f"lovely-{'aarch64' if machine == 'arm64' else 'x86_64'}-apple-darwin.tar.gz"
    asset = next((item for item in info.get("assets", []) if item.get("name") == target_name), None)
    if not asset:
        raise RuntimeError(f"Lovely sürümünde {target_name} bulunamadı. Resmî kurulum rehberini kontrol et.")
    print(f"Lovely {info.get('tag_name', '')} indiriliyor…", flush=True)
    with tarfile.open(fileobj=io.BytesIO(download(asset["browser_download_url"])), mode="r:gz") as archive:
        contents = {}
        for filename in ("liblovely.dylib", "run_lovely_macos.sh"):
            candidates = [member for member in archive.getmembers()
                          if member.isfile() and PurePosixPath(member.name).name == filename]
            if len(candidates) != 1 or candidates[0].size > 30 * 1024 * 1024:
                raise RuntimeError(f"Lovely arşivinde {filename} doğrulanamadı.")
            contents[filename] = archive.extractfile(candidates[0]).read()
    if game_dir != Path.home() / "Library/Application Support/Steam/steamapps/common/Balatro":
        script = contents["run_lovely_macos.sh"].decode("utf-8")
        script, count = re.subn(r'^defaultpath=.*$', lambda _: "defaultpath=" + shlex.quote(str(game_dir)),
                                script, count=1, flags=re.MULTILINE)
        if count != 1:
            raise RuntimeError("Lovely başlatma betiğinin oyun yolu uyarlanamadı.")
        contents["run_lovely_macos.sh"] = script.encode("utf-8")
    for filename, content in contents.items():
        target = game_dir / filename
        if not target.exists():
            target.write_bytes(content)
            if filename.endswith(".sh"):
                target.chmod(target.stat().st_mode | 0o100)
    print("Lovely oyun klasörüne kopyalandı.")


def install_smods(mods_dir: Path) -> None:
    target = mods_dir / "smods"
    if target.exists():
        if not (target / "manifest.json").exists():
            raise RuntimeError(f"{target} var ama Steamodded manifest.json yok. Klasörü kontrol et.")
        print("Steamodded zaten kurulu; mevcut sürüme dokunulmadı.")
        return
    info = release(SMODS_RELEASE)
    print(f"Steamodded {info.get('tag_name', '')} indiriliyor…", flush=True)
    zip_bytes = download(info["zipball_url"])
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        entries = [item for item in archive.infolist() if not item.is_dir()]
        roots = {PurePosixPath(item.filename).parts[0] for item in entries}
        if len(roots) != 1 or not any(PurePosixPath(item.filename).name == "manifest.json" for item in entries):
            raise RuntimeError("Steamodded arşivi beklenen biçimde değil.")
        with tempfile.TemporaryDirectory(prefix="balatro-smods-") as work:
            staged = Path(work) / "smods"
            staged.mkdir()
            total = 0
            for item in entries:
                parts = PurePosixPath(item.filename).parts[1:]
                if not parts or ".." in parts or item.file_size > 30 * 1024 * 1024:
                    raise RuntimeError("Steamodded arşivinde güvenilmeyen dosya yolu.")
                # Zip Unix mode bits: avoid extracting symlinks.
                if ((item.external_attr >> 16) & 0o170000) == 0o120000:
                    raise RuntimeError("Steamodded arşivinde sembolik bağlantı var.")
                total += item.file_size
                if total > MAX_DOWNLOAD * 2:
                    raise RuntimeError("Steamodded arşivi beklenenden büyük.")
                destination = staged.joinpath(*parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
            if not (staged / "manifest.json").is_file():
                raise RuntimeError("Steamodded ana klasörü bulunamadı.")
            shutil.move(str(staged), str(target))
    print("Steamodded mod klasörüne kopyalandı.")


def install_bridge(mods_dir: Path) -> None:
    source = Path(__file__).resolve().parent / "mod"
    target = mods_dir / "balatro_coach_bridge"
    target.mkdir(exist_ok=True)
    for filename in ("main.lua", "balatro_coach.json"):
        shutil.copy2(source / filename, target / filename)
    print("Balatro Coach köprüsü yüklendi.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Mac Steam Balatro için Lovely + Steamodded + Coach kurar.")
    parser.add_argument("--game-dir", type=Path, default=Path.home() / "Library/Application Support/Steam/steamapps/common/Balatro",
                        help="Steam Balatro oyun klasörü (farklı diskteyse belirt).")
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("Bu kurucu yalnızca macOS için.")
    game_dir = args.game_dir.expanduser()
    if not (game_dir / "Balatro.app").is_dir():
        parser.error(f"Balatro.app bulunamadı: {game_dir}. Steam indirmesi bitince yeniden dene veya --game-dir belirt.")
    mods_dir = Path.home() / "Library/Application Support/Balatro/Mods"
    print(f"Oyun: {game_dir}\nModlar: {mods_dir}", flush=True)
    try:
        # Validate network packages before writing into the game where possible.
        mods_dir.mkdir(parents=True, exist_ok=True)
        install_lovely(game_dir)
        install_smods(mods_dir)
        install_bridge(mods_dir)
    except (OSError, ValueError, KeyError, RuntimeError, urllib.error.URLError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"Kurulum tamamlanamadı: {exc}", file=sys.stderr)
        return 1
    print("\nBalatro'yu oyun klasöründeki run_lovely_macos.sh ile aç.")
    print("Koşuyu başlat; ayrı terminalde python3 coach.py çalıştır.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
