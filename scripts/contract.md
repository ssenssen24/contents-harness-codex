# 실행 산출물 계약 v1

이 문서는 검사기와 두 스킬이 공유하는 데이터 형식이다. 브랜드 규칙은 루트의 brand.md·content-design.md를 참조한다. Python 3.10 이상 표준 라이브러리만으로 검사한다. 현재 실행의 기록을 만드는 것은 Codex이며 검사기는 승인·콘텐츠를 생성하지 않는다.

## 명령과 상태

프로젝트 루트에서 실행한다.

```sh
python3 scripts/validate_run.py runs/RUN_ID --stage research
python3 scripts/validate_run.py runs/RUN_ID --stage plan
python3 scripts/validate_run.py runs/RUN_ID --digest plan
python3 scripts/validate_run.py runs/RUN_ID --stage preview
python3 scripts/validate_run.py runs/RUN_ID --digest preview
python3 scripts/validate_run.py runs/RUN_ID --stage final --report runs/RUN_ID/checks/report.json
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

stage 검사는 이전 단계도 누적 검사한다. 종료 코드 0은 자동 검사 통과, 1은 실패, 2는 CLI 사용 오류다. `--digest`는 승인할 버전의 식별값만 출력한다. 승인을 부여하지 않는다. 정상·오류 예시는 테스트가 임시 폴더에 만들고 삭제하므로 실제 콘텐츠 runs와 섞이지 않는다.

실제 실행 전 state.json을 만든다. 아래는 형식 예시이며 현재 실행·승인 기록이 아니다. placeholder를 실제 값으로 대체한다.

```json
{
  "schema_version": 1,
  "run_id": "RUN_ID",
  "input": {
    "topic": null,
    "accounts": ["nikerunning", "adidasrunning"],
    "size": [1080, 1350],
    "window": {"start": "2026-07-02T09:00:00+09:00", "end": "2026-09-30T09:00:00+09:00"}
  },
  "reference_hashes": {
    "brand.md": "실행 시작 시 SHA256",
    "content-design.md": "실행 시작 시 SHA256",
    "assets/reference/manifest.json": "실행 시작 시 SHA256"
  },
  "stages": {
    "research": {"status": "not_run"},
    "plan": {"status": "not_run"},
    "preview": {"status": "not_run"},
    "final": {"status": "not_run"}
  },
  "paths": {},
  "approvals": {},
  "resume": {"stage": "research", "reason": "최초 실행", "next_action": "Aside 접근 확인"}
}
```

시각은 ISO 8601과 timezone offset을 포함한다. 기본 기간은 실제 실행 시작 시각에서 90일 전부터 시작 시각까지다. 예시 날짜를 재사용하지 않는다. 상태는 `not_run`, `in_progress`, `awaiting_approval`, `approved`, `complete`, `blocked` 중 하나다. blocked에는 원인·시도·재개 위치를 추가한다. 자동 통과만으로 승인 상태를 설정하지 않는다.

`paths`에서 필요한 키만 덮어쓸 수 있다. 기본값은 다음과 같다. 모든 경로는 실행 폴더 기준이며 그 밖을 가리킬 수 없다.

| 키 | 경로 |
| --- | --- |
| research / pptx / sources | research/research.md / research/research.pptx / research/sources.json |
| plan | plan/plan.md |
| html / assets / browser | preview/preview.html / preview/assets.json / preview/browser-check.json |
| figma / png / caption | final/figma.json / final/png / final/caption.md |
| review | checks/review.md |

수정 시에만 해당 단계의 v002 같은 경로를 만들고 paths를 변경한다. 이전 파일과 승인 기록은 보존한다. 현재 승인을 옮겨 적어 실질적 변경을 승인된 것으로 만들지 않는다.

## 조사 데이터와 PPTX

sources.json 필수 필드:

- `collector`: `aside-repl`
- `accounts`, `window`: state.input과 동일
- `coverage`: 계정별 `{status: complete|partial|blocked, note: 설명}`. 설명에 기간 경계 확인 여부·누락 구간·접근 제한을 포함한다.
- `posts`: 직접 확인한 후보 전체. 기간 밖 경계 게시물을 기록해도 되지만 선정에서는 제외한다.
- `selected_ids`: 좋아요 내림차순·게시일 내림차순·URL 오름차순 상위 최대 6개 ID
- `ranking_scope`: `full_top6` 또는 `observed_top6`
- `limitations`: 조사 한계 설명. 부분 조사에서는 필수다.

게시물 형식:

```json
{
  "id": "s01",
  "account": "nikerunning",
  "url": "https://www.instagram.com/nikerunning/p/POST_ID/",
  "published_at": null,
  "checked_at": "2026-09-30T09:10:00+09:00",
  "likes": null,
  "unknown_reasons": {"published_at": "날짜 확인 불가", "likes": "좋아요 숨김"},
  "summary": "핵심 내용",
  "visual": "화면에서 관찰한 시각 구성",
  "observation": "직접 확인한 사실",
  "interpretation": "사실과 구분한 해석",
  "application": "런메이트 기획에 활용할 점",
  "evidence": ["research/evidence/s01.txt"]
}
```

likes는 정확히 확인한 비음수 정수 또는 null이다. 날짜·좋아요 중 하나라도 미확인이면 해당 게시물은 순위에서 제외하고 전체 순위를 주장하지 않는다. 한 계정이라도 coverage가 complete가 아니면 observed_top6다. 유효 후보 0개는 실패, 1–5개는 부족한 수를 명시한 제한 보고로 통과할 수 있다. complete 표기의 진위는 사람이 근거를 검토해야 한다.

research.md·research.pptx에는 선정 게시물 ID와 정규 permalink를 본문 텍스트로 포함한다. PPTX의 URL을 링크 속성에만 숨기지 않는다. 두 보고서에 확인 가능한 확인일·게시일·좋아요·핵심 내용·시각적 특징·활용점·관찰과 해석을 기록한다. 부분 조사일 때 research.md와 sources.json에는 한계와 “확인한 게시물 중” 표시를 남긴다. PPTX 슬라이드와 발표자 노트에는 한계·접근 실패·미확인 이유·검사 상태를 출력하지 않으며, 누락 값은 생략하고 제목은 “선정 게시물 분석”처럼 검증된 범위의 사실로 쓴다. 출처 링크와 ID는 유지한다. 검사기는 ZIP/OOXML·slide 관계·출처 텍스트를 확인하며, 실제 슬라이드 렌더는 프레젠테이션 도구로 별도 검토한다.

## plan.md: 단일 기획 원본

plan.md는 사람 검토용 기획서다. **기획 요약 → 카드별 구성표 → 사진 제작 방향 → 캡션 → 확인 사항 → 제작 데이터** 순서로 작성한다. `content-plan` 블록은 문서 맨 아래 하나만 둔다. 표에는 순서·ID·역할·실제 문구·화면 구성·사진 여부·CTA·근거 ID를 표시한다. 브랜드 사실은 새로 추정하지 않는다.

`scripts/plan_document.py`의 `compose(plan, notes)`가 하단 데이터와 동일한 검토 영역을 만든다. 하단 데이터 수정 후 `python3 scripts/plan_document.py PLAN_PATH --sync`로 표·사진 방향·캡션을 동기화한다. `--sync` 없이 실행하면 읽기 전용 일치 검사다. 확인 사항은 사람이 작성하며 확인값·관찰·제안·미확인, 검토 포인트와 조사 한계를 구분한다.

새 실행에는 `state.plan_document_format = "human-first-v1"`을 둔다. 단계 검사에서 검토 영역 누락, 표·사진 방향·캡션과 제작 데이터 불일치, 하단 배치 오류를 실패 처리한다. 문구·메시지의 적절성과 사실 여부는 별도 사람 판단이다. 기획 승인 요청에는 파일 링크와 카드별 표를 함께 제시한다.

이미 제작이 완료된 실행의 서식만 정리할 때는 승인된 원문을 `plan/archive/`에 그대로 보관하고 `paths.plan`을 보관본으로 연결한다. 사람이 읽는 `plan/plan.md`는 `paths.plan_presentation`에 기록한다. 검사기는 검토용 문서의 모든 제작 데이터가 승인 보관본과 같은지 확인한다. 승인 digest는 보관본을 기준으로 그대로 유지한다. 이는 완료본 열람용이며, 이후 의미·문구·구성을 바꿀 경우에는 새 기획 버전으로 전환하고 다시 승인받는다.

````markdown
```content-plan
{
  "topic": "기획 주제",
  "target": "선택한 대상",
  "purpose": "콘텐츠 목적",
  "message": "핵심 메시지",
  "width": 1080,
  "height": 1350,
  "card_count": 1,
  "primary_cta": "함께 달리고 싶은 친구에게 공유해요.",
  "caption": "최종 게시글 캡션",
  "cards": [{
    "id": "c01",
    "role": "카드 역할",
    "copy": ["내 페이스로, 함께 달려요.", "함께 달리고 싶은 친구에게 공유해요."],
    "cta": "함께 달리고 싶은 친구에게 공유해요.",
    "photo_required": true,
    "photo_brief": "기준 문서 스타일 안의 새로운 장면·구도·여백",
    "layout": "주제에 맞는 구성과 선택 이유",
    "source_ids": ["s01"]
  }]
}
```
````

카드 수는 가변이다. 카드별 ID는 고유한 영문·숫자·하이픈·밑줄을 사용한다. 주된 CTA가 있는 카드는 정확히 하나이며 다른 카드는 `cta: null`이다. 캡션에도 같은 행동을 안내할 수 있지만 다른 CTA를 추가하지 않는다. 무사진 카드는 photo_required=false, photo_brief에 사진이 필요 없는 이유를 적는다. 미해결 정보는 기획 설명에 남길 수 있지만 제작용 문구에는 해결되지 않은 표시를 남기지 않는다.

## 승인 기록

`approvals.plan`, `approvals.preview`에 각각 `{actor: "user", quote: "실제 사용자 승인 답변", at: "ISO 시각", digest: "명령 출력"}`를 저장한다. digest를 제시한 이후 파일이 바뀌었는지 확인하고 동일한 버전에만 승인을 연결한다. 새 승인 전 과거 기록은 history 배열에 보존한다.

plan digest는 기준 문서 해시·조사 데이터·research.md·plan.md를 포함한다. preview digest는 위 항목에 HTML과 실제 자산 내용·제작 기록을 추가한다. 브라우저 체크·스크린샷·검사 보고서는 digest에서 제외하므로 검사를 반복해도 승인이 무효화되지 않는다. 자산 경로만 바꾸면 URL을 자산 ID로 정규화하므로 화면이 같은 경우 승인 유지가 가능하다. 실제 화면 동일성은 브라우저에서 다시 확인한다.

검사기는 승인 필드의 형태·현재 버전 일치만 확인한다. 사용자가 정말 승인했는지는 대화 기록과 대조해야 하며 Codex가 자동 작성한 승인 문구로 대체할 수 없다.

## HTML과 자산

미리보기는 스크립트 없는 정적 HTML이다. 확대는 CSS 또는 브라우저 확대를 사용한다. 카드 내 문구 순서는 기획 copy와 동일하게 한다. 줄바꿈·연속 공백만 정규화한다.

```html
<article data-card-id="c01" data-width="1080" data-height="1350"
         style="width:1080px;height:1350px">
  <img src="images/c01.png" alt="사진 설명">
  <h1 data-copy>내 페이스로, 함께 달려요.</h1>
  <p data-copy>함께 달리고 싶은 친구에게 공유해요.</p>
</article>
```

모든 copy 요소는 카드 안에 있고 서로 중첩하지 않는다. 이미지·폰트·CSS 자원은 로컬 파일이며 assets.json에 등록한다. 인라인 CSS를 권장한다. SVG는 이미지 파일로 참조하거나 인라인 벡터로 배치한다. CSS 외부 파일을 사용하면 그 안의 추가 의존 파일도 등록·브라우저 확인한다.

assets.json은 `{items: [...]}`다. 각 항목 공통 필드: `id`, `kind`(photo/reference/font), `path`, `html_url`, `sha256`, `source`, `card_ids`(사용 카드 ID 배열).

- photo: 실행 폴더 기준 path. `run_id`, `method: codex-imagegen`, `created_at`, 실제 `prompt`도 필수다. 생성 시간은 기획 승인 이후다. 최소 검사기는 PNG를 디코드 검증하므로 제작·검수용 사진은 PNG로 준비한다. 다른 형식만 제공하는 도구이면 지원을 확인하고, 확장자만 바꾸지 않는다.
- reference: 프로젝트 루트 기준 `assets/reference/...` 경로. source에는 원본 Figma 노드 링크를 기록한다.
- font: 실행 폴더 기준 경로. source에는 서체 출처를 기록한다. 설치·배포 조건을 확인한다.
- html_url은 HTML에서 실제 쓰는 상대 URL이며 파일 path와 같은 파일을 가리킨다.

기존 runs의 assets.json 해시와 동일한 사진이면 재사용 오류다. 비교 가능한 기록이 없거나 변형된 사진은 자동으로 신규 여부를 보장하지 못한다.

browser-check.json은 실제 브라우저에서 읽은 값이다:

```json
{
  "tool": "실제 사용한 브라우저 도구",
  "checked_at": "ISO 시각",
  "html_sha256": "HTML SHA256",
  "preview_digest": "현재 --digest preview 출력",
  "fonts_loaded": true,
  "images_loaded": true,
  "overflow_card_ids": [],
  "cards": [{"id": "c01", "width": 1080, "height": 1350, "copy": ["문구들"]}],
  "screenshots": ["preview/screenshots/overview.png"]
}
```

cards 치수는 화면에 맞춰 줄인 CSS transform 비율을 보정한 제작 치수다. DOM의 실제 텍스트·렌더 치수·이미지 naturalWidth·document.fonts 확인을 수행한다. overflow에는 의도하지 않은 텍스트 넘침만 기록하며 의도적인 사진·장식 크롭은 시각 검토로 남긴다.

## Figma·PNG·최종 검토

figma.json 필드: `file_key`, `url`, `created_at`, `read_at`, `preview_digest`, `cards`. cards의 순서는 기획과 동일하다. Figma를 실제 다시 읽어 작성한다.

각 카드: `id`, `node_id`, `width`, `height`, `copy`, `text_nodes: [{id, type: "TEXT", characters}]`, `image_node_ids: [ID]`, `vector_node_ids: [ID]`, `screenshot: 실행폴더 상대 PNG 경로`. text_nodes는 copy의 읽는 순서로 정렬하며 배경 장식 문자·벡터 로고는 copy에 포함하지 않는다. 캡처 이미지만 놓고 TEXT 노드가 있는 것처럼 기록하지 않는다.

PNG 파일명은 카드 ID와 같게 `c01.png`로 정한다. 실제 프레임을 1배 PNG로 내보내고 비인터레이스 형식을 사용한다. 검사기는 CRC·압축 스트림·치수·장수·파일명을 확인한다. PNG가 올바른 Figma 장면을 담았는지는 화면 비교로 검토한다.

caption.md에는 승인된 캡션 본문만 저장한다. review.md에는 아래를 기록한다:

- 기획·프리뷰: 사용자 승인 대상과 실제 피드백, 메시지·말투·스타일의 판단 결과
- PPTX·HTML·Figma·PNG: 실제 열람/렌더한 도구와 시각, 글자 넘침·가독성·크롭·편집 가능성 검토
- 검토 주체를 user 또는 Codex로 정확히 표시. Codex 검토를 사용자 승인으로 기록하지 않음
- 미실행 항목·조사 한계·도구 실패·남은 작업

외부 도구 접근·시각 검토를 테스트 fixture로 대체하지 않는다. 검증 성공은 기록의 일관성에 대한 결과이며 실제 운영 성공 보고가 아니다.


완료 실행은 기준 문서 변경 전에 해시가 일치하는 원문을 실행 폴더에 보관하고 state.reference_snapshots에 기록할 수 있다. 이는 당시 승인 검증 전용이다. 진행 중이거나 새 실행에는 최신 기준 문서를 사용한다. 승인 digest를 새 기준으로 덮어쓰지 않는다.
