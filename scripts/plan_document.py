"""Render the human review portion from the one content-plan block."""
import argparse
import html
import json
import re
from pathlib import Path

START = '<!-- plan-review:start -->'
END = '<!-- plan-review:end -->'


def extract(document):
    blocks = re.findall(r'^```content-plan\s*\n(.*?)^```\s*$', document, re.M | re.S)
    if len(blocks) != 1:
        raise ValueError('content-plan 블록 하나 필요')
    return json.loads(blocks[0])


def cell(value):
    return html.escape(str(value), quote=False).replace('|', '&#124;').replace('\n', '<br>')


def render(plan):
    lines = [START, '# 콘텐츠 기획서', '', '## 기획 요약', '',
             '| 항목 | 내용 |', '| --- | --- |']
    for label, key in [('주제', 'topic'), ('대상', 'target'), ('목적', 'purpose'),
                       ('핵심 메시지', 'message'), ('주된 CTA', 'primary_cta')]:
        lines.append(f'| {label} | {cell(plan[key])} |')
    lines += [f'| 형식 | 카드뉴스 {plan["card_count"]}장 · {plan["width"]}×{plan["height"]} |',
              '', '## 카드별 구성', '',
              '| 순서 · ID | 역할 | 실제 문구 | 화면 구성 | 사진 | CTA | 근거 ID |',
              '| --- | --- | --- | --- | --- | --- | --- |']
    for i, c in enumerate(plan['cards'], 1):
        values = [f'{i:02d} · {c["id"]}', c['role'], '\n\n'.join(c['copy']),
                  c['layout'], '신규 사진' if c['photo_required'] else '없음',
                  c.get('cta') or '—', ', '.join(c['source_ids']) or '—']
        lines.append('| ' + ' | '.join(cell(v) for v in values) + ' |')
    lines += ['', '## 사진 제작 방향', '',
              '사진 스타일은 프로젝트의 brand.md·content-design.md를 우선합니다. 아래는 이번 기획의 장면과 구도입니다.', '']
    for c in plan['cards']:
        lines += [f'### {c["id"]}', '', cell(c['photo_brief']), '']
    lines += ['## 캡션', '', *['> ' + html.escape(line, quote=False)
                              for line in plan['caption'].split('\n')], '', END]
    return '\n'.join(lines)


def check(document):
    p = extract(document)
    if document.count(START) != 1 or document.count(END) != 1:
        raise ValueError('사람 검토용 기획 요약·카드별 표 누락')
    start, end = document.index(START), document.index(END) + len(END)
    if document[:start].strip() or document[start:end] != render(p):
        raise ValueError('기획 요약·카드별 표·사진 방향·캡션과 제작 데이터 불일치')
    tail = document[end:]
    if not re.search(r'^## 확인 사항\s*$', tail, re.M):
        raise ValueError('확인 사항 누락')
    if not re.search(r'\n```\s*\Z', tail) or tail.index('## 확인 사항') > tail.index('```content-plan'):
        raise ValueError('제작 데이터는 확인 사항 뒤 문서 하단에 배치')
    return p


def sync(document):
    p = extract(document)
    if document.count(START) != 1 or document.count(END) != 1:
        raise ValueError('동기화 영역이 없습니다. compose()로 최초 문서를 만드세요.')
    end = document.index(END) + len(END)
    return render(p) + document[end:]


def compose(plan, notes):
    return (render(plan) + '\n\n## 확인 사항\n\n' + notes.strip()
            + '\n\n## 제작 데이터 · 자동 검사용\n\n'
            + '```content-plan\n' + json.dumps(plan, ensure_ascii=False, indent=2) + '\n```\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--sync', action='store_true', help='하단 데이터를 기준으로 검토 영역 갱신')
    args = parser.parse_args()
    doc = args.path.read_text(encoding='utf-8')
    if args.sync:
        doc = sync(doc)
        args.path.write_text(doc, encoding='utf-8')
    check(doc)
    print('기획서와 제작 데이터 일치')
