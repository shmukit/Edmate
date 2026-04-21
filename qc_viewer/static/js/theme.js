export const ThemeManager = {
    init() {
        const savedTheme = localStorage.getItem('edmate-theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        this.setupEventListeners();
    },

    setupEventListeners() {
        if (this._initialized) return;
        this._initialized = true;

        document.addEventListener('click', (e) => {
            const toggle = e.target.closest('#themeToggle');
            if (toggle) {
                this.toggleTheme();
            }
        });
    },

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('edmate-theme', newTheme);
        
        // Optional: Dispatch event for other components
        window.dispatchEvent(new CustomEvent('themechanged', { detail: { theme: newTheme } }));
        
        if (window.AutomationUI && window.AutomationUI.showToast) {
            window.AutomationUI.showToast(`Switched to ${newTheme} mode`);
        }
    }
};
