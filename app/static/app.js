// API Base URL
const API_BASE = '';

// State
let currentFile = null;
let recentDocuments = [];

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const resultsSection = document.getElementById('resultsSection');
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    loadRecentDocuments();
});

function initializeEventListeners() {
    // Upload area click
    uploadArea.addEventListener('click', () => fileInput.click());

    // File input change
    fileInput.addEventListener('change', handleFileSelect);

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
        if (file) {
            handleFile(file);
        }
    });

    // Upload button
    uploadBtn.addEventListener('click', handleUpload);

    // Search
    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
}

function handleFile(file) {
    // Validate file type
    const validTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'text/plain'];
    if (!validTypes.includes(file.type) && !file.name.match(/\.(pdf|jpg|jpeg|png|txt)$/i)) {
        showToast('Invalid file type. Please upload PDF, JPG, PNG, or TXT files.', 'error');
        return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
        showToast('File size too large. Maximum size is 10MB.', 'error');
        return;
    }

    currentFile = file;
    uploadBtn.disabled = false;

    // Update UI
    uploadArea.innerHTML = `
        <div class="file-selected">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <div>
                <strong>${file.name}</strong>
                <p style="color: #64748b; font-size: 0.875rem;">${formatFileSize(file.size)}</p>
            </div>
        </div>
    `;
}

async function handleUpload() {
    if (!currentFile) return;

    // Update button state
    const btnText = uploadBtn.querySelector('.btn-text');
    const spinner = uploadBtn.querySelector('.spinner');
    uploadBtn.disabled = true;
    btnText.textContent = 'Processing...';
    spinner.hidden = false;

    // Create form data
    const formData = new FormData();
    formData.append('file', currentFile);

    try {
        const response = await fetch(`${API_BASE}/process-document`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Processing failed');
        }

        const result = await response.json();
        displayResults(result);
        saveToRecent(result);
        showToast('Document processed successfully!', 'success');

        // Reset upload area
        setTimeout(() => {
            resetUploadArea();
        }, 1000);

    } catch (error) {
        console.error('Upload error:', error);
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        // Reset button state
        btnText.textContent = 'Process Document';
        spinner.hidden = true;
        uploadBtn.disabled = false;
    }
}

function displayResults(result) {
    // Show results section
    resultsSection.hidden = false;
    resultsSection.scrollIntoView({ behavior: 'smooth' });

    // Update basic info
    document.getElementById('docId').textContent = result.document_id;

    const categoryBadge = document.getElementById('category');
    categoryBadge.textContent = formatCategory(result.category);
    categoryBadge.className = `result-value badge ${result.category}`;

    const urgencyBadge = document.getElementById('urgency');
    urgencyBadge.textContent = result.urgency.toUpperCase();
    urgencyBadge.className = `result-value badge ${result.urgency}`;

    document.getElementById('department').textContent = result.department;
    document.getElementById('confidence').textContent = `${(result.confidence_score * 100).toFixed(1)}%`;
    document.getElementById('immediate').textContent = result.requires_immediate_attention ? '⚠️ Yes' : '✓ No';

    // Customer information
    const customerInfo = document.getElementById('customerInfo');
    customerInfo.innerHTML = '';
    if (result.metadata) {
        Object.entries(result.metadata).forEach(([key, value]) => {
            if (value) {
                customerInfo.innerHTML += `
                    <div class="metadata-item">
                        <strong>${formatLabel(key)}</strong>
                        <span>${value}</span>
                    </div>
                `;
            }
        });
    }

    // Extracted information
    const extractedInfo = document.getElementById('extractedInfo');
    extractedInfo.innerHTML = '';
    if (result.extracted_info) {
        Object.entries(result.extracted_info).forEach(([key, value]) => {
            if (value) {
                extractedInfo.innerHTML += `
                    <div class="extracted-item">
                        <strong>${formatLabel(key)}</strong>
                        ${formatValue(value)}
                    </div>
                `;
            }
        });
    }
}

async function handleSearch() {
    const query = searchInput.value.trim();
    if (!query) {
        showToast('Please enter a search query', 'warning');
        return;
    }

    const searchResults = document.getElementById('searchResults');
    searchResults.innerHTML = '<p style="text-align: center; color: #64748b;">Searching...</p>';

    try {
        const response = await fetch(`${API_BASE}/search-documents?query=${encodeURIComponent(query)}&n_results=5`);

        if (!response.ok) {
            throw new Error('Search failed');
        }

        const data = await response.json();
        displaySearchResults(data.results);

    } catch (error) {
        console.error('Search error:', error);
        showToast(`Search error: ${error.message}`, 'error');
        searchResults.innerHTML = '<p class="empty-state">Search failed</p>';
    }
}

function displaySearchResults(results) {
    const searchResults = document.getElementById('searchResults');

    if (!results || results.length === 0) {
        searchResults.innerHTML = '<p class="empty-state">No results found</p>';
        return;
    }

    searchResults.innerHTML = results.map(result => `
        <div class="search-result-item">
            <div class="search-result-header">
                <span class="search-result-id">📄 ${result.document_id}</span>
                <span class="similarity-badge">${(result.similarity * 100).toFixed(0)}% match</span>
            </div>
            <p class="search-result-preview">${result.text_preview}</p>
            ${result.metadata ? `
                <div style="margin-top: 0.5rem; font-size: 0.875rem; color: #64748b;">
                    ${result.metadata.category ? `<span class="badge ${result.metadata.category}">${formatCategory(result.metadata.category)}</span>` : ''}
                </div>
            ` : ''}
        </div>
    `).join('');
}

function saveToRecent(result) {
    recentDocuments.unshift({
        id: result.document_id,
        category: result.category,
        urgency: result.urgency,
        timestamp: new Date().toISOString()
    });

    // Keep only last 10
    if (recentDocuments.length > 10) {
        recentDocuments = recentDocuments.slice(0, 10);
    }

    // Save to localStorage
    localStorage.setItem('recentDocuments', JSON.stringify(recentDocuments));
    displayRecentDocuments();
}

function loadRecentDocuments() {
    const stored = localStorage.getItem('recentDocuments');
    if (stored) {
        recentDocuments = JSON.parse(stored);
        displayRecentDocuments();
    }
}

function displayRecentDocuments() {
    const recentDocs = document.getElementById('recentDocs');

    if (recentDocuments.length === 0) {
        recentDocs.innerHTML = '<p class="empty-state">No documents processed yet</p>';
        return;
    }

    recentDocs.innerHTML = recentDocuments.map(doc => `
        <div class="document-item">
            <div class="document-info">
                <span class="document-id">📄 ${doc.id}</span>
                <span class="document-meta">
                    <span class="badge ${doc.category}">${formatCategory(doc.category)}</span>
                    <span class="badge ${doc.urgency}">${doc.urgency}</span>
                    • ${formatTimestamp(doc.timestamp)}
                </span>
            </div>
        </div>
    `).join('');
}

function resetUploadArea() {
    currentFile = null;
    uploadBtn.disabled = true;
    fileInput.value = '';
    uploadArea.innerHTML = `
        <svg class="upload-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p class="upload-text">Drag & drop your document here or click to browse</p>
        <p class="upload-hint">Supports: PDF, JPG, PNG, TXT</p>
    `;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${message}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Utility functions
function formatCategory(category) {
    return category
        .replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function formatLabel(key) {
    return key
        .replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function formatValue(value) {
    if (Array.isArray(value)) {
        return `<ul>${value.map(item => `<li>${item}</li>`).join('')}</ul>`;
    }
    return `<span>${value}</span>`;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
}
