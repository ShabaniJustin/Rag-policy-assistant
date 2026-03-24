import uuid
from flask import Flask, request, jsonify, render_template, session
from pdfreader import read_pdf_from_file
from chunker import chunk_pages
from embedder import embed_chunks, embed_User_query
from vectorstore import store_in_pinecone, search_in_pinecone
from llm import query_llm_with_context
from guardrails import validate_input, validate_output, log_successful_interaction

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

        # ── G1: Input guardrail — file size check ─────────────────────
        pdf_file.seek(0, 2)          # seek to end
        file_size = pdf_file.tell()
        pdf_file.seek(0)             # reset to beginning
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': 'File too large. Maximum size is 10 MB.'}), 400

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
        
         # ── G1: Input guardrail ──────────────────────────────────────
        input_check = validate_input(user_query)
        if not input_check["allowed"]:
            return jsonify({
                'response': f"⚠️ {input_check['reason']}",
                'status': 'blocked',
                'guardrail': 'input'
            }), 200   # 200 so frontend renders it as a chat message

        namespace = session.get('namespace', '')

        # Embed the user's query
        query_vector = embed_User_query(user_query)

        # Search vector DB for matching chunks
        matched_chunks = search_in_pinecone(query_vector, namespace=namespace)

        # ── G2: Context guardrail ────────────────────────────────────
        from guardrails import validate_context
        context_check = validate_context(matched_chunks)
        if not context_check["sufficient"]:
            return jsonify({
                'response': f"ℹ️ {context_check['reason']}",
                'status': 'no_context',
                'guardrail': 'context'
            }), 200

        # Generate response using LLM
        response = query_llm_with_context(user_query, matched_chunks)

        # ── G3: Output guardrail ─────────────────────────────────────
        output_check = validate_output(response, user_query)
        if not output_check["safe"]:
            return jsonify({
                'response': output_check["response"],
                'status': 'output_blocked',
                'guardrail': 'output'
            }), 200

        # ── G4: Log clean interaction ────────────────────────────────
        log_successful_interaction(user_query, output_check["response"], output_check["flags"])

        return jsonify({
            'response': output_check["response"],
            'status': 'success',
            'flags': output_check["flags"]       # visible in browser devtools for demo
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
