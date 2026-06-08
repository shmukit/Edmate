/**
 * Edmate Authentication & User Profile UI
 * Handles login modal, session persistence (JWT in memory), and UI state updates.
 */

export const AuthUI = {
    token: null,
    userProfile: null,

    init() {
        this.checkSession();
        this.setupListeners();
    },

    setupListeners() {
        const btnLogin = document.getElementById('btnLoginNav');
        const btnLogout = document.getElementById('btnLogout');
        const modal = document.getElementById('authModal');
        const closeBtn = document.getElementById('closeAuthModal');
        const authForm = document.getElementById('authForm');
        
        if (btnLogin) btnLogin.addEventListener('click', () => this.openModal());
        if (closeBtn) closeBtn.addEventListener('click', () => this.closeModal());
        if (btnLogout) btnLogout.addEventListener('click', () => this.logout());
        
        if (authForm) {
            authForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleAuthSubmit();
            });
        }
        
        // Tab switching
        const tabs = document.querySelectorAll('.auth-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                tabs.forEach(t => t.classList.remove('active'));
                e.target.classList.add('active');
                
                const mode = e.target.dataset.mode; // 'login' or 'signup'
                const btnSubmit = document.getElementById('btnAuthSubmit');
                if (btnSubmit) {
                    btnSubmit.textContent = mode === 'login' ? 'Sign In' : 'Create Account';
                }
            });
        });
    },

    openModal() {
        const modal = document.getElementById('authModal');
        if (modal) modal.style.display = 'flex';
    },

    closeModal() {
        const modal = document.getElementById('authModal');
        if (modal) modal.style.display = 'none';
        
        const errorEl = document.getElementById('authError');
        if (errorEl) errorEl.style.display = 'none';
    },

    async handleAuthSubmit() {
        const email = document.getElementById('authEmail')?.value;
        const password = document.getElementById('authPassword')?.value;
        const errorEl = document.getElementById('authError');
        const btnSubmit = document.getElementById('btnAuthSubmit');
        
        if (!email || !password) return;
        
        // This is a placeholder for the actual auth provider call.
        // For now, we simulate a successful login to unblock the UI.
        
        const activeTab = document.querySelector('.auth-tab.active');
        const mode = activeTab ? activeTab.dataset.mode : 'login';
        
        try {
            btnSubmit.disabled = true;
            btnSubmit.textContent = 'Please wait...';
            errorEl.style.display = 'none';
            
            // SIMULATED AUTH DELAY
            await new Promise(resolve => setTimeout(resolve, 800));
            
            // Simulate receiving a token and profile
            this.token = "simulated_jwt_token_for_" + email;
            this.userProfile = {
                user_id: "user_" + Date.now().toString(36),
                email: email,
                display_name: email.split('@')[0],
                plan: "free" // Default to free plan
            };
            
            // In a real implementation, you would store a refresh token in httpOnly cookie
            // and the short-lived access token in memory.
            // For this demo, we use sessionStorage
            sessionStorage.setItem('edmate_token', this.token);
            sessionStorage.setItem('edmate_profile', JSON.stringify(this.userProfile));
            
            this.updateUIState();
            this.closeModal();
            
            if (window.AutomationUI && window.AutomationUI.showToast) {
                window.AutomationUI.showToast(`Successfully signed in as ${this.userProfile.display_name}`);
            }
            
            // Refresh drafts to show user-scoped drafts
            if (window.AutomationUI) {
                window.AutomationUI.fetchDrafts();
            }
            
        } catch (error) {
            errorEl.textContent = error.message || 'Authentication failed. Please try again.';
            errorEl.style.display = 'block';
        } finally {
            btnSubmit.disabled = false;
            btnSubmit.textContent = mode === 'login' ? 'Sign In' : 'Create Account';
        }
    },

    logout() {
        this.token = null;
        this.userProfile = null;
        sessionStorage.removeItem('edmate_token');
        sessionStorage.removeItem('edmate_profile');
        
        this.updateUIState();
        
        if (window.AutomationUI && window.AutomationUI.showToast) {
            window.AutomationUI.showToast('You have been signed out.');
        }
        
        // Refresh drafts to show anonymous drafts
        if (window.AutomationUI) {
            window.AutomationUI.fetchDrafts();
        }
    },

    checkSession() {
        const token = sessionStorage.getItem('edmate_token');
        const profileStr = sessionStorage.getItem('edmate_profile');
        
        if (token && profileStr) {
            try {
                this.token = token;
                this.userProfile = JSON.parse(profileStr);
            } catch (e) {
                this.logout();
            }
        }
        
        this.updateUIState();
    },

    updateUIState() {
        const navLogin = document.getElementById('navLoginBtn');
        const navProfile = document.getElementById('navUserProfile');
        const profileName = document.getElementById('profileName');
        const profilePlan = document.getElementById('profilePlan');
        const anonBanner = document.getElementById('anonymousWarningBanner');
        
        if (this.token && this.userProfile) {
            // User is logged in
            if (navLogin) navLogin.style.display = 'none';
            if (navProfile) navProfile.style.display = 'flex';
            if (anonBanner) anonBanner.style.display = 'none';
            
            if (profileName) profileName.textContent = this.userProfile.display_name || this.userProfile.email;
            
            if (profilePlan) {
                profilePlan.textContent = String(this.userProfile.plan).toUpperCase();
                // Set badge color based on plan
                profilePlan.className = 'plan-badge ' + (this.userProfile.plan === 'pro' ? 'plan-pro' : (this.userProfile.plan === 'basic' ? 'plan-basic' : 'plan-free'));
            }
        } else {
            // User is anonymous
            if (navLogin) navLogin.style.display = 'block';
            if (navProfile) navProfile.style.display = 'none';
            
            // Only show banner if we are not in self-hosted mode
            // We can infer this if the user hasn't actively dismissed it
            if (anonBanner && !sessionStorage.getItem('edmate_dismiss_anon_banner')) {
                anonBanner.style.display = 'flex';
            }
        }
    },

    getAuthHeaders() {
        const headers = {};
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        return headers;
    }
};
