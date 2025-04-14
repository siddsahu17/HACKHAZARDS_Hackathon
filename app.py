import os
import streamlit as st 
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
groq_api_key = os.getenv("groq_api_key")
news_api_key = os.getenv("news_api_key")

st.sidebar.title("GROQ RAG Chatbot")
# prompt = st.sidebar.title("System Prompt: ")
model = st.sidebar.selectbox(
    "Choose The Model", ['Llama3-8b-8192', 'Llama3-70b-8192','Mixtral-8x7b-32768','Gemma-7b-It']
)

# groq client
client = Groq(api_key=groq_api_key)

@st.cache_resource
def load_news_api():
    return NewsApiClient(api_key=news_api_key)

news_api = load_news_api(news_api_key)

@st.cache_resource
def load_embedding_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

embedding_model = load_embedding_model()

@st.cache_resource
def init_pinecone(api_key, environment):
    pinecone.init(api_key=api_key, environment=environment)

init_pinecone(pinecone_api_key, pinecone_environment)

# Streamlit Interface
st.title("GROQ RAG Chatbot")


# Initialize sessesion state for history
if "financial_news" not in st.session_state:
    st.session_state.financial_news = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "start_chat" not in st.session_state:
    st.session_state.start_chat = False
if "news_topic" not in st.session_state:
    st.session_state.news_topic = "finance,Crypto,Economy,Markets"
if "news_language" not in st.session_state:
    st.session_state.news_language = "en"
if "news_country" not in st.session_state:
    st.session_state.news_country = "global"
if "pinecone_index" not in st.session_state:
    try:
        st.session_state.pinecone_index = pinecone.Index(pinecone_index_name)
        st.info(f"Connected to Pinecone index: {pinecone_index_name}")
    except Exception as e:
        st.error(f"Error connecting to Pinecone index '{pinecone_index_name}': {e}")
        st.session_state.pinecone_index = None

    
if st.session_state.financial_news is None:
    with st.spinner(f"Fetching latest financial news about '{st.session_state.news_topic}'..."):
        try:
            news = news_client.get_everything(q=st.session_state.news_topic, language='en', sort_by='relevancy', page_size=5)
            if news['status'] == 'ok' and news['totalResults'] > 0:
                st.session_state.financial_news = news['articles']
                # Index the news articles in Pinecone
                if st.session_state.pinecone_index:
                    vectors_to_upsert = []
                    for i, article in enumerate(st.session_state.financial_news):
                        content = article.get('content') or article.get('description')
                        if content:
                            embedding = embedding_model.encode(content)
                            article_id = f"news-{i}"
                            metadata = {
                                "title": article.get('title'),
                                "source": article['source']['name'],
                                "url": article.get('url'),
                                "content": content,
                            }
                            vectors_to_upsert.append((article_id, embedding.tolist(), metadata))

                    if vectors_to_upsert:
                        st.session_state.pinecone_index.upsert(vectors=vectors_to_upsert)
                        st.success(f"Indexed {len(vectors_to_upsert)} news articles in Pinecone.")
                    else:
                        st.warning("No relevant news content to index.")
            else:
                st.error(f"Error fetching financial news: {news['message']}")
        except Exception as e:
            st.error(f"An error occurred: {e}")
            