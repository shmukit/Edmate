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

    init() {
        ThemeManager.init();
        this.setupEventListeners();
        this.fetchDrafts();
        window.addEventListener('hashchange', () => this.checkHash());
        // Initial deep link check
        setTimeout(() => this.checkHash(), 400);
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
        
        // Analytics Nav
        document.getElementById('navAnalytics')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.openAnalytics();
        });
        document.getElementById('btnCloseAnalytics')?.addEventListener('click', () => this.closeAnalytics());
    },

    // Mix in modular controllers
    ...DraftController,
    ...ReviewController,
    ...AnalyticsController,
    ...EditorController
};
