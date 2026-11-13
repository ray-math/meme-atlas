# 공개 사전 구조 비교와 적용

확인: 2026-11-13. 항목 수나 인기보다 현재 사전의 검색·작성·검증에 유용한 구조를 비교했다. 외부 코드·뜻풀이·예문은 복사하지 않았고, 아래 개선은 독립 구현했다.

| 참고 | 직접 확인한 구조 | 현재 사전에 적용/유보 | 라이선스 |
| --- | --- | --- | --- |
| [chinese-meme-dict](https://github.com/re-skylar/chinese-meme-dict) | 원시 배치와 배포 JSON 분리, schema 버전, 독립 필드 | 기존 Markdown+파생 검색 인덱스 유지. 조회 응답에 schema_version을 추가. 중국어 감정·형식 태그와 짧은 뜻풀이 제한은 채택하지 않음 | [CC BY 4.0](https://github.com/re-skylar/chinese-meme-dict/blob/main/LICENSE). 실제 재사용 시 저자/출처/라이선스와 변경 표시 필요. 자료를 가져오지 않음 |
| [Wordset](https://github.com/wordset/wordset-dictionary/blob/master/Readme.md) | 단어별 식별자, meanings 배열에 뜻·예문·유의어 구분 | 단일 원본 Markdown을 유지하면서 뜻풀이·유래·관련 항목을 분리 조회. 유사 밈을 aliases에 넣지 않음. 의미별 고정 ID는 편집 규칙 확정 전 유보 | [CC BY-SA 4.0 및 WordNet 고지](https://github.com/wordset/wordset-dictionary/blob/master/LICENSE). 뜻풀이 복사하지 않음 |
| [tldr](https://github.com/tldr-pages/tldr/blob/main/CONTRIBUTING.md) | Markdown 한 항목, 구체적 사용 예, 스타일 가이드와 lint | 기존 구조 검사에 파생 검색/분야 목차의 원본 일치 검사 추가. 실제 사용 확인 기준 유지. 형식 통과를 사실 확인으로 간주하지 않음 | [문서 CC BY 4.0, scripts MIT](https://github.com/tldr-pages/tldr/blob/main/LICENSE.md). 코드·예제 복사하지 않음 |
| [Awesome](https://github.com/sindresorhus/awesome/blob/main/awesome.md) | 범위가 명확한 분류 목차, 수집량보다 선별 | 기존 README→전체/분야/월별 목차 구조 유지. 새 안내에서 검색→필요 부분 조회 경로 명시 | [CC0](https://github.com/sindresorhus/awesome/blob/main/license). 이름/배지로 선정받았다는 인상 주지 않음 |

## 이번 실제 변경

1. `get_entry.py`: 검색 결과의 안정적인 id로 한 항목 또는 `definition`, `origin`, `related` 부분만 JSON 조회. 기존 본문을 재작성하지 않는다. 임의 경로/누락 항목은 실패 처리한다. MCP를 나중에 붙이면 이 읽기 함수를 감싸면 되지만, 지금 서버를 배포했다는 뜻은 아니다.
2. `check_generated.py`: Markdown과 검색 JSON/분야 목차가 어긋나면 실패. 본문만 고치고 검색에 옛 내용이 남는 문제를 잡는다. 원본은 수정하지 않는다.
3. 100개 항목 전체의 뜻풀이/유래 조회, 단일 섹션, 별칭과 관련 항목 구분, 경로 제한, 누락 항목, 오래된 파생 파일 검사 포함 53개 테스트 통과.

## 유지·유보

기존 100개 본문/메타데이터와 월별 파일은 그대로 보존했다. 한국 범위 밖 기존 항목 4개는 이전 검토 목록 그대로이며 추가 인증하지 않았다. 새 수집/주간 자동화/main/PR/원격 MCP는 변경하지 않았다.

현재 저장소에는 명시적 LICENSE가 없다. 공개 GitHub라는 이유만으로 제3자 자유 재배포 허용이 되는 것은 아니다. 향후 외부 배포 시 원문·코드의 라이선스를 소유자가 선택해야 하며 이번에 임의 설정하지 않았다. 참고 레포의 라이선스가 이 사전에 자동 적용되는 것도 아니다.

검색의 의미적 품질, 최신 유행 여부, 사실성은 별도 검토가 필요하다. 항목 수가 큰 레포의 자체 AI 원작성 주장만으로 신뢰하거나 대량 번역하지 않는다.
