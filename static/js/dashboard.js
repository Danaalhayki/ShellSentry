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
            const errorMsg = data.error || 'Execution failed';
            const errorDetails = data.details ? `\n\nDetails: ${data.details}` : '';
            throw new Error(errorMsg + errorDetails);
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
                <div style="margin-top: 1rem; padding: 1rem; background-color: #fef3c7; border-radius: 0.5rem;">
                    <strong>💡 Troubleshooting Tips:</strong>
                    <ul style="margin-top: 0.5rem; margin-left: 1.5rem;">
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
    
    // Show generated command
    if (data.generated_command) {
        html += `
            <div class="generated-command">
                <strong>Generated Bash Command:</strong>
                <code>${escapeHtml(data.generated_command)}</code>
            </div>
        `;
    }
    
    // Show original request
    if (data.original_request) {
        html += `
            <div style="margin-bottom: 1rem; color: var(--secondary-color);">
                <strong>Original Request:</strong> ${escapeHtml(data.original_request)}
            </div>
        `;
    }
    
    // Show results for each server
    if (data.results && typeof data.results === 'object') {
        for (const [server, result] of Object.entries(data.results)) {
            const isSuccess = result.success !== false;
            const statusClass = isSuccess ? 'success' : 'error';
            const statusText = isSuccess ? 'Success' : 'Failed';
            
            html += `
                <div class="result-card">
                    <div class="result-card-header">
                        <span class="result-server">${escapeHtml(server)}</span>
                        <span class="result-status ${statusClass}">${statusText}</span>
                    </div>
                    
                    ${result.error ? `
                        <div class="result-error">
                            <strong>Error:</strong> ${escapeHtml(result.error)}
                        </div>
                    ` : ''}
                    
                    ${result.stdout ? `
                        <div class="result-content">
                            <strong>Standard Output:</strong>
                            <div class="result-output">${escapeHtml(result.stdout)}</div>
                        </div>
                    ` : ''}
                    
                    ${result.stderr ? `
                        <div class="result-content">
                            <strong>Standard Error:</strong>
                            <div class="result-error">${escapeHtml(result.stderr)}</div>
                        </div>
                    ` : ''}
                    
                    ${result.exit_code !== undefined ? `
                        <div style="margin-top: 0.5rem; color: var(--secondary-color); font-size: 0.875rem;">
                            Exit Code: ${result.exit_code}
                        </div>
                    ` : ''}
                </div>
            `;
        }
    } else if (data.error) {
        html += `
            <div class="result-card">
                <div class="result-card-header">
                    <span class="result-server">Error</span>
                    <span class="result-status error">Failed</span>
                </div>
                <div class="result-error">${escapeHtml(data.error)}</div>
                ${data.details ? `<div class="result-error" style="margin-top: 0.5rem;">${escapeHtml(data.details)}</div>` : ''}
            </div>
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

