import os
import requests
import streamlit as st
from groq import Groq
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh

# ✅ Set page config as the first Streamlit call
st.set_page_config(page_title="Inshorts-style News", layout="centered")

# Load API keys
load_dotenv()
groq_api_key = os.getenv("groq_api_key")
newsapi_key = os.getenv("newsapi_key")


# Groq client
client = Groq(api_key=groq_api_key)

# Auto-refresh every 15 minutes (15 * 60 * 1000 ms)
st_autorefresh(interval=15 * 60 * 1000, key="news_refresh")

# Streamlit UI
st.title("📰 Inshorts-Style India Financial News")
st.markdown("Summarized Indian business news with tone detection and auto-refresh every 15 mins.")

model = st.selectbox("Choose LLM Model", [
    'Llama3-8b-8192', 'Llama3-70b-8192','Mixtral-8x7b-32768','Gemma-7b-It'
])

# Tone to score mapping
tone_score_map = {
    "optimistic": 0.8,
    "fearful": 0.2,
    "neutral": 0.5,
    "excited": 0.9,
    "uncertain": 0.4,
    "positive": 0.7,
    "negative": 0.3
}

def extract_summary_and_tone(text):
    """Extract Summary and Tone from model output"""
    lines = text.strip().split("\n")
    summary = tone = ""
    for line in lines:
        if line.lower().startswith("summary:"):
            summary = line.split(":", 1)[1].strip()
        elif line.lower().startswith("tone:"):
            tone = line.split(":", 1)[1].strip().lower()
    return summary, tone

def get_tone_score(tone):
    for key in tone_score_map:
        if key in tone:
            return tone_score_map[key]
    return 0.5  # default

if st.button("Fetch News"):
    url = f"https://newsapi.org/v2/everything?q=cryptocurrency%20OR%20bitcoin%20OR%20ethereum&language=en&sortBy=publishedAt&apiKey={newsapi_key}"
    res = requests.get(url).json()

    st.json(res)
    if res.get("status") == "ok" and res.get("articles"):
        for article in res["articles"][:10]:
            title = article["title"]
            content = article.get("description") or article.get("content") or title
            source = article["source"]["name"]

            prompt = f"""
Summarize the following Indian financial news in a crisp, 60-word format like the Inshorts app.
Also analyze and report the tone/emotion of the article (e.g., optimistic, fearful, neutral, excited, uncertain).

News: {content}

Return in this format:
Summary: ...
Tone: ...
"""

            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model
            )
            result = chat_completion.choices[0].message.content.strip()
            summary, tone = extract_summary_and_tone(result)
            tone_score = get_tone_score(tone)

            # Display block
            with st.container():
                st.markdown(f"### 📌 {title}")
                st.markdown(f"**Summary:** {summary}")
                st.markdown(f"**Tone:** `{tone.capitalize()}`")

                # Sentiment bar
                st.progress(tone_score, text=f"Tone Score: {tone_score:.0%}")

                st.markdown(f"🔗 [Read Full Article]({article.get('url', '#')})")
                st.markdown("---")
    else:
        st.warning("No financial news found or API limit exceeded.")
