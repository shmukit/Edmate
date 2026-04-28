import { AutomationAPI } from '../automate_api.js';

export const DraftController = {
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
                    text.textContent = 'Upload complete! Starting extraction...';
                }
            });

            this.showToast('✅ Upload complete. Starting extraction...');
            
            // Immediate local update: Add the new draft record to the UI without waiting for poll
            if (result && result.id) {
                const initialDraft = {
                    id: result.id,
                    filename: file.name,
                    status: 'PROCESSING',
                    progress: 10,
                    status_message: 'Extracting content...',
                    timestamp: new Date().toISOString()
                };
                
                // Fetch current list and prepend
                const drafts = await AutomationAPI.fetchDrafts();
                // Ensure the new one is at the top if not already there
                if (!drafts.find(d => d.id === result.id)) {
                    drafts.unshift(initialDraft);
                }
                this.renderDrafts(drafts);
            }

            // Start polling immediately
            if (!this.pollingInterval) {
                this.pollingInterval = setInterval(() => this.fetchDrafts(), 2000); // Poll faster initially
            }

            setTimeout(() => {
                container.style.display = 'none';
                bar.style.width = '0%';
                text.textContent = 'Click to upload or drag and drop';
            }, 3000);
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

        if (hasProcessing && !this.pollingInterval) {
            this.pollingInterval = setInterval(() => this.fetchDrafts(), 3000);
        } else if (!hasProcessing && this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    },

    renderActionButton(d) {
        if (d.status === 'PROCESSED' || d.status === 'REVIEW_READY') {
            return `<button class="btn btn-outline btn-sm btn-review" data-id="${d.id}">Review</button>`;
        } else if (d.status === 'FAILED') {
            return `<span style="color:var(--danger); font-size:0.8rem;">Error</span>`;
        } else {
            return `<span class="loader" style="width:16px; height:16px;"></span>`;
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
