#!/usr/bin/env python3
"""Offline, standard-library checks. Never grants approval or calls production tools."""
import argparse
import hashlib
import json
import posixpath
import re
import struct
import sys
import zlib
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
from zipfile import ZipFile, BadZipFile
import xml.etree.ElementTree as ET
from plan_document import check as check_plan_document, START as PLAN_REVIEW_START

STAGES = ('research', 'plan', 'preview', 'final')
STATUSES = ('not_run', 'in_progress', 'awaiting_approval', 'approved', 'complete', 'blocked')
DONE = dict(research=('complete',), plan=('approved', 'complete'),
            preview=('approved', 'complete'), final=('complete',))
DEFAULT_PATHS = dict(research='research/research.md', pptx='research/research.pptx',
                     sources='research/sources.json', plan='plan/plan.md',
                     html='preview/preview.html', assets='preview/assets.json',
                     browser='preview/browser-check.json', figma='final/figma.json',
                     png='final/png', caption='final/caption.md', review='checks/review.md')
MARKERS = re.compile(r'\[\s*확인\s*필요[^\]]*\]|\bTODO\b|\bTBD\b', re.I)
# research_report_format=clean-pptx-v1: limits and check status stay in research.md/sources.json/checks.
REPORT_FORBIDDEN = re.compile(r'한계|미확인|확인\s*불가|접근\s*(?:실패|불가|제한)|\bblocked\b|\bnot_run\b'
                              r'|자동\s*검사|검사\s*(?:통과|실패|상태|결과)|limitation', re.I)
FULL_RANK_CLAIM = re.compile(r'전체\s*(?:인기\s*)?Top\s*\d+', re.I)


def norm(s):
    return ' '.join(s.split())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp(value):
    t = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if t.tzinfo is None:
        raise ValueError('시각에 timezone offset 필요')
    return t


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def png_size(path):
    """Check chunk CRCs, zlib stream, scanline length and dimensions (non-interlaced)."""
    raw = path.read_bytes()
    require(raw[:8] == b'\x89PNG\r\n\x1a\n', 'PNG signature 오류')
    pos, chunks, data, size, ended = 8, [], b'', None, False
    while pos < len(raw):
        require(pos + 12 <= len(raw), '잘린 PNG chunk')
        length = struct.unpack('>I', raw[pos:pos+4])[0]
        kind = raw[pos+4:pos+8]
        payload = raw[pos+8:pos+8+length]
        require(pos+12+length <= len(raw), '잘린 PNG payload')
        crc = struct.unpack('>I', raw[pos+8+length:pos+12+length])[0]
        require(zlib.crc32(kind+payload) & 0xffffffff == crc, 'PNG CRC 오류')
        chunks.append(kind)
        if kind == b'IHDR':
            require(length == 13 and len(chunks) == 1, 'PNG IHDR 오류')
            w, h, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            require(w > 0 and h > 0 and w*h <= 100_000_000, 'PNG 치수 오류')
            require(compression == filtering == interlace == 0, '비인터레이스 PNG로 내보내기 필요')
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
            require(channels and depth in (1, 2, 4, 8, 16), 'PNG color/depth 오류')
            size = (w, h)
        elif kind == b'IDAT':
            data += payload
        elif kind == b'IEND':
            require(length == 0, 'PNG IEND 오류')
            ended = True
            pos += length+12
            break
        pos += length+12
    require(size and data and ended and pos == len(raw), '불완전한 PNG')
    if color == 3:
        require(b'PLTE' in chunks, 'PNG palette 누락')
    row = (w*channels*depth+7)//8
    inflater = zlib.decompressobj()
    pixels = inflater.decompress(data, (row+1)*h+1)
    require(inflater.eof and not inflater.unused_data and len(pixels) == (row+1)*h,
            'PNG 디코드 크기 불일치')
    require(all(pixels[i] <= 4 for i in range(0, len(pixels), row+1)), 'PNG filter 오류')
    return size


def pptx_text(path):
    with ZipFile(path) as archive:
        require(archive.testzip() is None, 'PPTX CRC 오류')
        names = archive.namelist()
        for name in ('[Content_Types].xml', '_rels/.rels', 'ppt/presentation.xml',
                     'ppt/_rels/presentation.xml.rels'):
            require(name in names, f'PPTX 패키지 필수 항목 누락: {name}')
        xml = {n: ET.fromstring(archive.read(n)) for n in names
               if n.endswith(('.xml', '.rels'))}
        slides = [n for n in names if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)]
        require(slides, 'PPTX slide 없음')
        pns = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
        rns = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
        rels = {r.attrib['Id']: r.attrib['Target']
                for r in xml['ppt/_rels/presentation.xml.rels']}
        ids = xml['ppt/presentation.xml'].findall(f'.//{pns}sldId')
        require(len(ids) == len(slides), 'PPTX slide 연결 수 불일치')
        for node in ids:
            target = rels.get(node.attrib.get(rns+'id'), '')
            resolved = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'ppt/'+target)
            require(resolved in slides, 'PPTX slide 관계 누락')
        return '\n'.join(' '.join(xml[n].itertext()) for n in slides)


def pptx_notes(path):
    with ZipFile(path) as archive:
        notes = [n for n in archive.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml', n)]
        return '\n'.join(' '.join(ET.fromstring(archive.read(n)).itertext()) for n in notes)


class CardsHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cards, self.stack, self.copy, self.resources = [], [], None, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        card = self.stack[-1][1] if self.stack else None
        if 'data-card-id' in a:
            require(card is None, '카드 중첩 금지')
            card = dict(id=a['data-card-id'], width=int(a['data-width']),
                        height=int(a['data-height']), copy=[])
            self.cards.append(card)
        if 'data-copy' in a:
            require(card is not None and self.copy is None, 'data-copy 위치/중첩 오류')
            self.copy = [len(self.stack), card, '']
        if tag == 'br' and self.copy:
            self.copy[2] += ' '
        for key in ('src', 'poster'):
            if a.get(key):
                self.resources.append(a[key])
        if tag == 'link' and a.get('href'):
            self.resources.append(a['href'])
        if tag not in ('img', 'br', 'hr', 'meta', 'link', 'input', 'source', 'wbr', 'area', 'embed'):
            self.stack.append((tag, card))

    def handle_endtag(self, tag):
        require(self.stack and self.stack[-1][0] == tag, f'HTML 태그 불일치: {tag}')
        self.stack.pop()
        if self.copy and self.copy[0] == len(self.stack):
            self.copy[1]['copy'].append(norm(self.copy[2]))
            self.copy = None

    def handle_startendtag(self, tag, attrs):
        before = len(self.stack)
        self.handle_starttag(tag, attrs)
        if len(self.stack) > before:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.copy:
            self.copy[2] += data


class Run:
    def __init__(self, folder, project=None):
        self.root = Path(folder).resolve()
        self.project = Path(project).resolve() if project else self.root.parent.parent
        self.state = json.loads((self.root/'state.json').read_text())
        self.paths = DEFAULT_PATHS | self.state.get('paths', {})
        self.errors, self.warnings, self.passed = [], [], []

    def local(self, relative):
        p = (self.root/relative).resolve()
        require(p.is_relative_to(self.root), f'실행 폴더 밖 경로: {relative}')
        return p

    def path(self, key):
        return self.local(self.paths[key])

    def read(self, key):
        return self.path(key).read_text(encoding='utf-8')

    def obj(self, key):
        return json.loads(self.read(key))

    def plan(self):
        blocks = re.findall(r'^```content-plan\s*\n(.*?)^```\s*$', self.read('plan'), re.M | re.S)
        require(len(blocks) == 1, 'plan.md에 content-plan JSON 블록 하나 필요')
        return json.loads(blocks[0])

    def asset_path(self, asset):
        if asset['kind'] == 'reference':
            p = (self.project/asset['path']).resolve()
            require(p.is_relative_to((self.project/'assets/reference').resolve()), 'reference 경로 오류')
            return p
        return self.local(asset['path'])

    def baseline(self):
        require(self.state['schema_version'] == 1, 'state schema_version 오류')
        require(self.state['run_id'] == self.root.name, '실행 ID/폴더 불일치')
        for stage in STAGES:
            require(self.status(stage) in STATUSES, f'{stage} 상태 오류')
        for name in ('brand.md', 'content-design.md', 'assets/reference/manifest.json'):
            require(self.state['reference_hashes'][name] == sha(self.reference_path(name)),
                    f'기준 파일 변경: {name}, 기준 재검토 필요')
        reference_root = (self.project/'assets/reference').resolve()
        for asset in self.manifest()['assets']:
            p = (reference_root/asset['file']).resolve()
            require(p.is_relative_to(reference_root) and sha(p) == asset['sha256'],
                    f'원본 참조 자산 변경: {asset["file"]}')
        self.stage_claims()

    def status(self, stage):
        return self.state['stages'][stage]['status']

    def stage_claims(self):
        # The recorded status is a claim; back it with order, approval and resume records.
        for i, stage in enumerate(STAGES):
            status, record = self.status(stage), self.state['stages'][stage]
            if status != 'not_run':
                for earlier in STAGES[:i]:
                    require(self.status(earlier) in DONE[earlier],
                            f'상태 순서 오류: {earlier}이 {self.status(earlier)}인데 {stage}이 {status}')
            if status == 'blocked':
                require(text(record.get('reason')) and text(self.state.get('resume', {}).get('next_action')),
                        f'{stage} blocked 원인(reason)·재개 지점(resume.next_action) 누락')
            if stage in ('plan', 'preview'):
                if status in DONE[stage]:
                    self.approval(stage)
                elif status == 'awaiting_approval':
                    require(record.get('pending_digest') == self.digest(stage),
                            f'{stage} 승인 요청 버전(pending_digest)이 현재 파일과 다름')

    def manifest(self):
        return json.loads((self.project/'assets/reference/manifest.json').read_text())

    def reference_path(self, name):
        snapshots = self.state.get('reference_snapshots', {})
        if name in snapshots:
            require(self.state['stages']['final']['status'] == 'complete',
                    '기준 보관본은 완료 실행 검증에만 사용')
            return self.local(snapshots[name])
        return self.project/name

    def digest(self, stage):
        # Content based: directory renames alone do not invalidate approval.
        parts = {'reference_hashes': {n: sha(self.reference_path(n)) for n in self.state['reference_hashes']},
                 'sources': sha(self.path('sources')), 'research': sha(self.path('research')),
                 'plan': sha(self.path('plan'))}
        if stage == 'preview':
            assets = self.obj('assets')['items']
            identities = []
            html = self.read('html')
            for a in assets:
                p = self.asset_path(a)
                identity = {k: v for k, v in a.items() if k not in ('path', 'html_url')}
                identity['actual_sha256'] = sha(p)
                identities.append(identity)
                html = html.replace(a['html_url'], 'asset:'+a['id'])
            parts['assets'] = sorted(identities, key=lambda a: a['id'])
            parts['html'] = html
        return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    def approval(self, stage):
        a = self.state.get('approvals', {}).get(stage, {})
        require(a.get('actor') == 'user' and text(a.get('quote')), f'{stage} 사용자 승인 없음')
        stamp(a['at'])
        require(a.get('digest') == self.digest(stage), f'{stage} 승인 버전 불일치')

    def research(self):
        s = self.obj('sources')
        start, end = stamp(s['window']['start']), stamp(s['window']['end'])
        require(start <= end, '조사 기간 역전')
        require(s['accounts'] == self.state['input']['accounts'], '계정 설정 불일치')
        require(s['window'] == self.state['input']['window'], '기간 설정 불일치')
        require(s['collector'] == 'aside-repl', 'Aside 직접 조사 근거 필요')
        require(set(s['coverage']) == set(s['accounts']), '계정별 coverage 누락')
        eligible, ids, urls, incomplete = [], set(), set(), False
        for account, c in s['coverage'].items():
            require(c['status'] in ('complete', 'partial', 'blocked') and text(c['note']), 'coverage 설명 누락')
            incomplete |= c['status'] != 'complete'
        for p in s['posts']:
            require(text(p['id']) and p['id'] not in ids, '중복/빈 게시물 ID')
            u = urlparse(p['url'])
            require(u.scheme == 'https' and u.hostname in ('instagram.com', 'www.instagram.com')
                    and re.search(r'/(p|reel|tv)/[^/]+/?$', u.path) and not u.query,
                    '정규 Instagram permalink 필요')
            require(u.path.rstrip('/') not in urls, '중복 permalink')
            ids.add(p['id']); urls.add(u.path.rstrip('/'))
            require(p['account'] in s['accounts'], '허용 계정 밖 게시물')
            stamp(p['checked_at'])
            for k in ('summary', 'visual', 'observation', 'interpretation', 'application'):
                require(text(p[k]), f'{p["id"]} {k} 누락')
            require(p['evidence'], '조사 근거 파일 누락')
            for e in p['evidence']:
                require(self.local(e).is_file() and self.local(e).stat().st_size > 0, '근거 파일 없음')
            date = stamp(p['published_at']) if p['published_at'] else None
            likes = p['likes']
            for k in ('published_at', 'likes'):
                if p[k] is None:
                    require(text(p['unknown_reasons'].get(k)), f'{k} 미확인 이유 누락')
                    incomplete = True
            require(likes is None or (type(likes) is int and likes >= 0), '좋아요는 정확한 비음수 정수 또는 null')
            if date and start <= date <= end and likes is not None:
                eligible.append(p)
        n = self.state['input'].get('top_n', 6)  # 기록이 없는 기존 실행은 당시 기준 6개
        require(type(n) is int and n > 0, 'state.input.top_n은 양의 정수')
        ranked = sorted(eligible, key=lambda p: (-p['likes'], -stamp(p['published_at']).timestamp(), p['url']))[:n]
        require(ranked, '유효 조사 자료 0개: 완료 불가')
        require(s['selected_ids'] == [p['id'] for p in ranked], f'Top {n} 순위/선정 불일치')
        expected = f'{"observed" if incomplete else "full"}_top{n}'
        require(s['ranking_scope'] == expected, f'조사 범위와 Top {n} 주장 불일치: {expected} 필요')
        md, ppt = self.read('research'), pptx_text(self.path('pptx'))
        for p in ranked:
            for field in (p['id'], p['url']):
                require(field in md and field in ppt, f'보고서 출처/ID 누락: {field}')
        if self.state.get('research_report_format') == 'clean-pptx-v1':
            shown = ppt+'\n'+pptx_notes(self.path('pptx'))
            found = REPORT_FORBIDDEN.search(shown)
            require(not found, f'보고서 PPTX에 한계·미확인·검사 상태 표현: {found and found.group()}')
            claim = FULL_RANK_CLAIM.search(shown)
            require(not (incomplete and claim), f'미검증 전체 순위를 PPTX에 표현: {claim and claim.group()}')
        if incomplete:
            require(text(s['limitations']) and '확인한 게시물 중' in md,
                    '부분 조사 한계 표시 누락')
            self.warnings.append(f'확인한 게시물 중 순위. 전체 Top {n}가 아님.')
        if len(ranked) < n:
            self.warnings.append(f'유효 자료 {len(ranked)}개. 부족한 수를 임의로 채우지 않음.')

    def planning(self):
        p = self.plan()
        presentation = self.paths.get('plan_presentation')
        if presentation:
            review_plan = check_plan_document(self.local(presentation).read_text(encoding='utf-8'))
            require(review_plan == p, '검토용 기획서와 승인 보관본 제작 데이터 불일치')
        elif self.state.get('plan_document_format') == 'human-first-v1' or PLAN_REVIEW_START in self.read('plan'):
            check_plan_document(self.read('plan'))
        for key in ('topic', 'target', 'purpose', 'message', 'caption'):
            require(text(p[key]), f'기획 {key} 누락')
        require(type(p['width']) is int and type(p['height']) is int and p['width'] > 0 and p['height'] > 0,
                '기획 치수 오류')
        require([p['width'], p['height']] == self.state['input']['size'], '합의 규격/기획 불일치')
        cards = p['cards']
        require(cards and p['card_count'] == len(cards), '기획 장수 불일치')
        require(len({c['id'] for c in cards}) == len(cards), '중복 카드 ID')
        known = {x['id'] for x in self.obj('sources')['posts']}
        cta = []
        for c in cards:
            require(re.fullmatch(r'[A-Za-z0-9_-]+', c['id']), '파일명으로 쓸 수 없는 카드 ID')
            require(c['copy'] and all(text(v) for v in c['copy']), '카드 문구 누락')
            for k in ('role', 'layout', 'photo_brief'):
                require(text(c[k]), f'{c["id"]} {k} 누락')
            require(type(c['photo_required']) is bool, 'photo_required boolean 필요')
            require(set(c['source_ids']) <= known, '기획 출처 ID 없음')
            if c.get('cta'):
                cta.append(c['cta'])
                require(c['cta'] in c['copy'], 'CTA가 카드 문구에 없음')
        require(len(cta) == 1 and cta[0] == p['primary_cta'], '주된 CTA 정확히 하나 필요')
        public = p['caption']+'\n'+'\n'.join(v for c in cards for v in c['copy'])
        require(not MARKERS.search(public), '완성 문구에 미해결 표시')

    def preview(self):
        self.approval('plan')
        p = self.plan()
        html = self.read('html')
        parser = CardsHTML(); parser.feed(html); parser.close()
        require(not parser.stack and parser.copy is None, 'HTML 미닫힌 태그')
        self.compare_cards(parser.cards, 'HTML')
        require(not re.search(r'<(?:script|iframe)\b', html, re.I), '프리뷰는 실행 스크립트 없는 정적 HTML 사용')
        assets = self.obj('assets')['items']
        require(len({a['id'] for a in assets}) == len(assets), '중복 자산 ID')
        by_url = {}
        for a in assets:
            require(a['kind'] in ('photo', 'reference', 'font'), '자산 종류 오류')
            f = self.asset_path(a)
            require(f.is_file() and sha(f) == a['sha256'], f'자산 누락/해시 불일치: {a["id"]}')
            require(text(a['source']), '자산 출처 누락')
            require(set(a['card_ids']) <= {c['id'] for c in p['cards']}, '자산의 카드 ID 오류')
            require(a['html_url'] not in by_url, '중복 자산 URL')
            by_url[a['html_url']] = a
            require(not urlparse(a['html_url']).scheme and not a['html_url'].startswith('/'), '로컬 상대 자산 URL 필요')
            resolved = (self.path('html').parent/unquote(a['html_url'])).resolve()
            require(resolved == f, 'HTML 자산 URL/경로 불일치')
            if a['kind'] == 'photo':
                require(a['run_id'] == self.state['run_id'] and a['method'] == 'codex-imagegen', '신규 사진 제작 기록 오류')
                require(text(a['prompt']), '사진 프롬프트 누락')
                require(stamp(a['created_at']) >= stamp(self.state['approvals']['plan']['at']), '기획 승인 전 생성 사진')
                require(f.suffix.lower() == '.png', '검수용 신규 사진은 PNG로 준비')
                png_size(f)
                self.check_reuse(a['sha256'])
        resources = parser.resources + re.findall(r'url\(\s*[\"\']?([^\)\"\']+)[\"\']?\s*\)', html)
        for url in resources:
            if url.startswith('#'):
                continue
            require(url in by_url, f'등록하지 않은 HTML 자원: {url}')
        for a in assets:
            require(a['html_url'] in resources, f'HTML에서 쓰지 않는 자산: {a["id"]}')
        for c in p['cards']:
            photos = [a for a in assets if a['kind'] == 'photo' and c['id'] in a['card_ids']]
            require(not c['photo_required'] or photos, f'{c["id"]} 신규 사진 없음')
        b = self.obj('browser')
        require(b['html_sha256'] == sha(self.path('html')), '브라우저 검사가 오래된 HTML')
        require(b['preview_digest'] == self.digest('preview'), '브라우저 검사가 오래된 자산/기획')
        stamp(b['checked_at'])
        require(text(b['tool']) and b['fonts_loaded'] is True and b['images_loaded'] is True
                and b['overflow_card_ids'] == [], '브라우저 서체/이미지/넘침 오류')
        self.compare_cards(b['cards'], '브라우저')
        require(b['screenshots'], '프리뷰 검토 화면 누락')
        for shot in b['screenshots']:
            png_size(self.local(shot))

    def check_reuse(self, digest):
        for other in (self.project/'runs').glob('*/**/assets.json'):
            if other.is_relative_to(self.root):
                continue
            try:
                entries = json.loads(other.read_text())['items']
            except (ValueError, KeyError, TypeError):
                self.warnings.append(f'이전 자산 기록 읽기 실패: {other}')
                continue
            require(not any(a.get('kind') == 'photo' and a.get('sha256') == digest for a in entries),
                    '이전 기획과 동일한 사진 파일')

    def compare_cards(self, actual, label):
        p = self.plan()
        require([c['id'] for c in actual] == [c['id'] for c in p['cards']], f'{label} 카드 수/순서 불일치')
        for a, c in zip(actual, p['cards']):
            require(abs(a['width']-p['width']) < .1 and abs(a['height']-p['height']) < .1,
                    f'{label} 카드 규격 불일치')
            require([norm(t) for t in a['copy']] == [norm(t) for t in c['copy']], f'{label} 문구 불일치')

    def final(self):
        self.approval('preview')
        f = self.obj('figma')
        self.figma_destination(f)
        require(f['url'].startswith('https://www.figma.com/design/'+f['file_key']+'/'), 'Figma 결과 링크 오류')
        require(stamp(f['created_at']) >= stamp(self.state['approvals']['preview']['at']), '프리뷰 승인 전 Figma 제작')
        require(stamp(f['read_at']) >= stamp(f['created_at']), 'Figma 읽기 시각 오류')
        require(f['preview_digest'] == self.digest('preview'), 'Figma가 현재 프리뷰에 대응하지 않음')
        self.compare_cards(f['cards'], 'Figma')
        node_ids = []
        for c, plan in zip(f['cards'], self.plan()['cards']):
            node_ids.append(c['node_id'])
            require(c['text_nodes'] and all(n['type'] == 'TEXT' and text(n['id']) for n in c['text_nodes']),
                    '편집 가능한 TEXT 노드 없음')
            require([norm(n['characters']) for n in c['text_nodes']] == [norm(t) for t in plan['copy']],
                    'Figma 실제 텍스트 노드/기획 불일치')
            require(not plan['photo_required'] or c['image_node_ids'], 'Figma 별도 이미지 레이어 없음')
            require(c['vector_node_ids'], 'Figma 로고/도형 레이어 없음')
            png_size(self.local(c['screenshot']))
        require(len(set(node_ids)) == len(node_ids), '중복 Figma 카드 노드')
        cards = self.plan()['cards']
        expected = {c['id']+'.png' for c in cards}
        actual = {p.name for p in self.path('png').glob('*.png')}
        require(actual == expected, 'PNG 장수/파일명 불일치')
        for name in expected:
            require(png_size(self.path('png')/name) == (self.plan()['width'], self.plan()['height']), 'PNG 규격 불일치')
        caption = self.read('caption')
        require(norm(caption) == norm(self.plan()['caption']), '최종 캡션/승인 기획 불일치')
        require(not MARKERS.search(caption), '캡션 미해결 표시')
        require(text(self.read('review')), '시각 검토 기록 누락')

    def figma_destination(self, f):
        """Default: a new file per run. Existing file: only a user-directed new section."""
        a = self.state.get('figma_destination_authorization')
        if not a:
            require(f['file_key'] != self.manifest().get('file_key'),
                    '원본 Figma를 출력 대상으로 사용: 별도 섹션 추가 사용자 지시 필요')
            for other in (self.project/'runs').glob('*/**/figma.json'):
                if other.is_relative_to(self.root):
                    continue
                try:
                    used = json.loads(other.read_text()).get('file_key')
                except (ValueError, AttributeError):
                    self.warnings.append(f'이전 Figma 기록 읽기 실패: {other}')
                    continue
                require(used != f['file_key'], '다른 실행의 Figma 파일 재사용: 실행별 새 파일 또는 섹션 추가 지시 필요')
            return
        require(a.get('actor') == 'user' and text(a.get('quote'))
                and a.get('file_key') == f['file_key']
                and a.get('mode') == 'append_new_section'
                and text(f.get('section_id'))
                and a.get('output_section_id') == f['section_id'],
                '기존 Figma 파일을 출력 대상으로 사용: 해당 파일의 별도 섹션 추가 사용자 지시 필요')
        stamp(a['recorded_at'])
        existing = set(a.get('existing_node_ids', []))
        require(existing and f['section_id'] not in existing
                and all(c['node_id'] not in existing for c in f['cards']),
                '기존 Figma 파일의 기존 노드를 출력으로 사용')

    def validate(self, stage):
        tasks = [('state', self.baseline), ('research', self.research), ('plan', self.planning),
                 ('preview', self.preview), ('final', self.final)]
        for name, task in tasks[:STAGES.index(stage)+2]:
            try:
                task()
                self.passed.append(name)
            except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError,
                    ET.ParseError, zlib.error, struct.error, BadZipFile) as e:
                self.errors.append({'check': name, 'message': str(e)})
        return {'schema_version': 1, 'run_id': self.state.get('run_id'), 'stage': stage,
                'automatic_pass': not self.errors, 'passed': self.passed, 'errors': self.errors,
                'warnings': self.warnings,
                'limits': ['Offline evidence consistency only; no live Figma/Aside verification.',
                           'Approval authenticity, factual accuracy and visual quality require review.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--project', type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--stage', choices=STAGES)
    modes.add_argument('--digest', choices=('plan', 'preview'))
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        run = Run(args.run, args.project)
        if args.digest:
            print(run.digest(args.digest))
            return 0
        report = run.validate(args.stage)
    except Exception as e:
        report = {'automatic_pass': False, 'errors': [{'check': 'input', 'message': str(e)}]}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)+'\n'
    print(rendered, end='')
    if args.report:
        target = args.report.resolve()
        if not target.is_relative_to((args.run/'checks').resolve()):
            print('report는 실행 폴더의 checks/ 아래에 저장해야 합니다.', file=sys.stderr)
            return 2
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding='utf-8')
    return 0 if report['automatic_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
