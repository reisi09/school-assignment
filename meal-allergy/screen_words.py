# screen_words.py
# 주의 낱말 화면: 알레르기 번호로 표시되지 않는 재료(예: 아몬드)를 낱말로 등록하고, 목록을 보고, 찾고, 지운다.
# 등록한 낱말이 메뉴 이름에 들어 있으면 오늘·급식표·찾기 화면의 그 메뉴에 표시한다.

import streamlit as st

from common import esc, get_profile, is_logged_in, show_page_head, show_source
from database import WORD_MAX, add_watch_word, delete_watch_word, get_watch_words
from screen_account import show_login
from texts import TEXT as T

# 등록 결과에 맞는 안내 문구 이름
WORD_ERRORS = {
    "EMPTY": "err_word_empty",
    "TOO_LONG": "err_word_too_long",
    "DUPLICATE": "err_word_duplicate",
}

# 메모의 최대 글자 수
MEMO_MAX = 40


def remove_word(user_id, row):
    """지우기 버튼을 누르면 주의 낱말 하나를 지운다."""
    delete_watch_word(user_id, row["id"])
    st.toast(T["word_deleted"].format(word=row["word"]))


def show_add_form(user_id):
    """주의 낱말을 등록하는 칸"""
    with st.form("word_form", clear_on_submit=True):
        with st.container(horizontal=True, vertical_alignment="bottom"):
            word = st.text_input(
                T["field_word"],
                placeholder=T["word_placeholder"],
                max_chars=WORD_MAX,
                width=240,
            )
            memo = st.text_input(
                T["field_word_memo"],
                placeholder=T["word_memo_placeholder"],
                max_chars=MEMO_MAX,
                width=360,
            )
            added = st.form_submit_button(T["word_add_button"], type="primary")

    if added:
        status = add_watch_word(user_id, word, memo)

        if status == "SUCCESS":
            st.toast(T["word_added"].format(word=word.strip()))
        else:
            st.warning(T[WORD_ERRORS[status]])


def show_word_list(user_id):
    """내 주의 낱말 목록. 위의 검색칸에 글자를 넣으면 낱말이나 메모에 그 글자가 든 것만 보여 준다."""
    st.html(f'<h2 class="group-title">{esc(T["words_list_title"])}</h2>')
    keyword = st.text_input(
        T["words_search_label"],
        placeholder=T["words_search_placeholder"],
        key="word_search",
        width=360,
    )
    rows = get_watch_words(user_id, keyword)

    if len(rows) == 0:
        if keyword.strip() == "":
            st.html(f'<div class="empty">{esc(T["words_none"])}</div>')
        else:
            st.html(f'<div class="empty">{esc(T["words_search_none"])}</div>')

        return

    st.caption(T["words_count"].format(count=len(rows)))

    # 줄마다 낱말·메모와 지우기 버튼을 나란히 놓는다. 줄 key는 wrow_로 시작한다(style.css가 줄 사이에 선을 긋는다).
    for row in rows:
        with st.container(horizontal=True, vertical_alignment="center", key=f"wrow_{row['id']}"):
            st.html(f'<div class="word-row"><b>{esc(row["word"])}</b><span>{esc(row["memo"])}</span></div>')
            st.button(T["word_delete"], key=f"wdel_{row['id']}", on_click=remove_word, args=(user_id, row))


def show_words():
    """주의 낱말 화면"""
    profile = get_profile()

    with st.container(key="sec_page"):
        show_page_head(T["words_title"], T["words_intro"])

        if not is_logged_in():
            st.html(f'<div class="empty">{esc(T["words_login"])}</div>')

            if st.button(T["nav_login"], type="primary", key="words_login"):
                show_login()
        else:
            show_add_form(profile["id"])
            show_word_list(profile["id"])

        show_source()
