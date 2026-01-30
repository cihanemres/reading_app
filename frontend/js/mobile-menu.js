/**
 * Mobile Menu Component
 * Reusable mobile navigation menu
 */

const MobileMenu = {
    /**
     * Initialize mobile menu
     */
    init() {
        this.createMenu();
        this.attachEventListeners();
    },

    /**
     * Create mobile menu HTML
     */
    createMenu() {
        const menuHTML = `
            <!-- Mobile Menu Button -->
            <button id="mobileMenuBtn" class="mobile-menu-btn p-2 rounded-lg hover:bg-gray-100 transition">
                <i class="fas fa-bars text-2xl text-gray-700"></i>
            </button>

            <!-- Mobile Menu Overlay -->
            <div id="mobileMenuOverlay" class="mobile-menu-overlay"></div>

            <!-- Mobile Menu -->
            <div id="mobileMenu" class="mobile-menu">
                <div class="mobile-menu-header">
                    <div>
                        <p class="font-bold text-gray-800" id="mobileUserName">User</p>
                        <p class="text-sm text-gray-600" id="mobileUserRole">Role</p>
                    </div>
                    <div class="mobile-menu-close">
                        <i class="fas fa-times text-xl text-gray-600"></i>
                    </div>
                </div>
                <div class="mobile-menu-items" id="mobileMenuItems">
                    <!-- Menu items will be inserted here -->
                </div>
            </div>
        `;

        // Insert menu into navigation
        const nav = document.querySelector('nav .flex.items-center.space-x-4');
        if (nav) {
            nav.insertAdjacentHTML('afterbegin', menuHTML);
        }
    },

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        const menuBtn = document.getElementById('mobileMenuBtn');
        const overlay = document.getElementById('mobileMenuOverlay');
        const menu = document.getElementById('mobileMenu');
        const closeBtn = document.querySelector('.mobile-menu-close');

        if (menuBtn) {
            menuBtn.addEventListener('click', () => this.openMenu());
        }

        if (overlay) {
            overlay.addEventListener('click', () => this.closeMenu());
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeMenu());
        }

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeMenu();
            }
        });
    },

    /**
     * Open mobile menu
     */
    openMenu() {
        const overlay = document.getElementById('mobileMenuOverlay');
        const menu = document.getElementById('mobileMenu');

        if (overlay && menu) {
            overlay.classList.add('active');
            menu.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    },

    /**
     * Close mobile menu
     */
    closeMenu() {
        const overlay = document.getElementById('mobileMenuOverlay');
        const menu = document.getElementById('mobileMenu');

        if (overlay && menu) {
            overlay.classList.remove('active');
            menu.classList.remove('active');
            document.body.style.overflow = '';
        }
    },

    /**
     * Add menu item
     */
    addMenuItem(icon, text, onClick) {
        const container = document.getElementById('mobileMenuItems');
        if (!container) return;

        const item = document.createElement('div');
        item.className = 'mobile-menu-item';
        item.innerHTML = `
            <i class="${icon}"></i>
            <span>${text}</span>
        `;
        item.addEventListener('click', () => {
            onClick();
            this.closeMenu();
        });

        container.appendChild(item);
    },

    /**
     * Set user info
     */
    setUserInfo(name, role) {
        const nameEl = document.getElementById('mobileUserName');
        const roleEl = document.getElementById('mobileUserRole');

        if (nameEl) nameEl.textContent = name;
        if (roleEl) roleEl.textContent = role;
    },

    /**
     * Clear menu items
     */
    clearMenuItems() {
        const container = document.getElementById('mobileMenuItems');
        if (container) {
            container.innerHTML = '';
        }
    }
};

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => MobileMenu.init());
} else {
    MobileMenu.init();
}

console.log('Mobile menu component loaded');

