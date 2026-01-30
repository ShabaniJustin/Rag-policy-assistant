import uuid
from flask import Flask, request, jsonify, render_template, session
from pdfreader import read_pdf_from_file
from chunker import chunk_pages
from embedder import embed_chunks, embed_User_query
from vectorstore import store_in_pinecone, search_in_pinecone
from llm import query_llm_with_context

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'rag-policy-assistant-secret-key'

@app.route('/')
def index():
    """Serve the chatbot frontend page."""
    # Create a unique session namespace for each user
    if 'namespace' not in session:
        session['namespace'] = str(uuid.uuid4())[:8]
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    """Process uploaded PDF and store embeddings."""
    try:
        if 'pdf' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400

        pdf_file = request.files['pdf']

        if pdf_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not pdf_file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'File must be a PDF'}), 400

        # Get or create session namespace
        if 'namespace' not in session:
            session['namespace'] = str(uuid.uuid4())[:8]
        namespace = session['namespace']

        # Process PDF: read -> chunk -> embed -> store
        pages = read_pdf_from_file(pdf_file)
        chunks = chunk_pages(pages, chunk_size=900, chunk_overlap=150)
        embeddings = embed_chunks(chunks)
        store_in_pinecone(chunks, embeddings, namespace=namespace)

        session['pdf_uploaded'] = True
        session['pdf_name'] = pdf_file.filename

        return jsonify({
            'status': 'success',
            'message': f'Successfully processed {pdf_file.filename}',
            'chunks_count': len(chunks)
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process user query and return LLM response."""
    try:
        data = request.get_json()
        user_query = data.get('query', '').strip()

        if not user_query:
            return jsonify({'error': 'Query cannot be empty'}), 400

        if not session.get('pdf_uploaded'):
            return jsonify({'error': 'Please upload a PDF document first'}), 400

        namespace = session.get('namespace', '')

        # Embed the user's query
        query_vector = embed_User_query(user_query)

        # Search vector DB for matching chunks
        matched_chunks = search_in_pinecone(query_vector, namespace=namespace)

        # Generate response using LLM
        response = query_llm_with_context(user_query, matched_chunks)

        return jsonify({
            'response': response,
            'status': 'success'
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/status', methods=['GET'])
def status():
    """Get current session status."""
    return jsonify({
        'pdf_uploaded': session.get('pdf_uploaded', False),
        'pdf_name': session.get('pdf_name', None),
        'status': 'healthy'
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
