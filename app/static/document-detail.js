// Document Detail Page JavaScript
const API_BASE = '';

let documentId = null;
let chatHistory = [];

// DOM Elements
const documentInfo = document.getElementById('documentInfo');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get document ID from URL
    const params = new URLSearchParams(window.location.search);
    documentId = params.get('id');

    if (!documentId) {
        showToast('No document ID provided', 'error');
        setTimeout(() => window.location.href = '/', 2000);
        return;
    }

    loadDocument();
    initializeChatListeners();
});

function initializeChatListeners() {
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

async function loadDocument() {
    try {
        const response = await fetch(`${API_BASE}/document/${documentId}`);

        if (!response.ok) {
            throw new Error('Failed to load document');
        }

        const document = await response.json();
        displayDocumentInfo(document);

    } catch (error) {
        console.error('Load error:', error);
        documentInfo.innerHTML = '<p class="error">Failed to load document</p>';
        showToast(`Error: ${error.message}`, 'error');
    }
}

function displayDocumentInfo(document) {
    const metadata = document.metadata || {};

    documentInfo.innerHTML = `
        <div class="info-section">
            <h3>Basic Information</h3>
            <div class="info-item">
                <span class="info-label">Document ID:</span>
                <span class="info-value">${document.id}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Category:</span>
                <span class="badge ${metadata.category}">${formatCategory(metadata.category)}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Urgency:</span>
                <span class="badge ${metadata.urgency}">${metadata.urgency?.toUpperCase() || 'N/A'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Filename:</span>
                <span class="info-value">${metadata.filename || 'Unknown'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Processed:</span>
                <span class="info-value">${formatDate(metadata.processed_at)}</span>
            </div>
        </div>
        
        ${metadata.customer_id ? `
            <div class="info-section">
                <h3>Customer Details</h3>
                <div class="info-item">
                    <span class="info-label">Customer ID:</span>
                    <span class="info-value">${metadata.customer_id}</span>
                </div>
            </div>
        ` : ''}
        
        <div class="info-section">
            <h3>Document Preview</h3>
            <div class="document-preview">
                ${document.document ? document.document.substring(0, 500) + '...' : 'No content available'}
            </div>
        </div>
    `;
}

async function sendMessage() {
    const message = chatInput.value.trim();

    if (!message) return;

    // Add user message to chat
    addMessageToChat('user', message);
    chatInput.value = '';

    // Disable input while processing
    const btnText = sendBtn.querySelector('.btn-text');
    const spinner = sendBtn.querySelector('.spinner');
    sendBtn.disabled = true;
    chatInput.disabled = true;
    btnText.textContent = 'Thinking...';
    spinner.hidden = false;

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: message,
                document_id: documentId,
                chat_history: chatHistory
            })
        });

        if (!response.ok) {
            throw new Error('Chat request failed');
        }

        const data = await response.json();

        // Add to chat history
        chatHistory.push({ role: 'user', content: message });
        chatHistory.push({ role: 'assistant', content: data.response });

        // Add assistant response to chat
        addMessageToChat('assistant', data.response);

    } catch (error) {
        console.error('Chat error:', error);
        showToast(`Error: ${error.message}`, 'error');
        addMessageToChat('assistant', 'Sorry, I encountered an error. Please try again.');
    } finally {
        // Re-enable input
        sendBtn.disabled = false;
        chatInput.disabled = false;
        btnText.textContent = 'Send';
        spinner.hidden = true;
        chatInput.focus();
    }
}

function addMessageToChat(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.innerHTML = `
        <div class="message-content">
            ${formatMessageContent(content)}
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatMessageContent(content) {
    // Simple markdown-like formatting
    return content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
}

function formatCategory(category) {
    if (!category) return 'Unknown';
    return category
        .replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

