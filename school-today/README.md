# 학교한눈

나이스 교육정보 개방 포털의 공개 자료로 우리 학교의 급식·시간표·학사일정·학교 정보를 한곳에서 보고, 내 알레르기 표시·우리 반 일정·급식 평가를 더한 서비스입니다. 고색고 응용 프로그래밍 개발 개인 프로젝트(수행평가 4차)로 만들었습니다.

## 왜 만들었나

학생은 급식, 시간표, 학사일정을 따로 찾아봐야 합니다. 알레르기가 있는 학생은 메뉴 뒤 번호를 알레르기 번호표와 매번 대조해야 합니다. 수행평가도 한 주에 몰리기 쉽습니다. 필요한 학교 자료와 우리 반 일정을 한곳에서 확인하려고 만들었습니다.

## 배포 주소

배포 후 적음

## 화면 안내

처음에는 고색고등학교 2학년 1반을 보여 줍니다. 내 설정에서 학교와 반을 바꿉니다.

| 화면 | 하는 일 |
| --- | --- |
| 오늘 | 오늘 급식과 알레르기 표시, 오늘 시간표를 봅니다. 앞으로 4주 안의 학사일정과 우리 반 일정을 합쳐 최대 6개 보여 줍니다. 이번 주 수행평가가 3개 이상이면 경고합니다. |
| 급식 | 월요일부터 금요일까지 급식을 카드로 봅니다. 내 알레르기 식품이 든 메뉴는 빨갛게 표시합니다. 열량·급식 인원·영양 정보·원산지와 알레르기 번호표도 봅니다. 오늘 앞뒤 4주에서 메뉴를 찾고, 오늘 메뉴에 별점과 한줄평을 남깁니다. 인기 메뉴 순위와 최근 한줄평도 확인합니다. |
| 시간표 | 학년과 반을 골라 한 주 시간표를 봅니다. 지난주·이번 주·다음 주로 이동합니다. 오늘과 쉬는 날을 구분해 표시합니다. |
| 일정 | 한 달 학사일정과 우리 반 일정을 봅니다. 학사일정은 내 학년의 평일 일정만 보여 주며, 학년 정보가 없으면 모든 학년 일정으로 봅니다. 우리 반 일정을 등록·지우기·찾기 합니다. 오늘부터 90일 안에 등록된 수행평가 중 한 주에 3개 이상 몰린 주를 알려 줍니다. |
| 학교 | 주소·전화·홈페이지·학교 종류·남녀 구분·설립 구분과 학년별 학급 수를 봅니다. 알레르기 번호표와 앱·자료 안내도 확인합니다. |
| 내 설정 창 | 학교를 이름으로 찾고 학교·학년·반·알레르기를 이름표(별명)로 저장합니다. 저장한 설정은 이름표로 다시 불러옵니다. |

## 등록·조회·검색

| 구분 | 대상 | 사용 방법 |
| --- | --- | --- |
| 등록 | 내 설정 | 내 설정 창에서 이름표·학교·학년·반·알레르기를 저장합니다. 같은 이름표로 저장하면 기존 설정을 바꿉니다. |
| 등록 | 우리 반 일정 | 일정 화면에서 종류(수행평가·과제·시험·기타), 과목, 내용, 날짜, 메모를 입력합니다. |
| 등록 | 급식 평가 | 급식 화면에서 오늘 메뉴를 골라 1~5점과 한줄평을 남깁니다. 한줄평은 60자까지 입력하며, 비워도 됩니다. |
| 조회 | 학교 공개 자료 | 오늘·급식·시간표·일정·학교 화면에서 급식, 시간표, 학사일정, 학교 정보와 학급 수를 봅니다. |
| 조회 | 직접 저장한 자료 | 이름표로 내 설정을 불러옵니다. 같은 학교·학년·반의 일정, 같은 학교의 인기 메뉴 순위와 최근 한줄평을 봅니다. |
| 검색 | 메뉴 찾기 | 급식 화면에서 메뉴 이름을 입력합니다. 오늘 앞뒤 4주의 급식에서 찾으며, 띄어쓰기는 빼고 비교합니다. |
| 검색 | 우리 반 일정 찾기 | 일정 화면에서 과목·내용·메모에 들어간 낱말로 찾습니다. 보고 있는 달과 관계없이 2000년부터 2100년까지 저장된 우리 반 일정을 찾습니다. |
| 검색 | 학교 찾기 | 내 설정 창에서 학교 이름으로 찾습니다. 결과에 학교 이름과 주소를 함께 표시합니다. |

## 쓴 자료 (API)

학교 자료는 [나이스 교육정보 개방 포털](https://open.neis.go.kr)의 공개 API에서 받습니다. 요청 주소는 `https://open.neis.go.kr/hub/`입니다.

| 자료 | API 이름 | 앱에서 쓰는 내용 |
| --- | --- | --- |
| 학교 기본 정보 | `schoolInfo` | 학교 찾기, 학교 코드, 주소·전화·홈페이지 등 |
| 급식 | `mealServiceDietInfo` | 날짜·끼니·메뉴·알레르기 번호·열량·영양 정보·원산지·급식 인원 |
| 학사일정 | `SchoolSchedule` | 날짜·행사 이름·쉬는 날 여부·해당 학년 |
| 시간표 | `hisTimetable`·`misTimetable`·`elsTimetable` | 각각 고등학교·중학교·초등학교의 날짜·교시·과목 |
| 학급 정보 | `classInfo` | 해당 연도와 학년의 학급 수 |

인증키가 없으면 한 번에 5건까지만 받습니다. `neis.py`의 `fetch_range`는 먼저 전체 기간을 요청합니다. 자료가 덜 오면 일주일씩 나누고, 그래도 넘치는 주는 하루씩 나눠 받습니다.

하루씩 받아도 시간표는 5교시까지만 옵니다. 키가 없으면 나이스가 항상 앞 5건만 주기 때문입니다. 기간을 나누는 방법만으로 하루의 6교시 이후 자료까지 받을 수는 없습니다.

받은 자료는 `st.cache_data`로 1시간 기억합니다. 같은 조건으로 다시 조회할 때 그 자료를 사용합니다. 성적·출결 같은 개인 정보는 이 공개 포털에서 제공하지 않으며, 앱에서도 다루지 않습니다.

## 나이스 인증키 넣기(선택)

인증키를 넣으면 나이스에 등록된 시간표의 모든 교시가 보입니다. 나이스 교육정보 개방 포털에 회원가입한 뒤 인증키를 신청합니다.

로컬에서는 `app.py`가 있는 폴더 아래에 `.streamlit/secrets.toml` 파일을 만들고 다음 한 줄을 넣습니다.

```toml
NEIS_KEY = "발급받은 키"
```

Streamlit Community Cloud에서는 앱의 Settings → Secrets에 같은 줄을 넣습니다.

`.streamlit/secrets.toml`은 `.gitignore`에 있어 git에 올라가지 않습니다. 인증키는 코드에 적지 않습니다.

## 파일 구성

| 파일·폴더 | 역할 |
| --- | --- |
| `app.py` | 앱 설정과 위쪽 메뉴를 만들고, 선택한 화면을 부릅니다. DB 테이블을 준비하고 주소창의 이름표로 설정을 불러옵니다. |
| `common.py` | 기본 학교·반, 날짜 표시, 화면 제목, 주 이동 버튼 등 여러 화면이 함께 쓰는 값과 함수를 모읍니다. |
| `neis.py` | 나이스 API 요청, 기간 나누기, 학교·급식·학사일정·시간표·학급 수 조회를 맡습니다. |
| `foods.py` | 급식 글자에서 메뉴 이름·알레르기 번호·열량·영양 정보·원산지를 읽습니다. |
| `days.py` | 한국 시간, 주·월 이동, 남은 날 수, 수행평가가 몰린 주를 계산합니다. |
| `database.py` | SQLite에 내 설정·우리 반 일정·급식 평가를 저장하고 불러옵니다. |
| `screen_today.py` | 오늘 급식·시간표, 다가오는 일정, 이번 주 수행평가를 보여 줍니다. |
| `screen_meal.py` | 주간 급식, 메뉴 찾기, 급식 평가와 인기 메뉴 순위를 보여 줍니다. |
| `screen_timetable.py` | 학년·반 선택과 주간 시간표를 보여 줍니다. |
| `screen_schedule.py` | 월별 학사일정과 우리 반 일정, 일정 등록·삭제·검색, 수행평가 경고를 맡습니다. |
| `screen_school.py` | 학교 기본 정보·학급 수·알레르기 번호표·앱 안내를 보여 줍니다. |
| `screen_settings.py` | 내 설정 창에서 학교를 찾고 설정을 저장하거나 불러옵니다. |
| `texts.py` | 화면에 쓰는 문구를 `TEXT`에 모읍니다. |
| `test_school_today.py` | 급식 글자 읽기, 날짜 계산, API 요청, DB 저장을 확인하는 테스트 13개입니다. |
| `style.css` | 메뉴·카드·표·버튼과 CSS 로고의 모양을 정합니다. |
| `.gitignore` | 가상 환경, 임시 Python 파일, DB 파일, 인증키 파일을 git에서 제외합니다. |
| `.streamlit/config.toml` | 기본 색·글꼴·입력칸 모양을 정하고 정적 파일 제공을 켭니다. |
| `requirements.txt` | 설치할 Python 패키지와 버전을 적습니다. |
| `static/` | Pretendard 글꼴인 `PretendardVariable.woff2`와 사용 허가문인 `Pretendard-LICENSE.txt`를 담습니다. 글꼴은 SIL OFL 1.1을 따릅니다. |

## 코드 구조

### 파일끼리 부르는 방향

아래 화살표는 왼쪽 파일이 오른쪽 파일에서 가져오는 실제 `import` 방향입니다. 같은 폴더의 파일만 적었습니다.

| 가져오는 파일 | 가져오는 대상 |
| --- | --- |
| `app.py` | → `common.py`, `database.py`, 화면 파일 6개, `texts.py` |
| `screen_today.py` | → `common.py`, `database.py`, `days.py`, `foods.py`, `neis.py`, `screen_meal.py`, `screen_schedule.py`, `screen_settings.py`, `texts.py` |
| `screen_meal.py` | → `common.py`, `database.py`, `days.py`, `foods.py`, `neis.py`, `texts.py` |
| `screen_timetable.py` | → `common.py`, `days.py`, `neis.py`, `screen_settings.py`, `texts.py` |
| `screen_schedule.py` | → `common.py`, `database.py`, `days.py`, `neis.py`, `texts.py` |
| `screen_school.py` | → `common.py`, `days.py`, `foods.py`, `neis.py`, `screen_settings.py`, `texts.py` |
| `screen_settings.py` | → `common.py`, `database.py`, `days.py`, `foods.py`, `neis.py`, `texts.py` |
| `common.py` | → `days.py`, `texts.py` |
| `neis.py` | → `days.py` |
| `database.py` | → `days.py` |
| `test_school_today.py` | → `database.py`, `days.py`, `foods.py`, `neis.py` |
| `days.py`, `foods.py`, `texts.py` | 같은 폴더의 다른 파일을 가져오지 않습니다. |

`app.py`는 `show_nav`에서 고른 메뉴에 맞는 화면 함수를 부릅니다. 화면 파일은 `neis.py`에서 공개 자료를 받고, `database.py`에서 직접 등록한 자료를 읽거나 저장합니다. `foods.py`와 `days.py`는 글자와 날짜 계산을 맡습니다.

### 화면별 주요 함수

| 파일 | 주요 함수와 역할 |
| --- | --- |
| `screen_today.py` | `show_today`: 오늘 화면을 모읍니다. `show_hero`: 날짜와 학교·반을 표시합니다. `show_meal_card`, `show_timetable_card`, `show_upcoming_card`, `show_week_card`: 급식·시간표·다가오는 일정·이번 주 수행평가 카드를 만듭니다. |
| `screen_meal.py` | `show_meal`: 급식 화면을 모읍니다. `show_week`: 주간 급식을 표시합니다. `show_search`: 메뉴를 찾습니다. `show_reviews`: 평가를 저장하고 순위·한줄평을 표시합니다. `dishes_html`: 알레르기를 표시한 메뉴를 만듭니다. `day_card`, `pairs_html`, `allergy_legend_html`: 하루 카드·영양 정보와 원산지·번호표를 만듭니다. |
| `screen_timetable.py` | `show_timetable`: 학년·반·주를 고르고 자료를 받습니다. `timetable_html`: 주간 시간표를 만듭니다. |
| `screen_schedule.py` | `show_schedule`: 일정 화면을 모읍니다. `school_events_for`: 내 학년의 평일 학사일정을 고릅니다. `show_month_nav`, `move_month`: 달을 바꿉니다. `show_add_form`, `remove_event`, `show_search`: 우리 반 일정을 등록·삭제·검색합니다. `show_crowded`: 수행평가가 몰린 주를 표시합니다. `school_event_html`, `class_event_html`: 일정 한 줄을 만듭니다. |
| `screen_school.py` | `show_school`: 학교 정보와 학급 수, 알레르기 번호표, 앱 안내를 표시합니다. |
| `screen_settings.py` | `show_settings`: 내 설정 창을 엽니다. `use_profile`: 불러온 설정을 적용하고 주소창에 이름표를 남깁니다. `allergy_label`, `school_label`: 선택 칸의 글자를 만듭니다. |

오늘 화면은 급식 화면의 `dishes_html`과 일정 화면의 `school_events_for`, `class_event_html`을 함께 씁니다. 시간표와 학교 화면은 `screen_settings.py`의 `GRADE_COUNTS`로 학교 종류별 학년 수를 정합니다.

### 저장하는 자료와 함수

`database.py`의 `connect_db`는 `school_today.db`에 연결합니다. `create_tables`는 아래 테이블 세 개를 만들며, 이미 있으면 그대로 둡니다. 나이스에서 받은 급식·시간표·학사일정은 이 DB에 저장하지 않습니다.

| 테이블 | 저장하는 내용 | 관련 함수 |
| --- | --- | --- |
| `profiles` | 이름표, 학교 코드·이름·종류, 학년, 반, 알레르기 번호, 수정 시각 | `save_profile`: 이름표로 저장하거나 기존 설정을 바꿉니다. `load_profile`: 이름표로 불러옵니다. |
| `class_events` | 학교 코드, 학년, 반, 종류, 과목, 내용, 날짜, 메모, 등록 시각 | `add_event`: 등록합니다. `get_events`: 반·기간·검색어에 맞는 일정을 날짜순으로 읽습니다. `delete_event`: 일정 하나를 지웁니다. |
| `meal_reviews` | 학교 코드, 급식 날짜, 메뉴 이름, 별점, 한줄평, 등록 시각 | `add_review`: 평가를 남깁니다. `get_top_dishes`: 평균 별점이 높은 메뉴를 읽습니다. `get_recent_reviews`: 비어 있지 않은 최근 한줄평을 읽습니다. |

인기 메뉴는 평균 별점이 높은 순서로 최대 5개를 보여 줍니다. 평균이 같으면 평가 수가 많은 메뉴가 먼저 나오며, 둘 다 같으면 메뉴 이름순입니다. 최근 한줄평도 최대 5개를 보여 줍니다.

### 급식 메뉴 글자를 읽는 방법

나이스 급식 메뉴는 여러 줄이 `<br/>`로 이어진 글자로 옵니다. `foods.py`의 `parse_dishes`는 이를 줄마다 나눕니다. `parse_dish`는 각 줄 끝의 `(5.6.16)`처럼 숫자와 점으로 된 괄호를 알레르기 번호로 읽습니다. 이름 안의 `(수제)` 같은 괄호는 남깁니다.

```python
from foods import parse_dish

parse_dish("쇠고기콩나물국 (5.6.16)")
# ("쇠고기콩나물국", [5, 6, 16])

parse_dish("김치함박스테이크(수제) (2.5.6)")
# ("김치함박스테이크(수제)", [2, 5, 6])
```

`find_my_allergens`는 메뉴 번호와 내 알레르기 번호를 비교합니다. `dishes_html`은 겹치는 식품이 있는 메뉴를 빨갛게 표시합니다.

### 내 설정을 유지하는 방법

`screen_settings.py`의 `use_profile`은 현재 설정을 `st.session_state`에 넣고, 주소창에 `?me=이름표`를 남깁니다. 새로 열었을 때 `app.py`는 이 이름표를 읽어 `load_profile`로 저장된 설정을 불러옵니다. 주소창에는 설정 전체가 아니라 이름표만 들어갑니다. 이는 로그인이나 비밀번호가 아닙니다.

## 실행 방법

`app.py`가 있는 폴더에서 다음 명령을 차례로 입력합니다.

```bash
pip install -r requirements.txt
streamlit run app.py
```

DB 파일 `school_today.db`는 처음 실행할 때 같은 폴더에 자동으로 만들어집니다.

테스트 명령은 다음과 같습니다.

```bash
python -m unittest -v
```

`test_school_today.py`에는 테스트가 13개 있습니다. 급식 글자 읽기와 알레르기 비교 4개, 날짜 계산 2개, 나이스 요청 4개, DB 저장 3개입니다. 나이스에 실제로 연결하지 않고 가짜 응답으로 확인합니다. DB 테스트는 임시 DB를 써서 저장한 앱 자료를 건드리지 않습니다.

## 배포 방법

Streamlit Community Cloud에서 새 앱을 만들고 다음 값을 입력합니다.

| 항목 | 값 |
| --- | --- |
| Repository | `reisi09/school-assignment` |
| Branch | `school-today` |
| Main file path | `school-today/app.py` |
| Python 버전 | 기본값 |

인증키를 쓴다면 앱의 Settings → Secrets에 `NEIS_KEY`를 넣습니다. 배포가 끝나면 위의 배포 주소에 앱 주소를 적습니다.

## 알아 둘 점

- 로그인이 없습니다. 우리 반 일정·급식 평가·저장한 내 설정은 모든 방문자가 함께 씁니다. 실명이나 개인정보를 적지 않습니다. 같은 학교·학년·반을 고르면 다른 방문자도 일정을 지울 수 있고, 같은 이름표로 저장하면 설정이 바뀝니다.
- Streamlit Community Cloud에서 앱이 다시 시작되면 DB 파일이 지워질 수 있습니다. 저장한 설정·일정·평가가 계속 남는다고 보장하지 않습니다.
- 학교가 급식을 아직 올리지 않은 날은 급식 카드에 ‘급식 자료 미등록’으로 보입니다. 코드에서는 오늘 뒤의 날짜에 급식 자료가 없고 학사일정상 쉬는 날도 아니면 이 문구를 표시합니다. 그 밖에 자료가 없는 날은 ‘급식 없음’으로 표시합니다.
- 달력 등 Streamlit이 직접 그리는 일부 글자는 영어로 나옵니다.
- Streamlit은 HTML 안의 SVG 그림과 CSS 안의 꺾쇠 글자를 지우므로 로고는 CSS로 그렸습니다. `style.css`의 `.brand-mark`에서 달력 모양을 만듭니다.
