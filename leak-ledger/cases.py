# cases.py
# 실제로 있었던 개인정보 유출 사례
# 출처에 적힌 내용만 옮겼다. 출처에 없는 값은 비워 두었다.
#   region: 국내 / 해외
#   date  : 유출이 일어났거나 발표된 날 (출처에 없으면 None)
#   size  : 출처에 적힌 유출 규모 (확인되지 않았으면 0)
#   items : 출처에 적힌 유출 정보. rules.py의 점수 목록에 없는 이름은
#           점수를 매기지 않고 직접 확인하는 할 일로 들어간다.
#   note  : 사례를 설명하는 한 줄의 이름. 문구는 texts.py에 있다.

CASE_SOURCES = {
    # 연합뉴스 2026.11.1. [해킹 도미노] ① 은행도 카페도 학교도…일상 곳곳서 내 정보 털렸다
    "국내": "https://www.yna.co.kr/view/AKR20261030161900017",
    # Have I Been Pwned가 공개한 유출 사이트 목록
    "해외": "https://haveibeenpwned.com/PwnedWebsites",
}

REAL_CASES = [
    {
        "region": "국내",
        "name": "할리스 멤버십",
        "category": "쇼핑",
        "date": "2026-10-19",
        "size": 2760000,
        "items": [
            "아이디",
            "비밀번호",
            "이름",
            "생년월일",
            "전화번호",
            "주소",
            "이메일",
            "중복가입확인정보(DI)",
        ],
        "note": "case_note_hollys",
    },
    {
        "region": "국내",
        "name": "대신증권",
        "category": "금융",
        "date": "2026-10-28",
        "size": 38490,
        "items": ["이름", "이메일", "주소", "계좌번호"],
        "note": "case_note_daishin",
    },
    {
        "region": "국내",
        "name": "빗썸",
        "category": "금융",
        "date": None,
        "size": 6444,
        "items": ["주민등록번호", "계좌번호", "신분증 사본", "운전면허번호"],
        "note": "case_note_bithumb",
    },
    {
        "region": "국내",
        "name": "기프티엘",
        "category": "쇼핑",
        "date": None,
        "size": 18359,
        "items": ["이름", "전화번호", "이메일", "계좌번호"],
        "note": "case_note_giftiel",
    },
    {
        "region": "국내",
        "name": "놀유니버스 (옛 인터파크투어)",
        "category": "기타",
        "date": None,
        "size": 0,
        "items": ["아이디", "이름", "전화번호", "이메일", "예약 내역"],
        "note": "case_note_nol",
    },
    {
        "region": "해외",
        "name": "Adobe",
        "category": "기타",
        "date": "2013-10-04",
        "size": 152445165,
        "items": ["아이디", "이메일", "비밀번호", "비밀번호 힌트"],
        "note": "case_note_adobe",
    },
    {
        "region": "해외",
        "name": "LinkedIn",
        "category": "기타",
        "date": "2012-05-05",
        "size": 164611595,
        "items": ["이메일", "비밀번호"],
        "note": "case_note_linkedin",
    },
    {
        "region": "해외",
        "name": "Facebook",
        "category": "기타",
        "date": "2019-08-01",
        "size": 509458528,
        "items": [
            "이름",
            "전화번호",
            "이메일",
            "생년월일",
            "성별",
            "직장",
            "거주 지역",
            "연애 상태",
        ],
        "note": "case_note_facebook",
    },
    {
        "region": "해외",
        "name": "Canva",
        "category": "기타",
        "date": "2019-05-24",
        "size": 137272116,
        "items": ["이메일", "아이디", "이름", "비밀번호", "거주 지역"],
        "note": "case_note_canva",
    },
]
