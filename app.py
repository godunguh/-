import streamlit as st
import pandas as pd

# 페이지 설정
st.set_page_config(
    page_title="나만의 퀴즈 앱",
    page_icon="❓",
)

# CSV 파일에서 퀴즈 데이터 불러오기
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("quiz.csv")
        return df
    except FileNotFoundError:
        st.error("'quiz.csv' 파일을 찾을 수 없습니다. 같은 폴더에 파일이 있는지 확인해주세요.")
        return None

def main():
    st.title("나만의 퀴즈 애플리케이션")
    st.write("퀴즈를 풀고 당신의 지식을 시험해보세요!")

    quiz_df = load_data()

    if quiz_df is not None:
        # 사용자의 답변을 저장할 딕셔너리
        user_answers = {}
        
        # 퀴즈 문제 표시
        for index, row in quiz_df.iterrows():
            st.subheader(f"문제 {index + 1}: {row['question']}")
            options = [row['option1'], row['option2'], row['option3'], row['option4']]
            user_answers[index] = st.radio(
                "답을 선택하세요:",
                options,
                key=f"q{index}"
            )

        # 채점 버튼
        if st.button("채점하기"):
            score = 0
            correct_answers = []
            
            st.subheader("결과")
            for index, row in quiz_df.iterrows():
                correct_answer = row['answer']
                user_answer = user_answers[index]
                
                if user_answer == correct_answer:
                    score += 1
                    st.success(f"문제 {index + 1}: 정답입니다! (정답: {correct_answer})")
                else:
                    st.error(f"문제 {index + 1}: 오답입니다. (정답: {correct_answer}, 선택한 답: {user_answer})")
            
            st.markdown(f"### 총 점수: **{len(quiz_df)}점 만점에 {score}점**")

if __name__ == "__main__":
    main()