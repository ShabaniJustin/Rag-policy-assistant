document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chatForm');
    const userInput = document.getElementById('userInput');
    const chatMessages = document.getElementById('chatMessages');
    const sendButton = document.getElementById('sendButton');
    const statusIndicator = document.getElementById('statusIndicator');
    const headerSubtext = document.getElementById('headerSubtext');

    // Upload elements
    const uploadSection = document.getElementById('uploadSection');
    const welcomeMessage = document.getElementById('welcomeMessage');
    const uploadBtn = document.getElementById('uploadBtn');
    const pdfInput = document.getElementById('pdfInput');
    const uploadArea = document.getElementById('uploadArea');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const uploadStatus = document.getElementById('uploadStatus');
    const uploadNewBtn = document.getElementById('uploadNewBtn');

    let pdfUploaded = false;

    // Check if PDF was already uploaded in this session
    checkStatus();

    // Upload button click
    uploadBtn.addEventListener('click', () => pdfInput.click());

    // File input change
    pdfInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadPDF(e.target.files[0]);
        }
    });

    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file && file.type === 'application/pdf') {
            uploadPDF(file);
        } else {
            alert('Please upload a PDF file');
        }
    });

    // Upload new PDF button
    if (uploadNewBtn) {
        uploadNewBtn.addEventListener('click', () => {
            pdfInput.click();
        });
    }

    // Auto-resize textarea
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });

    // Handle Enter key (Shift+Enter for new line)
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // Handle form submission
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const query = userInput.value.trim();

        if (!query || !pdfUploaded) return;

        // Hide welcome message on first query
        if (welcomeMessage && welcomeMessage.style.display !== 'none') {
            welcomeMessage.style.display = 'none';
        }

        // Add user message
        addMessage(query, 'user');

        // Clear input
        userInput.value = '';
        userInput.style.height = 'auto';

        // Disable input while processing
        setInputState(false);

        // Show typing indicator
        const typingIndicator = addTypingIndicator();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: query })
            });

            const data = await response.json();

            // Remove typing indicator
            typingIndicator.remove();

            if (data.response) {
                addMessage(data.response, 'bot');
            } else {
                addErrorMessage(data.error || 'An error occurred. Please try again.');
            }
        } catch (error) {
            typingIndicator.remove();
            addErrorMessage('Failed to connect to the server. Please make sure the server is running.');
            updateStatus('offline');
        }

        // Re-enable input
        setInputState(true);
        userInput.focus();
    });

    async function uploadPDF(file) {
        // Show progress
        uploadArea.style.display = 'none';
        uploadProgress.style.display = 'block';
        progressFill.style.width = '30%';
        uploadStatus.textContent = 'Reading PDF...';

        const formData = new FormData();
        formData.append('pdf', file);

        try {
            progressFill.style.width = '60%';
            uploadStatus.textContent = 'Processing and embedding...';

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.status === 'success') {
                progressFill.style.width = '100%';
                uploadStatus.textContent = 'Done!';

                setTimeout(() => {
                    pdfUploaded = true;
                    enableChat(file.name);
                }, 500);
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        } catch (error) {
            uploadProgress.style.display = 'none';
            uploadArea.style.display = 'flex';
            addErrorMessage('Failed to upload PDF: ' + error.message);
        }
    }

    function enableChat(fileName) {
        uploadSection.style.display = 'none';
        welcomeMessage.style.display = 'block';

        userInput.disabled = false;
        userInput.placeholder = 'Ask a question about your document...';
        sendButton.disabled = false;

        headerSubtext.textContent = `Chatting about: ${fileName}`;
        userInput.focus();
    }

    function checkStatus() {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                if (data.pdf_uploaded) {
                    pdfUploaded = true;
                    enableChat(data.pdf_name || 'your document');
                }
                updateStatus('online');
            })
            .catch(() => {
                updateStatus('offline');
            });
    }

    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';

        if (sender === 'user') {
            avatarDiv.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                </svg>
            `;
        } else {
            avatarDiv.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
            `;
        }

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = text;

        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addTypingIndicator() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot';
        messageDiv.id = 'typingIndicator';

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
        `;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = `
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;

        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;

        return messageDiv;
    }

    function addErrorMessage(text) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = text;
        chatMessages.appendChild(errorDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function setInputState(enabled) {
        userInput.disabled = !enabled;
        sendButton.disabled = !enabled;
    }

    function updateStatus(status) {
        const statusDot = statusIndicator.querySelector('.status-dot');
        const statusText = statusIndicator.querySelector('.status-text');

        if (status === 'offline') {
            statusDot.style.background = '#ef4444';
            statusText.textContent = 'Offline';
        } else {
            statusDot.style.background = '#4ade80';
            statusText.textContent = 'Online';
        }
    }

    // Expose function for suggestion chips
    window.sendSuggestion = function(text) {
        userInput.value = text;
        chatForm.dispatchEvent(new Event('submit'));
    };
});
