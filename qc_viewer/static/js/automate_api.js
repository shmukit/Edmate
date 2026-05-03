/**
 * Edmate Automation API Service
 * Handles all communication with the FastAPI backend.
 */

export const AutomationAPI = {
    async uploadPDF(file, subject, paperCode, onProgress) {
        return new Promise((resolve, reject) => {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('subject', subject);
            formData.append('paper_code', paperCode);

            // Read pedagogy settings from UI
            const curriculum = document.getElementById('curriculumSelect')?.value || '';
            const lsProfile = document.getElementById('lsProfileSelect')?.value || 'default';
            const hiaMode = document.getElementById('hiaResilienceSelect')?.value || 'Low';
            formData.append('curriculum', curriculum);
            formData.append('ls_profile', lsProfile);
            formData.append('hia_mode', hiaMode);

            const detectionMode = document.getElementById('questionDetectionModeSelect')?.value || '';
            const minQ = document.getElementById('minQuestionNumberInput')?.value || '';
            const maxQ = document.getElementById('maxQuestionNumberInput')?.value || '';
            if (detectionMode) formData.append('question_detection_mode', detectionMode);
            if (minQ) formData.append('min_question_number', minQ);
            if (maxQ) formData.append('max_question_number', maxQ);

            // Read BYOK settings from UI (session-only, never persisted)
            const providerHint = document.getElementById('providerSelect')?.value;
            const byokProvider = document.getElementById('byokProviderSelect')?.value;
            const byokKey = document.getElementById('byokApiKey')?.value;
            const byokModel = document.getElementById('byokModelId')?.value;

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/automate/draft', true);

            // Only set BYOK headers if the user provided a key
            if (byokKey) {
                const resolvedProvider = byokProvider || providerHint;
                if (resolvedProvider) xhr.setRequestHeader('X-LLM-Provider', resolvedProvider);
                xhr.setRequestHeader('X-API-Key', byokKey);
                if (byokModel)    xhr.setRequestHeader('X-Model-ID', byokModel);
            }

            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable && onProgress) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    onProgress(percent);
                }
            };

            xhr.onload = () => {
                if (xhr.status === 200) {
                    resolve(JSON.parse(xhr.responseText));
                } else {
                    reject(new Error(xhr.statusText));
                }
            };

            xhr.onerror = () => reject(new Error('Network error during upload'));
            xhr.send(formData);
        });
    },

    async fetchDrafts() {
        const response = await fetch('/api/automate/drafts');
        if (!response.ok) throw new Error('Failed to fetch drafts');
        return await response.json();
    },

    async getDraft(id) {
        const response = await fetch(`/api/automate/draft/${id}`);
        if (!response.ok) throw new Error('Failed to fetch draft detail');
        return await response.json();
    },

    async updateDraft(id, updates) {
        const response = await fetch(`/api/automate/draft/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });
        if (!response.ok) throw new Error('Failed to update draft');
        return await response.json();
    },

    async deleteDraft(id) {
        const response = await fetch(`/api/automate/draft/${id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Failed to delete draft');
        return await response.json();
    },

    async stopDraft(id) {
        const response = await fetch(`/api/automate/draft/${id}/stop`, { method: 'POST' });
        if (!response.ok) throw new Error('Failed to stop processing');
        return await response.json();
    },

    async publishQuestion(payload) {
        // payload: { draft_id, table_name, question_data }
        const response = await fetch('/api/automate/publish', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Publishing failed');
        return result;
    },

    async refineQuestion(payload) {
        // payload: { feedback, original_q }
        const response = await fetch('/api/automate/refine', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Refinement failed');
        return result;
    },

    /**
     * Download draft metadata (format: json | csv | markdown | md | mdzip | docx).
     */
    async exportDraft(id, format) {
        const q = format === 'markdown' ? 'markdown' : format;
        const resp = await fetch(`/api/automate/draft/${encodeURIComponent(id)}/export?format=${encodeURIComponent(q)}`);
        if (!resp.ok) {
            let detail = `Export failed (${resp.status})`;
            try {
                const err = await resp.json();
                if (err.detail) detail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
            } catch (_) { /* ignore */ }
            throw new Error(detail);
        }
        const blob = await resp.blob();
        const cd = resp.headers.get('Content-Disposition') || '';
        const match = cd.match(/filename="([^"]+)"/);
        const ext =
            format === 'markdown' || format === 'md'
                ? 'md'
                : format === 'mdzip'
                  ? 'zip'
                  : format === 'csv'
                    ? 'csv'
                    : format === 'docx'
                      ? 'docx'
                      : 'json';
        const filename = match ? match[1] : `draft_${id}.${ext}`;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.rel = 'noopener';
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    }
};
