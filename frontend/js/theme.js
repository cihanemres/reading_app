/**
 * Theme Manager
 * Handles dark/light theme switching with localStorage persistence
 */
const ThemeManager = {
    /**
     * Initialize theme system
     */
    init() {
        // Load saved theme or default to light
        const savedTheme = localStorage.getItem('theme') || 'light';
        this.setTheme(savedTheme, false);
        this.setupToggleButton();
    },

    /**
     * Set theme and save to localStorage
     * @param {string} theme - 'light' or 'dark'
     * @param {boolean} animate - Whether to animate the transition
     */
    setTheme(theme, animate = true) {
        const root = document.documentElement;

        if (!animate) {
            root.classList.add('no-transition');
        }

        root.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        this.updateToggleButton(theme);

        if (!animate) {
            // Force reflow
            root.offsetHeight;
            root.classList.remove('no-transition');
        }
    },

    /**
     * Toggle between light and dark theme
     */
    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    },

    /**
     * Setup theme toggle button event listener
     */
    setupToggleButton() {
        const button = document.getElementById('themeToggle');
        if (button) {
            button.addEventListener('click', () => this.toggleTheme());
        }
    },

    /**
     * Update toggle button icon based on current theme
     * @param {string} theme - Current theme
     */
    updateToggleButton(theme) {
        const button = document.getElementById('themeToggle');
        if (button) {
            const icon = button.querySelector('i');
            if (icon) {
                if (theme === 'dark') {
                    icon.className = 'fas fa-sun text-yellow-400';
                } else {
                    icon.className = 'fas fa-moon text-gray-600';
                }
            }
        }
    }
};

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => ThemeManager.init());
} else {
    ThemeManager.init();
}

