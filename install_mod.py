"""Copy the local read-only bridge into Balatro's Mods folder."""
from __future__ import annotations

import shutil
from pathlib import Path

from run_coach import default_state_file


def main() -> None:
    mods = default_state_file().parent / "Mods"
    source = Path(__file__).resolve().parent / "mod"
    if not mods.is_dir():
        print(f"Mods klasörü bulunamadı: {mods}")
        print("Önce Lovely + Steamodded kurup oyunu bir kez modlu başlat; sonra yeniden dene.")
        return
    target = mods / "balatro_coach_bridge"
    target.mkdir(exist_ok=True)
    for name in ("main.lua", "balatro_coach.json"):
        shutil.copy2(source / name, target / name)
    print(f"Balatro Coach köprüsü yüklendi: {target}")
    print("Balatro'yu modlu biçimde yeniden başlat. Ardından python coach.py çalıştır.")


if __name__ == "__main__":
    main()
