/**
 * Agentic RAG Frontend Application
 */

const API_BASE = '';  // Same origin

// State
let selectedDisease = null;
let diseases = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadDiseases();
    setupDragAndDrop();
});

// ==================== Disease Management ====================

async function loadDiseases() {
    try {
        const response = await fetch(`${API_BASE}/diseases`);
        diseases = await response.json();
        renderDiseaseList();
        renderDiseaseDropdown();
    } catch (error) {
        console.error('Failed to load diseases:', error);
        document.getElementById('diseaseList').innerHTML =
            '<p class="error">Failed to load diseases</p>';
    }
}

function renderDiseaseList() {
    const container = document.getElementById('diseaseList');

    if (diseases.length === 0) {
        container.innerHTML = '<p class="empty">No disease collections yet. Create one to get started.</p>';
        return;
    }

    container.innerHTML = diseases.map(disease => `
        <div class="disease-item ${selectedDisease === disease.name ? 'selected' : ''}"
             onclick="selectDisease('${disease.name}', '${disease.display_name}')">
            <span class="name">${disease.display_name}</span>
            <span class="count">${disease.document_count} docs</span>
            <button class="delete-btn" onclick="event.stopPropagation(); deleteDisease('${disease.name}')" title="Delete">
                🗑️
            </button>
        </div>
    `).join('');
}

function renderDiseaseDropdown() {
    const dropdown = document.getElementById('queryDisease');
    dropdown.innerHTML = '<option value="">-- Select a disease --</option>' +
        diseases.map(d => `<option value="${d.name}">${d.display_name}</option>`).join('');
}

async function createDisease() {
    const input = document.getElementById('newDiseaseName');
    const name = input.value.trim();

    if (!name) {
        alert('Please enter a disease name');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/diseases`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });

        if (response.ok) {
            input.value = '';
            await loadDiseases();
            // Auto-select the new disease
            const newDisease = await response.json();
            selectDisease(newDisease.name, newDisease.display_name);
        } else {
            const error = await response.json();
            alert(`Failed to create disease: ${error.detail || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Failed to create disease:', error);
        alert('Failed to create disease');
    }
}

async function deleteDisease(name) {
    if (!confirm(`Are you sure you want to delete "${name}" and all its documents?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/diseases/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            if (selectedDisease === name) {
                selectedDisease = null;
                document.getElementById('uploadPanel').style.display = 'none';
            }
            await loadDiseases();
        } else {
            alert('Failed to delete disease');
        }
    } catch (error) {
        console.error('Failed to delete disease:', error);
        alert('Failed to delete disease');
    }
}

function selectDisease(name, displayName) {
    selectedDisease = name;
    renderDiseaseList();

    // Show upload panel
    document.getElementById('uploadPanel').style.display = 'block';
    document.getElementById('selectedDiseaseName').textContent = displayName;

    // Load documents for this disease
    loadDocuments(name);

    // Update query dropdown
    document.getElementById('queryDisease').value = name;
}

// ==================== Document Management ====================

async function loadDocuments(diseaseName) {
    try {
        const response = await fetch(`${API_BASE}/diseases/${encodeURIComponent(diseaseName)}/documents`);
        const documents = await response.json();
        renderDocumentList(documents);
    } catch (error) {
        console.error('Failed to load documents:', error);
    }
}

function renderDocumentList(documents) {
    const container = document.getElementById('documentList');

    if (documents.length === 0) {
        container.innerHTML = '<p class="empty">No documents uploaded</p>';
        return;
    }

    container.innerHTML = documents.map(doc => `
        <div class="document-item">
            <span class="filename" title="${doc.filename}">${doc.filename}</span>
            <button class="delete-btn" onclick="deleteDocument('${doc.document_id}')" title="Delete">
                🗑️
            </button>
        </div>
    `).join('');
}

async function deleteDocument(documentId) {
    if (!confirm('Are you sure you want to delete this document?')) {
        return;
    }

    try {
        const response = await fetch(
            `${API_BASE}/documents/${encodeURIComponent(selectedDisease)}/${documentId}`,
            { method: 'DELETE' }
        );

        if (response.ok) {
            await loadDocuments(selectedDisease);
            await loadDiseases();  // Update document counts
        } else {
            alert('Failed to delete document');
        }
    } catch (error) {
        console.error('Failed to delete document:', error);
        alert('Failed to delete document');
    }
}

// ==================== File Upload ====================

function setupDragAndDrop() {
    const uploadArea = document.getElementById('uploadArea');

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.remove('dragover');
        });
    });

    uploadArea.addEventListener('drop', handleDrop);
}

function handleDrop(e) {
    const files = e.dataTransfer.files;
    handleFiles(files);
}

function handleFileSelect(e) {
    const files = e.target.files;
    handleFiles(files);
    e.target.value = '';  // Reset input
}

async function handleFiles(files) {
    if (!selectedDisease) {
        alert('Please select a disease first');
        return;
    }

    const progressContainer = document.getElementById('uploadProgress');
    progressContainer.innerHTML = '';

    for (const file of files) {
        const itemId = `upload-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        progressContainer.innerHTML += `
            <div class="upload-item" id="${itemId}">
                <span class="filename">${file.name}</span>
                <span class="status uploading">Uploading...</span>
            </div>
        `;

        await uploadFile(file, itemId);
    }

    // Refresh documents and diseases
    await loadDocuments(selectedDisease);
    await loadDiseases();
}

async function uploadFile(file, itemId) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(
            `${API_BASE}/upload/${encodeURIComponent(selectedDisease)}`,
            {
                method: 'POST',
                body: formData
            }
        );

        const item = document.getElementById(itemId);
        const statusEl = item.querySelector('.status');

        if (response.ok) {
            const result = await response.json();
            statusEl.className = 'status success';
            statusEl.textContent = `${result.chunks_added} chunks`;
        } else {
            const error = await response.json();
            statusEl.className = 'status error';
            statusEl.textContent = error.detail || 'Failed';
        }
    } catch (error) {
        const item = document.getElementById(itemId);
        const statusEl = item.querySelector('.status');
        statusEl.className = 'status error';
        statusEl.textContent = 'Error';
        console.error('Upload error:', error);
    }
}

// ==================== Query ====================

function onQueryDiseaseChange() {
    const disease = document.getElementById('queryDisease').value;
    if (disease && disease !== selectedDisease) {
        // Find display name
        const diseaseObj = diseases.find(d => d.name === disease);
        if (diseaseObj) {
            selectDisease(diseaseObj.name, diseaseObj.display_name);
        }
    }
}

async function submitQuery() {
    const disease = document.getElementById('queryDisease').value;
    const query = document.getElementById('queryInput').value.trim();
    const useVerification = document.getElementById('useVerification').checked;
    const maxAttempts = parseInt(document.getElementById('maxAttempts').value) || 5;

    if (!disease) {
        alert('Please select a disease');
        return;
    }

    if (!query) {
        alert('Please enter a question');
        return;
    }

    // Show loading state
    const btn = document.getElementById('queryBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Processing...';

    // Hide previous results
    document.getElementById('resultsPanel').style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                disease,
                query,
                use_verification: useVerification,
                max_attempts: maxAttempts
            })
        });

        const result = await response.json();
        displayResults(result);

    } catch (error) {
        console.error('Query error:', error);
        alert('Failed to process query. Please try again.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Ask Question';
    }
}

function displayResults(result) {
    const panel = document.getElementById('resultsPanel');
    panel.style.display = 'block';

    // Verification badge
    const badge = document.getElementById('verificationBadge');
    if (result.verified) {
        badge.className = 'verification-badge verified';
        badge.textContent = '✓ Verified';
    } else if (result.confidence > 0.5) {
        badge.className = 'verification-badge unverified';
        badge.textContent = '⚠ Partially Verified';
    } else {
        badge.className = 'verification-badge failed';
        badge.textContent = '✗ Unverified';
    }

    // Answer
    document.getElementById('answerContent').textContent = result.answer;

    // Confidence
    const confidence = Math.round((result.confidence || 0) * 100);
    document.getElementById('confidenceValue').textContent = `${confidence}%`;

    const fill = document.getElementById('confidenceFill');
    fill.style.width = `${confidence}%`;
    fill.className = 'confidence-fill' +
        (confidence < 50 ? ' low' : confidence < 80 ? ' medium' : '');

    // Warning
    const warningBox = document.getElementById('warningBox');
    if (result.warning) {
        warningBox.style.display = 'block';
        warningBox.textContent = result.warning;
    } else {
        warningBox.style.display = 'none';
    }

    // References
    const refList = document.getElementById('referencesList');
    if (result.references && result.references.length > 0) {
        refList.innerHTML = result.references.map(ref => `
            <div class="reference-item">
                <div class="source">[Source ${ref.source_id}] ${ref.filename}</div>
                <div class="excerpt">${ref.excerpt}</div>
                <div class="score">Relevance: ${Math.round((ref.relevance_score || 0) * 100)}%</div>
            </div>
        `).join('');
    } else {
        refList.innerHTML = '<p class="empty">No specific references cited</p>';
    }

    // Attempts
    const attemptsDetails = document.getElementById('attemptsDetails');
    const attemptsList = document.getElementById('attemptsList');
    const attemptCount = document.getElementById('attemptCount');

    if (result.attempts && result.attempts.length > 0) {
        attemptsDetails.style.display = 'block';
        attemptCount.textContent = result.attempts.length;

        attemptsList.innerHTML = result.attempts.map(attempt => `
            <div class="attempt-item">
                <div class="attempt-header">
                    <span class="attempt-number">Attempt ${attempt.attempt}</span>
                    <span class="attempt-confidence">
                        Confidence: ${Math.round((attempt.confidence || 0) * 100)}%
                        ${attempt.is_verified ? '✓' : ''}
                    </span>
                </div>
                ${attempt.query_used !== undefined ?
                    `<div class="attempt-query">Query: ${attempt.query_used}</div>` : ''}
                ${attempt.issues && attempt.issues.length > 0 ?
                    `<div class="attempt-issues">Issues: ${attempt.issues.join(', ')}</div>` : ''}
            </div>
        `).join('');
    } else {
        attemptsDetails.style.display = 'none';
    }

    // Scroll to results
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Handle Enter key in query input
document.getElementById('queryInput')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
        submitQuery();
    }
});

// Handle Enter key in disease name input
document.getElementById('newDiseaseName')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        createDisease();
    }
});
