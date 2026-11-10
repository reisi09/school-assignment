# 유출장부

가입한 서비스의 개인정보 유출 통지를 기록하고, 해야 할 대응 조치를 끝까지 챙기는 Streamlit 앱입니다.
고색고 응용 프로그래밍 개발 개인 프로젝트(수행평가 4차)입니다.

## 기능

- 서비스 등록: 가입한 서비스를 이름·분류·계정 별칭·메모로 저장합니다.
- 유출 기록: 통지일과 유출 항목을 기록하면 위험 점수와 권장 조치 목록을 만듭니다.
- 대응 현황: 조치를 완료할 때마다 체크하고, 비밀번호가 공개된 유출 목록에 있는지 조회합니다.
- 내 기록 검색: 서비스 이름·분류·대응 상태로 기록을 다시 찾습니다.

## 파일

| 파일 | 역할 |
| --- | --- |
| `app.py` | Streamlit 화면 |
| `database.py` | SQLite 저장·조회 (`services`, `incidents` 테이블) |
| `rules.py` | 위험 점수, 등급, 권장 조치 규칙 |
| `api.py` | Pwned Passwords API 조회 |
| `test_leak_ledger.py` | 검증 계획(TC) 테스트 |
| `.streamlit/config.toml` | 색, 글꼴, 모서리 등 화면 설정 |
| `style.css` | 설정 파일로 바꿀 수 없는 글자색 대비와 포커스 표시 |
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

색은 다섯 가지 팔레트를 쓰고, 글꼴은 Pretendard입니다.

| 색 | 쓰는 곳 |
| --- | --- |
| `#07beb8` | 주요 버튼, 체크, 선택한 유출 항목 |
| `#3dccc7` | 주요 버튼에 마우스를 올렸을 때 |
| `#68d8d6` | 표 안쪽 선, 사이드바와 접는 영역의 테두리 |
| `#9ceaef` | 성공 안내 배경, 글자 선택 영역 |
| `#c4fff9` | 현재 메뉴 표시, 정보 안내 배경 |

팔레트가 모두 밝은 색이라 글자색으로는 대비가 부족합니다.
글자(`#0b3231`), 링크와 포커스 표시(`#06706d`), 입력창 테두리(`#078f8b`)는 같은 색상 계열의 어두운 색을 따로 정했습니다.

화면의 넓은 면은 흰색으로 두고, 팔레트 색은 누를 수 있는 곳과 현재 상태를 알리는 곳에만 썼습니다.
경고(노란색)와 오류·위험 높음(빨간색)은 뜻이 바로 통하도록 Streamlit 기본 색을 그대로 둡니다.

## 테스트

```bash
python -m unittest -v
```

## 배포 (Streamlit Community Cloud)

1. https://streamlit.io/cloud 에 GitHub 계정으로 로그인하고 Create app을 선택합니다.
2. Repository는 `reisi09/school-assignment`, Branch는 `leak-ledger`를 고릅니다.
3. Main file path에 `leak-ledger/app.py`를 입력합니다.
4. Advanced settings에서 Python version을 3.12로 고르고 배포합니다. (`requirements.txt`를 Python 3.12에서 만들었습니다.)

`requirements.txt`, `.streamlit/config.toml`, `static/` 폴더가 `app.py`와 같은 폴더에 있어 패키지와 화면 설정은 자동으로 적용됩니다.

## 주의

- 위험 점수는 대응 순서를 정하기 위한 앱 자체 기준이며 공식 위험 등급이 아닙니다.
- 비밀번호는 저장하지 않고, 외부로는 SHA-1 해시 앞 5자리만 보냅니다.
- 배포된 주소에서는 입력값이 앱 서버를 거치므로 시연용 비밀번호만 입력하세요.
- Streamlit Community Cloud는 앱이 다시 시작되면 `leak_ledger.db`가 초기화됩니다.
