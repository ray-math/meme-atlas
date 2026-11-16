# Meme Atlas · 밈 사전

밈을 처음 접한 사람도 **무슨 뜻인지, 언제 어떻게 쓰는지, 어디에서 퍼졌는지** 이해할 수 있도록 정리하는 한국어 밈 사전입니다. 한국에서 실제로 쓰이는 개별 밈을 다루며, 해외 기원도 국내 사용 맥락을 확인한 뒤 포함합니다.

## 찾아보기

| 찾는 방법 | 안내 |
| --- | --- |
| [전체 밈 목록](memes/README.md) | 이름으로 항목 찾기 |
| [분야·소재별 목록](collections/topics.md) | 게임·방송·영화 등 분야로 찾기 |
| [최근 1년 선별](collections/latest-year.md) | 관찰 시기를 검토한 최근 선택 |
| [월별 목록](months/README.md) | 특정 시기에 관찰된 밈 찾아보기 |

각 밈은 하나의 본문으로 관리합니다. 뜻풀이 가까이에 사용 예를 두고, 뉘앙스와 유래를 설명하며 관련 밈으로 연결합니다. 월은 탄생일이 아니라 사용·확산이 관찰된 시기입니다. 최근 선별 목록의 기준일과 대상 기간은 해당 목록에 표시합니다.

## 필요한 내용만 조회

현재는 Python CLI이며 원격 MCP 서버가 실행되는 것은 아닙니다.

```sh
python scripts/search_dictionary.py '럭키비키' --limit 3
python scripts/get_entry.py wonyoung-thinking --section definition
python scripts/get_entry.py wonyoung-thinking --section origin
```

## 편집

[작성 가이드](CONTRIBUTING.md) · [항목 템플릿](templates/meme.md) · [편집 작업대](review/README.md) · [과거 확장 기록](reports/README.md)

```sh
python scripts/build_navigation.py
python scripts/build_index.py
python scripts/check_dictionary.py
python scripts/check_generated.py
python scripts/build_navigation.py --check
python scripts/check_editorial.py
python -m unittest discover -s tests -v
```

목차·검색 인덱스·자동 역링크는 파생물입니다. 자동 검사는 구조를 확인하며 내용의 사실성을 보증하지 않습니다.

## 감정·의도·상황 검색

기존 28개 밈의 38개 용법에 대한 검토된 맥락 태그를 제공합니다. 미주석 항목은 중립으로 간주하지 않으며, 조회와 실제 사용 추천을 구분합니다.

- [사용 맥락 검색과 AI 호출 가이드](docs/usage-search.md)
