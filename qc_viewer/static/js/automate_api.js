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

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/automate/draft', true);

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
    }
};
