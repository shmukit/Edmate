export const LayoutManager = {
    init() {
        this.setupEventListeners();
        this.restoreState();
    },

    setupEventListeners() {
        // Shared Layout Handlers (using delegation for robustness)
        document.addEventListener('click', (e) => {
            // Sidebar Collapse
            const collapseBtn = e.target.closest('#btnCollapseSidebar');
            if (collapseBtn) {
                this.toggleSidebar();
                return;
            }

            // Settings Panel Toggle
            const settingsToggle = e.target.closest('#btnToggleSettings');
            if (settingsToggle) {
                this.toggleSettings();
            }
        });
    },

    toggleSidebar() {
        const aside = document.querySelector('aside');
        if (!aside) return;
        
        aside.classList.toggle('collapsed');
        const isCollapsed = aside.classList.contains('collapsed');
        localStorage.setItem('edmate-sidebar-collapsed', isCollapsed);
        
        // Dispatch event for layout shifts if needed
        window.dispatchEvent(new CustomEvent('layoutresize'));
    },

    toggleSettings() {
        const panel = document.querySelector('.settings-panel');
        if (!panel) return;
        
        panel.classList.toggle('hidden');
        const isHidden = panel.classList.contains('hidden');
        localStorage.setItem('edmate-settings-hidden', isHidden);
    },

    restoreState() {
        // Restore Sidebar
        const aside = document.querySelector('aside');
        if (aside && localStorage.getItem('edmate-sidebar-collapsed') === 'true') {
            aside.classList.add('collapsed');
        }

        // Restore Settings
        const panel = document.querySelector('.settings-panel');
        if (panel && localStorage.getItem('edmate-settings-hidden') === 'true') {
            panel.classList.add('hidden');
        }
    }
};
