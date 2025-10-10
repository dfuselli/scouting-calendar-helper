import os

import streamlit as st

from chatbot.llm import analyze_image, model, ai_embeddings
from chatbot.prompts import chat_prompt_template
from chatbot.agent import ChatAgent
from chatbot.vector_store import (
    add_to_vector_store,
    get_chunks,
)

from langchain_core.documents.base import Document

from common.media_handler import save_uploaded_file, save_uploaded_image
from common.pdf_reader import extract_text_from_doc, convert_doc_to_images


def extract_pdf_data(pdf_doc):
    file_path = save_uploaded_file(pdf_doc)
    docs = []
    if os.getenv("USE_TEXT_DOC_ANALYSIS", "False").lower() == "true":
        docs += extract_text_from_doc(file_path)

    if os.getenv("USE_VISION_DOC_ANALYSIS", "False").lower() == "true":
        images = convert_doc_to_images(file_path)
        for i, img in enumerate(images):
            img_name = f"{pdf_doc.name}_{i + 1}.png"
            save_uploaded_image(img, img_name)
            docs.append(
                Document(page_content=analyze_image(img), metadata={"source": img_name})
            )
    return docs


def clean_extracted_pdf_data(pdf_docs):
    docs = []
    for pdf_doc in pdf_docs:
        docs += extract_pdf_data(pdf_doc)
    return docs


# Configurazione iniziale dell'app
st.set_page_config(layout="wide", page_title="Weak Risk Geo Map")
st.write(
    "<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True
)

top1col, top2col, top3col = st.columns([3, 3, 4])

with top1col:
    st.title("Document Processor")

with top2col:
    uploaded_pdf_docs = st.file_uploader(
        "Upload your PDF Files",
        accept_multiple_files=True,
    )

process_files = st.button("Process Files")

if uploaded_pdf_docs and process_files:
    with st.spinner("Processing..."):
        extracted_docs = clean_extracted_pdf_data(uploaded_pdf_docs)
        add_to_vector_store(docs=get_chunks(extracted_docs), embeddings=ai_embeddings)

    st.success("Done")

if "chat_agent" not in st.session_state:
    st.session_state.chat_agent = ChatAgent(
        prompt=chat_prompt_template,
        model=model,
        embeddings=ai_embeddings,
    )

chat_agent = st.session_state.chat_agent
chat_agent.start_conversation()
