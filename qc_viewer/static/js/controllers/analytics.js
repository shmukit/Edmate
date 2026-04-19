import { AutomationAPI } from '../automate_api.js';

export const AnalyticsController = {
    async openAnalytics() {
        window.location.hash = 'analytics';
        document.getElementById('analyticsPanel').classList.add('active');
        this.updateAnalytics();
    },

    closeAnalytics() {
        document.getElementById('analyticsPanel').classList.remove('active');
        window.location.hash = '';
    },

    async updateAnalytics() {
        try {
            const drafts = await AutomationAPI.fetchDrafts();
            
            // Calculate Stats
            const totalDrafts = drafts.length;
            const processed = drafts.filter(d => d.status === 'PROCESSED' || d.status === 'COMPLETED').length;
            let totalQ = 0;
            let injectedQ = 0;
            let rejectedQ = 0;

            drafts.forEach(d => {
                if (d.questions) {
                    totalQ += d.questions.length;
                    injectedQ += d.questions.filter(q => q.status === 'INJECTED').length;
                    rejectedQ += d.questions.filter(q => q.status === 'REJECTED').length;
                }
            });

            const injectionRate = totalQ > 0 ? Math.round((injectedQ / totalQ) * 100) : 0;

            // Render Stats
            document.getElementById('statTotalDrafts').textContent = totalDrafts;
            document.getElementById('statProcessed').textContent = processed;
            document.getElementById('statInjected').textContent = injectedQ;
            document.getElementById('statRejected').textContent = rejectedQ;
            document.getElementById('statTotalQuestions').textContent = totalQ;
            document.getElementById('statInjectionRate').textContent = injectionRate + '%';

            // Render Activity Feed
            const activityFeed = document.getElementById('analyticsActivity');
            if (drafts.length === 0) {
                activityFeed.innerHTML = '<div class="subtitle">No recent activity</div>';
                return;
            }

            const recentDrafts = [...drafts].sort((a,b) => b.created_at - a.created_at).slice(0, 10);
            activityFeed.innerHTML = recentDrafts.map(d => {
                const date = new Date(parseFloat(d.created_at) * 1000).toLocaleDateString();
                const qCount = d.questions ? d.questions.length : 0;
                return `
                    <div class="activity-row">
                        <div class="activity-name">${d.filename}</div>
                        <div class="activity-meta">
                            <span class="activity-questions">${qCount} Questions</span>
                            <span>${date}</span>
                            <span class="status-badge status-${d.status.toLowerCase()}">${d.status}</span>
                        </div>
                    </div>
                `;
            }).join('');

        } catch (error) {
            console.error('Analytics update failed:', error);
        }
    }
};
