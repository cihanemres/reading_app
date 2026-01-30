/**
 * Loading Utilities
 * Provides helper functions for loading states and animations
 */
const LoadingUtils = {
    /**
     * Show full-page spinner overlay
     * @param {string} message - Loading message to display
     */
    showSpinner(message = 'Yükleniyor...') {
        // Remove existing overlay if any
        this.hideSpinner();

        const overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'spinner-overlay';
        overlay.innerHTML = `
            <div class="spinner-wrapper">
                <div class="spinner-large"></div>
                <p class="loading-text" style="color: white;">${message}</p>
            </div>
        `;

        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden';
    },

    /**
     * Hide spinner overlay
     */
    hideSpinner() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.remove();
            document.body.style.overflow = '';
        }
    },

    /**
     * Create skeleton card HTML
     * @param {number} count - Number of skeleton cards to create
     * @returns {string} HTML string
     */
    createSkeletonCards(count = 3) {
        let html = '';
        for (let i = 0; i < count; i++) {
            html += `
                <div class="skeleton-card fade-in" style="animation-delay: ${i * 0.1}s">
                    <div class="skeleton skeleton-title"></div>
                    <div class="skeleton skeleton-text"></div>
                    <div class="skeleton skeleton-text"></div>
                    <div class="skeleton skeleton-text"></div>
                </div>
            `;
        }
        return html;
    },

    /**
     * Create skeleton list item HTML
     * @param {number} count - Number of items
     * @returns {string} HTML string
     */
    createSkeletonList(count = 5) {
        let html = '';
        for (let i = 0; i < count; i++) {
            html += `
                <div class="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg mb-3">
                    <div class="skeleton skeleton-avatar"></div>
                    <div class="flex-1">
                        <div class="skeleton skeleton-text" style="width: 40%; margin-bottom: 8px;"></div>
                        <div class="skeleton skeleton-text" style="width: 60%;"></div>
                    </div>
                </div>
            `;
        }
        return html;
    },

    /**
     * Fade in element
     * @param {HTMLElement} element - Element to animate
     * @param {number} duration - Animation duration in ms
     */
    fadeIn(element, duration = 300) {
        if (!element) return;

        element.style.opacity = '0';
        element.style.display = '';
        element.classList.add('fade-in');

        // Remove animation class after completion
        setTimeout(() => {
            element.classList.remove('fade-in');
            element.style.opacity = '';
        }, duration);
    },

    /**
     * Fade in multiple elements with stagger
     * @param {NodeList|Array} elements - Elements to animate
     * @param {number} staggerDelay - Delay between each element in ms
     */
    fadeInStagger(elements, staggerDelay = 50) {
        elements.forEach((element, index) => {
            setTimeout(() => {
                this.fadeIn(element);
            }, index * staggerDelay);
        });
    },

    /**
     * Show loading state on button
     * @param {HTMLElement} button - Button element
     * @param {string} originalText - Original button text (optional)
     */
    setButtonLoading(button, originalText = null) {
        if (!button) return;

        if (originalText) {
            button.dataset.originalText = originalText;
        } else {
            button.dataset.originalText = button.textContent;
        }

        button.disabled = true;
        button.classList.add('btn-loading');
    },

    /**
     * Remove loading state from button
     * @param {HTMLElement} button - Button element
     */
    removeButtonLoading(button) {
        if (!button) return;

        button.disabled = false;
        button.classList.remove('btn-loading');

        if (button.dataset.originalText) {
            button.textContent = button.dataset.originalText;
            delete button.dataset.originalText;
        }
    },

    /**
     * Update progress bar
     * @param {HTMLElement} progressBar - Progress bar element
     * @param {number} percentage - Progress percentage (0-100)
     */
    updateProgress(progressBar, percentage) {
        if (!progressBar) return;

        const fill = progressBar.querySelector('.progress-fill');
        if (fill) {
            fill.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
        }
    },

    /**
     * Create and show toast notification
     * @param {string} message - Message to display
     * @param {string} type - Type: 'success', 'error', 'info', 'warning'
     * @param {number} duration - Duration in ms
     */
    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type} fade-in`;
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            padding: 16px 24px;
            background: ${this.getToastColor(type)};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            max-width: 400px;
        `;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    /**
     * Get toast background color based on type
     * @param {string} type - Toast type
     * @returns {string} Color value
     */
    getToastColor(type) {
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };
        return colors[type] || colors.info;
    },

    /**
     * Smooth scroll to element
     * @param {HTMLElement|string} target - Element or selector
     * @param {number} offset - Offset from top in px
     */
    smoothScrollTo(target, offset = 0) {
        const element = typeof target === 'string'
            ? document.querySelector(target)
            : target;

        if (!element) return;

        const top = element.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({
            top: top,
            behavior: 'smooth'
        });
    }
};

// Auto-initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('LoadingUtils initialized');
    });
} else {
    console.log('LoadingUtils initialized');
}

