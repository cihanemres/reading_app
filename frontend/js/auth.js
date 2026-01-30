// Authentication utilities

// Check if user is logged in
function checkAuth() {
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');

    if (!token || !user) {
        window.location.href = '/login.html';
        return false;
    }

    return true;
}

// Check user role
function checkRole(requiredRole) {
    const userStr = localStorage.getItem('user');
    if (!userStr) {
        window.location.href = '/login.html';
        return false;
    }

    const user = JSON.parse(userStr);

    if (user.rol !== requiredRole) {
        alert('Bu sayfaya erişim yetkiniz yok!');
        window.location.href = '/login.html';
        return false;
    }

    return true;
}

// Get current user info
function getCurrentUserInfo() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

// Logout function
function performLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login.html';
}

// Update user display in navbar
function updateUserDisplay() {
    const user = getCurrentUserInfo();
    if (!user) return;

    const userNameElement = document.getElementById('userName');
    const userRoleElement = document.getElementById('userRole');

    if (userNameElement) {
        userNameElement.textContent = user.ad_soyad;
    }

    if (userRoleElement) {
        const roleNames = {
            'ogrenci': 'Öğrenci',
            'ogretmen': 'Öğretmen',
            'veli': 'Veli',
            'yonetici': 'Yönetici'
        };
        userRoleElement.textContent = roleNames[user.rol] || user.rol;
    }
}

// Initialize auth on page load
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on a protected page (not login/register/index)
    const publicPages = ['login.html', 'register.html', 'index.html'];
    const currentPage = window.location.pathname.split('/').pop();

    if (!publicPages.includes(currentPage) && currentPage !== '') {
        checkAuth();
        updateUserDisplay();
    }

    // Add logout handler to logout buttons
    const logoutButtons = document.querySelectorAll('[data-logout]');
    logoutButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            performLogout();
        });
    });
});

