"""검토한 커밋과 공개 채점 스냅샷으로 USB 제출용 디렉터리를 만든다."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".github", "AGENTS.md", "CONTRIBUTING.md", "legacy", "design-system", "mockup", "web", "data"}
DOCS = {"docs/submission.md", "docs/ui-redesign.md", "docs/backend", "docs/route-planning",
        "docs/restaurants", "docs/scoring-ai/README.md", "docs/scoring-ai/spec",
        "docs/scoring-ai/assets", "docs/presentation/final"}
DATA_FILES = ("attractions.json", "attractions_seed.json", "features.json", "grades.json",
              "scores_v2.json", "visit_modes_v2_1.json", "visit_modes_v2_2.json")


def included(name):
    path = Path(name)
    if path.parts[0] in EXCLUDED or path.name in {"HANDOFF.txt", ".DS_Store"}:
        return False
    if path.parts[0] == "docs":
        return any(name == item or name.startswith(item + "/") for item in DOCS)
    return True


def export(destination, data_root, revision):
    # 기존 제출본을 덮어쓰지 않으며 Git에 기록된 파일만 내보낸다.
    commit = subprocess.check_output(["git", "rev-parse", "--verify", revision + "^{commit}"], cwd=ROOT, text=True).strip()
    archive = subprocess.check_output(["git", "archive", commit], cwd=ROOT)
    scoring = data_root / "scoring"
    required = [scoring / name for name in DATA_FILES]
    required += [scoring / "derived/climate_danang.json"]
    for path in required:
        if not path.is_file():
            raise ValueError(f"필수 공개 데이터 없음: {path.name}")
    destination.mkdir(parents=True, exist_ok=False)
    try:
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            for entry in bundle:
                if entry.isfile() and included(entry.name):
                    target = destination / entry.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.extractfile(entry) as source, target.open("wb") as output:
                        shutil.copyfileobj(source, output)
        shutil.copyfile(destination / "docs/submission.md", destination / "README.md")
        for source in required:
            target = destination / "data" / source.relative_to(data_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        # 공개 평가 근거만 포함. HITL 임시 기록, 세션, 원문 수집 캐시는 제외한다.
        for folder in ("derived", "judge/v2"):
            for source in sorted((scoring / folder).glob("*.json")):
                target = destination / "data/scoring" / folder / source.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        hashes = {str(path.relative_to(destination)): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted(destination.rglob("*")) if path.is_file()}
        manifest = {"commit": commit, "sha256": hashes}
        (destination / "SUBMISSION.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except BaseException:
        shutil.rmtree(destination)
        raise
    print(f"제출본 생성: {destination} ({len(hashes)}개 파일, commit {commit[:12]})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data")
    parser.add_argument("--revision", default="HEAD")
    args = parser.parse_args()
    export(args.destination.expanduser().resolve(), args.data_root.expanduser().resolve(), args.revision)
