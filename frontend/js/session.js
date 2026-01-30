// Session Management Utilities
// Handles token expiry, auto-logout, and session refresh

const SessionManager = {
    // Session timeout in milliseconds (30 minutes)
    SESSION_TIMEOUT: 30 * 60 * 1000,

    // Check interval (every 5 minutes)
    CHECK_INTERVAL: 5 * 60 * 1000,

    // Warning before timeout (5 minutes)
    WARNING_BEFORE: 5 * 60 * 1000,

    lastActivity: Date.now(),
    timeoutId: null,
    warningShown: false,

    /**
     * Initialize session management
     */
    init() {
        // Track user activity
        ['click', 'keypress', 'scroll', 'mousemove'].forEach(event => {
            document.addEventListener(event, () => this.updateActivity(), { passive: true });
        });

        // Start session check
        this.startSessionCheck();

        // Check token validity on page load
        this.verifyToken();

        console.log('Session manager initialized');
    },

    /**
     * Update last activity timestamp
     */
    updateActivity() {
        this.lastActivity = Date.now();
        this.warningShown = false;
    },

    /**
     * Start periodic session check
     */
    startSessionCheck() {
        this.timeoutId = setInterval(() => {
            this.checkSession();
        }, this.CHECK_INTERVAL);
    },

    /**
     * Check session status
     */
    checkSession() {
        const timeSinceActivity = Date.now() - this.lastActivity;

        // Show warning 5 minutes before timeout
        if (timeSinceActivity >= this.SESSION_TIMEOUT - this.WARNING_BEFORE && !this.warningShown) {
            this.showTimeoutWarning();
            this.warningShown = true;
        }

        // Auto logout after timeout
        if (timeSinceActivity >= this.SESSION_TIMEOUT) {
            this.handleTimeout();
        }
    },

    /**
     * Verify token with server
     */
    async verifyToken() {
        const token = localStorage.getItem('token');
        if (!token) return;

        try {
            const response = await fetch(`${API_BASE_URL}/auth/verify-token`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                // Token is invalid or expired
                this.handleInvalidToken();
            }
        } catch (error) {
            console.error('Token verification failed:', error);
        }
    },

    /**
     * Show session timeout warning
     */
    showTimeoutWarning() {
        const modal = document.createElement('div');
        modal.id = 'sessionWarningModal';
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-xl p-6 max-w-md mx-4 text-center">
                <i class="fas fa-clock text-5xl text-yellow-500 mb-4"></i>
                <h3 class="text-xl font-bold text-gray-800 mb-2">Oturum Süreniz Doluyor</h3>
                <p class="text-gray-600 mb-4">5 dakika içinde aktivite olmazsa oturumunuz sonlandırılacak.</p>
                <button onclick="SessionManager.dismissWarning()" 
                    class="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700 transition">
                    Devam Et
                </button>
            </div>
        `;
        document.body.appendChild(modal);
    },

    /**
     * Dismiss warning and refresh activity
     */
    dismissWarning() {
        const modal = document.getElementById('sessionWarningModal');
        if (modal) modal.remove();
        this.updateActivity();
    },

    /**
     * Handle session timeout
     */
    handleTimeout() {
        clearInterval(this.timeoutId);
        localStorage.removeItem('token');
        localStorage.removeItem('user');

        // Show timeout message
        alert('Oturumunuz zaman aşımına uğradı. Lütfen tekrar giriş yapın.');
        window.location.href = '/login.html';
    },

    /**
     * Handle invalid/expired token
     */
    handleInvalidToken() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login.html';
    },

    /**
     * Stop session management (on logout)
     */
    stop() {
        if (this.timeoutId) {
            clearInterval(this.timeoutId);
        }
    }
};

// Password utilities
const PasswordUtils = {
    /**
     * Validate password strength
     * @returns {Object} { isValid: boolean, errors: string[] }
     */
    validatePassword(password) {
        const errors = [];

        if (password.length < 6) {
            errors.push('En az 6 karakter olmalıdır');
        }
        if (!/[A-Z]/.test(password)) {
            errors.push('En az bir büyük harf içermelidir');
        }
        if (!/[0-9]/.test(password)) {
            errors.push('En az bir rakam içermelidir');
        }

        return {
            isValid: errors.length === 0,
            errors
        };
    },

    /**
     * Show password change modal
     */
    showChangePasswordModal() {
        const modal = document.createElement('div');
        modal.id = 'changePasswordModal';
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-xl p-6 max-w-md w-full mx-4">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-xl font-bold text-gray-800">
                        <i class="fas fa-key text-purple-600 mr-2"></i>Şifre Değiştir
                    </h3>
                    <button onclick="PasswordUtils.closeModal()" class="text-gray-500 hover:text-gray-700">
                        <i class="fas fa-times text-xl"></i>
                    </button>
                </div>

                <form id="changePasswordForm" onsubmit="PasswordUtils.handleSubmit(event)">
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-1">Mevcut Şifre</label>
                        <input type="password" id="currentPassword" required
                            class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-purple-600">
                    </div>
                    
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-1">Yeni Şifre</label>
                        <input type="password" id="newPassword" required
                            class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-purple-600"
                            oninput="PasswordUtils.checkStrength(this.value)">
                        <div id="passwordStrength" class="mt-2"></div>
                    </div>
                    
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-1">Yeni Şifre (Tekrar)</label>
                        <input type="password" id="confirmPassword" required
                            class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-purple-600">
                    </div>

                    <p class="text-xs text-gray-500 mb-4">
                        <i class="fas fa-info-circle mr-1"></i>
                        Şifre en az 6 karakter, bir büyük harf ve bir rakam içermelidir.
                    </p>

                    <div id="passwordError" class="hidden bg-red-100 text-red-700 p-3 rounded-lg mb-4"></div>

                    <button type="submit" id="changePasswordBtn"
                        class="w-full bg-purple-600 text-white py-2 rounded-lg hover:bg-purple-700 transition">
                        <i class="fas fa-save mr-2"></i>Şifreyi Değiştir
                    </button>
                </form>
            </div>
        `;
        document.body.appendChild(modal);
    },

    /**
     * Check password strength and show indicator
     */
    checkStrength(password) {
        const result = this.validatePassword(password);
        const strengthDiv = document.getElementById('passwordStrength');

        if (password.length === 0) {
            strengthDiv.innerHTML = '';
            return;
        }

        if (result.isValid) {
            strengthDiv.innerHTML = '<span class="text-green-600 text-sm"><i class="fas fa-check mr-1"></i>Güçlü şifre</span>';
        } else {
            strengthDiv.innerHTML = `<span class="text-red-500 text-sm"><i class="fas fa-exclamation-triangle mr-1"></i>${result.errors[0]}</span>`;
        }
    },

    /**
     * Handle password change form submit
     */
    async handleSubmit(event) {
        event.preventDefault();

        const currentPassword = document.getElementById('currentPassword').value;
        const newPassword = document.getElementById('newPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        const errorDiv = document.getElementById('passwordError');
        const submitBtn = document.getElementById('changePasswordBtn');

        // Reset error
        errorDiv.classList.add('hidden');

        // Check if passwords match
        if (newPassword !== confirmPassword) {
            errorDiv.textContent = 'Yeni şifreler eşleşmiyor';
            errorDiv.classList.remove('hidden');
            return;
        }

        // Validate new password
        const validation = this.validatePassword(newPassword);
        if (!validation.isValid) {
            errorDiv.textContent = validation.errors.join(', ');
            errorDiv.classList.remove('hidden');
            return;
        }

        // Submit request
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Kaydediliyor...';
        submitBtn.disabled = true;

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${API_BASE_URL}/auth/change-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.closeModal();
                this.showToast('✅ Şifre başarıyla değiştirildi', 'success');
            } else {
                errorDiv.textContent = data.detail || 'Şifre değiştirilirken hata oluştu';
                errorDiv.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Password change error:', error);
            errorDiv.textContent = 'Bir hata oluştu. Lütfen tekrar deneyin.';
            errorDiv.classList.remove('hidden');
        } finally {
            submitBtn.innerHTML = '<i class="fas fa-save mr-2"></i>Şifreyi Değiştir';
            submitBtn.disabled = false;
        }
    },

    /**
     * Close password modal
     */
    closeModal() {
        const modal = document.getElementById('changePasswordModal');
        if (modal) modal.remove();
    },

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 ${type === 'success' ? 'bg-green-600' : 'bg-blue-600'
            } text-white`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
};

// Auto-init session manager if on a protected page
document.addEventListener('DOMContentLoaded', () => {
    const publicPages = ['login.html', 'register.html', 'index.html'];
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';

    if (!publicPages.includes(currentPage)) {
        SessionManager.init();
    }
});

// Global function for profile page
function showChangePasswordModal() {
    PasswordUtils.showChangePasswordModal();
}

console.log('Session and password utilities loaded');

