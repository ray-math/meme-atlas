# 안습: 본문만 추가

공개 메타 manifest와 정확한 Git blob을 통해 별도 canonical 초안을 읽고 임시 input.json으로 기존 pilot_batch importer를 실행했다. 원시 배치는 저장소에 저장하지 않았다.

b24687067496f70f2a92f017826d3166536ca6a8, GitHub Actions 44027137798: 실제 added1/updated0, 같은 배치 재실행 unchanged. 370 tests 성공. 새 항목·목차·분야목록·일반 및 용법 색인·pilot state만 생성되었으며 후보대장/최근관측/최근선정은 입력 전후 해시가 같았다.

전체 본문355, reviewed64 profiles/79용법은 그대로다. 안습은 새 용법을 자동 생성하거나 reviewed로 올리지 않고 미주석으로 남긴다. 일반 사전 본문 수록과 AI 사용 추천 검토를 구별한다.

근거는 독립 두 매체의 뜻풀이·한국 인터넷 사용 보도다. 원댓글 직접 열람, 최초 창작자·발생연도·사전등재·최근 유행을 주장하지 않는다. 기존 후보대장에 없는 항목이므로 대장 ID나 included 상태를 임의 생성하지 않았다. main은 변경하지 않는다. 최종 생성물을 커밋한 뒤 check-only CI를 별도로 확인한다.
