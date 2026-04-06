// Dashboard JavaScript

// Fill example command when clicked
function fillExample(command) {
    document.getElementById('command').value = command;
    document.getElementById('command').focus();
}

// Handle form submission
document.getElementById('commandForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const commandInput = document.getElementById('command').value.trim();
    const serversInput = document.getElementById('servers').value.trim();
    const executeBtn = document.getElementById('executeBtn');
    const resultsSection = document.getElementById('resultsSection');
    const resultsContainer = document.getElementById('resultsContainer');
    
    if (!commandInput) {
        alert('Please enter a command');
        return;
    }
    
    // Disable button and show loading
    executeBtn.disabled = true;
    executeBtn.querySelector('.btn-text').style.display = 'none';
    executeBtn.querySelector('.btn-loader').style.display = 'inline-block';
    
    // Parse servers
    const servers = serversInput ? serversInput.split(',').map(s => s.trim()).filter(s => s) : [];
    
    try {
        // Add timeout to fetch request
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout
        
        const response = await fetch('/api/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                command: commandInput,
                servers: servers
            }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        const data = await response.json();
        
        if (!response.ok) {
            const nl = data.natural_language_summary;
            const errorMsg = data.error || 'Execution failed';
            const err = new Error(nl || errorMsg);
            err.payload = data;
            throw err;
        }
        
        // Display results
        displayResults(data);
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
    } catch (error) {
        console.error('Error:', error);
        let errorMessage = error.message;
        
        // Provide more specific error messages
        if (error.name === 'AbortError' || error.message.includes('timeout')) {
            errorMessage = 'Request timeout: The server took too long to respond. Please try again.';
        } else if (error.message === 'Failed to fetch' || error.message.includes('NetworkError')) {
            errorMessage = 'Network error: Could not connect to the server. Please check your connection and try again.';
        }
        
        resultsContainer.innerHTML = `
            <div class="result-card">
                <div class="result-card-header">
                    <span class="result-server">Error</span>
                    <span class="result-status error">Failed</span>
                </div>
                <div class="result-error">${escapeHtml(errorMessage).replace(/\n/g, '<br>')}</div>
                ${error.payload && (error.payload.reason || error.payload.details) ? `
                <div class="result-meta-error">
                    ${error.payload.reason ? `<div><strong>Reason:</strong> ${escapeHtml(error.payload.reason)}</div>` : ''}
                    ${error.payload.details ? `<div style="margin-top:0.35rem;"><strong>Details:</strong> ${escapeHtml(error.payload.details)}</div>` : ''}
                </div>` : ''}
                ${error.payload && error.payload.generated_command ? `
                <div class="generated-command" style="margin-top:1rem;">
                    <strong>Generated command (not run)</strong>
                    <pre class="result-inline-command">${escapeHtml(error.payload.generated_command)}</pre>
                </div>` : ''}
                <div class="troubleshooting-tips">
                    <strong>💡 Troubleshooting Tips:</strong>
                    <ul>
                        <li>Check your internet connection</li>
                        <li>Verify the Flask server is running</li>
                        <li>Check if LLM_API_KEY is correctly set in your .env file</li>
                        <li>Verify your API key is valid and has credits/quota</li>
                        <li>Try refreshing the page and submitting again</li>
                        <li>Check server logs for detailed error messages</li>
                    </ul>
                </div>
            </div>
        `;
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } finally {
        // Re-enable button
        executeBtn.disabled = false;
        executeBtn.querySelector('.btn-text').style.display = 'inline-block';
        executeBtn.querySelector('.btn-loader').style.display = 'none';
    }
});

// Display execution results
function displayResults(data) {
    const resultsContainer = document.getElementById('resultsContainer');
    
    let html = '';

    if (data.natural_language_summary) {
        html += `
            <div class="result-summary">
                <h4 class="result-summary-title">What happened (simple explanation)</h4>
                <p class="result-summary-text">${escapeHtml(data.natural_language_summary)}</p>
            </div>
        `;
    }

    if (data.ai_report_explanation) {
        html += `
            <details class="ai-report-explanation">
                <summary class="ai-report-explanation-title">Explanation of the report</summary>
                <div class="ai-report-explanation-body">${formatAiExplanationText(data.ai_report_explanation)}</div>
            </details>
        `;
    } else if (data.ai_report_explanation_error) {
        html += `
            <div class="ai-report-explanation ai-report-explanation--muted">
                <p class="ai-report-explanation-fallback">${escapeHtml(data.ai_report_explanation_error)}</p>
            </div>
        `;
    }

    if (data.formatted_report) {
        html += `
            <details class="result-report-details">
                <summary class="result-report-summary">Technical report (raw command output)</summary>
                <pre class="result-output result-formatted-report" role="region">${escapeHtml(data.formatted_report)}</pre>
            </details>
        `;
    }
    
    resultsContainer.innerHTML = html;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/** Turn AI plain text into safe HTML: paragraphs and line breaks, no raw HTML. */
function formatAiExplanationText(text) {
    if (!text) return '';
    const blocks = text.split(/\n\n+/).map((p) => p.trim()).filter(Boolean);
    if (blocks.length === 0) {
        return `<p>${escapeHtml(text)}</p>`;
    }
    return blocks.map((p) => `<p>${escapeHtml(p).replace(/\n/g, '<br>')}</p>`).join('');
}

