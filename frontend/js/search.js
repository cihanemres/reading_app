const SearchUtils = {
    /**
     * Debounce function to limit API calls
     * @param {Function} func - Function to debounce
     * @param {number} wait - Delay in milliseconds
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Setup search input listener
     * @param {string} inputId - ID of the search input element
     * @param {Function} callback - Function to call with search value
     * @param {number} delay - Debounce delay (default 300ms)
     */
    setupSearch(inputId, callback, delay = 300) {
        const input = document.getElementById(inputId);
        if (!input) {
            console.warn(`Search input with ID '${inputId}' not found`);
            return;
        }

        input.addEventListener('input', this.debounce((e) => {
            const value = e.target.value.trim();
            // Pass null instead of empty string
            callback(value === '' ? null : value);
        }, delay));
    }
};

