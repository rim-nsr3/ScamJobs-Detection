import streamlit as st
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
import google.generativeai as genai
from scipy.sparse import hstack
import os
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# Access the API key
api_key = os.getenv("API_KEY")

# Load your trained models and vectorizer
log_model = joblib.load("data/logistic_model.pkl")
rf_model = joblib.load("data/random_forest.pkl")
dt_model = joblib.load("data/decision_tree.pkl")
vectorizer = joblib.load("data/tfidf_vectorizer.pkl")

# Gemini API setup (make sure to install `google-generativeai`)
genai.configure(api_key=st.secrets["API_KEY"])

st.title("🔍 Scam Job Detector")
job_text = st.text_area("Paste a job description:", height=200)

if st.button("Predict"):
    if job_text.strip() == "":
        st.warning("Please enter a job description.")
    else:
        features = vectorizer.transform([job_text])

        def get_suspicious_features(text):
            suspicious_keywords = ["daily payout", "quick hire", "easy job", "work from home", "no experience"]
            vague_words = ["flexible", "competitive", "negotiable", "ASAP", "great opportunity"]

            text_lower = text.lower()
            suspicious_score = sum(word in text_lower for word in suspicious_keywords)
            is_vague = any(word in text_lower for word in vague_words)

            return np.array([[suspicious_score, int(is_vague)]])


        tfidf_features = vectorizer.transform([job_text])
        numeric_features = get_suspicious_features(job_text)

        # Combine just like training
        combined_features = hstack([tfidf_features, numeric_features])

        # Make predictions
        preds = {
            "Logistic Regression": log_model.predict(combined_features)[0],
            "Random Forest": rf_model.predict(combined_features)[0],
            "Decision Tree": dt_model.predict(combined_features)[0]
        }

        # Display predictions
        for name, pred in preds.items():
            label = "⚠️ Scam" if pred == 1 else "✅ Legit"
            st.write(f"**{name}**: {label}")

        # Ask Gemini to explain
        prompt = f"""This job description was pasted into a real or scam classifier:
        
\"{job_text}\"

Can you explain why this might be considered a scam or a real authentic job, based on phrasing, red flags, or lack of professionalism. Most jobs posted are going to be real."""

        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        response = model.generate_content(prompt)
        st.subheader("🧠 AI Explanation")
        st.write(response.text)
