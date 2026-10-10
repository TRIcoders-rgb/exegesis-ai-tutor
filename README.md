# Exegesis AI Tutor

This project is a Streamlit-based Socratic tutor that asks one question, gives progressive hints, and keeps the learner solving instead of giving the answer immediately.

## Features

- Question-based tutoring flow
- Up to 3 guided attempts
- Progressive hints that adapt to previous mistakes
- AI-powered answer checking
- Full explanation after all attempts are used

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Add your Groq API key to a `.env` file:

   ```env
   GROQ_API_KEY=your_api_key_here
   GROQ_MODEL=llama-3.3-70b-versatile
   ```

4. Start the app:

   ```bash
   streamlit run app.py
   ```

## Files

- `app.py` – Main Streamlit app
- `.env.example` – Example environment configuration
- `requirements.txt` – Python dependencies

## Notes

This app uses Groq's API for tutoring and grading. If you do not have a Groq API key, the app will not run until that key is set.
