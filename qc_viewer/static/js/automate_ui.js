import { DraftController } from './controllers/drafts.js';
import { ReviewController } from './controllers/review.js';
import { AnalyticsController } from './controllers/analytics.js';
import { EditorController } from './controllers/editor.js';
import { ThemeManager } from './theme.js';

export const AutomationUI = {
    currentDraftData: null,
    currentQuestionIndex: null,
    pollingInterval: null,
    isDirty: false,
    
    // Editor State
    canvas: null,
    editingFieldId: null,
    isCropMode: false,
    isDraggingCrop: false,

    async init() {
        ThemeManager.init();
        this.setupEventListeners();
        this.initByokConfig();
        await this.fetchPipelineConfig();
        this.fetchDrafts();
        window.addEventListener('hashchange', () => this.checkHash());
        // Initial deep link check
        setTimeout(() => this.checkHash(), 400);
    },

    initByokConfig() {
        const savedProvider = localStorage.getItem('edmate-byok-provider');
        const savedKey = localStorage.getItem('edmate-byok-key');
        const savedModel = localStorage.getItem('edmate-byok-model');
        const apiPref = localStorage.getItem('edmate-api-preference');

        const sidebarProvider = document.getElementById('byokProviderSelect');
        const sidebarKey = document.getElementById('byokApiKey');
        const sidebarModel = document.getElementById('byokModelId');

        if (sidebarProvider && savedProvider) sidebarProvider.value = savedProvider;
        if (sidebarKey && savedKey) sidebarKey.value = savedKey;
        if (sidebarModel && savedModel) sidebarModel.value = savedModel;

        // If no preference is set, trigger the onboarding modal
        if (!apiPref) {
            const modal = document.getElementById('byokOnboardingModal');
            if (modal) modal.style.display = 'flex';
        }
    },

    async fetchPipelineConfig() {
        try {
            const resp = await fetch('/api/automate/config');
            if (!resp.ok) throw new Error('Failed to fetch config');
            const config = await resp.json();
            
            if (config.workspace) {
                const curSelect = document.getElementById('curriculumSelect');
                const tableSelect = document.getElementById('targetTableSelect');
                
                if (curSelect && config.workspace.curriculums) {
                    curSelect.innerHTML = config.workspace.curriculums.map(c => 
                        `<option value="${c}">${c}</option>`
                    ).join('');
                }
                
                if (tableSelect && config.workspace.target_tables) {
                    tableSelect.innerHTML = config.workspace.target_tables.map(t => 
                        `<option value="${t.id}">${t.label}</option>`
                    ).join('');
                }

            }

            const engine = (config.extraction_settings && config.extraction_settings.engine) || 'unknown';
            const mode = (config.extraction_settings && config.extraction_settings.question_detection_mode) || '';
            const kit = config.kit_present ? 'present' : 'missing';
            const hint = (config.extraction_hints && config.extraction_hints.summary) || '';
            const warn = (config.extraction_hints && config.extraction_hints.warning) || '';
            const banner = document.getElementById('extractionContextBanner');
            if (banner) {
                const safeEngine = String(engine).replace(/</g, '&lt;');
                const engKey = String(engine).toLowerCase();
                let mainLine = '';
                if (engKey === 'pdf_extract_kit') {
                    mainLine = `<strong>Active extraction engine:</strong> PDF-Extract-Kit <span style="opacity:0.72;font-size:0.82em;">(pdf_extract_kit)</span> · kit: ${kit}`;
                } else {
                    mainLine = `<strong>Active extraction engine:</strong> ${safeEngine}`;
                }
                const det = mode ? ` <span>· detection: ${String(mode).replace(/</g, '&lt;')}</span>` : '';
                const hintHtml = hint ? `<br>${String(hint).replace(/</g, '&lt;')}` : '';
                const warnHtml = warn ? `<br><strong style="color:#f97316;">${String(warn).replace(/</g, '&lt;')}</strong>` : '';
                const bannerTip =
                    'Backend from edmate_config.yaml. For PDF-Extract-Kit, kit means the local checkout under content_gen/tools/PDF-Extract-Kit (layout/diagram support). Other engines do not use that directory.';
                banner.innerHTML = `
                    <div style="display:flex;align-items:flex-start;gap:10px;flex-wrap:wrap;">
                        <div style="flex:1;min-width:0;">${mainLine}${det}${hintHtml}${warnHtml}</div>
                        <span class="info-icon" data-tooltip="${bannerTip.replace(/"/g, '&quot;')}">ⓘ</span>
                    </div>`;
            }
            const footer = document.getElementById('settingsEngineFooter');
            if (footer) {
                const gen = (config.model_routing && config.model_routing.generation) || '—';
                footer.textContent = `Pipeline engine: ${engine} · kit: ${kit} · generation model: ${gen}`;
            }

            const es = config.extraction_settings || {};
            const mr = config.model_routing || {};
            const ws = config.workspace || {};
            const bud = config.budget || {};
            const minQ = es.min_question_number;
            const maxQ = es.max_question_number;
            const qRange = (minQ != null && maxQ != null)
                ? `${minQ}–${maxQ}`
                : (minQ != null && (maxQ === null || maxQ === undefined))
                    ? `${minQ}–∞ (no max)`
                    : '—';

            const setTxt = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.textContent = val == null || val === '' ? '—' : String(val);
            };
            setTxt('cfgEngine', engine);
            setTxt('cfgDetection', mode || '—');
            setTxt('cfgKit', kit);
            setTxt('cfgQuestionRange', qRange);
            setTxt('cfgSubject', ws.default_subject);
            setTxt('cfgCurriculum', ws.default_curriculum);
            setTxt('cfgBudget', bud.max_daily_usd != null ? String(bud.max_daily_usd) : '—');
            setTxt('cfgModelExt', mr.extraction);
            setTxt('cfgModelGen', mr.generation);
            setTxt('cfgModelVal', mr.validation);

            const segRaw = (es.segmentation_preset || '').toString().trim().toLowerCase();
            const segLabel =
                segRaw === 'bangladeshi'
                    ? 'Sections + numbered (legacy id: bangladeshi)'
                    : segRaw === 'numbered_only'
                      ? 'Numbered questions only'
                      : segRaw || '—';
            setTxt('cfgSegmentation', segLabel);

            this.setupTooltips();
        } catch (e) {
            console.error('Error loading pipeline config:', e);
        }
    },

    setupEventListeners() {
        // ThemeManager now handles its own listeners globally during init()
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

        // Draft export (review header)
        document.getElementById('btnExportToggle')?.addEventListener('click', (e) => {
            e.stopPropagation();
            const menu = document.getElementById('exportMenu');
            if (!menu) return;
            const open = menu.style.display === 'flex';
            menu.style.display = open ? 'none' : 'flex';
            menu.style.flexDirection = 'column';
        });
        document.querySelectorAll('#exportMenu [data-fmt]').forEach((btn) => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const fmt = btn.getAttribute('data-fmt');
                if (fmt && this.triggerExport) await this.triggerExport(fmt);
            });
        });
        document.addEventListener('click', (e) => {
            if (e.target.closest('.export-menu')) return;
            const menu = document.getElementById('exportMenu');
            if (menu) menu.style.display = 'none';
        });
        
        // Image Editor Actions
        document.getElementById('closeEditor')?.addEventListener('click', () => this.closeImageEditor());
        document.getElementById('cancelEditor')?.addEventListener('click', () => this.closeImageEditor());
        document.getElementById('saveEditor')?.addEventListener('click', () => this.saveImageEditor());
        
        // Tool Actions
        document.getElementById('toolSelect')?.addEventListener('click', () => this.setEditorTool('select'));
        document.getElementById('toolPencil')?.addEventListener('click', () => this.setEditorTool('pencil'));
        document.getElementById('toolHighlighter')?.addEventListener('click', () => this.setEditorTool('highlighter'));
        document.getElementById('toolCrop')?.addEventListener('click', () => this.setEditorTool('crop'));
        document.getElementById('toolClear')?.addEventListener('click', () => this.resetEditorCanvas());

        // File Upload for Images
        document.getElementById('imageUploadInput')?.addEventListener('change', (e) => this.handleImageUpload(e));

        // BYOK Onboarding Modal Listeners
        const onboardingModal = document.getElementById('byokOnboardingModal');
        const btnOnboardByok = document.getElementById('btnOnboardByok');
        const btnOnboardDefault = document.getElementById('btnOnboardDefault');
        const onboardOptions = document.getElementById('onboardOptions');
        const onboardByokForm = document.getElementById('onboardByokForm');
        const btnBackToOptions = document.getElementById('btnBackToOptions');
        const btnSaveOnboardKeys = document.getElementById('btnSaveOnboardKeys');

        btnOnboardByok?.addEventListener('click', () => {
            if (onboardOptions) onboardOptions.style.display = 'none';
            if (onboardByokForm) onboardByokForm.style.display = 'block';
        });

        btnOnboardDefault?.addEventListener('click', () => {
            localStorage.setItem('edmate-api-preference', 'default');
            if (onboardingModal) onboardingModal.style.display = 'none';
            const sidebarKey = document.getElementById('byokApiKey');
            if (sidebarKey) sidebarKey.value = '';
        });

        btnBackToOptions?.addEventListener('click', () => {
            if (onboardByokForm) onboardByokForm.style.display = 'none';
            if (onboardOptions) onboardOptions.style.display = 'flex';
        });

        btnSaveOnboardKeys?.addEventListener('click', () => {
            const provider = document.getElementById('onboardProviderSelect')?.value || 'gemini';
            const key = document.getElementById('onboardApiKey')?.value || '';
            
            if (!key) {
                alert('Please enter a valid API key.');
                return;
            }

            localStorage.setItem('edmate-byok-provider', provider);
            localStorage.setItem('edmate-byok-key', key);
            localStorage.setItem('edmate-api-preference', 'byok');

            const sidebarProvider = document.getElementById('byokProviderSelect');
            const sidebarKey = document.getElementById('byokApiKey');
            if (sidebarProvider) sidebarProvider.value = provider;
            if (sidebarKey) sidebarKey.value = key;

            if (onboardingModal) onboardingModal.style.display = 'none';
        });

        // Paywall Modal listeners
        const paywallModal = document.getElementById('downloadPaywallModal');
        const btnPaywallByok = document.getElementById('btnPaywallByok');
        const btnClosePaywall = document.getElementById('btnClosePaywall');

        btnPaywallByok?.addEventListener('click', () => {
            if (paywallModal) paywallModal.style.display = 'none';
            if (onboardingModal) {
                const savedKey = localStorage.getItem('edmate-byok-key') || '';
                const savedProvider = localStorage.getItem('edmate-byok-provider') || 'gemini';
                const onboardApiKey = document.getElementById('onboardApiKey');
                const onboardProviderSelect = document.getElementById('onboardProviderSelect');
                if (onboardApiKey) onboardApiKey.value = savedKey;
                if (onboardProviderSelect) onboardProviderSelect.value = savedProvider;

                if (onboardOptions) onboardOptions.style.display = 'none';
                if (onboardByokForm) onboardByokForm.style.display = 'block';
                onboardingModal.style.display = 'flex';
            }
        });

        btnClosePaywall?.addEventListener('click', () => {
            if (paywallModal) paywallModal.style.display = 'none';
        });

        // Analytics Nav
        document.getElementById('navAnalytics')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.openAnalytics();
        });
        document.getElementById('btnCloseAnalytics')?.addEventListener('click', () => this.closeAnalytics());

        document.getElementById('btnCloseAnalytics')?.addEventListener('click', () => this.closeAnalytics());

        // Settings section collapse/expand (bound directly for reliability)
        document.querySelectorAll('.settings-group-toggle').forEach((toggle) => {
            toggle.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();

                const group = toggle.closest('.settings-group-collapsible');
                if (!group) return;

                const expanded = group.classList.toggle('settings-group-expanded');
                toggle.setAttribute('aria-expanded', String(expanded));

                const icon = toggle.querySelector('.settings-group-toggle-icon');
                if (icon) icon.textContent = expanded ? '−' : '+';
            };
        });

        document.getElementById('btnRefreshPipelineConfig')?.addEventListener('click', () => {
            this.fetchPipelineConfig();
        });
        
        this.setupTooltips();
    },

    setupTooltips() {
        // Create global tooltip if it doesn't exist
        let tooltip = document.getElementById('globalTooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'globalTooltip';
            tooltip.className = 'floating-tooltip';
            document.body.appendChild(tooltip);
        }

        const icons = document.querySelectorAll('.info-icon[data-tooltip]:not([data-tooltip-bound])');
        icons.forEach(icon => {
            icon.setAttribute('data-tooltip-bound', '1');
            icon.addEventListener('mouseenter', (e) => {
                const text = icon.getAttribute('data-tooltip');
                const rect = icon.getBoundingClientRect();
                
                tooltip.textContent = text;
                tooltip.classList.add('active');
                
                // Position tooltip above the icon, growing leftward
                const tooltipRect = tooltip.getBoundingClientRect();
                tooltip.style.top = `${rect.top - tooltipRect.height - 10}px`;
                tooltip.style.left = `${rect.left - tooltipRect.width + 10}px`;
            });

            icon.addEventListener('mouseleave', () => {
                tooltip.classList.remove('active');
            });
        });
    },

    async openPedagogy() {
        const overlay = document.getElementById('pedagogyOverlay');
        const content = document.getElementById('pedagogyContent');
        overlay.style.display = 'block';
        
        try {
            const resp = await fetch('/docs/PEDAGOGY.md');
            const md = await resp.text();
            content.innerHTML = marked.parse(md);
            if (window.MathJax) MathJax.typesetPromise([content]);
        } catch (e) {
            content.innerHTML = '<div class="alert alert-danger">Failed to load pedagogy documentation.</div>';
        }
    },

    // Mix in modular controllers
    ...DraftController,
    ...ReviewController,
    ...AnalyticsController,
    ...EditorController
};
