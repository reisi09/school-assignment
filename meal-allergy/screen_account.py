# screen_account.py
# 로그인 창: [로그인] [회원가입] [비밀번호 찾기] 탭이 있다. 로그아웃도 여기서 한다.
# 로그인한 계정은 st.session_state["user"]에 둔다. 새로고침하면 로그인이 풀린다.
# 가입하거나 비밀번호를 바꾸면 새 복구 코드를 st.session_state["recovery_code"]에 잠깐 두고 창으로 한 번 보여 준다.

import streamlit as st

from common import DEFAULT_SCHOOL, esc
from database import create_user, login, make_recovery_code, reset_password
from texts import TEXT as T

# 회원가입 결과에 맞는 안내 문구 이름
SIGNUP_ERRORS = {
    "BAD_USERNAME": "err_username_rule",
    "SHORT_PASSWORD": "err_password_short",
    "MISMATCH": "err_password_mismatch",
    "TAKEN": "err_username_taken",
}

# 비밀번호 찾기 결과에 맞는 안내 문구 이름
RESET_ERRORS = {
    "SHORT_PASSWORD": "err_password_short",
    "MISMATCH": "err_password_mismatch",
    "WRONG_CODE": "err_reset_failed",
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


@st.dialog(T["recovery_title"], width="small", dismissible=False)
def show_recovery_code():
    """새 복구 코드를 한 번만 보여 주는 창. 닫기 단추가 없어서 [적어 두었습니다]를 눌러야 닫힌다."""
    code = st.session_state["recovery_code"]
    st.html(
        f'<p class="dialog-intro">{esc(T["recovery_body"])}</p>'
        f'<p class="recovery-code">{esc(code)}</p>'
    )
    st.caption(T["recovery_used_note"])

    if st.button(T["recovery_confirm"], type="primary", key="recovery_confirm"):
        # 코드를 지워서 다시는 보여 주지 않는다. DB에는 해시만 남아 있다.
        st.session_state.pop("recovery_code")
        st.rerun()


@st.dialog(T["login_title"], width="small")
def show_login():
    """로그인 창. 로그인, 회원가입, 비밀번호 찾기 탭이 있다."""
    st.html(f'<p class="dialog-intro">{esc(T["login_intro"])}</p>')
    login_tab, signup_tab, reset_tab = st.tabs([T["tab_login"], T["tab_signup"], T["tab_reset"]])

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
            code = make_recovery_code()
            status = create_user(new_username, new_password, confirm, DEFAULT_SCHOOL, code)

            if status == "SUCCESS":
                # 가입하면 바로 로그인하고, 다시 그린 화면에서 복구 코드 창을 띄운다.
                user = login(new_username, new_password)
                st.session_state["recovery_code"] = code
                start_session(user, T["signup_done"].format(username=user["username"]))
            else:
                st.warning(T[SIGNUP_ERRORS[status]])

    with reset_tab:
        st.caption(T["reset_intro"])

        with st.form("reset_form"):
            reset_username = st.text_input(T["field_username"], key="reset_username")
            recovery_code = st.text_input(
                T["field_recovery_code"],
                placeholder=T["recovery_code_placeholder"],
                key="reset_code",
            )
            changed_password = st.text_input(T["field_new_password"], type="password", key="reset_password")
            changed_confirm = st.text_input(T["field_new_password_confirm"], type="password", key="reset_confirm")
            changed = st.form_submit_button(T["reset_button"], type="primary")

        if changed:
            new_code = make_recovery_code()
            status = reset_password(reset_username, recovery_code, changed_password, changed_confirm, new_code)

            if status == "SUCCESS":
                # 비밀번호를 바꾸면 바로 로그인하고, 새 복구 코드를 보여 준다. 쓴 코드는 더는 쓸 수 없다.
                user = login(reset_username, changed_password)
                st.session_state["recovery_code"] = new_code
                start_session(user, T["reset_done"].format(username=user["username"]))
            else:
                st.warning(T[RESET_ERRORS[status]])

    st.caption(T["account_notice"])
