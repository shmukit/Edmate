import { AutomationAPI } from '../automate_api.js';

export const DraftController = {
    async handleUpload(file) {
        const container = document.getElementById('progressContainer');
        const bar = document.getElementById('progressBar');
        const text = document.getElementById('uploadText');
        
        container.style.display = 'block';
        text.textContent = 'Uploading: 0%';

        try {
            const result = await AutomationAPI.uploadPDF(file, (percent) => {
                bar.style.width = percent + '%';
                text.textContent = `Uploading: ${percent}%`;
            });

            this.showToast('✅ Upload complete. Starting extraction...');
            this.fetchDrafts();
            this.triggerProcess(result.id);
            
            setTimeout(() => {
                container.style.display = 'none';
                bar.style.width = '0%';
                text.textContent = 'Click to upload or drag and drop';
            }, 2000);
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
            const isProcessing = d.status === 'PROCESSING';
            if (isProcessing) hasProcessing = true;
            
            const dateStr = d.created_at ? new Date(parseFloat(d.created_at) * 1000).toLocaleString() : 'Recently';
            const reviewedStr = d.last_reviewed_at ? ` | Reviewed: ${new Date(parseFloat(d.last_reviewed_at) * 1000).toLocaleTimeString()}` : '';

            return `
            <div class="draft-card ${isProcessing ? 'processing-active' : ''}" data-id="${d.id}">
                <div class="draft-info">
                    <h3>${d.filename || 'Untitled Document'}</h3>
                    <p>${dateStr}${reviewedStr}</p>
                    ${isProcessing ? `
                        <div class="mini-progress-container" style="width: 200px; height: 4px; background: #334155; border-radius: 2px; margin-top: 8px; overflow: hidden;">
                            <div style="width: ${d.progress || 0}%; height: 100%; background: var(--primary-light); transition: width 0.5s;"></div>
                        </div>
                        <span style="font-size: 0.7rem; color: var(--primary-light);">${d.progress || 0}% complete</span>
                    ` : ''}
                </div>
                <div style="display: flex; align-items: center; gap: 16px;">
                    <span class="status-badge status-${d.status.toLowerCase()}">${d.status}</span>
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

        document.querySelectorAll('.btn-process').forEach(btn => {
            btn.onclick = (e) => { e.stopPropagation(); this.triggerProcess(btn.dataset.id); };
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
        if (d.status === 'UPLOADED') {
            return `<button class="btn btn-primary btn-sm btn-process" data-id="${d.id}">Process</button>`;
        } else if (d.status === 'PROCESSED') {
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

    async triggerProcess(id) {
        const modalities = [];
        if (document.getElementById('mod_core_concept').checked) modalities.push('core_concept');
        if (document.getElementById('mod_detailed_explanation').checked) modalities.push('detailed_explanation');
        if (document.getElementById('mod_option_analysis').checked) modalities.push('option_analysis');
        if (document.getElementById('mod_flashcards').checked) modalities.push('flashcards');

        const config = {
            provider: document.getElementById('providerSelect').value,
            modalities: modalities,
            language: document.getElementById('languageSelect').value,
            curriculum: document.getElementById('curriculumSelect').value
        };

        try {
            await AutomationAPI.triggerProcess(id, config);
            this.showToast('✨ AI Extraction initiated');
            this.fetchDrafts();
        } catch (error) {
            this.showToast('❌ AI Error: ' + error.message, 'danger');
            this.fetchDrafts();
        }
    }
};
