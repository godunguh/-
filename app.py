# app.py

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import os
import json
import uuid

# --- 구글 시트 인증 및 클라이언트 초기화 ---

# Streamlit의 Secrets에서 인증 정보를 가져오거나, 로컬의 credentials.json 파일을 사용합니다.
def get_gspread_client():
    # Streamlit Cloud에 배포된 경우
    if 'gcp_service_account' in st.secrets:
        creds_json = st.secrets["gcp_service_account"]
    # 로컬에서 실행하는 경우
    elif os.path.exists("credentials.json"):
        with open("credentials.json") as f:
            creds_json = json.load(f)
    else:
        st.error("Google Sheets API 인증 정보를 찾을 수 없습니다. credentials.json 파일을 추가하거나 Streamlit Secrets를 설정해주세요.")
        st.stop()

    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(creds_json, scopes=scopes)
    client = gspread.authorize(credentials)
    return client

# --- 구글 시트 워크시트 가져오기 ---
def get_quiz_sheet(sheet_name):
    try:
        client = get_gspread_client()
        spreadsheet = client.open(sheet_name)
        worksheet = spreadsheet.sheet1
        return worksheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"'{sheet_name}'라는 이름의 구글 시트를 찾을 수 없습니다. 구글 시트 파일의 이름을 확인하고, 서비스 계정에 공유했는지 확인해주세요.")
        st.stop()
    except Exception as e:
        st.error(f"구글 시트에 연결하는 중 오류가 발생했습니다: {e}")
        st.stop()

# --- 데이터프레임 로드 ---
def load_data(worksheet):
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    # id, creator 열이 없으면 빈 값으로 생성 (기존 데이터 호환)
    if 'id' not in df.columns:
        df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]
    if 'creator' not in df.columns:
        df['creator'] = '익명'
    return df

# --- 페이지 렌더링 ---

# 퀴즈 풀기 페이지
def render_quiz_page(quiz):
    st.header(f"퀴즈 풀기: {quiz['question']}")
    st.write(f"출제자: {quiz.get('creator', '익명')}")
    st.markdown("---")

    options = [quiz['option1'], quiz['option2'], quiz['option3'], quiz['option4']]
    
    session_key = f"quiz_{quiz['id']}"
    if session_key not in st.session_state:
        st.session_state[session_key] = {'submitted': False, 'user_answer': None}

    with st.form(key=f"quiz_form_{quiz['id']}"):
        user_choice = st.radio(
            "정답을 선택하세요:",
            options,
            key=f"radio_{quiz['id']}"
        )
        submitted = st.form_submit_button("정답 제출")

    if submitted:
        st.session_state[session_key]['submitted'] = True
        st.session_state[session_key]['user_answer'] = user_choice

    if st.session_state[session_key]['submitted']:
        user_answer = st.session_state[session_key]['user_answer']
        # quiz['answer']가 숫자 형태의 문자열일 수 있으므로 int로 변환
        correct_answer_index = int(quiz['answer']) - 1
        correct_answer = options[correct_answer_index]
        
        if user_answer == correct_answer:
            st.success(f"정답입니다! (정답: {correct_answer})")
        else:
            st.error(f"오답입니다. (정답: {correct_answer}, 당신의 선택: {user_answer})")
        
        if st.button("목록으로 돌아가기", key=f"back_{quiz['id']}"):
            st.session_state.page = 'list'
            st.session_state.selected_quiz_id = None
            st.experimental_rerun()

# 퀴즈 목록 페이지
def render_list_page(df):
    st.header("📝 퀴즈 목록")
    st.write("풀고 싶은 퀴즈의 '풀기' 버튼을 누르세요.")

    if df.empty or all(col not in df for col in ['question', 'creator']):
        st.info("아직 만들어진 퀴즈가 없습니다. '퀴즈 만들기' 탭에서 새로운 퀴즈를 만들어보세요!")
        return

    # 최신 퀴즈가 위로 오도록 데이터프레임 순서 뒤집기
    df_reversed = df.iloc[::-1]

    for index, row in df_reversed.iterrows():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(row['question'])
            st.caption(f"출제자: {row.get('creator', '익명')}")
        with col2:
            if st.button("풀기", key=f"solve_{row['id']}"):
                st.session_state.page = 'solve'
                st.session_state.selected_quiz_id = row['id']
                st.experimental_rerun()
        st.markdown("---")

# 퀴즈 만들기 페이지
def render_create_page(worksheet):
    st.header("✍️ 새로운 퀴즈 만들기")

    with st.form(key="create_quiz_form", clear_on_submit=True):
        question = st.text_input("질문 (Question)", placeholder="예: 대한민국의 수도는?")
        options = [st.text_input(f"선택지 {i+1}", placeholder=f"예시: {opt}") for i, opt in enumerate(["서울", "부산", "인천", "대구"])]
        answer = st.selectbox("정답 선택 (Correct Answer)", [1, 2, 3, 4], format_func=lambda x: f"선택지 {x}")
        creator = st.text_input("출제자 이름 (Creator's Name)", placeholder="예: 홍길동")
        
        submit_button = st.form_submit_button("퀴즈 제출하기")

    if submit_button:
        if not all([question, options[0], options[1], options[2], options[3], creator]):
            st.warning("모든 필드를 채워주세요.")
        else:
            try:
                new_quiz_id = str(uuid.uuid4())
                # 구글 시트의 헤더 순서와 정확히 일치해야 합니다.
                new_row = [
                    new_quiz_id, question, 
                    options[0], options[1], options[2], options[3], 
                    answer, creator
                ]
                worksheet.append_row(new_row, value_input_option='USER_ENTERED')
                st.success("🎉 새로운 퀴즈가 성공적으로 등록되었습니다!")
            except Exception as e:
                st.error(f"퀴즈를 등록하는 중 오류가 발생했습니다: {e}")

# --- 메인 앱 로직 ---
def main():
    st.set_page_config(page_title="모두의 퀴즈", page_icon="🧠")
    st.title("🧠 모두의 퀴즈 플랫폼")
    st.caption("누구나 퀴즈를 만들고, 풀고, 공유할 수 있는 공간입니다.")

    # --- 중요 ---
    # 사용자가 만든 구글 시트 파일의 실제 이름을 여기에 입력해야 합니다.
    google_sheet_name = "quiz_db" 
    
    worksheet = get_quiz_sheet(google_sheet_name)

    st.sidebar.title("메뉴")
    page_options = ["퀴즈 목록", "퀴즈 만들기"]
    
    if 'page' not in st.session_state:
        st.session_state.page = 'list'
        st.session_state.selected_quiz_id = None

    choice = st.sidebar.radio("이동할 페이지를 선택하세요", page_options, key="nav")
    
    page_map = {"퀴즈 목록": "list", "퀴즈 만들기": "create"}
    
    # 네비게이션 선택이 변경되면 페이지 상태 업데이트
    if st.session_state.page != page_map[choice]:
        st.session_state.page = page_map[choice]
        st.session_state.selected_quiz_id = None
        st.experimental_rerun()

    df = load_data(worksheet)

    if st.session_state.page == 'list':
        render_list_page(df)
    elif st.session_state.page == 'create':
        render_create_page(worksheet)
    elif st.session_state.page == 'solve':
        if st.session_state.selected_quiz_id:
            # 데이터프레임에서 최신 데이터를 다시 찾아야 할 수 있음
            if st.session_state.selected_quiz_id in df['id'].values:
                selected_quiz = df[df['id'] == st.session_state.selected_quiz_id].iloc[0]
                render_quiz_page(selected_quiz)
            else:
                st.error("퀴즈를 찾을 수 없습니다. 목록으로 돌아갑니다.")
                st.session_state.page = 'list'
                st.session_state.selected_quiz_id = None
                st.experimental_rerun()

if __name__ == "__main__":
    main()
