// Dashboard JavaScript

// Fill example command when clicked
function fillExample(command) {
    var input = document.getElementById('command');
    if (!input) return;
    input.value = command;
    input.focus();
    input.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Example category filter (network / storage / system / security / all)
document.addEventListener('DOMContentLoaded', function() {
    var filters = document.querySelectorAll('.examples-filter');
    var cards = document.querySelectorAll('.example-card-v2');
    var emptyMsg = document.querySelector('.examples-empty');
    if (!filters.length || !cards.length) return;

    function applyFilter(value) {
        var visible = 0;
        cards.forEach(function(card) {
            var category = card.getAttribute('data-category') || '';
            var match = value === 'all' || category === value;
            card.hidden = !match;
            if (match) visible++;
        });
        if (emptyMsg) emptyMsg.hidden = visible !== 0;
    }

    filters.forEach(function(btn) {
        btn.addEventListener('click', function() {
            filters.forEach(function(b) {
                b.classList.remove('is-active');
                b.setAttribute('aria-selected', 'false');
            });
            btn.classList.add('is-active');
            btn.setAttribute('aria-selected', 'true');
            applyFilter(btn.getAttribute('data-filter') || 'all');
        });
    });
});

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
    const btnText = executeBtn.querySelector('.btn-text');
    const btnLoader = executeBtn.querySelector('.btn-loader');
    if (btnText) btnText.style.display = 'none';
    if (btnLoader) btnLoader.style.display = 'inline-flex';
    
    // Parse servers
    const servers = serversInput ? serversInput.split(',').map(s => s.trim()).filter(s => s) : [];
    
    try {
        // Add timeout to fetch request. Backend now runs SSH in parallel with a
        // fast pre-flight reachability check, so unreachable servers no longer
        // block reachable ones. The safety-net timeout is generous so large
        // server batches with one slow command still finish.
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minute timeout
        
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
                    <strong>Tips</strong>
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
        const btnTextEnd = executeBtn.querySelector('.btn-text');
        const btnLoaderEnd = executeBtn.querySelector('.btn-loader');
        if (btnTextEnd) btnTextEnd.style.display = 'inline-flex';
        if (btnLoaderEnd) btnLoaderEnd.style.display = 'none';
    }
});

// Display execution results
function countServerResults(results) {
    if (!results || typeof results !== 'object') return null;
    var keys = Object.keys(results);
    if (keys.length === 0) return null;
    var ok = 0;
    var fail = 0;
    keys.forEach(function (host) {
        var r = results[host];
        if (r && typeof r === 'object' && r.success) ok++;
        else fail++;
    });
    return { total: keys.length, ok: ok, fail: fail };
}

function buildResultsMetaStrip(data) {
    var cmd = data.generated_command ? escapeHtml(String(data.generated_command)) : '';
    var req = data.original_request ? escapeHtml(String(data.original_request)) : '';
    var stats = countServerResults(data.results);
    var badges = '';
    if (stats) {
        badges +=
            '<span class="results-badge results-badge--ok" title="Hosts that completed successfully">' +
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 13l4 4L19 7"/></svg>' +
            stats.ok + ' succeeded</span>';
        if (stats.fail > 0) {
            badges +=
                '<span class="results-badge results-badge--warn" title="Hosts with errors or timeouts">' +
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>' +
                stats.fail + ' failed</span>';
        }
        badges +=
            '<span class="results-badge results-badge--neutral">' +
            stats.total + ' host' + (stats.total !== 1 ? 's' : '') +
            '</span>';
    }
    return (
        '<div class="results-meta-strip">' +
        '<div class="results-meta-main">' +
        (req
            ? '<div class="results-meta-block"><span class="results-meta-label">Your request</span><p class="results-meta-request">' +
              req +
              '</p></div>'
            : '') +
        (cmd
            ? '<div class="results-meta-block"><span class="results-meta-label">Generated command</span><code class="results-meta-cmd">' +
              cmd +
              '</code></div>'
            : '') +
        '</div>' +
        (badges ? '<div class="results-meta-badges">' + badges + '</div>' : '') +
        '</div>'
    );
}

function displayResults(data) {
    var resultsContainer = document.getElementById('resultsContainer');
    if (!resultsContainer) return;

    var html = '<div class="results-stack">';

    html += buildResultsMetaStrip(data);

    if (data.natural_language_summary) {
        html +=
            '<div class="result-summary result-summary-v2">' +
            '<div class="result-summary-head">' +
            '<span class="result-summary-icon" aria-hidden="true">' +
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="9"/></svg>' +
            '</span>' +
            '<div><h4 class="result-summary-title">What happened</h4><p class="result-summary-kicker">Plain-language summary</p></div>' +
            '</div>' +
            '<p class="result-summary-text">' +
            escapeHtml(data.natural_language_summary) +
            '</p>' +
            '</div>';
    }

    if (data.ai_report_explanation) {
        html +=
            '<details class="ai-report-explanation ai-report-v2">' +
            '<summary class="ai-report-explanation-title ai-report-summary-row">' +
            '<span class="ai-report-summary-icon" aria-hidden="true">' +
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"/><path d="M9 7h6M9 11h6M9 15h4"/></svg>' +
            '</span>' +
            '<span class="ai-report-summary-text">' +
            '<span class="ai-report-summary-title-text">Explanation of the report</span>' +
            '<span class="ai-report-summary-sub">AI walkthrough of hosts, command, and output</span>' +
            '</span>' +
            '<span class="details-chevron" aria-hidden="true"></span>' +
            '</summary>' +
            '<div class="ai-report-explanation-body ai-report-body-pad">' +
            formatAiExplanationText(data.ai_report_explanation) +
            '</div>' +
            '</details>';
    } else if (data.ai_report_explanation_error) {
        html +=
            '<div class="ai-report-explanation ai-report-explanation--muted ai-report-fallback-card">' +
            '<p class="ai-report-explanation-fallback">' +
            escapeHtml(data.ai_report_explanation_error) +
            '</p>' +
            '</div>';
    }

    if (data.script_explanation) {
        html +=
            '<details class="ai-report-explanation ai-report-v2">' +
            '<summary class="ai-report-explanation-title ai-report-summary-row">' +
            '<span class="ai-report-summary-icon" aria-hidden="true">' +
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M10 13h4M10 17h4"/></svg>' +
            '</span>' +
            '<span class="ai-report-summary-text">' +
            '<span class="ai-report-summary-title-text">Saved script</span>' +
            '<span class="ai-report-summary-sub">What this archived script does</span>' +
            '</span>' +
            '<span class="details-chevron" aria-hidden="true"></span>' +
            '</summary>' +
            '<div class="ai-report-explanation-body ai-report-body-pad">' +
            formatAiExplanationText(data.script_explanation) +
            '</div>' +
            '</details>';
    }

    if (data.formatted_report) {
        var reportId = 'formatted-report-' + Date.now();
        html +=
            '<details class="result-report-details result-report-v2" id="' +
            reportId +
            '">' +
            '<summary class="result-report-summary result-report-summary-row">' +
            '<span class="result-report-summary-icon" aria-hidden="true">' +
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h16M4 12h10M4 18h14"/></svg>' +
            '</span>' +
            '<span class="result-report-summary-text">' +
            '<span class="result-report-summary-title-text">Technical report</span>' +
            '<span class="result-report-summary-sub">Full ShellSentry execution log</span>' +
            '</span>' +
            '<span class="details-chevron" aria-hidden="true"></span>' +
            '</summary>' +
            '<div class="result-terminal">' +
            '<div class="result-terminal-toolbar">' +
            '<span class="result-terminal-dots" aria-hidden="true"><i></i><i></i><i></i></span>' +
            '<span class="result-terminal-filename">execution-report.txt</span>' +
            '<button type="button" class="result-copy-btn" data-copy-target="' +
            reportId +
            '-pre" aria-label="Copy full report to clipboard">' +
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>' +
            '<span class="result-copy-label">Copy</span>' +
            '</button>' +
            '</div>' +
            '<pre class="result-output result-formatted-report" id="' +
            reportId +
            '-pre" role="region" tabindex="0">' +
            escapeHtml(data.formatted_report) +
            '</pre>' +
            '</div>' +
            '</details>';
    }

    html += '</div>';

    resultsContainer.innerHTML = html;

    var copyBtn = resultsContainer.querySelector('.result-copy-btn');
    if (copyBtn && data.formatted_report) {
        copyBtn.addEventListener('click', function () {
            var text = data.formatted_report;
            var label = copyBtn.querySelector('.result-copy-label');
            function done() {
                if (label) {
                    var prev = label.textContent;
                    label.textContent = 'Copied!';
                    setTimeout(function () {
                        label.textContent = prev;
                    }, 2000);
                }
            }
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(done).catch(function () {});
            }
        });
    }
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

