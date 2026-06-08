import { AutomationAPI } from '../automate_api.js';

const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
}[char]));

const sanitizeRenderedHtml = (html) => {
    const template = document.createElement('template');
    template.innerHTML = html;
    template.content
        .querySelectorAll('script, iframe, object, embed, link, meta, style')
        .forEach((node) => node.remove());
    template.content.querySelectorAll('*').forEach((node) => {
        [...node.attributes].forEach((attr) => {
            const name = attr.name.toLowerCase();
            const value = attr.value.trim().toLowerCase();
            if (
                name.startsWith('on') ||
                name === 'style' ||
                ((name === 'href' || name === 'src' || name === 'xlink:href') &&
                    (value.startsWith('javascript:') || value.startsWith('data:text/html')))
            ) {
                node.removeAttribute(attr.name);
            }
        });
    });
    return template.innerHTML;
};

export const ReviewController = {
    async openReview(id) {
        try {
            console.log(`🔍 Loading draft review: ${id}`);
            this.currentDraftData = await AutomationAPI.getDraft(id);
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
                    <b style="color:${q.status === 'REJECTED' ? 'var(--danger)' : 'var(--primary-light)'}">Q${q.question_number}</b>${(q.extraction_warnings && q.extraction_warnings.length) ? '<span class="extraction-warn-inline" title="Extraction may be incomplete (e.g. options)">⚠</span>' : ''}: 
                    ${escapeHtml(String(q.text || '').substring(0, 50))}...
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
        const hia = q.hia_details || {};
        
        // Render Resilience Badge
        const badge = document.getElementById('resilienceBadge');
        if (badge) {
            const score = q.ai_integrity_label || 'Low';
            badge.textContent = `${score} Integrity`;
            badge.className = `resilience-badge ${score.toLowerCase()}`;
        }

        document.getElementById('currentQNum').textContent = `Question ${q.question_number} (${q.status || 'Draft'})`;
        const preview = document.getElementById('previewCard');
        
        let typeSpecificHtml = '';
        const qType = q.type || 'mcq';
        const extWarn = Array.isArray(q.extraction_warnings) && q.extraction_warnings.length > 0;
        const warnBanner = extWarn
            ? `<div class="extraction-warn-banner" role="status">Extraction note: some PDF fields (often MCQ options) could not be split reliably. Compare with the source PDF or use edit mode to fix.</div>`
            : '';

        if (qType === 'mcq') {
            const opts = q.options || { A: '', B: '', C: '', D: '' };
            typeSpecificHtml = `
                ${warnBanner}
                <div style="margin-top:20px; border-top: 1px solid #e2e8f0; padding-top:12px;">
                    <b style="color:var(--primary); font-size: 0.75rem; text-transform:uppercase; letter-spacing:0.05em;">Options</b>
                    <div class="mcq-options-grid">
                        ${['A', 'B', 'C', 'D'].map(opt => `
                            <div class="edit-group opt-field" id="group-opt-${opt}">
                                <label class="field-label" style="font-weight:700; text-transform:uppercase; font-size:0.7rem;">Option ${opt}</label>
                                ${this.renderImageWrapper(q[`option_${opt}_diagram_base64`], `option_${opt}_diagram_base64`, true)}
                                <textarea class="editable-field" id="edit-opt-${opt}" data-target="preview-opt-${opt}" style="min-height:40px; margin:0">${escapeHtml(opts[opt] || '')}</textarea>
                                <div id="preview-opt-${opt}" class="preview-render-box" style="padding:8px; font-size:0.88rem; min-height:36px;"></div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        } else if (qType === 'ai_critique') {
            typeSpecificHtml = `
                <div class="hia-container">
                    <div class="hia-title">🛡️ High-Integrity Assessment: AI Critique</div>
                    <div class="critique-box">
                        <label class="field-label">AI-Generated Answer (Stimulus)</label>
                        <textarea class="editable-field" id="edit-hia-stimulus" style="height:100px;">${escapeHtml(hia.ai_generated_answer || '')}</textarea>
                        <div id="preview-hia-stimulus" class="preview-render-box"></div>
                    </div>
                    <label class="field-label">Planted Errors (Student must identify)</label>
                    <div id="hia-errors-list">
                        ${(hia.planted_errors || []).map((err, i) => `
                            <div class="error-item">
                                <span class="error-tag">Error ${i+1}</span>
                                <div id="preview-hia-error-${i}" class="preview-render-box" style="margin:0; min-height:0; padding:8px 10px;"></div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        } else if (qType === 'viva_prompt') {
            typeSpecificHtml = `
                <div class="hia-container">
                    <div class="hia-title">🛡️ High-Integrity Assessment: Viva Defense Probes</div>
                    <div class="viva-grid">
                        ${Object.entries(hia.viva_probes || {}).map(([stage, probe]) => `
                            <div class="viva-card">
                                <h4>${escapeHtml(stage)}</h4>
                                <div id="preview-viva-probe-${stage.toLowerCase().replace(/\s+/g,'-')}" class="preview-render-box" style="margin:0; min-height:0; padding:8px 10px;"></div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        preview.innerHTML = `
            ${qType !== 'mcq' ? warnBanner : ''}
            <div class="edit-group" id="group-text">
                <label class="field-label">Question Text</label>
                <textarea class="editable-field" id="edit-text" style="height:80px;">${escapeHtml(q.text || '')}</textarea>
                <div id="preview-text" class="preview-render-box"></div>
            </div>

            ${this.renderImageWrapper(q.diagram_base64, 'diagram_base64')}
            
            ${typeSpecificHtml}

            <div class="edit-group" id="group-core" style="margin-top:20px;">
                <label class="field-label" style="color:var(--primary);">Core Concept</label>
                <textarea class="editable-field" id="edit-core-concept" data-target="preview-core-concept">${escapeHtml(gen.core_concept || '')}</textarea>
                <div id="preview-core-concept" class="preview-render-box"></div>
            </div>

            <div class="edit-group" id="group-explanation">
                <label class="field-label" style="color:#0ea5e9;">Detailed Explanation</label>
                <textarea class="editable-field" id="edit-explanation" data-target="preview-explanation" style="height:150px;">${escapeHtml(gen.detailed_explanation || '')}</textarea>
                <div id="preview-explanation" class="preview-render-box"></div>
            </div>
        `;

        // Reset dirty state and edit mode for each new question
        this.setDirty(false);
        this.setEditMode(false);
        
        // Attach live preview listeners
        this.attachLivePreviews();
        this.updateAllPreviews();
        this.renderAdditionalBlocks(qType, hia);
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
        const textEl = document.getElementById('edit-text');
        const coreEl = document.getElementById('edit-core-concept');
        const expEl = document.getElementById('edit-explanation');
        if (textEl) this.renderContent(textEl.value, 'preview-text');
        if (coreEl) this.renderContent(coreEl.value, 'preview-core-concept');
        if (expEl) this.renderContent(expEl.value, 'preview-explanation');
        ['A', 'B', 'C', 'D'].forEach(opt => {
            const optEl = document.getElementById(`edit-opt-${opt}`);
            if (optEl) this.renderContent(optEl.value, `preview-opt-${opt}`);
        });
    },

    renderContent(text, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        if (!text || text.trim() === '' || text === '[PARSING_FAILED]') {
            container.innerHTML = '<span style="color:var(--text-dim); font-style:italic; font-size:0.8rem;">No content generated for this section.</span>';
            return;
        }

        // Convert Markdown to HTML
        try {
            const html = sanitizeRenderedHtml(marked.parse(text || ''));
            container.innerHTML = html;

            // Trigger MathJax typesetting
            if (window.MathJax) {
                MathJax.typesetPromise([container]).catch((err) => console.log('MathJax Error:', err));
            }
        } catch (e) {
            console.warn('Markdown parsing failed, falling back to raw text:', e);
            container.textContent = text;
        }
    },

    renderAdditionalBlocks(qType, hia = {}) {
        if (qType === 'ai_critique') {
            this.renderContent(hia.ai_generated_answer || '', 'preview-hia-stimulus');
            (hia.planted_errors || []).forEach((err, i) => {
                this.renderContent(err || '', `preview-hia-error-${i}`);
            });
        } else if (qType === 'viva_prompt') {
            Object.entries(hia.viva_probes || {}).forEach(([stage, probe]) => {
                const id = `preview-viva-probe-${stage.toLowerCase().replace(/\s+/g, '-')}`;
                this.renderContent(probe || '', id);
            });
        }
    },

    async saveCurrentEdits(manual = false, force = false) {
        if (!this.currentDraftData?.id || (!this.isDirty && !force)) return;

        if (this.currentQuestionIndex !== null) {
            const q = this.currentDraftData.questions[this.currentQuestionIndex];
        
            const textEl = document.getElementById('edit-text');
            if (textEl) q.text = textEl.value;
            const optA = document.getElementById('edit-opt-A');
            const optB = document.getElementById('edit-opt-B');
            const optC = document.getElementById('edit-opt-C');
            const optD = document.getElementById('edit-opt-D');
            if (optA && optB && optC && optD && q.options) {
                q.options.A = optA.value;
                q.options.B = optB.value;
                q.options.C = optC.value;
                q.options.D = optD.value;
            }
        
            if (!q.generated_content) q.generated_content = {};
            const coreEl = document.getElementById('edit-core-concept');
            const expEl = document.getElementById('edit-explanation');
            if (coreEl) q.generated_content.core_concept = coreEl.value;
            if (expEl) q.generated_content.detailed_explanation = expEl.value;
        }
        
        const statusEl = document.getElementById('saveStatus');
        if (statusEl) statusEl.textContent = 'Saving changes...';

        try {
            const lastReviewed = new Date().toISOString();
            await AutomationAPI.updateDraft(this.currentDraftData.id, { 
                questions: this.currentDraftData.questions,
                last_reviewed_at: lastReviewed
            });
            this.currentDraftData.last_reviewed_at = lastReviewed; // Update local state
            
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
        await this.saveCurrentEdits();
        const q = this.currentDraftData.questions[index];
        const gen = q.generated_content || {};
        const tableName = document.getElementById('targetTableSelect').value;
        const optionToIndex = { A: 0, B: 1, C: 2, D: 3 };
        const answerLetter = (q.correct_answer || '').toString().trim().toUpperCase();
        const mappedCorrect = Number.isInteger(optionToIndex[answerLetter]) ? optionToIndex[answerLetter] : 0;

        const payload = {
            draft_id: this.currentDraftData.id,
            table_name: tableName,
            question_data: {
                question_identifier: `${this.currentDraftData.id}/Q${q.question_number}`,
                title: q.text,
                options: [q.options?.A || '', q.options?.B || '', q.options?.C || '', q.options?.D || ''],
                correct_options: [mappedCorrect],
                option_explanations: [
                    gen.option_analysis?.A || 'No analysis available.',
                    gen.option_analysis?.B || 'No analysis available.',
                    gen.option_analysis?.C || 'No analysis available.',
                    gen.option_analysis?.D || 'No analysis available.'
                ],
                detailed_explanation: gen.detailed_explanation || 'No detailed explanation available.',
                core_concept: gen.core_concept || '',
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
            await this.saveCurrentEdits(false, true);
            this.renderReviewList();
        } catch (error) { this.showToast('❌ Injection failed', 'danger'); }
    },

    async acceptAll() {
        if (!confirm('Inject all processed questions into the production database?')) return;
        for (const [i, q] of this.currentDraftData.questions.entries()) {
            if (q.status !== 'INJECTED' && q.status !== 'REJECTED') {
                await this.publishQuestion(i);
            }
        }
    },

    async rejectCurrentQuestion() {
        if (this.currentQuestionIndex === null) return;
        const q = this.currentDraftData.questions[this.currentQuestionIndex];
        q.status = 'REJECTED';
        this.showToast(`🚫 Q${q.question_number} rejected`);
        await this.saveCurrentEdits(false, true);
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
            if (result.refined_question) {
                this.currentDraftData.questions[this.currentQuestionIndex] = result.refined_question;
            } else {
                if (!q.generated_content) q.generated_content = {};
                q.generated_content.detailed_explanation = result.explanation || q.generated_content.detailed_explanation || '';
            }
            this.previewQuestion(this.currentQuestionIndex);
            this.setDirty(true);
            await this.saveCurrentEdits(false, true);
            this.showToast('✨ Content refined successfully');
        } catch (e) { this.showToast('Refine failed', 'danger'); }
    },

    closeModal(id) { document.getElementById(id).style.display = 'none'; },

    closeReview() {
        if (this.isDirty) this.saveCurrentEdits();
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
    },

    closeExportMenu() {
        const menu = document.getElementById('exportMenu');
        if (menu) menu.style.display = 'none';
    },

    async triggerExport(format) {
        if (!this.currentDraftData?.id) {
            this.showToast('Open a draft in Review to export', 'danger');
            return;
        }
        
        // Paid solutions / Auth Paywall Gate
        import('/js/auth.js').then(async ({ AuthUI }) => {
            if (!AuthUI.token) {
                const paywallModal = document.getElementById('downloadPaywallModal');
                if (paywallModal) {
                    paywallModal.style.display = 'flex';
                    this.closeExportMenu();
                    return;
                }
            }

            try {
                await AutomationAPI.exportDraft(this.currentDraftData.id, format);
                this.showToast(`Downloaded ${String(format).toUpperCase()}`, 'success');
                this.closeExportMenu();
            } catch (err) {
                this.showToast(err.message || 'Export failed', 'danger');
            }
        });
    },
};
