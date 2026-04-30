/**
 * Edmate Documentation Controller
 * Manages fetching and rendering documentation sections.
 */

export const DocsController = {
    sections: {
        pedagogy: '/docs/pedagogy/PEDAGOGY.md',
        extraction: '/docs/technical/ARCHITECTURE.md', 
        routing: '/docs/technical/SYSTEM_DESIGN.md',
        hia: '/docs/pedagogy/PEDAGOGY.md',
        pipeline_settings: '/docs/technical/PIPELINE_SETTINGS.md'
    },
    sectionTitles: {
        pedagogy: 'Learning Science (Pedagogy)',
        extraction: 'Vision Extraction Pipeline',
        routing: 'AI Model Routing',
        hia: 'High-Impact Accuracy (HIA)',
        pipeline_settings: 'Pipeline Settings'
    },

    init() {
        this.configureMarkdownRenderer();
        this.initializeMermaid();
        this.renderSection('pedagogy');
        this.setupListeners();
    },

    configureMarkdownRenderer() {
        if (!window.marked) return;

        // Force GFM so tables/fenced code are parsed consistently.
        marked.setOptions({
            gfm: true,
            breaks: true
        });

        const renderer = new marked.Renderer();
        renderer.code = (codeOrToken, infostring) => {
            const code = typeof codeOrToken === 'object' ? (codeOrToken.text || '') : codeOrToken;
            const tokenLang = typeof codeOrToken === 'object' ? codeOrToken.lang : '';
            const lang = (tokenLang || infostring || '').trim().toLowerCase();
            if (lang === 'mermaid') {
                return `<div class="mermaid">${code}</div>`;
            }
            return `<pre><code>${this.escapeHtml(code)}</code></pre>`;
        };
        marked.use({ renderer });
    },

    initializeMermaid() {
        if (!window.mermaid) return;
        window.mermaid.initialize({
            startOnLoad: false,
            theme: 'dark',
            securityLevel: 'loose'
        });
    },

    setupListeners() {
        document.querySelectorAll('.doc-nav-item').forEach(item => {
            item.onclick = () => {
                const section = item.dataset.section;
                this.renderSection(section);
                
                // Update active state
                document.querySelectorAll('.doc-nav-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
            };
        });
    },

    async renderSection(id) {
        const content = document.getElementById('docContent');
        const url = this.sections[id];
        
        try {
            const resp = await fetch(url);
            if (!resp.ok) throw new Error('Document not found');
            const md = await resp.text();
            
            content.innerHTML = marked.parse(md);
            await this.renderMermaid(content);
            
            // Re-render MathJax
            if (window.MathJax) {
                MathJax.typesetPromise([content]);
            }

            // Scroll to top of content
            content.scrollTop = 0;
            this.updateBreadcrumb(id);
            
        } catch (e) {
            content.innerHTML = `
                <div style="text-align: center; padding: 40px;">
                    <h2 style="color: var(--danger);">Coming Soon</h2>
                    <p style="color: var(--text-dim);">The <b>${id}</b> documentation section is currently being finalized.</p>
                </div>
            `;
            this.updateBreadcrumb(id);
        }
    },

    updateBreadcrumb(id) {
        const active = document.getElementById('activeDocBreadcrumb');
        if (!active) return;
        active.textContent = this.sectionTitles[id] || 'Documentation';
    },

    async renderMermaid(container) {
        if (!window.mermaid) return;
        const nodes = container.querySelectorAll('.mermaid');
        if (!nodes.length) return;
        try {
            await window.mermaid.run({ nodes: Array.from(nodes) });
        } catch (e) {
            console.warn('Mermaid render failed:', e);
        }
    },

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        };
        return String(text).replace(/[&<>"']/g, (m) => map[m]);
    }
};
