/**
 * Notification Manager
 * Handles fetching, displaying, and managing user notifications
 */

const NotificationManager = {
    pollingInterval: null,
    dropdownOpen: false,

    /**
     * Initialize notification system
     */
    init() {
        this.createBellIcon();
        this.attachEventListeners();
        this.fetchNotifications();
        this.startPolling(30000); // Poll every 30 seconds
    },

    /**
     * Create bell icon HTML
     */
    createBellIcon() {
        const bellHTML = `
            <div class="relative notification-bell-container">
                <button id="notificationBtn" class="relative p-2 rounded-lg hover:bg-gray-100 transition touch-target" title="Bildirimler">
                    <i class="fas fa-bell text-xl text-gray-600"></i>
                    <span id="notificationBadge" class="hidden absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
                        0
                    </span>
                </button>
                
                <!-- Notification Dropdown -->
                <div id="notificationDropdown" class="hidden absolute right-0 mt-2 w-80 md:w-96 bg-white rounded-lg shadow-xl z-50 max-h-96 overflow-hidden flex flex-col">
                    <!-- Header -->
                    <div class="p-4 border-b flex justify-between items-center">
                        <h3 class="font-bold text-gray-800">Bildirimler</h3>
                        <button id="markAllReadBtn" class="text-sm text-purple-600 hover:text-purple-700">
                            Tümünü Okundu İşaretle
                        </button>
                    </div>
                    
                    <!-- Notifications List -->
                    <div id="notificationsList" class="overflow-y-auto flex-1">
                        <div class="text-center py-8">
                            <i class="fas fa-spinner fa-spin text-2xl text-gray-400"></i>
                            <p class="text-gray-500 mt-2">Yükleniyor...</p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Insert before theme toggle or first button in nav
        const nav = document.querySelector('nav .flex.items-center.space-x-2, nav .flex.items-center.space-x-4');
        if (nav) {
            const themeToggle = document.getElementById('themeToggle');
            if (themeToggle) {
                themeToggle.insertAdjacentHTML('beforebegin', bellHTML);
            } else {
                nav.insertAdjacentHTML('afterbegin', bellHTML);
            }
        }
    },

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        const bellBtn = document.getElementById('notificationBtn');
        const dropdown = document.getElementById('notificationDropdown');
        const markAllBtn = document.getElementById('markAllReadBtn');

        if (bellBtn) {
            bellBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleDropdown();
            });
        }

        if (markAllBtn) {
            markAllBtn.addEventListener('click', () => this.markAllAsRead());
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (dropdown && !dropdown.contains(e.target) && !bellBtn.contains(e.target)) {
                this.closeDropdown();
            }
        });
    },

    /**
     * Toggle notification dropdown
     */
    toggleDropdown() {
        const dropdown = document.getElementById('notificationDropdown');
        if (!dropdown) return;

        this.dropdownOpen = !this.dropdownOpen;

        if (this.dropdownOpen) {
            dropdown.classList.remove('hidden');
            this.fetchNotifications();
        } else {
            dropdown.classList.add('hidden');
        }
    },

    /**
     * Close dropdown
     */
    closeDropdown() {
        const dropdown = document.getElementById('notificationDropdown');
        if (dropdown) {
            dropdown.classList.add('hidden');
            this.dropdownOpen = false;
        }
    },

    /**
     * Fetch notifications from API
     */
    async fetchNotifications() {
        try {
            const response = await fetch('https://okuma-backend.onrender.com/api/notifications?limit=10', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (!response.ok) throw new Error('Failed to fetch notifications');

            const data = await response.json();
            this.displayNotifications(data.notifications);
            this.updateBadge(data.unread_count);
        } catch (error) {
            console.error('Error fetching notifications:', error);
        }
    },

    /**
     * Display notifications in dropdown
     */
    displayNotifications(notifications) {
        const container = document.getElementById('notificationsList');
        if (!container) return;

        if (notifications.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8">
                    <i class="fas fa-bell-slash text-4xl text-gray-300"></i>
                    <p class="text-gray-500 mt-2">Bildirim yok</p>
                </div>
            `;
            return;
        }

        container.innerHTML = notifications.map(notif => this.createNotificationItem(notif)).join('');

        // Attach click handlers
        notifications.forEach(notif => {
            const item = document.getElementById(`notif-${notif.id}`);
            if (item) {
                item.addEventListener('click', () => this.handleNotificationClick(notif));
            }
        });
    },

    /**
     * Create notification item HTML
     */
    createNotificationItem(notif) {
        const isUnread = !notif.is_read;
        const icon = this.getNotificationIcon(notif.type);
        const timeAgo = this.getTimeAgo(notif.created_at);

        return `
            <div id="notif-${notif.id}" class="notification-item p-4 border-b hover:bg-gray-50 cursor-pointer transition ${isUnread ? 'bg-blue-50' : ''}">
                <div class="flex items-start gap-3">
                    <div class="flex-shrink-0">
                        <div class="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
                            <i class="${icon} text-purple-600"></i>
                        </div>
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="font-semibold text-gray-800 text-sm ${isUnread ? 'font-bold' : ''}">${notif.title}</p>
                        <p class="text-gray-600 text-sm mt-1">${notif.message}</p>
                        <p class="text-gray-400 text-xs mt-1">${timeAgo}</p>
                    </div>
                    ${isUnread ? '<div class="flex-shrink-0"><div class="w-2 h-2 bg-blue-500 rounded-full"></div></div>' : ''}
                </div>
            </div>
        `;
    },

    /**
     * Get icon for notification type
     */
    getNotificationIcon(type) {
        const icons = {
            'evaluation': 'fas fa-star',
            'progress': 'fas fa-chart-line',
            'achievement': 'fas fa-trophy',
            'general': 'fas fa-info-circle'
        };
        return icons[type] || 'fas fa-bell';
    },

    /**
     * Get time ago string
     */
    getTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);

        if (seconds < 60) return 'Az önce';
        if (seconds < 3600) return `${Math.floor(seconds / 60)} dakika önce`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)} saat önce`;
        if (seconds < 604800) return `${Math.floor(seconds / 86400)} gün önce`;
        return date.toLocaleDateString('tr-TR');
    },

    /**
     * Handle notification click
     */
    async handleNotificationClick(notif) {
        // Mark as read
        if (!notif.is_read) {
            await this.markAsRead(notif.id);
        }

        // Navigate to link if exists
        if (notif.link) {
            window.location.href = notif.link;
        }

        this.closeDropdown();
    },

    /**
     * Mark notification as read
     */
    async markAsRead(notificationId) {
        try {
            await fetch(`https://okuma-backend.onrender.com/api/notifications/${notificationId}/mark-read`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            this.fetchNotifications();
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    },

    /**
     * Mark all notifications as read
     */
    async markAllAsRead() {
        try {
            await fetch('https://okuma-backend.onrender.com/api/notifications/mark-all-read', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            this.fetchNotifications();
        } catch (error) {
            console.error('Error marking all as read:', error);
        }
    },

    /**
     * Update badge count
     */
    updateBadge(count) {
        const badge = document.getElementById('notificationBadge');
        if (!badge) return;

        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    },

    /**
     * Start polling for new notifications
     */
    startPolling(interval = 30000) {
        // Clear existing interval
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }

        // Fetch unread count periodically
        this.pollingInterval = setInterval(async () => {
            try {
                const response = await fetch('https://okuma-backend.onrender.com/api/notifications/unread-count', {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    this.updateBadge(data.count);
                }
            } catch (error) {
                console.error('Error polling notifications:', error);
            }
        }, interval);
    },

    /**
     * Stop polling
     */
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
};

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // Only init if user is logged in
        if (localStorage.getItem('token')) {
            NotificationManager.init();
        }
    });
} else {
    if (localStorage.getItem('token')) {
        NotificationManager.init();
    }
}

console.log('Notification manager loaded');

