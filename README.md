# 콘텐츠 자동화 하네스

인스타그램 경쟁사 조사부터 카드뉴스 제작과 검수까지의 작업 기준, 스킬, 실행 산출물을 보관합니다.

- [작업 지침](AGENTS.md)
- [브랜드 기준](brand.md) · [콘텐츠 디자인 기준](content-design.md)
- [조사 스킬](.agents/skills/ig-competitor-scout/SKILL.md) · [제작 스킬](.agents/skills/ig-content-maker/SKILL.md)
- [산출물 계약](scripts/contract.md) · [검사 도구](scripts/validate_run.py)
- 검사: Python 3.10 이상, 표준 라이브러리만 사용. `python3 -m unittest discover -s scripts -p 'test_*.py'`와 `python3 scripts/check_all_runs.py`를 GitHub Actions가 push마다 실행합니다.
- [2026-09-30 실행 기록](runs/20260930-running-research-01/)

`runs/`에는 조사 근거, 기획, 프리뷰, 최종 PNG·캡션·전달 ZIP, 검사 기록이 들어 있습니다. 외부 게시물의 이미지와 문구는 조사 출처를 확인하는 용도로 보관하며, 원 게시물의 권리는 각 권리자에게 있습니다.
