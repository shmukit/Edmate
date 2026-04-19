import { AutomationAPI } from './automate_api.js';

export const AutomationUI = {
    currentDraftData: null,
    currentQuestionIndex: null,
    pollingInterval: null,
    isDirty: false,

    init() {
        this.setupEventListeners();
        this.fetchDrafts();
        window.addEventListener('hashchange', () => this.checkHash());
        // Initial deep link check
        setTimeout(() => this.checkHash(), 500);
    },

    setupEventListeners() {
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');

        // Drag & Drop
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragging'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragging'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragging');
            if (e.dataTransfer.files.length) this.handleUpload(e.dataTransfer.files[0]);
        });
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) this.handleUpload(e.target.files[0]);
        });

        // Review Actions
        document.getElementById('btnAcceptAll')?.addEventListener('click', () => this.acceptAll());
        document.getElementById('btnRejectQuestion')?.addEventListener('click', () => this.rejectCurrentQuestion());
        document.getElementById('btnRefineQuestion')?.addEventListener('click', () => this.openRefineModal());
        document.getElementById('btnToggleEdit')?.addEventListener('click', () => this.toggleEditMode());
        
        // Modal Actions
        document.getElementById('closeRefine')?.addEventListener('click', () => this.closeModal('refineModal'));
        document.getElementById('cancelRefine')?.addEventListener('click', () => this.closeModal('refineModal'));
        document.getElementById('submitRefine')?.addEventListener('click', () => this.submitRefinement());
        document.getElementById('btnSaveEdits')?.addEventListener('click', () => this.saveCurrentEdits(true));
        
        // Analytics Nav
        document.getElementById('navAnalytics')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.openAnalytics();
        });
        document.getElementById('btnCloseAnalytics')?.addEventListener('click', () => this.closeAnalytics());
    },

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
    },

    async openReview(id) {
        try {
            console.log(`🔍 Loading draft review: ${id}`);
            const response = await fetch(`/api/automate/drafts/${id}`);
            
            if (!response.ok) {
                const errorBody = await response.text();
                console.error(`❌ Failed to load draft review. Status: ${response.status}`, errorBody);
                throw new Error(`Failed to load review (Status ${response.status})`);
            }

            this.currentDraftData = await response.json();
            window.location.hash = `review/${id}`;
            document.getElementById('reviewPanel').classList.add('active');
            this.renderReviewList();
        } catch (error) {
            console.error('❌ Draft Loading Error:', error);
            this.showToast('Failed to load review: ' + error.message, 'danger');
        }
    },

    renderReviewList() {
        const questions = this.currentDraftData.questions || [];
        const list = document.getElementById('reviewQuestionsList');
        list.innerHTML = questions.map((q, i) => `
            <div class="draft-card question-item ${q.status === 'REJECTED' ? 'rejected' : ''}" data-index="${i}" style="margin-bottom:10px; ${this.currentQuestionIndex === i ? 'border-color:var(--primary)' : ''}">
                <div style="flex:1">
                    <b style="color:${q.status === 'REJECTED' ? 'var(--danger)' : 'var(--primary-light)'}">Q${q.question_number}</b>: 
                    ${q.text.substring(0, 50)}...
                </div>
                ${q.status !== 'INJECTED' ? `
                    <button class="btn btn-primary btn-sm btn-inject" data-index="${i}">Inject</button>
                ` : '<span style="color:var(--accent); font-size:0.8rem">Injected ✅</span>'}
            </div>
        `).join('');

        document.querySelectorAll('.question-item').forEach(el => {
            el.onclick = () => {
                this.saveCurrentEdits();
                this.previewQuestion(parseInt(el.dataset.index));
                this.renderReviewList(); // Update highlight
            };
        });
        document.querySelectorAll('.btn-inject').forEach(btn => {
            btn.onclick = (e) => { e.stopPropagation(); this.injectQuestion(parseInt(btn.dataset.index)); };
        });
    },

    previewQuestion(index) {
        this.currentQuestionIndex = index;
        const q = this.currentDraftData.questions[index];
        const gen = q.generated_content || {};
        
        document.getElementById('currentQNum').textContent = `Question ${q.question_number} (${q.status || 'Draft'})`;
        const preview = document.getElementById('previewCard');
        
        preview.innerHTML = `
            <div class="edit-group" id="group-text">
                <label class="field-label">Question Text</label>
                <textarea class="editable-field" id="edit-text" style="height:80px;">${q.text}</textarea>
                <div id="preview-text" class="preview-render-box"></div>
            </div>

            ${q.diagram_base64 ? `<img src="${q.diagram_base64}" style="max-width:100%;margin:12px 0;border-radius:8px" />` : ''}
            
            <div style="margin-top:20px; border-top: 1px solid #e2e8f0; padding-top:12px;">
                <b style="color:var(--primary); font-size: 0.75rem; text-transform:uppercase; letter-spacing:0.05em;">Options</b>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:10px;">
                    ${['A', 'B', 'C', 'D'].map(opt => `
                        <div class="edit-group opt-field" id="group-opt-${opt}">
                            <label class="field-label" style="font-weight:700; text-transform:uppercase; font-size:0.7rem;">Option ${opt}</label>
                            <textarea class="editable-field" id="edit-opt-${opt}" data-target="preview-opt-${opt}" style="min-height:40px; margin:0">${q.options[opt]}</textarea>
                            <div id="preview-opt-${opt}" class="preview-render-box" style="padding:8px; font-size:0.88rem; min-height:36px;"></div>
                        </div>
                    `).join('')}
                </div>
            </div>

            <div class="edit-group" id="group-core" style="margin-top:20px;">
                <label class="field-label" style="color:var(--primary);">Core Concept</label>
                <textarea class="editable-field" id="edit-core-concept" data-target="preview-core-concept">${gen.core_concept || ''}</textarea>
                <div id="preview-core-concept" class="preview-render-box"></div>
            </div>

            <div class="edit-group" id="group-explanation">
                <label class="field-label" style="color:#0ea5e9;">Detailed Explanation</label>
                <textarea class="editable-field" id="edit-explanation" data-target="preview-explanation" style="height:150px;">${gen.detailed_explanation || ''}</textarea>
                <div id="preview-explanation" class="preview-render-box"></div>
            </div>
        `;

        // Reset dirty state and edit mode for each new question
        this.setDirty(false);
        this.setEditMode(false);
        
        // Attach live preview listeners
        this.attachLivePreviews();
        this.updateAllPreviews();
    },

    toggleEditMode() {
        const preview = document.getElementById('previewCard');
        const isNowEditing = !preview.classList.contains('edit-mode');
        this.setEditMode(isNowEditing);
    },

    setEditMode(active) {
        const preview = document.getElementById('previewCard');
        const btn = document.getElementById('btnToggleEdit');
        if (active) {
            preview.classList.add('edit-mode');
            if (btn) btn.textContent = '👁 Preview';
        } else {
            preview.classList.remove('edit-mode');
            if (btn) btn.textContent = '✏ Edit Mode';
        }
    },

    setDirty(status) {
        this.isDirty = status;
        const saveBtn = document.getElementById('btnSaveEdits');
        if (saveBtn) {
            saveBtn.style.display = status ? 'inline-block' : 'none';
        }
    },

    attachLivePreviews() {
        const fields = document.querySelectorAll('.editable-field');
        fields.forEach(field => {
            field.addEventListener('input', () => {
                this.setDirty(true);
                const targetId = field.dataset.target || `preview-${field.id.replace('edit-', '')}`;
                this.renderContent(field.value, targetId);
            });
        });
    },

    updateAllPreviews() {
        this.renderContent(document.getElementById('edit-text').value, 'preview-text');
        this.renderContent(document.getElementById('edit-core-concept').value, 'preview-core-concept');
        this.renderContent(document.getElementById('edit-explanation').value, 'preview-explanation');
        ['A', 'B', 'C', 'D'].forEach(opt => {
            this.renderContent(document.getElementById(`edit-opt-${opt}`).value, `preview-opt-${opt}`);
        });
    },

    renderContent(text, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        // Convert Markdown to HTML
        const html = marked.parse(text || '');
        container.innerHTML = html;

        // Trigger MathJax typesetting
        if (window.MathJax) {
            MathJax.typesetPromise([container]).catch((err) => console.log('MathJax Error:', err));
        }
    },

    async saveCurrentEdits(manual = false) {
        if (this.currentQuestionIndex === null) return;
        const q = this.currentDraftData.questions[this.currentQuestionIndex];
        
        q.text = document.getElementById('edit-text').value;
        q.options.A = document.getElementById('edit-opt-A').value;
        q.options.B = document.getElementById('edit-opt-B').value;
        q.options.C = document.getElementById('edit-opt-C').value;
        q.options.D = document.getElementById('edit-opt-D').value;
        
        if (!q.generated_content) q.generated_content = {};
        q.generated_content.core_concept = document.getElementById('edit-core-concept').value;
        q.generated_content.detailed_explanation = document.getElementById('edit-explanation').value;
        
        const statusEl = document.getElementById('saveStatus');
        if (statusEl) statusEl.textContent = 'Saving changes...';

        try {
            await AutomationAPI.updateDraft(this.currentDraftData.id, { questions: this.currentDraftData.questions });
            const now = new Date().toLocaleTimeString();
            if (statusEl) statusEl.textContent = `Last saved at ${now}`;
            this.setDirty(false);
            if (manual) this.showToast('✨ Edits saved successfully', 'success');
        } catch (error) {
            console.error('Save error:', error);
            if (statusEl) statusEl.textContent = '❌ Save failed';
            if (manual) this.showToast('Failed to save edits', 'danger');
        }
    },

    async injectQuestion(index) {
        this.saveCurrentEdits();
        const q = this.currentDraftData.questions[index];
        const gen = q.generated_content || {};
        const tableName = document.getElementById('targetTableSelect').value;

        const payload = {
            table_name: tableName,
            question_data: {
                question_identifier: `${this.currentDraftData.filename.replace('.pdf', '')}/Q${q.question_number}`,
                title: q.text,
                options: [q.options.A, q.options.B, q.options.C, q.options.D],
                correct_options: [0], // Defaulting to A for now
                option_explanations: gen.option_analysis ? [gen.option_analysis.A, gen.option_analysis.B, gen.option_analysis.C, gen.option_analysis.D] : [],
                detailed_explanation: gen.detailed_explanation,
                topic_id: null, // Admin needs to map these eventually or we extract them
                subtopic_id: null,
                diagrams: q.diagram_base64 ? [q.diagram_base64] : [],
                flashcards: gen.flashcards || []
            }
        };

        try {
            await AutomationAPI.injectQuestion(payload);
            q.status = 'INJECTED';
            this.showToast(`✅ Injected Q${q.question_number} to ${tableName}`);
            this.saveCurrentEdits();
            this.renderReviewList();
        } catch (error) { this.showToast('❌ Injection failed', 'danger'); }
    },

    acceptAll() {
        if (!confirm('Inject all processed questions into the production database?')) return;
        this.currentDraftData.questions.forEach((q, i) => {
            if (q.status !== 'INJECTED' && q.status !== 'REJECTED') {
                this.injectQuestion(i);
            }
        });
    },

    rejectCurrentQuestion() {
        if (this.currentQuestionIndex === null) return;
        const q = this.currentDraftData.questions[this.currentQuestionIndex];
        q.status = 'REJECTED';
        this.showToast(`🚫 Q${q.question_number} rejected`);
        this.saveCurrentEdits();
        this.renderReviewList();
    },

    openRefineModal() {
        if (this.currentQuestionIndex === null) return;
        document.getElementById('refine-q-num').textContent = this.currentDraftData.questions[this.currentQuestionIndex].question_number;
        document.getElementById('refineModal').style.display = 'flex';
    },

    async submitRefinement() {
        const feedback = document.getElementById('refineFeedback').value;
        if (!feedback) return;
        
        const q = this.currentDraftData.questions[this.currentQuestionIndex];
        this.showToast('🤖 AI is refining content...');
        this.closeModal('refineModal');

        try {
            const result = await AutomationAPI.refineQuestion({ feedback, original_q: q });
            this.currentDraftData.questions[this.currentQuestionIndex] = result.refined_question;
            this.previewQuestion(this.currentQuestionIndex);
            this.showToast('✨ Content refined successfully');
            this.saveCurrentEdits();
        } catch (e) { this.showToast('Refine failed', 'danger'); }
    },

    closeModal(id) { document.getElementById(id).style.display = 'none'; },

    closeReview() {
        this.saveCurrentEdits();
        document.getElementById('reviewPanel').classList.remove('active');
        window.location.hash = '';
        this.fetchDrafts();
    },

    checkHash() {
        const hash = window.location.hash;
        if (hash.startsWith('#review/')) {
            const id = hash.split('/')[1];
            if (!this.currentDraftData || this.currentDraftData.id !== id) this.openReview(id);
        } else if (hash === '#analytics') {
            this.openAnalytics();
        }
    },

    async openAnalytics() {
        window.location.hash = 'analytics';
        document.getElementById('analyticsPanel').classList.add('active');
        this.updateAnalytics();
    },

    closeAnalytics() {
        document.getElementById('analyticsPanel').classList.remove('active');
        window.location.hash = '';
    },

    async updateAnalytics() {
        try {
            const drafts = await AutomationAPI.fetchDrafts();
            
            // Calculate Stats
            const totalDrafts = drafts.length;
            const processed = drafts.filter(d => d.status === 'PROCESSED' || d.status === 'COMPLETED').length;
            let totalQ = 0;
            let injectedQ = 0;
            let rejectedQ = 0;

            drafts.forEach(d => {
                if (d.questions) {
                    totalQ += d.questions.length;
                    injectedQ += d.questions.filter(q => q.status === 'INJECTED').length;
                    rejectedQ += d.questions.filter(q => q.status === 'REJECTED').length;
                }
            });

            const injectionRate = totalQ > 0 ? Math.round((injectedQ / totalQ) * 100) : 0;

            // Render Stats
            document.getElementById('statTotalDrafts').textContent = totalDrafts;
            document.getElementById('statProcessed').textContent = processed;
            document.getElementById('statInjected').textContent = injectedQ;
            document.getElementById('statRejected').textContent = rejectedQ;
            document.getElementById('statTotalQuestions').textContent = totalQ;
            document.getElementById('statInjectionRate').textContent = injectionRate + '%';

            // Render Activity Feed
            const activityFeed = document.getElementById('analyticsActivity');
            if (drafts.length === 0) {
                activityFeed.innerHTML = '<div class="subtitle">No recent activity</div>';
                return;
            }

            const recentDrafts = [...drafts].sort((a,b) => b.created_at - a.created_at).slice(0, 10);
            activityFeed.innerHTML = recentDrafts.map(d => {
                const date = new Date(parseFloat(d.created_at) * 1000).toLocaleDateString();
                const qCount = d.questions ? d.questions.length : 0;
                return `
                    <div class="activity-row">
                        <div class="activity-name">${d.filename}</div>
                        <div class="activity-meta">
                            <span class="activity-questions">${qCount} Questions</span>
                            <span>${date}</span>
                            <span class="status-badge status-${d.status.toLowerCase()}">${d.status}</span>
                        </div>
                    </div>
                `;
            }).join('');

        } catch (error) {
            console.error('Analytics update failed:', error);
        }
    },

    showToast(msg, type = 'primary') {
        const t = document.getElementById('toast');
        t.textContent = msg;
        t.style.display = 'block';
        t.style.borderColor = type === 'danger' ? 'var(--danger)' : 'var(--primary)';
        setTimeout(() => t.style.display = 'none', 4000);
    }
};
