import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

run=Path(__file__).resolve().parent.parent
ev=run/'research/evidence'
state=json.loads((run/'state.json').read_text())
dates={}
for f in sorted(ev.glob('*posts-*.json')):
    for p in json.loads(f.read_text()): dates[p['href']]=p
for f in ev.glob('*boundary.json'):
    for p in json.loads(f.read_text()): dates.setdefault(p['href'],p)
posts=[]
for account,prefix,fn in [('nikerunning','n','nike-candidates.json'),('adidasrunning','a','adidas-candidates-more.json')]:
    for i,p in enumerate(json.loads((ev/fn).read_text()),1):
        code=p['href'].rstrip('/').split('/')[-1]
        raw=p['metrics'].split('\n')[0].strip()
        likes=int(raw.replace(',','')) if raw.replace(',','').isdigit() else None
        meta=dates.get(p['href'],{})
        pub=meta.get('dates',[{}])[0].get('date') if meta.get('dates') else None
        reasons={}
        if likes is None: reasons['likes']=f'화면 표시값 {raw!r}. 축약 표시는 정확한 정수로 환산하지 않음.'
        if pub is None: reasons['published_at']='프로필에서 발견한 추가 후보. 기간 경계 아래의 게시물로, 개별 게시 시각까지 조회하지 않음. 순위에서 제외.'
        evidence=['research/evidence/'+fn,'research/evidence/hover-'+code+'.txt']
        if (ev/('post-'+code+'.txt')).exists(): evidence.append('research/evidence/post-'+code+'.txt')
        evidence=[x for x in evidence if (run/x).exists()]
        excerpt=' '.join(p.get('alt','').split()[:15])
        posts.append(dict(id=f'{prefix}{i:03}',account=account,url='https://www.instagram.com'+p['href'],published_at=pub,
            checked_at=meta.get('checked_at',p['checked_at']),likes_checked_at=p['checked_at'],likes=likes,displayed_likes=raw,
            unknown_reasons=reasons,summary='캡션 짧은 발췌: '+excerpt,
            visual='미확인: 순위 비교용 후보로 수집했으며 개별 시각 분석은 선정 6개에 한정함.',
            observation='지정 계정 프로필의 게시물 링크와 캡션, 좋아요 표시값을 확인함. 캡션 속 제품 효능·경기 기록의 외부 사실 검증은 하지 않음.',
            interpretation='미평가: 순위에서 선정되지 않은 후보의 메시지 효과는 추정하지 않음.',
            application='순위 및 조사 범위 확인 근거로 보존. 개별 기획 인사이트는 선정 게시물 분석 참조.',evidence=evidence,
            screenshot='research/evidence/post-'+code+'.png'))

details={
'DcdsVnXDLex':dict(title='제품의 탄생 과정을 한 장면으로',summary='Agravic Speed Ultra Evo 개발 이야기를\n제품 소개와 연결합니다.',visual='첫 장: 장비에 놓인 분홍색 신발,\n청록빛과 기계 프레임의 강한 대비.',interpretation='제품 뒤의 과정을 보여주며\n개발 서사에 구체성을 더합니다.',application='런메이트는 허구의 기술 대신\n함께 달리기 전의 작은 준비를 보여줍니다.',crop=[234,59,994,1008]),
'DbDKXpTjKdr':dict(title='동네의 러닝을 엽서처럼 소개하기',summary='LA 러닝 장면을 엽서 형식으로 묶어\nHyperboost 제품군을 소개합니다.',visual='첫 장: 하늘을 배경으로 올려다본 러너,\n전경의 신발과 상단의 도시명.',interpretation='장소와 관점이 제품 소개를\n하나의 러닝 장면으로 바꿉니다.',application='익숙한 동네와 동행의 장면을 연결하되\n도시명·운영 지역을 임의로 붙이지 않습니다.',crop=[140,59,1088,772]),
'DaZjf1jlbby':dict(title='한 장면과 큰 이름으로 전하는 경기 결과',summary='Pre Classic 선수들의 경기 결과를\n사진과 선수명 중심으로 소개합니다.',visual='첫 장: 모래에 착지하는 선수의 풀 사진,\n큰 흰색 이름과 작은 종목명.',interpretation='동작과 이름의 위계가 한눈에\n주인공을 알아보게 합니다.',application='승리·기록 대신 함께 달리는 장면에\n짧은 공감 문장 하나를 배치합니다.',crop=[234,59,994,1008]),
'DdgQbnSjCBY':dict(title='기록 소식의 첫 장을 감정으로 보여주기',summary='캡션은 Agnes Ngetich의 하프마라톤\n기록 소식을 전합니다.',visual='얼굴과 두 손을 크게 크롭한 사진,\n넓은 자간의 흰색 세리프 제목.',interpretation='숫자보다 인물의 표정이 먼저 보여\n소식에 감정을 붙이는 구성입니다.',application='완주 성과를 보장하지 않고, 함께 달린\n뒤 웃는 순간을 새 사진으로 보여줍니다.',crop=[254,59,974,1008]),
'DdwfExQDHzk':dict(title='러닝 경험을 공간으로 보여주기',summary='베를린 Home of Fast 전시 공간과\n제품을 소개합니다.',visual='분홍·파랑 공간 속 붉은 신발 한 켤레,\n중앙 진열대와 위쪽 로고.',interpretation='공간 전체의 색과 중심 피사체가\n현장에 들어온 느낌을 만듭니다.',application='동네 러닝 장소가 보이는 넓은 장면을\n쓰되, 실제 운영 장소처럼 주장하지 않습니다.',crop=[258,59,970,1008]),
'DdqgtSCsM7Y':dict(title='작은 디테일을 주인공으로 만들기',summary='Adios Pro 5의 세부 요소를\n강조하는 제품 릴스입니다.',visual='확인한 장면: 밝은 배경 위 손과\n신발 안쪽의 근접 촬영.',interpretation='주변 정보를 덜어내 제품 디테일에\n시선이 머물게 하는 방식입니다.',application='신발·보폭의 신규 디테일 컷으로\n편안하게 맞춰 달리는 순간을 표현합니다.',crop=[347,59,882,1008]),
}
for p in posts:
    code=p['url'].rstrip('/').split('/')[-1]
    if code in details:
        d=details[code].copy();c=d.pop('crop');p.update(d)
        p['crop']=dict(left=c[0]/1760,top=c[1]/1437,right=(1760-c[2])/1760,bottom=(1437-c[3])/1437)
        p['observation']=p['summary'].replace('\n',' ')+' '+p['visual'].replace('\n',' ')+' 캐러셀은 첫 장, 릴스는 캡처 시점 장면만 시각 분석함.'
        if (ev/('media-'+code+'.png')).exists():
            p['full_screenshot']=p['screenshot']
            p['screenshot']='research/evidence/media-'+code+'.png'
            p['evidence'] += [p['full_screenshot'],p['screenshot'],'research/evidence/media-'+code+'.txt']
start,end=map(datetime.fromisoformat,[state['input']['window']['start'],state['input']['window']['end']])
eligible=[p for p in posts if p['published_at'] and start<=datetime.fromisoformat(p['published_at'])<=end and p['likes'] is not None]
selected=sorted(eligible,key=lambda p:(-p['likes'],-datetime.fromisoformat(p['published_at']).timestamp(),p['url']))[:6]
within=[p for p in posts if p['published_at'] and start<=datetime.fromisoformat(p['published_at'])<=end]
counts={a:len([p for p in within if p['account']==a]) for a in state['input']['accounts']}
lim='확인한 게시물 중 정확한 좋아요 수와 게시일을 모두 확인한 후보만 순위에 포함했다. 만 단위 축약 표시 게시물은 null로 기록하고 제외했으므로, 이 목록은 전체 인기 Top 6가 아니다. 선정작보다 실제 좋아요가 많은 제외 게시물이 존재한다. 프로필에 보이지 않는 보관·삭제·제한 게시물은 확인할 수 없다. 영상 전편·캐러셀 모든 장을 분석한 것은 아니며, 도달·광고 집행·성과의 원인은 미확인이다.'
coverage={a:dict(status='partial',note=f'프로필 기간 경계 확인. 기간 내 개별 게시 시각 확인 {counts[a]}개. 목록에 표시된 공동 게시물 포함. 숨김·보관·삭제 게시물과 정확한 수치가 표시되지 않는 좋아요는 미확인. 상세 날짜를 확인하지 않은 더 오래된 발견 후보는 순위에서 제외.') for a in counts}
data=dict(collector='aside-repl',accounts=state['input']['accounts'],window=state['input']['window'],coverage=coverage,posts=posts,selected_ids=[p['id'] for p in selected],ranking_scope='observed_top6',limitations=lim,coverage_summary=f'기간 내 게시 시각 확인: Nike {counts["nikerunning"]}개 / adidas {counts["adidasrunning"]}개.\n정확한 좋아요 확인 {len(eligible)}개에서 6개 선정. 숨김·축약 수치의 한계는 남아 있습니다.')
(run/'research/sources.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps([dict(id=p['id'],url=p['url'],likes=p['likes'],title=p.get('title')) for p in selected],ensure_ascii=False,indent=2))

def kst(s): return datetime.fromisoformat(s).astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S KST') if s else '미확인'
def flat(s): return s.replace('\n',' ')
lines=['# 런메이트 경쟁사 리서치','',f'실행: `{state["run_id"]}` · 확인일: 2026-09-30 KST','',
'## 범위와 읽는 방법','',f'- 대상: nikerunning, adidasrunning. 두 계정 통합 기준이며 계정별 할당은 없다.',f'- 기간: {kst(state["input"]["window"]["start"])} ~ {kst(state["input"]["window"]["end"])}.',
'- 수집: 현재 Codex가 Aside 화면·DOM을 직접 읽었다. 프로필의 게시물·릴스를 확인하고, 고정 게시물은 개별 게시 시각으로 판단했다.',
f'- 발견 후보 {len(posts)}개. 기간 내 게시 시각 확인 {len(within)}개(Nike {counts["nikerunning"]}, adidas {counts["adidasrunning"]}). 이 중 정확한 좋아요 수가 확인된 {len(eligible)}개를 비교해 6개를 선정했다.',
'- 지정 계정 프로필에 표시된 공동 게시물도 발견 후보에 포함했다. permalink의 작성자 계정이 다른 것은 원본 링크를 보존한 결과이며 다른 프로필을 추가 조사한 것이 아니다.',
'- 좋아요 확인 시각과 게시일 확인 시각은 sources.json에 각각 보존했다. 단일 시점의 동시 스냅샷이 아니며 수치는 이후 바뀔 수 있다.',
'', '**조사 한계:** '+lim,'',
'기간의 경계는 Nike 2026-07-05 게시물 다음의 2026-07-01 UTC 게시물, adidas의 7월 게시물 다음 6월 게시물들을 직접 열어 확인했다. 모든 숨김·보관·삭제 게시물까지 포함한 전수 조사를 주장하지 않는다. 영상 전체 재생 및 캐러셀 전체 장면 분석도 미실시다.',
'','## 확인한 게시물 중 Top 6','',
'이 표는 **정확한 정수 수치를 확인한 후보만의 순위**다. 전체 인기 순위로 사용하면 안 된다. 동률은 게시일 내림차순, URL 오름차순으로 정렬한다.','',
'| 순위 | ID·출처 | 계정 | 좋아요 | 게시일(KST) |','| --- | --- | --- | ---: | --- |']
for i,p in enumerate(selected,1): lines.append(f'| {i} | [{p["id"]}]({p["url"]}) | {p["account"]} | {p["likes"]:,} | {kst(p["published_at"])} |')
lines+=['','## 선정 게시물 분석','', '아래의 관찰은 캡션과 실제 캡처 화면에 근거한다. 해석·활용은 Codex의 기획 제안이며 성과의 원인을 입증한 결과가 아니다.']
for p in selected:
    if not p.get('title'): raise ValueError('선정 게시물의 시각 분석 누락: '+p['id'])
    lines+=['',f'### {p["id"]} · {p["title"]}','',f'- 출처: [{p["url"]}]({p["url"]})',f'- 게시: {kst(p["published_at"])} · 상세 확인: {kst(p["checked_at"])}',f'- 좋아요: {p["likes"]:,} · 수치 확인: {kst(p["likes_checked_at"])}',f'- **관찰·핵심 내용:** {flat(p["summary"])}',f'- **시각적 특징:** {flat(p["visual"])}',f'- **해석:** {flat(p["interpretation"])}',f'- **기획 활용:** {flat(p["application"])}',f'- 확인 범위: 캐러셀 첫 장 또는 릴스 캡처 장면과 캡션. 영상의 편집 리듬·음악, 후속 장의 흐름은 미확인.',f'- 근거: [화면]({p["screenshot"].replace("research/", "",1)}) · [DOM]({"evidence/post-"+p["url"].rstrip("/").split("/")[-1]+".txt"})']
lines+=['','## 정확한 수치 미확인 사례','', '아래는 제외 사례일 뿐 별도의 인기 순위가 아니다. 축약 표시의 존재를 감추지 않기 위해 남긴다.','', '| ID·출처 | 화면 표시 | 제외 이유 |','| --- | --- | --- |']
for code in ['DdlQYW8DK7f','DcYhRAzDOJA','DdZJyeDiIrb','Db6Say9GGDm']:
    p=next(p for p in posts if code in p['url'])
    lines.append(f'| [{p["id"]}]({p["url"]}) | {p["displayed_likes"]} | 정확한 좋아요 수 미확인; 정수로 추정하지 않음 |')
lines+=['','## 주제 후보 — 사용자 선택 대기','',
'1. **추천: 함께 달려도, 내 페이스는 그대로** — 다른 사람의 속도를 따라가는 것이 부담스러운 사람. 브랜드의 핵심 가치와 직접 연결되며, 경쟁사의 속도·기록 메시지를 그대로 가져올 필요가 없다.',
'2. **혼자 달리기 심심한 날** — 혼자 달리는 것이 심심한 러너. 선수의 표정·러닝 순간을 먼저 보여주는 전달 방식을 평범한 동행 장면으로 전환한다.',
'3. **멀리 가지 않아도, 함께 달릴 수 있어요** — 동네에서 가볍게 시작하고 싶은 사람. 장소를 중심에 둔 구성에서 착안하되 특정 운영 지역은 주장하지 않는다.',
'','후보는 브랜드 기준과 리서치에서 도출한 제안이다. 해당 주제가 좋아요를 높인다는 증거는 아니다. **추천안도 아직 승인된 기획이 아니다.** 선택 후 plan.md에서 대상·핵심 문구·장수·CTA 하나를 제시하고 기획 승인을 받는다.',
'','## 기준·미확인·다음 단계','',
'- 제작 기준: [brand.md](../../../brand.md), [content-design.md](../../../content-design.md). 신규 사진은 경쟁사 스타일 복제 대신 이 두 문서를 우선한다.',
'- 실제 브랜드 URL·계정명, 서비스 운영 지역과 성과 수치는 여전히 미확인이다. 연구를 통해 채워 넣지 않는다.',
'- 출처 원장: [sources.json](sources.json). 발견 후보 전체의 링크·수치·날짜 미확인 이유·근거 경로를 보존했다. 선정 외 후보는 시각적 효과 분석을 했다고 주장하지 않는다.',
'- 프레젠테이션: [research.pptx](research.pptx). 선정 목록·분석은 동일한 sources.json에서 작성한다.',
'- 신규 사진·HTML·Figma·최종 PNG·캡션은 아직 제작하지 않았다. 주제 선택 → plan.md → 기획 승인 → 사진·HTML → 프리뷰 승인 → Figma·최종 전달 순서로 진행한다.',
'- 실제 게시와 예약 발행은 실행하지 않는다.','']
(run/'research/research.md').write_text('\n'.join(lines))
