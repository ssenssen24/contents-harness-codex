"""Synthetic offline fixtures; never invokes Aside, image generation or Figma."""
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED

from validate_run import Run, sha, pptx_text
from check_all_runs import claimed_stage
from plan_document import compose, check, sync


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def write_text(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding='utf-8')


def png(path, width=1080, height=1350, color=b'\x10\x20\x30'):
    def chunk(kind, body):
        return struct.pack('>I', len(body))+kind+body+struct.pack('>I', zlib.crc32(kind+body)&0xffffffff)
    data = b'\x89PNG\r\n\x1a\n'
    data += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    data += chunk(b'IDAT', zlib.compress((b'\x00'+color*width)*height))
    data += chunk(b'IEND', b'')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def pptx(path, content, slide_target='slides/slide1.xml', notes=None):
    # Minimal OOXML fixture for structural checks, not a deliverable slide deck.
    p = 'http://schemas.openxmlformats.org/presentationml/2006/main'
    a = 'http://schemas.openxmlformats.org/drawingml/2006/main'
    r = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    rel = 'http://schemas.openxmlformats.org/package/2006/relationships'
    parts = {
        '[Content_Types].xml': '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                              '<Default Extension="xml" ContentType="application/xml"/>'
                              '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
                              '<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/></Types>',
        '_rels/.rels': f'<Relationships xmlns="{rel}"><Relationship Id="rId1" Type="{r}/officeDocument" Target="ppt/presentation.xml"/></Relationships>',
        'ppt/presentation.xml': f'<p:presentation xmlns:p="{p}" xmlns:r="{r}"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst></p:presentation>',
        'ppt/_rels/presentation.xml.rels': f'<Relationships xmlns="{rel}"><Relationship Id="rId1" Type="{r}/slide" Target="{escape(slide_target)}"/></Relationships>',
        'ppt/slides/slide1.xml': f'<p:sld xmlns:p="{p}" xmlns:a="{a}"><p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{escape(content)}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>'
    }
    if notes is not None:
        parts['ppt/notesSlides/notesSlide1.xml'] = (f'<p:notes xmlns:p="{p}" xmlns:a="{a}"><p:cSld><p:spTree><p:sp><p:txBody>'
                                                     f'<a:p><a:r><a:t>{escape(notes)}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:notes>')
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, 'w', ZIP_DEFLATED) as z:
        for name, value in parts.items():
            z.writestr(name, value)


class HarnessTests(unittest.TestCase):
    def test_pptx_package_root_slide_target(self):
        path=self.root/'absolute.pptx'
        pptx(path,'root target works','/ppt/slides/slide1.xml')
        self.assertIn('root target works',pptx_text(path))

    def test_pptx_missing_absolute_slide_target(self):
        path=self.root/'missing.pptx'
        pptx(path,'missing target','/ppt/slides/slide99.xml')
        with self.assertRaisesRegex(ValueError,'PPTX slide 관계 누락'):
            pptx_text(path)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='content-harness-test-')
        self.project = Path(self.temp.name)
        self.root = self.project/'runs/example'
        self.root.mkdir(parents=True)
        for name in ('brand.md', 'content-design.md', 'assets/reference/manifest.json'):
            write_text(self.project/name, 'synthetic reference: '+name)
        write_text(self.project/'assets/reference/logo.svg', '<svg xmlns="http://www.w3.org/2000/svg"/>')
        write_json(self.project/'assets/reference/manifest.json', {'file_key': 'SOURCE_FILE', 'assets': [
            {'file': 'logo.svg', 'sha256': sha(self.project/'assets/reference/logo.svg')}]})
        self.window = {'start': '2026-07-02T09:00:00+09:00', 'end': '2026-09-30T09:00:00+09:00'}
        self.state = {
            'schema_version': 1, 'run_id': 'example',
            'input': {'accounts': ['nikerunning', 'adidasrunning'], 'size': [1080, 1350], 'window': self.window},
            'reference_hashes': {n: sha(self.project/n) for n in
                                ('brand.md', 'content-design.md', 'assets/reference/manifest.json')},
            'stages': {n: {'status': 'in_progress'} for n in ('research', 'plan', 'preview', 'final')},
            'approvals': {}}
        self.save_state()
        posts = []
        for i in range(7):
            evidence = f'research/evidence/s{i}.txt'
            write_text(self.root/evidence, 'SYNTHETIC offline fixture, no browser visit')
            posts.append(dict(id=f's{i}', account=self.state['input']['accounts'][i % 2],
                              url=f'https://www.instagram.com/p/TEST{i}/',
                              published_at=f'2026-09-{i+1:02}T12:00:00+09:00',
                              checked_at='2026-09-30T09:10:00+09:00', likes=100-i,
                              unknown_reasons={}, summary='요약', visual='시각', observation='관찰',
                              interpretation='해석', application='활용', evidence=[evidence]))
        self.sources = dict(collector='aside-repl', accounts=self.state['input']['accounts'], window=self.window,
                            coverage={a: {'status': 'complete', 'note': 'synthetic boundary evidence'}
                                      for a in self.state['input']['accounts']},
                            posts=posts, selected_ids=[f's{i}' for i in range(6)],
                            ranking_scope='full_top6', limitations='')
        self.save_sources()
        report = '\n'.join(p['id']+' '+p['url'] for p in posts[:6])
        write_text(self.root/'research/research.md', report)
        pptx(self.root/'research/research.pptx', report)
        self.plan = dict(topic='주제', target='대상', purpose='목적', message='메시지',
                         width=1080, height=1350, card_count=2, primary_cta='함께해요.', caption='승인 캡션',
                         cards=[dict(id='c01', role='공감', copy=['함께 달려요.'], cta=None,
                                     photo_required=True, photo_brief='새 사진', layout='사진형', source_ids=['s0']),
                                dict(id='c02', role='행동', copy=['함께해요.'], cta='함께해요.',
                                     photo_required=False, photo_brief='무사진', layout='문구형', source_ids=['s1'])])
        self.save_plan()
        self.approve('plan', '2026-09-30T10:00:00+09:00')
        png(self.root/'preview/images/new.png')
        png(self.root/'preview/screenshots/overview.png', 400, 500)
        self.assets = {'items': [
            dict(id='photo1', kind='photo', path='preview/images/new.png', html_url='images/new.png',
                 sha256=sha(self.root/'preview/images/new.png'), source='synthetic generation fixture',
                 card_ids=['c01'], run_id='example', method='codex-imagegen',
                 created_at='2026-09-30T10:10:00+09:00', prompt='synthetic prompt'),
            dict(id='logo', kind='reference', path='assets/reference/logo.svg',
                 html_url='../../../assets/reference/logo.svg', sha256=sha(self.project/'assets/reference/logo.svg'),
                 source='source node test', card_ids=['c01', 'c02'])]}
        write_json(self.root/'preview/assets.json', self.assets)
        self.html = '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>'
        for c in self.plan['cards']:
            self.html += f'<article data-card-id="{c["id"]}" data-width="1080" data-height="1350">'
            self.html += '<img src="../../../assets/reference/logo.svg" />'
            if c['photo_required']:
                self.html += '<img src="images/new.png">'
            self.html += ''.join(f'<p data-copy>{escape(t)}</p>' for t in c['copy'])+'</article>'
        self.html += '</body></html>'
        write_text(self.root/'preview/preview.html', self.html)
        self.browser = dict(tool='synthetic browser fixture', checked_at='2026-09-30T10:20:00+09:00',
                            html_sha256=sha(self.root/'preview/preview.html'),
                            preview_digest=self.checker().digest('preview'), fonts_loaded=True, images_loaded=True,
                            overflow_card_ids=[], screenshots=['preview/screenshots/overview.png'],
                            cards=[dict(id=c['id'], width=1080, height=1350, copy=c['copy']) for c in self.plan['cards']])
        write_json(self.root/'preview/browser-check.json', self.browser)
        self.approve('preview', '2026-09-30T10:30:00+09:00')
        self.figma = dict(file_key='NEW_FILE', url='https://www.figma.com/design/NEW_FILE/',
                          created_at='2026-09-30T10:40:00+09:00', read_at='2026-09-30T10:50:00+09:00',
                          preview_digest=self.checker().digest('preview'), cards=[])
        for i, c in enumerate(self.plan['cards']):
            png(self.root/f'final/png/{c["id"]}.png')
            self.figma['cards'].append(dict(id=c['id'], node_id=f'10:{i}', width=1080, height=1350,
                copy=c['copy'], text_nodes=[dict(id=f'20:{i}', type='TEXT', characters=t) for t in c['copy']],
                image_node_ids=['30:1'] if c['photo_required'] else [], vector_node_ids=['40:1'],
                screenshot='preview/screenshots/overview.png'))
        write_json(self.root/'final/figma.json', self.figma)
        write_text(self.root/'final/caption.md', self.plan['caption'])
        write_text(self.root/'checks/review.md', 'Synthetic only, no real human/visual approval.')
        self.set_status(research='complete', plan='approved', preview='approved', final='in_progress')

    def tearDown(self):
        self.temp.cleanup()

    def checker(self):
        return Run(self.root, self.project)

    def set_status(self, **statuses):
        for stage, status in statuses.items():
            self.state['stages'][stage]['status'] = status
        self.save_state()

    def research_only(self):
        # Research-data edits change the plan digest, so model a run still in research.
        self.set_status(research='in_progress', plan='not_run', preview='not_run', final='not_run')

    def save_state(self):
        write_json(self.root/'state.json', self.state)

    def save_sources(self):
        write_json(self.root/'research/sources.json', self.sources)

    def save_plan(self):
        write_text(self.root/'plan/plan.md', '# Fixture\n```content-plan\n'+json.dumps(self.plan, ensure_ascii=False)+'\n```\n')

    def approve(self, stage, at):
        self.state['approvals'][stage] = dict(actor='user', quote='SYNTHETIC 승인 fixture', at=at,
                                              digest=self.checker().digest(stage))
        self.save_state()

    def fails(self, stage, message):
        report = self.checker().validate(stage)
        self.assertFalse(report['automatic_pass'], report)
        self.assertIn(message, str(report['errors']))

    def test_valid_all_stages(self):
        for stage in ('research', 'plan', 'preview', 'final'):
            with self.subTest(stage=stage):
                report = self.checker().validate(stage)
                self.assertTrue(report['automatic_pass'], report)

    def test_missing_pptx(self):
        (self.root/'research/research.pptx').unlink()
        self.fails('research', 'research.pptx')

    def test_corrupt_pptx(self):
        (self.root/'research/research.pptx').write_bytes(b'not zip')
        self.fails('research', 'zip')

    def test_wrong_rank(self):
        self.sources['selected_ids'].reverse(); self.save_sources()
        self.fails('research', 'Top 6 순위')

    def test_out_of_window_selection(self):
        self.sources['posts'][0]['published_at'] = '2026-01-01T00:00:00+09:00'; self.save_sources()
        self.fails('research', 'Top 6 순위')

    def test_hidden_likes_reason_required(self):
        self.sources['posts'][6]['likes'] = None; self.save_sources()
        self.fails('research', '미확인 이유')

    def test_partial_cannot_claim_full(self):
        self.sources['coverage']['nikerunning']['status'] = 'partial'; self.save_sources()
        self.fails('research', 'Top 6 주장')

    def test_partial_report_passes_with_caveat(self):
        self.research_only()
        self.sources['coverage']['nikerunning']['status'] = 'partial'
        self.sources['ranking_scope'] = 'observed_top6'
        self.sources['limitations'] = '일부 접근 불가'; self.save_sources()
        report = (self.root/'research/research.md').read_text()+'\n확인한 게시물 중 Top 6'
        write_text(self.root/'research/research.md', report)
        pptx(self.root/'research/research.pptx', report.replace('확인한 게시물 중 Top 6', '선정 게시물 분석'))
        result = self.checker().validate('research')
        self.assertTrue(result['automatic_pass'], result)
        self.assertTrue(result['warnings'])

    def test_partial_report_still_needs_internal_limits(self):
        self.sources['coverage']['nikerunning']['status'] = 'partial'
        self.sources['ranking_scope'] = 'observed_top6'
        self.sources['limitations'] = ''
        self.save_sources()
        self.fails('research', '한계 표시 누락')

    def test_completed_reference_snapshot(self):
        before = self.checker().digest('plan')
        original = (self.project/'brand.md').read_text()
        write_text(self.root/'references/brand.md', original)
        self.state['reference_snapshots'] = {'brand.md': 'references/brand.md'}
        self.state['stages']['final']['status'] = 'complete'
        self.save_state()
        write_text(self.project/'brand.md', original+'\n경쟁사 설정 추가')
        self.assertEqual(before, self.checker().digest('plan'))
        self.assertTrue(self.checker().validate('final')['automatic_pass'])
        write_text(self.root/'references/brand.md', '보관본 변조')
        self.fails('plan', '기준 파일 변경')

    def test_source_missing_in_ppt(self):
        pptx(self.root/'research/research.pptx', 'no sources')
        self.fails('research', '출처/ID 누락')

    def test_wrong_card_count(self):
        self.plan['card_count'] = 3; self.save_plan()
        self.fails('plan', '기획 장수')

    def test_unresolved_marker(self):
        self.plan['cards'][0]['copy'][0] = '[확인 필요: 지역]'; self.save_plan()
        self.fails('plan', '미해결 표시')

    def test_two_ctas(self):
        self.plan['cards'][0]['cta'] = self.plan['cards'][0]['copy'][0]; self.save_plan()
        self.fails('plan', 'CTA 정확히 하나')

    def test_missing_plan_approval(self):
        del self.state['approvals']['plan']; self.save_state()
        self.fails('preview', '사용자 승인 없음')

    def test_stale_plan_approval(self):
        self.plan['message'] = '변경'; self.save_plan()
        self.fails('preview', 'plan 승인 버전')

    def test_human_plan_consistency(self):
        doc = compose(self.plan, '미확인: 실제 URL. 사람 판단: 메시지와 사진 분위기.')
        self.assertEqual(check(doc), self.plan)
        # A reviewer seeing different copy must block production.
        bad = doc.replace(self.plan['cards'][0]['copy'][0], '표에서만 바뀐 문구', 1)
        with self.assertRaisesRegex(ValueError, '불일치'):
            check(bad)
        self.assertEqual(check(sync(bad)), self.plan)

    def test_human_plan_missing_review(self):
        self.state['plan_document_format'] = 'human-first-v1'
        self.save_state()
        self.fails('plan', '검토용')

    def test_archived_approval_with_presentation(self):
        before = self.checker().digest('plan')
        doc = compose(self.plan, '확인 사항')
        write_text(self.root/'plan/archive/v001.md', (self.root/'plan/plan.md').read_text())
        write_text(self.root/'plan/plan.md', doc)
        self.state.setdefault('paths', {}).update(plan='plan/archive/v001.md', plan_presentation='plan/plan.md')
        self.save_state()
        self.assertEqual(before, self.checker().digest('plan'))
        self.assertTrue(self.checker().validate('final')['automatic_pass'])
        changed = json.loads(json.dumps(self.plan))
        changed['cards'][0]['layout'] = '새로운 화면 구성'
        write_text(self.root/'plan/plan.md', compose(changed, '확인 사항'))
        self.fails('plan', '승인 보관본')

    def test_human_plan_caption_and_bottom_data(self):
        doc = compose(self.plan, '확인 사항')
        with self.assertRaisesRegex(ValueError, '불일치'):
            check(doc.replace('> ', '> 다른 캡션 ', 1))
        with self.assertRaisesRegex(ValueError, '하단'):
            check(doc + '\n기계 데이터 뒤 별도 설명\n')

    def test_stale_preview_approval(self):
        write_text(self.root/'preview/preview.html', self.html+'\n<!-- layout changed -->')
        self.fails('final', 'preview 승인 버전')

    def test_html_copy_mismatch(self):
        write_text(self.root/'preview/preview.html', self.html.replace('함께 달려요.', '다른 문구'))
        self.fails('preview', 'HTML 문구')

    def test_html_card_order(self):
        changed = self.html.replace('c01', 'tmp').replace('c02', 'c01').replace('tmp', 'c02')
        write_text(self.root/'preview/preview.html', changed)
        self.fails('preview', 'HTML 카드 수/순서')

    def test_asset_missing(self):
        (self.root/'preview/images/new.png').unlink()
        self.fails('preview', '자산 누락')

    def test_photo_before_approval(self):
        self.assets['items'][0]['created_at'] = '2026-09-30T09:00:00+09:00'
        write_json(self.root/'preview/assets.json', self.assets)
        self.fails('preview', '승인 전 생성')

    def test_reused_photo(self):
        write_json(self.project/'runs/previous/preview/assets.json', self.assets)
        self.fails('preview', '이전 기획과 동일')

    def test_browser_stale_assets(self):
        png(self.root/'preview/images/new.png', color=b'\x40\x40\x40')
        self.assets['items'][0]['sha256'] = sha(self.root/'preview/images/new.png')
        write_json(self.root/'preview/assets.json', self.assets)
        self.fails('preview', '브라우저 검사가 오래된 자산')

    def test_path_only_move_preserves_digest(self):
        old = self.checker().digest('preview')
        (self.root/'preview/images/new.png').rename(self.root/'preview/images/moved.png')
        self.assets['items'][0].update(path='preview/images/moved.png', html_url='images/moved.png')
        write_json(self.root/'preview/assets.json', self.assets)
        write_text(self.root/'preview/preview.html', self.html.replace('images/new.png', 'images/moved.png'))
        self.assertEqual(old, self.checker().digest('preview'))

    def test_frozen_original_figma(self):
        self.figma['file_key'] = 'SOURCE_FILE'
        write_json(self.root/'final/figma.json', self.figma)
        self.fails('final', '원본 Figma')

    def test_figma_file_reused_from_other_run(self):
        write_json(self.project/'runs/previous/final/figma.json', {'file_key': 'NEW_FILE'})
        self.fails('final', '다른 실행의 Figma 파일')

    def test_figma_authorization_for_other_file(self):
        self.state['figma_destination_authorization'] = dict(
            actor='user', quote='SYNTHETIC: 다른 파일 지정', file_key='OTHER_FILE', mode='append_new_section',
            output_section_id='99:1', existing_node_ids=['1:1'], recorded_at='2026-09-30T10:40:00+09:00')
        self.save_state()
        self.fails('final', '별도 섹션 추가 사용자 지시')

    def test_stage_order(self):
        self.set_status(plan='in_progress')
        self.fails('research', '상태 순서 오류')

    def test_claimed_approval_needs_record(self):
        del self.state['approvals']['preview']; self.save_state()
        self.fails('research', 'preview 사용자 승인 없음')

    def test_claimed_approval_must_match_files(self):
        self.plan['message'] = '승인 후 변경'; self.save_plan()
        self.fails('research', 'plan 승인 버전')

    def test_awaiting_approval_pending_digest(self):
        self.set_status(plan='awaiting_approval', preview='not_run', final='not_run')
        self.state['stages']['plan']['pending_digest'] = self.checker().digest('plan')
        self.save_state()
        self.assertTrue(self.checker().validate('plan')['automatic_pass'])
        self.plan['message'] = '제시 후 변경'; self.save_plan()
        self.fails('research', 'pending_digest')

    def test_blocked_needs_reason_and_resume(self):
        self.set_status(final='blocked')
        self.fails('research', 'blocked 원인')
        self.state['stages']['final']['reason'] = 'Figma 접근 실패'
        self.state['resume'] = {'stage': 'final', 'next_action': 'Figma 권한 확인 후 재시도'}
        self.save_state()
        self.assertTrue(self.checker().validate('preview')['automatic_pass'])

    def test_top_n_from_state(self):
        self.research_only()
        self.state['input']['top_n'] = 3; self.save_state()
        self.fails('research', 'Top 3 순위')
        self.sources.update(selected_ids=['s0', 's1', 's2'], ranking_scope='full_top3'); self.save_sources()
        self.assertTrue(self.checker().validate('research')['automatic_pass'])
        self.sources['ranking_scope'] = 'full_top6'; self.save_sources()
        self.fails('research', 'full_top3 필요')

    def test_clean_pptx_report(self):
        self.research_only()
        report = (self.root/'research/research.md').read_text()
        self.state['research_report_format'] = 'clean-pptx-v1'; self.save_state()
        self.assertTrue(self.checker().validate('research')['automatic_pass'])
        pptx(self.root/'research/research.pptx', report+'\n이 보고서의 순위에는 한계가 있습니다')
        self.fails('research', '한계·미확인·검사 상태')
        pptx(self.root/'research/research.pptx', report, notes='좋아요 미확인 게시물 제외')
        self.fails('research', '한계·미확인·검사 상태')

    def test_clean_pptx_no_unverified_full_rank(self):
        self.research_only()
        self.state['research_report_format'] = 'clean-pptx-v1'; self.save_state()
        self.sources['coverage']['nikerunning']['status'] = 'partial'
        self.sources.update(ranking_scope='observed_top6', limitations='일부 구간 미확인'); self.save_sources()
        report = (self.root/'research/research.md').read_text()+'\n확인한 게시물 중 Top 6'
        write_text(self.root/'research/research.md', report)
        pptx(self.root/'research/research.pptx', report.replace('확인한 게시물 중 Top 6', '전체 Top 6'))
        self.fails('research', '미검증 전체 순위')
        pptx(self.root/'research/research.pptx', report.replace('확인한 게시물 중 Top 6', '선정 게시물 분석'))
        self.assertTrue(self.checker().validate('research')['automatic_pass'])

    def test_claimed_stage_for_ci(self):
        self.assertEqual(claimed_stage(self.state), 'preview')
        self.set_status(final='complete')
        self.assertEqual(claimed_stage(self.state), 'final')
        self.set_status(research='in_progress', plan='not_run', preview='not_run', final='not_run')
        self.assertIsNone(claimed_stage(self.state))

    def test_no_editable_text(self):
        self.figma['cards'][0]['text_nodes'] = []
        write_json(self.root/'final/figma.json', self.figma)
        self.fails('final', 'TEXT 노드 없음')

    def test_explicit_append_to_original(self):
        self.figma.update(file_key='SOURCE_FILE',
                          url='https://www.figma.com/design/SOURCE_FILE/', section_id='99:1')
        self.state['figma_destination_authorization'] = dict(
            actor='user', quote='SYNTHETIC: 여기 섹션 옆에 추가',
            file_key=self.figma['file_key'], mode='append_new_section',
            output_section_id='99:1', existing_node_ids=['1:1'],
            recorded_at='2026-09-30T10:40:00+09:00')
        self.save_state()
        write_json(self.root/'final/figma.json', self.figma)
        self.assertTrue(self.checker().validate('final')['automatic_pass'])
        self.state['figma_destination_authorization']['existing_node_ids'].append('10:0')
        self.save_state()
        self.fails('final', '기존 노드')

    def test_png_missing(self):
        (self.root/'final/png/c02.png').unlink()
        self.fails('final', 'PNG 장수')

    def test_png_wrong_dimensions(self):
        png(self.root/'final/png/c01.png', 100, 100)
        self.fails('final', 'PNG 규격')

    def test_png_corruption(self):
        p = self.root/'final/png/c01.png'
        data = bytearray(p.read_bytes()); data[45] ^= 1; p.write_bytes(data)
        self.fails('final', 'PNG CRC')

    def test_caption_mismatch(self):
        write_text(self.root/'final/caption.md', '승인과 다른 캡션')
        self.fails('final', '캡션/승인')

    def test_changed_reference(self):
        write_text(self.project/'brand.md', 'changed')
        self.fails('plan', '기준 파일 변경')

    def test_changed_original_logo(self):
        write_text(self.project/'assets/reference/logo.svg', '<svg>changed</svg>')
        self.fails('plan', '원본 참조 자산 변경')

    def test_unused_photo_cannot_pass(self):
        write_text(self.root/'preview/preview.html', self.html.replace('<img src="images/new.png">', ''))
        self.fails('preview', 'HTML에서 쓰지 않는 자산')

    def test_malformed_schema_fails(self):
        write_json(self.root/'plan/plan.md', {})
        self.fails('plan', 'content-plan')

    def test_cli_exit_codes_and_report(self):
        tool = str(Path(__file__).with_name('validate_run.py'))
        cmd = [sys.executable, tool, str(self.root), '--stage', 'final', '--report', str(self.root/'checks/report.json')]
        ok = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout)
        self.assertTrue(json.loads((self.root/'checks/report.json').read_text())['automatic_pass'])
        (self.root/'final/png/c02.png').unlink()
        bad = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertFalse(json.loads(bad.stdout)['automatic_pass'])


if __name__ == '__main__':
    unittest.main()
