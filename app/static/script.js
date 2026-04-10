document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const documentList = document.getElementById('document-list');
    const queryForm = document.getElementById('query-form');
    const queryInput = document.getElementById('query-input');
    const chatMessages = document.getElementById('chat-messages');
    const sendBtn = document.getElementById('send-btn');

    // Load initial documents
    fetchDocuments();
    setInterval(fetchDocuments, 5000); // Poll for status updates

    // --- File Upload Logic ---

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    ['dragleave', 'drop'].forEach(event => {
        dropZone.addEventListener(event, () => dropZone.classList.remove('drag-over'));
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        const files = e.dataTransfer.files;
        if (files.length > 0) handleFileUpload(files[0]);
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) handleFileUpload(fileInput.files[0]);
    });

    async function handleFileUpload(file) {
        if (!file.name.endsWith('.pdf')) {
            showNotification('Only PDF files are supported', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        showNotification('Uploading document...', 'info');

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.error) {
                showNotification(data.error, 'error');
            } else {
                showNotification('Upload successful! Processing...', 'success');
                fetchDocuments();
            }
        } catch (error) {
            showNotification('Upload failed. Please try again.', 'error');
            console.error('Upload error:', error);
        }
    }

    // --- Document List Logic ---

    async function fetchDocuments() {
        try {
            const response = await fetch('/documents');
            const docs = await response.json();
            renderDocumentList(docs);
        } catch (error) {
            console.error('Error fetching documents:', error);
        }
    }

    function renderDocumentList(docs) {
        if (docs.length === 0) {
            documentList.innerHTML = '<p class="empty-state">No documents uploaded yet.</p>';
            return;
        }

        documentList.innerHTML = docs.map(doc => `
            <div class="doc-item">
                <div class="doc-info">
                    <span class="doc-status status-${doc.status.toLowerCase()}"></span>
                    <span class="doc-name" title="${doc.filename}">${doc.filename}</span>
                </div>
                <span style="font-size: 0.7rem; color: var(--text-muted)">${doc.status}</span>
                <button class="delete-btn" onclick="deleteDocument(${doc.id}, '${doc.filename}')" title="Delete document">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        <line x1="10" y1="11" x2="10" y2="17"></line>
                        <line x1="14" y1="11" x2="14" y2="17"></line>
                    </svg>
                </button>
            </div>
        `).join('');
    }

    window.deleteDocument = async function (id, filename) {
        if (!confirm(`Are you sure you want to delete "${filename}"? This will remove it from the knowledge base permanently.`)) {
            return;
        }

        try {
            const response = await fetch(`/documents/${id}`, {
                method: 'DELETE'
            });
            const data = await response.json();

            if (data.error) {
                showNotification(data.error, 'error');
            } else {
                showNotification('Document deleted successfully', 'success');
                fetchDocuments();
            }
        } catch (error) {
            showNotification('Failed to delete document', 'error');
            console.error('Delete error:', error);
        }
    }

    // --- Chat Logic ---

    queryForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = queryInput.value.trim();
        if (!query) return;

        // Add user message
        addMessage(query, 'user');
        queryInput.value = '';

        // Add loading indicator
        const loadingId = addLoadingMessage();

        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            });
            const data = await response.json();

            removeLoadingMessage(loadingId);

            if (data.error) {
                addMessage('Sorry, an error occurred: ' + data.error, 'bot');
            } else {
                addMessage(data.answer, 'bot', data.sources);
            }
        } catch (error) {
            removeLoadingMessage(loadingId);
            addMessage('Failed to connect to the server.', 'bot');
            console.error('Query error:', error);
        }
    });

    function addMessage(text, sender, sources = []) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;

        let content = text;
        if (sources && sources.length > 0) {
            content += '<div class="sources"><small>Sources: ' +
                [...new Set(sources.map(s => s.filename))].join(', ') +
                '</small></div>';
        }

        messageDiv.innerHTML = content;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addLoadingMessage() {
        const id = 'loading-' + Date.now();
        const loadingDiv = document.createElement('div');
        loadingDiv.id = id;
        loadingDiv.className = 'message bot-message loading-dots';
        loadingDiv.innerHTML = 'Thinking<span>.</span><span>.</span><span>.</span>';
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return id;
    }

    function removeLoadingMessage(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function showNotification(text, type) {
        const container = document.getElementById('notification-container');
        const notif = document.createElement('div');
        notif.className = `notification ${type}`;
        notif.innerText = text;
        container.appendChild(notif);

        setTimeout(() => {
            notif.style.opacity = '0';
            setTimeout(() => notif.remove(), 500);
        }, 3000);
    }
});
