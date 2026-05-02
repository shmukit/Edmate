import { AutomationAPI } from '../automate_api.js';

export const DraftController = {
    activeStreams: {},

    async handleUpload(file) {
        const text = document.getElementById('uploadText');
        const uploadPrompt = document.querySelector('.upload-prompt');
        
        // Disable upload zone temporarily
        if (uploadPrompt) uploadPrompt.style.opacity = '0.5';
        text.textContent = `Uploading ${file.name}...`;

        try {
            const subject = document.getElementById('curriculumSelect')?.value || 'General';
            const paperCode = document.getElementById('targetTableSelect')?.value || '';
            
            // Upload the file
            const result = await AutomationAPI.uploadPDF(file, subject, paperCode);

            // Toast is enough
            this.showToast(`✅ Added ${file.name} to processing queue.`);
            
            // Reset upload zone immediately
            if (uploadPrompt) uploadPrompt.style.opacity = '1';
            text.textContent = 'Click to upload or drag and drop';

            // IMMEDIATE HANDOVER: Inject the card right away without waiting for any fetches
            if (result && result.id) {
                const handoverState = {
                    id: result.id,
                    filename: file.name,
                    status: 'PROCESSING',
                    progress: 10,
                    status_message: 'Initializing AI pipeline...',
                    timestamp: new Date().toISOString(),
                    questions: []
                };
                
                // Read current state from DOM instead of fetching, or just force render
                // We'll append a dummy card directly to the DOM to be truly instant
                const draftList = document.getElementById('draftList');
                if (draftList) {
                    // Remove "No extraction drafts" message if present
                    const subtitle = draftList.querySelector('.subtitle');
                    if (subtitle) subtitle.remove();
                    
                    // Prepend the new card HTML
                    const dateStr = 'Just now';
                    const newCardHTML = `
                    <div class="draft-card processing-active" data-id="${result.id}">
                        <div class="draft-info">
                            <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                                <h3 style="margin:0;">${file.name}</h3>
                            </div>
                            <p>
                                <span>${dateStr}</span>
                                <span class="status-message-streaming" style="font-size:0.75rem;"> • Initializing AI pipeline...</span>
                            </p>
                            <div class="mini-progress-container" style="width: 200px; height: 4px; background: #334155; border-radius: 2px; margin-top: 8px; overflow: hidden;">
                                <div style="width: 10%; height: 100%; background: var(--primary-light); transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);"></div>
                            </div>
                            <span style="font-size: 0.7rem; color: var(--primary-light);">10% complete</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 16px;">
                            <span class="status-badge status-processing">PROCESSING</span>
                            <div class="action-buttons">
                                <div style="display:flex; align-items:center; gap:8px;">
                                    <span class="loader" style="width:16px; height:16px;"></span>
                                    <button class="btn btn-outline btn-sm btn-stop" data-id="${result.id}" style="border:1px solid rgba(239, 68, 68, 0.3); color:var(--danger)">Stop</button>
                                </div>
                                <button type="button" class="btn btn-outline btn-sm btn-delete" data-id="${result.id}" style="border:1px solid rgba(239,68,68,0.3); color:var(--danger)">Delete</button>
                            </div>
                        </div>
                    </div>`;
                    
                    draftList.insertAdjacentHTML('afterbegin', newCardHTML);
                    
                    // Attach event listeners to the new card
                    const newCard = draftList.firstElementChild;
                    newCard.querySelector('.btn-stop')?.addEventListener('click', (e) => { e.stopPropagation(); this.stopProcessing(result.id); });
                    newCard.querySelector('.btn-delete')?.addEventListener('click', (e) => { e.stopPropagation(); this.deleteDraft(result.id); });
                    
                    // Scroll to it
                    draftList.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }

                // Connect to stream immediately
                this.setupStreaming(result.id);
                
                // Now we can safely fetch in the background to sync other drafts
                AutomationAPI.fetchDrafts().then(drafts => {
                    // Ensure our new draft is in the list if the fetch returns quickly
                    if (!drafts.find(d => d.id === result.id)) {
                        drafts.unshift(handoverState);
                    }
                    this.renderDrafts(drafts);
                }).catch(e => console.warn("Background fetch failed", e));
            }

        } catch (error) {
            this.showToast('❌ Upload failed: ' + error.message, 'danger');
            if (uploadPrompt) uploadPrompt.style.opacity = '1';
            text.textContent = 'Click to upload or drag and drop';
        }
    },

    async fetchDrafts() {
        try {
            const drafts = await AutomationAPI.fetchDrafts();
            this.renderDrafts(drafts);
        } catch (error) {
            console.error('Fetch failed:', error);
        }
    },

    renderDrafts(drafts) {
        const draftList = document.getElementById('draftList');
        if (!drafts.length) {
            draftList.innerHTML = '<div class="subtitle">No extraction drafts found. Start a new one!</div>';
            return;
        }

        let hasProcessing = false;
        draftList.innerHTML = drafts.map(d => {
            const status = d.status || 'UNKNOWN';
            const isProcessing = status === 'PROCESSING' || status === 'EXTRACTING';
            if (isProcessing) hasProcessing = true;
            
            const dateStr = d.timestamp ? new Date(d.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : 'Recently';
            
            let reviewedStr = '';
            if (d.last_reviewed_at) {
                const revDate = new Date(d.last_reviewed_at);
                if (!isNaN(revDate.getTime())) {
                    reviewedStr = ` | Reviewed: ${revDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
                }
            }
            let timeStr = '';
            if (d.telemetry && d.telemetry.total_time_sec) {
                const mins = Math.floor(d.telemetry.total_time_sec / 60);
                const secs = Math.round(d.telemetry.total_time_sec % 60);
                timeStr = ` | ⏱️ ${mins}m ${secs}s`;
            }

            const qCount = d.questions?.length || d.processed_count || 0;
            const statusMsg = d.status_message || (isProcessing ? 'Processing...' : '');

            return `
            <div class="draft-card ${isProcessing ? 'processing-active' : ''}" data-id="${d.id}">
                <div class="draft-info">
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                        <h3 style="margin:0;">${d.filename || 'Untitled Document'}</h3>
                        ${qCount > 0 ? `<span class="question-count-badge">${qCount} Questions</span>` : ''}
                    </div>
                    <p>
                        <span>${dateStr}${reviewedStr}${timeStr}</span>
                        <span class="status-message-streaming" style="font-size:0.75rem;">${statusMsg ? ` • ${statusMsg}` : ''}</span>
                    </p>
                    ${isProcessing ? `
                        <div class="mini-progress-container" style="width: 200px; height: 4px; background: #334155; border-radius: 2px; margin-top: 8px; overflow: hidden;">
                            <div style="width: ${d.progress || 0}%; height: 100%; background: var(--primary-light); transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);"></div>
                        </div>
                        <span style="font-size: 0.7rem; color: var(--primary-light);">${d.progress || 0}% complete</span>
                    ` : ''}
                </div>
                <div style="display: flex; align-items: center; gap: 16px;">
                    <span class="status-badge status-${status.toLowerCase()}">${status}</span>
                    <div class="action-buttons">
                        ${this.renderActionButton(d)}
                        <button type="button" class="btn btn-outline btn-sm btn-delete" data-id="${d.id}" style="border:1px solid rgba(239,68,68,0.3); color:var(--danger)">Delete</button>
                    </div>
                </div>
            </div>
        `}).join('');

        // Attach event listeners
        document.querySelectorAll('.draft-card').forEach(card => {
            card.onclick = (e) => {
                if (e.target.closest('.action-buttons')) return;
                const id = card.dataset.id;
                const d = drafts.find(x => x.id === id);
                if (d.status === 'PROCESSED') this.openReview(id);
            };
        });

        document.querySelectorAll('.btn-review').forEach(btn => {
            btn.onclick = (e) => { e.stopPropagation(); this.openReview(btn.dataset.id); };
        });
        document.querySelectorAll('.btn-delete').forEach(btn => {
            btn.onclick = (e) => { e.stopPropagation(); this.deleteDraft(btn.dataset.id); };
        });
        document.querySelectorAll('.btn-stop').forEach(btn => {
            btn.onclick = (e) => { e.stopPropagation(); this.stopProcessing(btn.dataset.id); };
        });
        document.querySelectorAll('.btn-card-export').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                this.openDraftExportPopover(btn, btn.dataset.id);
            };
        });

        if (hasProcessing && !this.pollingInterval) {
            this.pollingInterval = setInterval(() => this.fetchDrafts(), 10000); // Slower polling if streaming is active
            
            // Ensure all processing drafts have a stream
            drafts.forEach(d => {
                const isProcessing = d.status === 'PROCESSING' || d.status === 'EXTRACTING';
                if (isProcessing) this.setupStreaming(d.id);
            });
        } else if (!hasProcessing && this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    },

    setupStreaming(draftId) {
        if (this.activeStreams[draftId]) return;

        console.log(`📡 Starting stream for draft: ${draftId}`);
        const eventSource = new EventSource(`/api/automate/draft/${draftId}/stream`);
        this.activeStreams[draftId] = eventSource;

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.updateDraftUI(data);
                
                if (data.status === 'PROCESSED' || data.status === 'FAILED') {
                    console.log(`✅ Stream complete for ${draftId}`);
                    eventSource.close();
                    delete this.activeStreams[draftId];
                    // Final fetch to sync everything
                    setTimeout(() => this.fetchDrafts(), 1000);
                }
            } catch (e) {
                console.error('SSE Parse Error:', e);
            }
        };

        eventSource.onerror = (err) => {
            console.error('SSE Error:', err);
            eventSource.close();
            delete this.activeStreams[draftId];
        };
    },

    updateDraftUI(d) {
        // 1. (Removed top-level progress bar update as per UAC)

        // 2. Update the specific draft card
        const card = document.querySelector(`.draft-card[data-id="${d.id}"]`);
        if (!card) return;

        // Update progress bar
        const bar = card.querySelector('.mini-progress-container div');
        if (bar) bar.style.width = `${d.progress || 0}%`;

        // Update percentage text
        const pctText = card.querySelector('.draft-info span[style*="color: var(--primary-light)"]');
        if (pctText) pctText.textContent = `${d.progress || 0}% complete`;

        // Update status message
        const statusMsgContainer = card.querySelector('.draft-info p');
        let statusMsgSpan = statusMsgContainer.querySelector('.status-message-streaming');
        if (!statusMsgSpan) {
            statusMsgSpan = document.createElement('span');
            statusMsgSpan.className = 'status-message-streaming';
            statusMsgSpan.style.fontSize = '0.75rem';
            statusMsgContainer.appendChild(statusMsgSpan);
        }
        statusMsgSpan.textContent = ` • ${d.status_message || 'Processing...'}`;
        
        // Update question count if available
        const qCount = d.questions?.length || d.processed_count || 0;
        if (qCount > 0) {
            let badge = card.querySelector('.question-count-badge');
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'question-count-badge';
                const titleBlock = card.querySelector('div[style*="display:flex; align-items:center"]');
                if (titleBlock) titleBlock.appendChild(badge);
            }
            badge.textContent = `${qCount} Questions`;
        }
    },

    renderActionButton(d) {
        if (d.status === 'PROCESSED' || d.status === 'REVIEW_READY') {
            return `<div style="display:flex; align-items:center; gap:8px;">
                <button type="button" class="btn btn-outline btn-sm btn-review" data-id="${d.id}">Review</button>
                <button type="button" class="btn btn-outline btn-sm btn-card-export" data-id="${d.id}" title="Choose export format">📥 Export ▾</button>
            </div>`;
        } else if (d.status === 'FAILED') {
            return `<span style="color:var(--danger); font-size:0.8rem;">Error</span>`;
        } else if (d.status === 'PROCESSING' || d.status === 'EXTRACTING') {
            return `
                <div style="display:flex; align-items:center; gap:8px;">
                    <span class="loader" style="width:16px; height:16px;"></span>
                    <button class="btn btn-outline btn-sm btn-stop" data-id="${d.id}" style="border:1px solid rgba(239, 68, 68, 0.3); color:var(--danger)">Stop</button>
                </div>
            `;
        } else {
            return `<span class="loader" style="width:16px; height:16px;"></span>`;
        }
    },

    async stopProcessing(id) {
        try {
            await AutomationAPI.stopDraft(id);
            this.showToast('🛑 Stopping process...');
            this.fetchDrafts();
        } catch (e) {
            this.showToast('Failed to stop process', 'danger');
        }
    },

    async deleteDraft(id) {
        if (!confirm('Are you sure you want to delete this draft and all processed questions?')) return;
        try {
            await AutomationAPI.deleteDraft(id);
            this.showToast('🗑️ Draft deleted');
            this.fetchDrafts();
        } catch (e) { this.showToast('Delete failed', 'danger'); }
    },

    openReview(id) {
        window.AutomationUI.openReview(id);
    },

    /**
     * Floating export format picker for a draft card (PROCESSED / REVIEW_READY).
     */
    openDraftExportPopover(anchorEl, draftId) {
        document.querySelector('.draft-export-popover')?.remove();
        const pop = document.createElement('div');
        pop.className = 'draft-export-popover';
        pop.style.cssText = [
            'position:fixed',
            'z-index:10050',
            'background:var(--card-bg,#1e293b)',
            'border:1px solid var(--card-border,#334155)',
            'border-radius:8px',
            'padding:8px',
            'display:flex',
            'flex-direction:column',
            'gap:6px',
            'min-width:220px',
            'box-shadow:0 8px 24px rgba(0,0,0,0.35)',
        ].join(';');
        const r = anchorEl.getBoundingClientRect();
        pop.style.top = `${Math.min(window.innerHeight - 120, r.bottom + 6)}px`;
        pop.style.left = `${Math.max(8, Math.min(r.left, window.innerWidth - 150))}px`;

        const addFmt = (fmt, label) => {
            const b = document.createElement('button');
            b.type = 'button';
            b.className = 'btn btn-outline btn-sm';
            b.textContent = label;
            b.style.width = '100%';
            b.style.justifyContent = 'flex-start';
            b.onclick = async (ev) => {
                ev.stopPropagation();
                try {
                    await AutomationAPI.exportDraft(draftId, fmt);
                    this.showToast(`Exported ${label}`, 'success');
                } catch (err) {
                    this.showToast(err.message || 'Export failed', 'danger');
                }
                pop.remove();
                document.removeEventListener('click', onDoc);
            };
            pop.appendChild(b);
        };
        addFmt('json', 'JSON');
        addFmt('csv', 'CSV');
        addFmt('markdown', 'Markdown (.md)');
        addFmt('mdzip', 'Markdown + Images (.zip)');
        addFmt('docx', 'Word (.docx)');
        document.body.appendChild(pop);

        const onDoc = (ev) => {
            if (!pop.contains(ev.target) && ev.target !== anchorEl) {
                pop.remove();
                document.removeEventListener('click', onDoc);
            }
        };
        setTimeout(() => document.addEventListener('click', onDoc), 0);
    },
};
