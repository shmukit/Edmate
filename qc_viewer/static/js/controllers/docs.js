/**
 * Edmate Documentation Controller
 * Manages fetching and rendering documentation sections.
 */

export const DocsController = {
    sections: {
        pedagogy: '/docs/pedagogy/PEDAGOGY.md',
        extraction: '/docs/technical/ARCHITECTURE.md', 
        routing: '/docs/technical/ARCHITECTURE.md',
        hia: '/docs/pedagogy/PEDAGOGY.md'
    },

    init() {
        this.renderSection('pedagogy');
        this.setupListeners();
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
            
            // Re-render MathJax
            if (window.MathJax) {
                MathJax.typesetPromise([content]);
            }

            // Scroll to top of content
            content.scrollTop = 0;
            
        } catch (e) {
            content.innerHTML = `
                <div style="text-align: center; padding: 40px;">
                    <h2 style="color: var(--danger);">Coming Soon</h2>
                    <p style="color: var(--text-dim);">The <b>${id}</b> documentation section is currently being finalized.</p>
                </div>
            `;
        }
    }
};
