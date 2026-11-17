# 검증 명세 유지보수

## 승인된 용법 집합 검사
d4c4584a4cf18d4af4daa7ec80940e89b640782b의 실제 GitHub CI 44023619837에서 340 tests가 성공했다. 기존 7개 테스트 파일의 전역 reviewed 개수 비교 8줄만 제거하고, 개별 source SHA·상태·검색 조건·양성 및 반례 검사는 그대로 두었다.

tests/fixtures/approved-usage-membership.json은 개별 검토 후의 60항목과 75용법을 명시한다. 실행 때 현재 데이터로 기대값을 자동 생성하지 않는다. 중앙 테스트는 전체 canonical 354개 및 profile·생성 index·저장 index의 집합/coverage/내용 정합성을 검사한다. 같은 개수의 항목·용법 교체와 중복에 대한 양쪽 변형 8건도 거부한다. 다음 검토된 확장은 이 명세의 변경 사유와 실제 검증을 남겨 갱신해야 한다.

## 초기 동결 테스트의 타입 경계
기존 context/direction/memory 공개 회귀의 전체행 비교를 strict_equal로 통일했다. Python의 True==1 및 정수==동일값 실수 동치로 JSON 타입 변화를 놓치지 않도록 한다. 원 trace·gold·용법·검색 코드는 수정하지 않는다.

회귀는 별도 복제 비교가 아니라 해당 3개의 실제 guard 메서드를 직접 호출하며, replay 결과만 원본 공개 trace의 수정 사본으로 바꾼다. bool→int, bool→float, int→float 변형 9건은 거부되어야 하고, 원문 및 오직 coverage 변경 6경로는 기존 계약대로 허용되어야 한다. coverage 제외는 검색 내용의 임의 변경 허가가 아니며, 실제 canonical/profile/index coverage는 위 중앙 테스트가 별도 검증한다.

이 작업은 평가파일 무결성과 유지보수 중복을 다루며 의미 정확도·사람 평가·미노출 모델 성능을 새로 측정하지 않는다. main 병합은 하지 않는다.

타입 경계 최종 실행: a235bd1ed13e6496d37c0d9dcd069081946f6c5a, GitHub Actions 44023814220, 342 tests 성공. 이는 구조 회귀 결과이며 새 의미 정확도 측정이 아니다.

## 첫 인사 replay 원자료 검사
이 단계에서는 최신 replay 한 파일의 7개 입력에만 고유 ID·필수 ID·문자열 prompt·계획 action/filters 구조 검사를 추가한다. 과거 28개 A/E 계획의 누락이 조용히 비교 범위를 줄이지 못하게 한다. no-search의 기존 mode/limit 메타는 허용하며 검색은 호출하지 않는다. 모든 과거 replay를 한꺼번에 바꾼 것은 아니며 실제 입력 해석·후보 내용·원 trace는 보존한다. 이 추가 단계의 실제 통과 여부는 해당 커밋 Actions에서 별도 확인한다.
