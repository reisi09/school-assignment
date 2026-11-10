# 유출장부

유출장부는 개인정보 유출 알림을 기록하고, 위험 정도와 할 일을 확인하는 앱입니다.

고색고 응용 프로그래밍 개발 개인 프로젝트(수행평가 4차)로 만들었습니다.

## 배포 주소

https://reisi09-school-assignment-leak-ledgerapp-leak-ledger-jeudp4.streamlit.app/

## 화면 안내

| 화면 | 하는 일 |
| --- | --- |
| 소개 | 앱의 사용 방법과 해 주는 일을 안내합니다. 기록하기나 실제 사례로 시작합니다. |
| 기록하기 | 유출 알림 내용을 직접 적거나 실제 사례를 골라 기록합니다. 위험 점수를 매기는 기준도 확인합니다. |
| 할 일 | 기록별 위험 정도와 할 일을 확인합니다. 끝낸 일을 체크하면 바로 저장됩니다. 이미 퍼진 비밀번호인지 확인하는 기능도 있습니다. |

## 파일 구성

| 파일 | 역할 |
| --- | --- |
| `app.py` | Streamlit 화면을 구성합니다. |
| `texts.py` | 화면에 나오는 모든 문구를 모아 둡니다. |
| `database.py` | SQLite의 `services`, `incidents` 두 테이블에 기록을 저장하고 조회합니다. |
| `rules.py` | 위험 점수와 등급, 할 일을 정합니다. |
| `api.py` | Pwned Passwords의 비밀번호 목록에서 입력한 비밀번호를 확인합니다. |
| `cases.py` | 실제 유출 사례 9건을 담습니다. 국내 5건은 연합뉴스 2026.11.1. 보도, 해외 4건은 Have I Been Pwned 공개 자료를 바탕으로 합니다. |
| `test_leak_ledger.py` | 앱의 기능을 테스트합니다. |
| `.streamlit/config.toml` | 색과 글꼴을 설정합니다. |
| `style.css` | 카드와 버튼 등 화면 모양을 정합니다. |
| `static/` | Pretendard 글꼴(SIL OFL 1.1)과 로고를 담습니다. |
| `requirements.txt` | 배포에 필요한 패키지 목록입니다. |

## 실행 방법

`app.py`가 있는 폴더에서 다음 명령을 차례로 실행합니다.

```bash
pip install -r requirements.txt
streamlit run app.py
```

처음 실행하면 기록을 저장할 `leak_ledger.db` 파일이 자동으로 만들어집니다.

테스트는 같은 폴더에서 실행합니다.

```bash
python -m unittest -v
```

## 배포 방법

Streamlit Community Cloud에서 다음 값을 입력합니다.

| 설정 | 값 |
| --- | --- |
| Repository | `reisi09/school-assignment` |
| Branch | `leak-ledger` |
| Main file path | `leak-ledger/app.py` |
| Python 버전 | 기본값인 `3.14` |

`requirements.txt`는 Python 3.12에서 `pip freeze`로 만들었습니다. 프로젝트 배포 시 Python 3.14에서도 패키지 설치와 테스트가 되는 것을 확인했습니다.

## 디자인

화면 짜임은 Ronas IT가 디자인해 Dribbble에 올린 [Travel App Landing Page](https://dribbble.com/shots/25536003-Travel-App-Landing-Page)를 참고했습니다. 남색과 선명한 민트를 쓰고, 파스텔 색은 쓰지 않았습니다.

- 회색 바탕 위에 모서리가 둥근 종이 한 장을 올리고 모든 내용을 그 안에 담았습니다.
- 맨 위에는 로고, 화면 이름 세 개, 테두리 버튼을 한 줄로 놓았습니다.
- 제목은 아주 크게 쓰고 굵은 줄과 가늘고 기울인 줄을 짝지었습니다.
- 소개 화면에는 굵은 곡선이 지나는 민트색 판이 있습니다. 판 오른쪽에는 할 일 화면을 휴대전화 모양으로 미리 보여 줍니다.
- 그 아래에는 큰 숫자 세 개와 사용 방법 세 단계가 이어집니다.
- 버튼은 모두 알약 모양입니다. 주요 버튼은 남색 바탕이고, 보조 버튼은 남색 테두리만 있습니다.

| 용도 | 색 |
| --- | --- |
| 글자·주요 버튼 | 남색 `#0d1627` |
| 소개 화면의 판·체크·진행 막대 | 선명한 민트 `#06e7c4` |
| 종이 | `#f5f5f4` |
| 화면 바탕 | `#d5dae0` |
| 카드 | 흰색 |
| 위험 표시 | 빨강 `#d92d3a`, 노랑 `#ffd21f`, 회색 `#475467` |

글꼴은 Pretendard입니다. 로고는 이미지 생성 모델인 GPT Image로 만들었습니다.

## 알아 둘 점

- 위험 점수는 앱이 정한 기준입니다. 공식 위험 등급이 아닙니다.
- 비밀번호는 저장하지 않습니다. 알아볼 수 없게 바꾼 값의 앞 5자리만 밖으로 보냅니다.
- 배포된 앱에는 로그인이 없습니다. 모든 방문자가 같은 기록을 함께 보므로 실제 개인정보는 적지 마세요.
- Streamlit Community Cloud에서 앱이 다시 시작되면 기록을 저장한 파일이 지워질 수 있습니다.
- 달력 등 Streamlit이 직접 그리는 일부 글자는 영어로 나옵니다.
