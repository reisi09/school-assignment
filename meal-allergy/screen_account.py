# screen_account.py
# 로그인 창: [로그인] [회원가입] 탭이 있다. 로그아웃도 여기서 한다.
# 로그인한 계정은 st.session_state["user"]에 둔다. 새로고침하면 로그인이 풀린다.

import streamlit as st

from common import DEFAULT_SCHOOL, esc
from database import create_user, login
from texts import TEXT as T

# 회원가입 결과에 맞는 안내 문구 이름
SIGNUP_ERRORS = {
    "BAD_USERNAME": "err_username_rule",
    "SHORT_PASSWORD": "err_password_short",
    "MISMATCH": "err_password_mismatch",
    "TAKEN": "err_username_taken",
}


def start_session(user, message):
    """계정을 로그인 상태로 두고, 알림을 띄운 뒤 화면을 다시 그린다(창이 닫힌다)."""
    st.session_state["user"] = user
    st.toast(message)
    st.rerun()


def log_out():
    """로그아웃 버튼을 누르면 로그인한 계정 정보를 지운다."""
    st.session_state.pop("user", None)
    st.toast(T["logout_done"])


@st.dialog(T["login_title"], width="small")
def show_login():
    """로그인 창. 로그인 탭과 회원가입 탭이 있다."""
    st.html(f'<p class="dialog-intro">{esc(T["login_intro"])}</p>')
    login_tab, signup_tab = st.tabs([T["tab_login"], T["tab_signup"]])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input(T["field_username"], key="login_username")
            password = st.text_input(T["field_password"], type="password", key="login_password")
            submitted = st.form_submit_button(T["login_button"], type="primary")

        if submitted:
            user = login(username, password)

            # 아이디가 틀렸는지 비밀번호가 틀렸는지 알려 주지 않는다. 남의 아이디를 알아내기 어렵게 하려는 것이다.
            if user is None:
                st.warning(T["err_login_failed"])
            else:
                start_session(user, T["login_done"].format(username=user["username"]))

    with signup_tab:
        with st.form("signup_form"):
            new_username = st.text_input(T["field_username"], key="signup_username")
            st.caption(T["username_help"])
            new_password = st.text_input(T["field_password"], type="password", key="signup_password")
            confirm = st.text_input(T["field_password_confirm"], type="password", key="signup_confirm")
            st.caption(T["password_help"])
            joined = st.form_submit_button(T["signup_button"], type="primary")

        if joined:
            status = create_user(new_username, new_password, confirm, DEFAULT_SCHOOL)

            if status == "SUCCESS":
                # 가입하면 바로 로그인한다.
                user = login(new_username, new_password)
                start_session(user, T["signup_done"].format(username=user["username"]))
            else:
                st.warning(T[SIGNUP_ERRORS[status]])

    st.caption(T["account_notice"])
