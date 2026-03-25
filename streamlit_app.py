import streamlit as st
import uuid
from pdfreader import read_pdf_from_file
from chunker import chunk_pages
from embedder import embed_chunks, embed_User_query
from vectorstore import store_in_pinecone, search_in_pinecone
from llm import query_llm_with_context
from guardrails import validate_input, validate_output, log_successful_interaction

# Page config
st.set_page_config(
    page_title="RAG Policy Assistant",
    page_icon="💬",
    layout="centered"
)

# Initialize session state
if "namespace" not in st.session_state:
    st.session_state.namespace = str(uuid.uuid4())[:8]
if "pdf_processed" not in st.session_state:
    st.session_state.pdf_processed = False
if "messages" not in st.session_state:
    st.session_state.messages = []

# Header
st.title("RAG Policy Assistant")
st.caption("Upload a PDF and ask questions about its content")

# Sidebar for PDF upload
with st.sidebar:
    st.header("Upload Document")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file is not None:
        if st.button("Process PDF", type="primary"):
            with st.spinner("Processing PDF..."):
                try:
                    # Read PDF
                    pages = read_pdf_from_file(uploaded_file)

                    # Chunk the text
                    chunks = chunk_pages(pages, chunk_size=900, chunk_overlap=150)

                    # Create embeddings
                    embeddings = embed_chunks(chunks)

                    # Store in Pinecone
                    store_in_pinecone(chunks, embeddings, namespace=st.session_state.namespace)

                    st.session_state.pdf_processed = True
                    st.session_state.pdf_name = uploaded_file.name
                    st.success(f"Processed {len(chunks)} chunks from {uploaded_file.name}")
                except Exception as e:
                    st.error(f"Error processing PDF: {str(e)}")

    if st.session_state.pdf_processed:
        st.divider()
        st.success(f"Current document: {st.session_state.get('pdf_name', 'Unknown')}")
        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

# Main chat area
if not st.session_state.pdf_processed:
    st.info("Please upload and process a PDF document to start chatting.")
else:
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask a question about your document..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # ── G1: Input guardrail ──────────────────────────────
                    input_check = validate_input(prompt)
                    if not input_check["allowed"]:
                        reply = f"⚠️ {input_check['reason']}"
                        st.warning(reply)
                        st.session_state.messages.append({"role": "assistant", "content": reply})
                        st.stop()

                    # Embed query
                    query_vector = embed_User_query(prompt)

                    # Search for relevant chunks
                    matched_chunks = search_in_pinecone(
                        query_vector,
                        namespace=st.session_state.namespace
                    )

                    # Generate response (G2 context check runs inside llm.py)
                    response = query_llm_with_context(prompt, matched_chunks)

                    # ── G3: Output guardrail ─────────────────────────────
                    output_check = validate_output(response, prompt)
                    if not output_check["safe"]:
                        reply = output_check["response"]
                        st.warning(reply)
                        st.session_state.messages.append({"role": "assistant", "content": reply})
                        st.stop()

                    # ── G4: Log clean interaction ────────────────────────
                    log_successful_interaction(prompt, output_check["response"], output_check["flags"])

                    st.markdown(output_check["response"])
                    st.session_state.messages.append({"role": "assistant", "content": output_check["response"]})
                except Exception as e:
                    st.error(f"Error: {str(e)}")
