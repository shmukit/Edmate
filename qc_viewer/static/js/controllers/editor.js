export const EditorController = {
    renderImageWrapper(base64, fieldId, isSmall = false) {
        if (!base64) {
            return `
                <div class="image-wrapper has-placeholder" style="${isSmall ? 'min-height:30px; margin-bottom:4px;' : ''}" onclick="AutomationUI.triggerImageUpload('${fieldId}')">
                    <div class="image-placeholder">
                        <span>➕ Add Diagram</span>
                    </div>
                </div>
            `;
        }

        return `
            <div class="image-wrapper ${isSmall ? 'image-wrapper-small' : 'image-wrapper-main'}" style="${isSmall ? 'margin-bottom:8px;' : ''}">
                <img src="${base64}" id="img-${fieldId}" />
                <div class="image-actions">
                    <button class="img-btn" onclick="AutomationUI.openImageEditor('${fieldId}')" title="Edit/Crop">✏</button>
                    <button class="img-btn" onclick="AutomationUI.triggerImageUpload('${fieldId}')" title="Replace">🔄</button>
                    <button class="img-btn btn-delete" onclick="AutomationUI.removeImage('${fieldId}')" title="Remove">🗑</button>
                </div>
            </div>
        `;
    },

    removeImage(fieldId) {
        if (!confirm('Remove this diagram?')) return;
        const q = this.currentDraftData.questions[this.currentQuestionIndex];
        q[fieldId] = null;
        this.previewQuestion(this.currentQuestionIndex);
        this.setDirty(true);
    },

    triggerImageUpload(fieldId) {
        this.pendingImageField = fieldId;
        document.getElementById('imageUploadInput').click();
    },

    handleImageUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            const q = this.currentDraftData.questions[this.currentQuestionIndex];
            q[this.pendingImageField] = event.target.result;
            this.previewQuestion(this.currentQuestionIndex);
            e.target.value = ''; // Reset input
            this.setDirty(true);
        };
        reader.readAsDataURL(file);
    },

    async openImageEditor(fieldId) {
        this.editingFieldId = fieldId;
        const q = this.currentDraftData.questions[this.currentQuestionIndex];
        const base64 = q[fieldId];

        document.getElementById('imageEditorModal').style.display = 'flex';
        document.getElementById('editorStatus').textContent = 'Loading...';

        if (!this.canvas) {
            this.canvas = new fabric.Canvas('editorCanvas', {
                width: 800,
                height: 500,
                backgroundColor: '#fff'
            });
            this.initEditorEvents();
        }

        this.canvas.clear();
        this.canvas.isDrawingMode = false;
        this.canvas.backgroundColor = '#fff';

        fabric.Image.fromURL(base64, (img) => {
            const scale = Math.min(780 / img.width, 450 / img.height, 1);
            img.scale(scale);
            // Lock the background image to prevent accidental movement and canvas hit trails
            img.set({ selectable: false, evented: false, name: 'mainImage' });
            this.canvas.add(img);
            this.canvas.centerObject(img);
            this.canvas.renderAll();
            document.getElementById('editorStatus').textContent = `Ready · ${img.width}x${img.height}`;
            this.setEditorTool('select');
        });
    },

    initEditorEvents() {
        this.canvas.on('mouse:down', (o) => {
            if (!this.isCropMode) return;
            
            // Allow native resizing/moving if clicking on the existing crop box
            if (this.cropRect && o.target === this.cropRect) {
                this.isDraggingCrop = false;
                return;
            }

            this.isDraggingCrop = true;
            const pointer = this.canvas.getPointer(o.e);
            this.cropStartX = pointer.x;
            this.cropStartY = pointer.y;
            
            if (!this.cropRect) {
                this.cropRect = new fabric.Rect({
                    fill: 'rgba(14, 165, 233, 0.2)',
                    stroke: '#0ea5e9',
                    strokeWidth: 2,
                    strokeDashArray: [5, 5],
                    visible: false,
                    selectable: true,
                    name: 'cropRect'
                });
                this.canvas.add(this.cropRect);
            }
            
            this.cropRect.set({
                left: this.cropStartX,
                top: this.cropStartY,
                width: 0,
                height: 0,
                visible: true
            });
            this.canvas.setActiveObject(this.cropRect);
        });

        this.canvas.on('mouse:move', (o) => {
            if (!this.isCropMode || !this.isDraggingCrop || !this.cropRect || !this.cropRect.visible) return;
            const pointer = this.canvas.getPointer(o.e);
            
            this.cropRect.set({
                left: Math.min(this.cropStartX, pointer.x),
                top: Math.min(this.cropStartY, pointer.y),
                width: Math.abs(pointer.x - this.cropStartX),
                height: Math.abs(pointer.y - this.cropStartY)
            });
            this.canvas.renderAll();
        });

        this.canvas.on('mouse:up', () => {
            if (this.isCropMode && this.isDraggingCrop && this.cropRect) {
                this.isDraggingCrop = false;
                this.cropRect.setCoords(); // Required for Fabric to recalculate the interactable boundary
                this.canvas.setActiveObject(this.cropRect);
                this.canvas.renderAll();
            }
        });
    },

    setEditorTool(tool) {
        if (!this.canvas) return;
        
        this.canvas.isDrawingMode = false;
        this.canvas.selection = true;
        this.isCropMode = false;

        if (this.cropRect) this.cropRect.visible = false;
        this.canvas.renderAll();

        document.querySelectorAll('.editor-tools .btn').forEach(b => b.classList.remove('active'));
        
        if (tool === 'pencil') {
            this.canvas.isDrawingMode = true;
            this.canvas.freeDrawingBrush = new fabric.PencilBrush(this.canvas);
            this.canvas.freeDrawingBrush.width = 3;
            this.canvas.freeDrawingBrush.color = '#ff0000';
            document.getElementById('toolPencil').classList.add('active');
        } else if (tool === 'highlighter') {
            this.canvas.isDrawingMode = true;
            this.canvas.freeDrawingBrush = new fabric.PencilBrush(this.canvas);
            this.canvas.freeDrawingBrush.width = 24;
            this.canvas.freeDrawingBrush.color = 'rgba(255, 255, 0, 0.35)';
            document.getElementById('toolHighlighter').classList.add('active');
        } else if (tool === 'crop') {
            this.isCropMode = true;
            this.canvas.selection = false;
            document.getElementById('toolCrop').classList.add('active');
        } else {
            document.getElementById('toolSelect').classList.add('active');
        }
    },

    resetEditorCanvas() {
        this.openImageEditor(this.editingFieldId);
    },

    saveImageEditor() {
        let exportData;
        
        if (this.isCropMode && this.cropRect && this.cropRect.visible) {
            const { left, top, width, height } = this.cropRect;
            this.cropRect.visible = false;
            exportData = this.canvas.toDataURL({ left, top, width, height, format: 'png' });
        } else {
            exportData = this.canvas.toDataURL({ format: 'png' });
        }

        const q = this.currentDraftData.questions[this.currentQuestionIndex];
        q[this.editingFieldId] = exportData;
        
        this.closeImageEditor();
        this.previewQuestion(this.currentQuestionIndex);
        this.setDirty(true);
        this.showToast('✨ Diagram ready to save');
    },

    closeImageEditor() {
        document.getElementById('imageEditorModal').style.display = 'none';
        this.editingFieldId = null;
        this.isCropMode = false;
    }
};
