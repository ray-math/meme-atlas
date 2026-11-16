# 감정·의도·상황으로 밈 찾기

이 기능은 기존 밈의 **용법별 편집 주석**을 검색한다. 실제 작성자의 마음이나 숨은 의도를 판정하지 않는다. 분야 태그 `tags`와 사용 맥락은 별개다.

## 첫 범위와 한계

전체 343개 중 기존 28개에 38개 용법을 주석했다. 신규 밈 등록은 하지 않았다. 10개 용법은 standard, 27개는 caution, 1개는 avoid다. 이는 상황별 편집 판단이며 안전 인증이나 나쁜 밈 목록이 아니다. 수록되지 않은 나머지 항목은 미주석 상태이며 감정이 중립이라는 뜻이 아니다.

28개 본문을 읽은 편집 주석과 일부 독립 재검토를 거쳤다. 두 명의 독립 주석자 전수 평가를 수행한 것은 아니다. 불확실한 감정은 빈 배열로 남겼다. 중립기어의 판단 보류를 중립 감정으로 바꾸지 않는다.

이미지·음성·억양·대화 전후 문맥은 이 텍스트 색인만으로 복원되지 않는다. 자유문장 이해나 생성 모델을 탑재한 서비스가 아니며, 논문 성능을 이 검색기의 정확도로 해석하면 안 된다.

## 데이터 계약

- Markdown: 밈 뜻풀이·유래·분야·별칭의 원본.
- `data/usage-profiles.json`: 사용 맥락 주석의 유일한 원본. 본문을 복제하지 않고 entry_id와 검토한 Git blob source_sha로 연결.
- `data/usage-vocabulary.json`: 버전 1 통제어휘와 명시적 대체 표기. 새로운 표기는 검토 후 등록.
- `schemas/usage-profiles.schema.json`: JSON Schema 2020-12 형태 계약.
- `data/usage-index.json`: 위 원본을 합친 재생성 가능한 검색 데이터. 직접 편집하지 않는다.

각 profile에는 검토 상태(draft/reviewed), 검토 메모와 usages가 있다. 각 usage는 독립 ID, emotions, intents, situations, targets, registers, risk_flags, safety, context, avoid_when, 편집 예문 및 검토 메모를 가진다.

emotions는 용례가 전달하는 정서, intents는 화용적 쓰임이다. 상황 키워드와 대상·말투를 분리한다. 같은 밈이 자조와 상대 비꼼으로 쓰이면 별도의 usage로 나눈다. 빈 감정 목록은 미판정 또는 명시할 감정 없음이며 자동으로 중립을 넣지 않는다. 이 구분의 세부 사유는 review_note에 적는다.

예문은 모두 `kind: editorial`인 창작 예시다. 실제 발생한 인용·출처 사례로 재사용하지 않는다. reviewed는 기존 본문과의 편집적 정합성 검토이지 독립 출처 재조사나 사실 인증이 아니다. 숫자 confidence는 제공하지 않는다.

본문이 바뀌면 source_sha 불일치로 검사와 AI용 CLI가 중단된다. 뜻·용법을 다시 읽고 영향받은 주석을 검토한 다음 SHA와 review_note를 갱신한다. 해시만 자동 덮어쓰지 않는다.

## 조회와 추천

```sh
python scripts/search_usage.py --emotion 놀람 --situation 예상밖사실 --mode lookup
python scripts/search_usage.py --intent 자조 --target 자기 --situation 반복발언
python scripts/search_usage.py --intent 조롱 --mode lookup
python scripts/search_usage.py --intent 다짐 --target 자기 --exclude-risk 비속어
python scripts/get_entry.py real-lol --usage
```

- 같은 축에 여러 값을 넣으면 OR, 다른 축 사이는 AND다.
- 모든 필터가 **하나의 usage에서** 만족되어야 한다. 다른 용법에서 감정과 의도를 하나씩 가져오지 않는다.
- 기본 recommend는 reviewed + standard만 반환한다. caution/avoid는 lookup에서만 볼 수 있다.
- lookup은 의미 이해를 위한 조회이지 사용 승인이나 권고가 아니다.
- exclude-risk는 해당 위험 라벨이 있는 용법을 제외한다.
- 미등록 필터는 unsupported_filter, 빈 요청은 insufficient_query, 해당 용법이 없으면 no_match다. 없는 결과를 만들어내지 않는다.
- 선택적 위치 인수 query는 긍정 어휘 보조 검색이다. 자연어의 부정·조건·관계를 이해하지 않는다. 일부 어휘 일치로만 순위를 정한다. 부정 조건인 avoid_when이나 위험 메모는 긍정 검색 텍스트에서 제외한다.
- 감정의 intensity나 sentiment를 임의로 추정하지 않으며 사용 빈도·인기순을 주장하지 않는다.

결과는 coverage, usage_id, matched_facets, 문맥·피해야 할 상황·위험·예문 종류·source_sha를 포함한다. requires_context_check는 항상 true다. standard여도 문맥 없는 자동 발화를 허용한다는 뜻이 아니다.

### AI 호출 순서

1. 사용자의 목적을 확인해 emotion/intent/situation/target/register의 명시 조건으로 바꾼다. 위로 요청과 위로 제공, 자조와 상대 조롱을 구별한다.
2. 조회인지 실제 사용 추천인지 정한다. 조회 결과를 그대로 발화에 붙이지 않는다.
3. 검색 결과의 context와 avoid_when을 현재 대화에 대조한다. 관계·상대 동의·부정 조건을 판단할 정보가 없으면 쓰지 않거나 묻는다.
4. 적합한 결과가 없으면 일반적인 말로 답한다. 격식 있는 위로나 심각한 고통 상황에 밈을 억지로 끼우지 않는다.
5. 의미가 중요하면 get_entry로 본문을 읽고, 예문은 실제 인용처럼 표현하지 않는다.

## 검증과 확장

```sh
python scripts/usage_profiles.py
python scripts/build_usage_index.py
python scripts/build_usage_index.py --check
python scripts/evaluate_usage.py
python -m unittest discover -s tests -v
```

34개 파일럿 회귀 질의는 26개 관련 용법 조회와 8개 경계·거부 조건을 포함한다. fixture의 prompt는 사람이 해석한 요청의 설명이며 파서에 넣는 자연문장이 아니다. 실제 호출은 filters를 사용한다. 주석과 함께 만든 진단이므로 독립 평가나 추천 정확도 수치로 발표하지 않는다. 미지의 질의·분리된 검토자 평가와 실제 사용자 오검색을 모은 후 어휘를 조정한다.

기존 title/alias/분야 CLI와 생성물은 호환 유지한다. batch importer는 새 usage 색인도 갱신하며, 주석된 본문이 변경되면 원자적 staging 단계에서 재검토를 요구한다. 343개 일괄 자동태깅이나 신규 수록 자동 승격은 하지 않는다.

## 설계 근거

아래 연구는 축을 분리하고 불확실성을 남기는 근거다. 이 저장소의 한국 밈 태그 목록을 검증한 표준은 아니다.

- [GoEmotions, ACL 2020](https://aclanthology.org/2020.acl-main.372/): 영어 Reddit의 세분·복수 감정 주석을 참고한다. 영어권 분류를 한국 밈에 그대로 이식하지 않았다.
- [KOTE, LREC-COLING 2024](https://aclanthology.org/2024.lrec-main.1499/): 한국어 감정 어휘와 도메인·편향의 한계를 참고한다.
- [DailyDialog, IJCNLP 2017](https://aclanthology.org/I17-1099/): 정서와 대화행위를 별도 주석하는 선례다.
- [Memotion, SemEval 2020](https://aclanthology.org/2020.semeval-1.99/): 유머·풍자·공격성 등 기능과 복수 해석을 참고한다. 이미지 밈 결과를 텍스트 검색 성능으로 전이하지 않는다.
- [Social Bias Frames, ACL 2020](https://aclanthology.org/2020.acl-main.486/): 대상·함축·공격성을 맥락과 함께 다루는 관점만 적용한다. 숨은 의도를 확정하지 않는다.
- [Out-of-Scope Intent Evaluation, EMNLP 2019](https://aclanthology.org/D19-1131/): 지원하지 않는 요청에 답을 강제하지 않는 평가 원칙을 참고한다.
- [W3C SKOS Reference](https://www.w3.org/TR/skos-reference/): 대표 개념과 대체 표기의 분리 원칙을 참고한다. 이 JSON을 RDF/SKOS 준수 구현이라 주장하지 않는다.
- [JSON Schema 2020-12](https://json-schema.org/draft/2020-12): 필수 필드·타입·닫힌 속성 계약에 사용한다. 원본 해시와 어휘 참조는 별도 Python 검사로 검증한다.
