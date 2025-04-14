import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv
from newsapi import NewsApiClient
from sentence_transformers import SentenceTransformer
import chromadb
import numpy as np

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
news_api_key = os.getenv("NEWS_API_KEY")

st.sidebar.title("GROQ RAG Chatbot")
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
def load_chroma_db():
    return chromadb.Chroma()

chroma_db = load_chroma_db()
collection_name = "financial_news"

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


if st.session_state.financial_news is None:
    with st.spinner(f"Fetching latest financial news about '{st.session_state.news_topic}'..."):
        try:
            news = news_api.get_everything(q=st.session_state.news_topic, language='en', sort_by='relevancy', page_size=5)
            if news['status'] == 'ok' and news['totalResults'] > 0:
                st.session_state.financial_news = news['articles']
                # Index the news articles in ChromaDB
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
                    if collection_name in chroma_db.list_collections():
                        collection = chroma_db.get_collection(name=collection_name)
                    else:
                        collection = chroma_db.create_collection(name=collection_name)
                    documents = [item[2]['content'] for item in vectors_to_upsert]
                    embeddings = [item[1] for item in vectors_to_upsert]
                    metadatas = [item[2] for item in vectors_to_upsert]
                    ids = [item[0] for item in vectors_to_upsert]
                    collection.add(
                        documents=documents,
                        embeddings=embeddings,
                        metadatas=metadatas,
                        ids=ids
                    )
                    st.success(f"Indexed {len(vectors_to_upsert)} news articles in ChromaDB.")
                else:
                    st.warning("No relevant news content to index.")
            else:
                st.error(f"Error fetching financial news: {news['message']}")
        except Exception as e:
            st.error(f"An error occurred: {e}")

#scrollable news display
if st.session_state.financial_news:
    st.subheader(f"Latest Financial News about '{st.session_state.news_topic}':")
    news_display = ""
    for i, article in enumerate(st.session_state.financial_news):
        news_display += f"**{i+1}. [{article['title']}]({article['url']})**\n"
        news_display += f"*Source: {article['source']['name']}*\n"
        news_display += f"{article['description'] if article['description'] else 'No description available.'}\n"
        news_display += "---\n"

    st.markdown(f"""
        <div style="height: 300px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px;">
            {news_display}
        </div>
    """, unsafe_allow_html=True)

    st.session_state.start_chat = st.checkbox("Start Chatting about this News")


# Chatbot interface (only shows if start_chat is True)
if st.session_state.start_chat and st.session_state.financial_news:
    st.subheader("Chat with the Financial News Chatbot")
    user_chat_input = st.text_input("Ask me anything about this news:", "")

    if st.button("Send Chat"):
        if user_chat_input:
            with st.spinner("Searching news and generating response..."):
                try:
                    # Embed the user's query
                    query_embedding = embedding_model.encode(user_chat_input)

                    # Query ChromaDB for relevant articles
                    if collection_name in chroma_db.list_collections():
                        collection = chroma_db.get_collection(name=collection_name)
                        results = collection.query(
                            query_embeddings=[query_embedding.tolist()],
                            n_results=2,  # Retrieve top 2 most relevant articles
                            include=["metadatas", "documents"]
                        )

                        if results and results['documents']:
                            context = ""
                            for i in range(len(results['documents'][0])):
                                metadata = results['metadatas'][0][i]
                                content = results['documents'][0][i]
                                context += f"Title: {metadata['title']}\nSource: {metadata['source']}\nContent: {content}\nURL: {metadata['url']}\n\n"

                            # --- Chatbot Prompt with RAG from ChromaDB ---
                            chat_prompt = f"You are a financial news expert. Answer the user's questions based on the following context:\n\n{context}\n\nUser's question: {user_chat_input}"

                            st.session_state.chat_history.append({"role": "user", "content": user_chat_input})

                            chat_completion = client.chat.completions.create(
                                messages=[
                                    {
                                        "role": "user",
                                        "content": chat_prompt,
                                    }
                                ],
                                model=model,
                            )
                            response = chat_completion.choices[0].message.content
                            st.session_state.chat_history.append({"role": "assistant", "content": response})
                        else:
                            response = "No relevant information found in the news to answer your question."
                            st.session_state.chat_history.append({"role": "assistant", "content": response})
                    else:
                        st.warning("ChromaDB collection not found.")

                except Exception as e:
                    st.error(f"An error occurred during chat: {e}")

# chat history
st.sidebar.title("Chat History")
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.sidebar.markdown(f'<div style="padding: 8px; margin-bottom: 5px; border-radius: 5px; background-color: #e1f1ff;">👤 **You:** {message["content"]}</div>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown(f'<div style="padding: 8px; margin-bottom: 5px; border-radius: 5px; background-color: #f0f0f0;">🤖 **Bot:** {message["content"]}</div>', unsafe_allow_html=True)


#st response box
st.markdown(
    """
    <style>
    .response-box {
        background-color: #ffffff; /* White background */
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        border: 1px solid #d3d3d3; /* Light gray border */
        box-shadow: 2px 2px 5px #e0e0e0; /* Subtle shadow */
        white-space: pre-wrap; /* Preserve formatting like newlines */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.start_chat and st.session_state.financial_news:
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.markdown(f'<div style="padding: 10px; margin-bottom: 10px; border-radius: 5px; background-color: #e1f1ff;">👤 **You:** {message["content"]}</div>', unsafe_allow_html=True)
        elif message["role"] == "assistant":
            st.markdown(f'<div class="response-box">{message["content"]}</div>', unsafe_allow_html=True)