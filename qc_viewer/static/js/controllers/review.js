import { AutomationAPI } from '../automate_api.js';

export const ReviewController = {
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
            
            // Set Filename in Header
            const filenameEl = document.getElementById('reviewFilename');
            if (filenameEl) filenameEl.textContent = this.currentDraftData.filename;

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
            btn.onclick = (e) => { e.stopPropagation(); this.publishQuestion(parseInt(btn.dataset.index)); };
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

            ${this.renderImageWrapper(q.diagram_base64, 'diagram_base64')}
            
            <div style="margin-top:20px; border-top: 1px solid #e2e8f0; padding-top:12px;">
                <b style="color:var(--primary); font-size: 0.75rem; text-transform:uppercase; letter-spacing:0.05em;">Options</b>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:10px;">
                    ${['A', 'B', 'C', 'D'].map(opt => `
                        <div class="edit-group opt-field" id="group-opt-${opt}">
                            <label class="field-label" style="font-weight:700; text-transform:uppercase; font-size:0.7rem;">Option ${opt}</label>
                            
                            <!-- Option Diagram Wrapper -->
                            ${this.renderImageWrapper(q[`option_${opt}_diagram_base64`], `option_${opt}_diagram_base64`, true)}

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

    async publishQuestion(index) {
        this.saveCurrentEdits();
        const q = this.currentDraftData.questions[index];
        const gen = q.generated_content || {};
        const tableName = document.getElementById('targetTableSelect').value;

        const payload = {
            draft_id: this.currentDraftData.id,
            table_name: tableName,
            question_data: {
                question_identifier: `${this.currentDraftData.id}/Q${q.question_number}`,
                title: q.text,
                options: [q.options.A, q.options.B, q.options.C, q.options.D],
                correct_options: [0], // Defaulting to A for now
                option_explanations: gen.option_analysis ? [gen.option_analysis.A, gen.option_analysis.B, gen.option_analysis.C, gen.option_analysis.D] : [],
                detailed_explanation: gen.detailed_explanation,
                topic_id: null, 
                subtopic_id: null,
                diagrams: q.diagram_base64 ? [q.diagram_base64] : [],
                flashcards: gen.flashcards || []
            }
        };

        try {
            await AutomationAPI.publishQuestion(payload);
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
                this.publishQuestion(i);
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

    showToast(msg, type = 'primary') {
        const t = document.getElementById('toast');
        t.textContent = msg;
        t.style.display = 'block';
        t.style.borderColor = type === 'danger' ? 'var(--danger)' : 'var(--primary)';
        setTimeout(() => t.style.display = 'none', 4000);
    }
};
