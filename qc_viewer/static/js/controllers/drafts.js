import { AutomationAPI } from '../automate_api.js';

export const DraftController = {
    activeStreams: {},
    currentUploadingDraftId: null,

    async handleUpload(file) {
        const container = document.getElementById('progressContainer');
        const bar = document.getElementById('progressBar');
        const text = document.getElementById('uploadText');
        
        container.style.display = 'block';
        text.textContent = 'Uploading: 0%';

        try {
            const subject = document.getElementById('curriculumSelect')?.value || 'General';
            const paperCode = document.getElementById('targetTableSelect')?.value || '';
            
            text.textContent = 'Uploading: 0%';
            
            const result = await AutomationAPI.uploadPDF(file, subject, paperCode, (percent) => {
                bar.style.width = percent + '%';
                text.textContent = `Uploading: ${percent}%`;
                if (percent === 100) {
                    text.textContent = 'Upload received! Initializing extraction...';
                }
            });

            this.showToast('✅ Upload complete. Starting extraction...');
            
            // IMMEDIATE HANDOVER: Transition to 15% right away to eliminate the sync gap
            if (result && result.id) {
                this.currentUploadingDraftId = result.id;
                const handoverState = {
                    id: result.id,
                    filename: file.name,
                    status: 'PROCESSING',
                    progress: 15,
                    status_message: 'Initializing AI pipeline...',
                    timestamp: new Date().toISOString()
                };
                
                // Add to list and update UI immediately
                const drafts = await AutomationAPI.fetchDrafts();
                if (!drafts.find(d => d.id === result.id)) {
                    drafts.unshift(handoverState);
                }
                this.renderDrafts(drafts);
                this.updateDraftUI(handoverState);

                // Start streaming
                this.setupStreaming(result.id);
            }

            // Do not hide container immediately if streaming
            if (!result || !result.id) {
                setTimeout(() => {
                    container.style.display = 'none';
                    bar.style.width = '0%';
                    text.textContent = 'Click to upload or drag and drop';
                }, 3000);
            }
        } catch (error) {
            this.showToast('❌ Upload failed: ' + error.message, 'danger');
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
                        <span>${dateStr}${reviewedStr}</span>
                        ${statusMsg ? `<span style="opacity:0.6; font-size:0.75rem;">• ${statusMsg}</span>` : ''}
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
                        <button class="btn btn-outline btn-sm btn-delete" data-id="${d.id}" style="border:none; color:var(--danger)">×</button>
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
        // 1. Update the top-level upload zone if this is the active upload
        if (d.id === this.currentUploadingDraftId) {
            const topBar = document.getElementById('progressBar');
            const topText = document.getElementById('uploadText');
            const topContainer = document.getElementById('progressContainer');
            
            if (topBar) topBar.style.width = `${d.progress || 0}%`;
            if (topText) topText.textContent = d.status_message || `${d.progress || 0}% complete`;
            if (topContainer) topContainer.style.display = 'block';

            if (d.status === 'PROCESSED' || d.status === 'FAILED') {
                setTimeout(() => {
                    if (this.currentUploadingDraftId === d.id) {
                        topContainer.style.display = 'none';
                        topText.textContent = 'Click to upload or drag and drop';
                        this.currentUploadingDraftId = null;
                    }
                }, 5000);
            }
        }

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
            return `<button class="btn btn-outline btn-sm btn-review" data-id="${d.id}">Review</button>`;
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
    }
};
