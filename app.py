import os
from dataclasses import dataclass, field

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_TRIES = 3

st.set_page_config(
    page_title="Exegesis AI – Socratic Tutor",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)


@dataclass
class TutorSession:
    question: str
    hints: list[str] = field(default_factory=list)
    attempts: list[str] = field(default_factory=list)
    completed: bool = False
    failed: bool = False


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def ask_model(client, instructions: str, prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Groq returned an empty response.")
    return content.strip()


def create_hint(client, session: TutorSession) -> str:
    previous_hints = "\n".join(f"- {hint}" for hint in session.hints) or "(none)"
    previous_attempts = "\n".join(f"- {attempt}" for attempt in session.attempts) or "(none)"

    hint = ask_model(
        client,
        instructions=(
            "You are a Socratic tutor. Help the learner solve the question, but do "
            "not reveal the answer, a completed solution, or wording that makes the "
            "answer obvious. Give exactly one concise hint. Each new hint must use a "
            "different approach and be more specific than earlier hints. Address "
            "mistakes visible in the learner's attempts."
        ),
        prompt=(
            f"Question:\n{session.question}\n\n"
            f"Previous hints:\n{previous_hints}\n\n"
            f"Learner attempts:\n{previous_attempts}\n\n"
            "Give the next distinct hint only."
        ),
    )
    session.hints.append(hint)
    return hint


def is_correct(client, session: TutorSession, attempt: str) -> bool:
    verdict = ask_model(
        client,
        instructions=(
            "Judge whether the learner's answer is substantively correct for the "
            "question. Accept equivalent wording and reasonable rounding. Respond "
            "with exactly CORRECT or INCORRECT and nothing else."
        ),
        prompt=f"Question:\n{session.question}\n\nLearner answer:\n{attempt}",
    )
    return verdict.upper().strip() == "CORRECT"


def explain_answer(client, session: TutorSession) -> str:
    attempts = "\n".join(f"- {attempt}" for attempt in session.attempts)
    return ask_model(
        client,
        instructions=(
            "You are a patient tutor. The learner has used all three tries. Give the "
            "correct answer, explain it clearly step by step, and briefly point out "
            "the key misunderstanding in the learner's attempts. Keep the response "
            "focused and encouraging."
        ),
        prompt=f"Question:\n{session.question}\n\nLearner's three attempts:\n{attempts}",
    )


st.title("🎓 Exegesis AI – Socratic Tutor")
st.markdown(
    "<div style='padding: 0.5rem 0 1.2rem 0; font-size: 1.02rem; color: #dfe7f5;'>"
    "Test your knowledge. The AI tutor gives progressive hints instead of revealing the answer immediately."
    "</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("How it works")
    st.markdown(
        "1. Enter a question.\n"
        "2. Receive a first hint.\n"
        "3. Submit up to 3 answers.\n"
        "4. Learn from guided explanations when you miss the goal."
    )

client = get_groq_client()
if not client:
    st.error("⚠️ `GROQ_API_KEY` is not set. Add it to your environment or `.env` file before running the app.")
    st.code(
        "GROQ_API_KEY=your_api_key_here\nGROQ_MODEL=llama-3.3-70b-versatile",
        language="dotenv",
    )
    st.stop()

if "session" not in st.session_state:
    st.session_state.session = None

question_input = st.text_input(
    "What question would you like to study?",
    placeholder="e.g., What is the derivative of x^3 * sin(x)?",
)

if st.button("Start Tutor Session") and question_input.strip():
    st.session_state.session = TutorSession(question=question_input.strip())
    try:
        create_hint(client, st.session_state.session)
    except Exception as exc:
        st.error(f"Unable to start the tutor: {exc}")
        st.session_state.session = None
    else:
        st.rerun()

session = st.session_state.session

if session:
    st.markdown("---")
    st.subheader(f"Question: {session.question}")

    if session.hints:
        for index, hint in enumerate(session.hints, start=1):
            st.info(f"**Hint {index}:** {hint}")

    if session.attempts:
        for attempt_index, attempt in enumerate(session.attempts, start=1):
            badge = "✅ Correct" if attempt_index == len(session.attempts) and session.completed else "📝 Attempt"
            st.write(f"{badge} **Attempt {attempt_index}:** {attempt}")

    if not session.completed and not session.failed:
        current_try = len(session.attempts) + 1
        st.markdown(f"**Attempt {current_try} of {MAX_TRIES}**")

        with st.form(key=f"attempt_form_{len(session.attempts)}"):
            user_answer = st.text_input("Your answer:", key=f"answer_{len(session.attempts)}")
            submit_button = st.form_submit_button("Submit Answer")

            if submit_button:
                answer = user_answer.strip() if user_answer.strip() else "(The learner did not provide an answer.)"
                session.attempts.append(answer)

                try:
                    verdict = is_correct(client, session, answer)
                except Exception as exc:
                    st.error(f"The tutor could not grade your answer right now: {exc}")
                    session.attempts.pop()
                    st.stop()

                if verdict:
                    session.completed = True
                    st.rerun()
                else:
                    if len(session.attempts) >= MAX_TRIES:
                        session.failed = True
                        st.rerun()
                    else:
                        try:
                            create_hint(client, session)
                        except Exception as exc:
                            st.warning(f"A new hint could not be generated: {exc}")
                        st.rerun()

    if session.completed:
        st.success("🎉 Correct! You worked it out.")
        st.balloons()
        if st.button("Start a New Question"):
            st.session_state.session = None
            st.rerun()

    if session.failed:
        st.error("You've used all 3 attempts.")
        with st.spinner("Generating full explanation..."):
            try:
                explanation = explain_answer(client, session)
            except Exception as exc:
                st.error(f"Could not generate the explanation: {exc}")
                explanation = "Please try again in a moment."
        st.markdown("### 📚 Full Explanation")
        st.write(explanation)

        if st.button("Try Another Question"):
            st.session_state.session = None
            st.rerun()

else:
    st.info("Enter a question above to begin your tutoring session.")


st.markdown("<div style='margin-top: 2rem; color: #9fb3d1; text-align: center;'>Powered by Groq</div>", unsafe_allow_html=True)
