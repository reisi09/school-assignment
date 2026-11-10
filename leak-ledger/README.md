# 유출장부

가입한 서비스의 개인정보 유출 통지를 기록하고, 해야 할 대응 조치를 끝까지 챙기는 Streamlit 앱입니다.
고색고 응용 프로그래밍 개발 개인 프로젝트(수행평가 4차)입니다.

## 기능

- 서비스 등록: 가입한 서비스를 이름·분류·계정 별칭·메모로 저장합니다.
- 유출 기록: 통지일과 유출 항목을 기록하면 위험 점수와 권장 조치 목록을 만듭니다. 보도된 실제 사례를 눌러 기록을 만들어 볼 수도 있습니다.
- 대응 현황: 조치를 완료할 때마다 체크하고, 비밀번호가 공개된 유출 목록에 있는지 조회합니다.
- 내 기록 검색: 서비스 이름·분류·대응 상태로 기록을 다시 찾습니다.

## 파일

| 파일 | 역할 |
| --- | --- |
| `app.py` | Streamlit 화면 |
| `database.py` | SQLite 저장·조회 (`services`, `incidents` 테이블) |
| `rules.py` | 위험 점수, 등급, 권장 조치 규칙 |
| `api.py` | Pwned Passwords API 조회 |
| `cases.py` | 보도된 실제 유출 사례 5건 (출처: 연합뉴스 2026.11.1.) |
| `test_leak_ledger.py` | 검증 계획(TC) 테스트 |
| `.streamlit/config.toml` | 색, 글꼴, 모서리 등 화면 설정 |
| `style.css` | 카드, 알약 모양 표시, 포커스 표시 등 화면 모양 |
| `static/PretendardVariable.woff2` | Pretendard 글꼴 (SIL OFL 1.1, `static/Pretendard-LICENSE.txt`) |
| `requirements.txt` | 배포용 패키지 목록 (`pip freeze` 결과) |

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

`app.py`가 있는 폴더에서 실행합니다. 화면 설정은 같은 폴더의 `.streamlit/config.toml`에 있습니다.
데이터베이스 파일 `leak_ledger.db`는 처음 실행할 때 같은 폴더에 자동으로 만들어집니다.

## 화면 디자인

VESSL Cloud 화면을 참고했습니다. 옅은 회청색 바탕에 흰 카드를 올리고, 버튼과 상태 표시는 알약 모양으로 둡니다. 글꼴은 Pretendard입니다.

| 색 | 쓰는 곳 |
| --- | --- |
| `#f4f8fb` | 화면 바탕 |
| `#ffffff` | 카드, 사이드바 |
| `#101828` | 본문 글자, 주요 버튼 |
| `#07beb8`, `#3dccc7` | 체크, 진행 막대 |
| `#68d8d6`, `#9ceaef`, `#c4fff9` | 화면 머리 영역, 현재 메뉴, 정보 안내 |
| `#d9f6e5` 연두, `#fff3c4` 노랑, `#ffe1e8` 분홍, `#e1eeff` 하늘 | 상태와 위험 등급 표시 |

파스텔 색 위의 글자는 같은 계열의 어두운 색을 써서 대비를 4.5:1 이상으로 맞췄습니다.

## 테스트

```bash
python -m unittest -v
```

## 배포 (Streamlit Community Cloud)

배포 주소: https://reisi09-school-assignment-leak-ledgerapp-leak-ledger-jeudp4.streamlit.app/

1. https://streamlit.io/cloud 에 GitHub 계정으로 로그인하고 Create app을 선택합니다.
2. Repository는 `reisi09/school-assignment`, Branch는 `leak-ledger`를 고릅니다.
3. Main file path에 `leak-ledger/app.py`를 입력하고 배포합니다.

Python 버전은 기본값(3.14)을 그대로 썼습니다. `requirements.txt`는 Python 3.12에서 만들었고, 3.14에서도 설치와 테스트가 되는 것을 확인했습니다.

`requirements.txt`, `.streamlit/config.toml`, `static/` 폴더가 `app.py`와 같은 폴더에 있어 패키지와 화면 설정은 자동으로 적용됩니다.

## 주의

- 위험 점수는 대응 순서를 정하기 위한 앱 자체 기준이며 공식 위험 등급이 아닙니다.
- 비밀번호는 저장하지 않고, 외부로는 SHA-1 해시 앞 5자리만 보냅니다.
- 배포된 주소에서는 입력값이 앱 서버를 거치므로 시연용 비밀번호만 입력하세요.
- Streamlit Community Cloud는 앱이 다시 시작되면 `leak_ledger.db`가 초기화됩니다.
