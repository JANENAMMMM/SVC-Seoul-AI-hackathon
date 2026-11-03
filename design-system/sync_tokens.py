"""tokens.json에서 tokens.css 생성. --check는 파일을 수정하지 않고 동기화 확인."""

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    tokens = json.loads((root / 'tokens.json').read_text(encoding='utf-8'))
    lines = ['/* tokens.json에서 생성. 색상 외 간격·크기·반응형 값은 반걸음 제안입니다. */', ':root {']
    for group in ('color', 'space', 'radius', 'font', 'layout'):
        for key, value in tokens[group].items():
            lines.append(f'  --bg-{group}-{key}: {value};')
    content = '\n'.join([*lines, '}']) + '\n'
    target = root / 'tokens.css'
    if args.check:
        if not target.exists() or target.read_text(encoding='utf-8') != content:
            raise SystemExit('tokens.css 갱신이 필요합니다: uv run python design-system/sync_tokens.py')
        print('디자인 토큰 동기화 확인 완료')
    else:
        target.write_text(content, encoding='utf-8')


if __name__ == '__main__':
    main()
