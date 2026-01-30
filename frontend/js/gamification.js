/**
 * Gamification System
 * Handles achievement badges, leaderboard, and progress tracking
 */
const Gamification = {
    /**
     * Badge definitions (matches backend)
     */
    badges: {
        first_step: {
            name: 'İlk Adım',
            description: 'İlk hikayeni okudun!',
            icon: '🌟',
            color: 'gold'
        },
        speed_reader: {
            name: 'Hızlı Okuyucu',
            description: '5 hikaye okudun',
            icon: '⚡',
            color: 'blue'
        },
        bookworm: {
            name: 'Kitap Kurdu',
            description: '10 hikaye okudun',
            icon: '📚',
            color: 'purple'
        },
        super_reader: {
            name: 'Süper Okuyucu',
            description: '25 hikaye okudun',
            icon: '🦸',
            color: 'red'
        },
        master: {
            name: 'Ustalaşma',
            description: '50 hikaye okudun',
            icon: '👑',
            color: 'gold'
        },
        practice_master: {
            name: 'Pratik Ustası',
            description: '10 pratik tamamladın',
            icon: '🎯',
            color: 'green'
        },
        speed_champion: {
            name: 'Hız Şampiyonu',
            description: '150+ kelime/dakika hıza ulaştın',
            icon: '🏃',
            color: 'orange'
        },
        perfect_comprehension: {
            name: 'Mükemmel Anlama',
            description: 'Anlama puanında 9+ aldın',
            icon: '🧠',
            color: 'pink'
        }
    },

    /**
     * Check for new achievements
     */
    async checkAchievements() {
        try {
            const response = await fetch(`${API_BASE_URL}/gamification/check-achievements`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) return;

            const data = await response.json();

            if (data.new_badges && data.new_badges.length > 0) {
                this.showBadgeNotifications(data.new_badges);
            }
        } catch (error) {
            console.error('Error checking achievements:', error);
        }
    },

    /**
     * Show badge earned notifications
     */
    showBadgeNotifications(badges) {
        badges.forEach((badge, index) => {
            setTimeout(() => {
                this.showBadgeModal(badge);
            }, index * 2000); // Stagger notifications
        });
    },

    /**
     * Display badge earned modal
     */
    showBadgeModal(badge) {
        const modal = document.createElement('div');
        modal.className = 'badge-modal';
        modal.innerHTML = `
            <div class="badge-celebration">
                <div class="badge-icon-huge">${badge.icon}</div>
                <h2 class="text-3xl font-bold text-gray-800 mb-2">Tebrikler! 🎉</h2>
                <h3 class="text-2xl font-bold text-purple-600 mb-2">${badge.name}</h3>
                <p class="text-gray-600 mb-6">${badge.description}</p>
                <button onclick="this.closest('.badge-modal').remove()" 
                    class="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition font-semibold">
                    Harika!
                </button>
            </div>
        `;

        document.body.appendChild(modal);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (modal.parentElement) {
                modal.remove();
            }
        }, 5000);
    },

    /**
     * Load and render user badges
     */
    async loadMyBadges(containerId) {
        try {
            const response = await fetch(`${API_BASE_URL}/gamification/badges/me`, {
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`
                }
            });

            if (!response.ok) throw new Error('Failed to load badges');

            const data = await response.json();
            this.renderBadges(data.badges, document.getElementById(containerId));
        } catch (error) {
            console.error('Error loading badges:', error);
        }
    },

    /**
     * Render badges in container
     */
    renderBadges(badges, container) {
        if (!container) return;

        if (badges.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center py-8">
                    <p class="text-gray-500">Henüz rozet kazanmadın. Hikaye okuyarak rozetler kazanabilirsin!</p>
                </div>
            `;
            return;
        }

        const html = badges.map(badge => `
            <div class="badge-card ${badge.color} fade-in">
                <div class="badge-icon-large">${badge.icon}</div>
                <h4 class="font-bold text-gray-800 mt-2">${badge.name}</h4>
                <p class="text-sm text-gray-600 mt-1">${badge.description}</p>
                <span class="badge-date text-xs text-gray-500 mt-2">${this.formatDate(badge.earned_at)}</span>
            </div>
        `).join('');

        container.innerHTML = html;
    },

    /**
     * Load progress towards next milestone
     */
    async loadProgress(containerId) {
        try {
            const response = await fetch(`${API_BASE_URL}/gamification/progress/me`, {
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`
                }
            });

            if (!response.ok) throw new Error('Failed to load progress');

            const data = await response.json();
            this.renderProgress(data, document.getElementById(containerId));
        } catch (error) {
            console.error('Error loading progress:', error);
        }
    },

    /**
     * Render progress milestone
     */
    renderProgress(progress, container) {
        if (!container) return;

        const nextBadge = this.getNextBadge(progress.next_milestone);

        container.innerHTML = `
            <div class="bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl p-6 text-white">
                <h3 class="text-xl font-bold mb-2">🎯 Bir Sonraki Hedef</h3>
                <p class="text-sm mb-4">${nextBadge.name} ${nextBadge.icon}</p>
                <div class="progress-bar bg-white bg-opacity-30 rounded-full h-4 mb-2">
                    <div class="progress-fill bg-white rounded-full h-4 transition-all duration-500" 
                        style="width: ${progress.progress_percentage}%"></div>
                </div>
                <p class="text-sm">
                    ${progress.current_stories}/${progress.next_milestone} hikaye - 
                    ${progress.remaining} hikaye kaldı!
                </p>
            </div>
        `;
    },

    /**
     * Get next badge info based on milestone
     */
    getNextBadge(milestone) {
        const badgeMap = {
            1: this.badges.first_step,
            5: this.badges.speed_reader,
            10: this.badges.bookworm,
            25: this.badges.super_reader,
            50: this.badges.master,
            100: { name: 'Efsane Okuyucu', icon: '🌟' }
        };
        return badgeMap[milestone] || { name: 'Sonraki Hedef', icon: '🎯' };
    },

    /**
     * Format date
     */
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('tr-TR', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    },

    /**
     * Load leaderboard
     */
    async loadLeaderboard(containerId, period = 'weekly', gradeLevel = null) {
        try {
            let url = `${API_BASE_URL}/gamification/leaderboard?period=${period}`;
            if (gradeLevel) url += `&grade_level=${gradeLevel}`;

            const response = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`
                }
            });

            if (!response.ok) throw new Error('Failed to load leaderboard');

            const data = await response.json();
            this.renderLeaderboard(data.leaderboard, document.getElementById(containerId));
        } catch (error) {
            console.error('Error loading leaderboard:', error);
        }
    },

    /**
     * Render leaderboard
     */
    renderLeaderboard(leaderboard, container) {
        if (!container) return;

        if (leaderboard.length === 0) {
            container.innerHTML = '<p class="text-center text-gray-500 py-8">Henüz veri yok</p>';
            return;
        }

        const html = leaderboard.map(entry => `
            <div class="leaderboard-item ${entry.rank <= 3 ? 'top-three' : ''}">
                <div class="leaderboard-rank ${this.getRankClass(entry.rank)}">
                    ${entry.rank <= 3 ? this.getRankIcon(entry.rank) : entry.rank}
                </div>
                <div class="flex-1">
                    <h4 class="font-bold text-gray-800">${entry.name}</h4>
                    <p class="text-sm text-gray-600">${entry.grade_level}. Sınıf</p>
                </div>
                <div class="text-right">
                    <p class="font-bold text-purple-600">${entry.story_count} hikaye</p>
                    <p class="text-sm text-gray-600">${entry.avg_speed} k/dk</p>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    },

    /**
     * Get rank class for styling
     */
    getRankClass(rank) {
        if (rank === 1) return 'first';
        if (rank === 2) return 'second';
        if (rank === 3) return 'third';
        return '';
    },

    /**
     * Get rank icon
     */
    getRankIcon(rank) {
        const icons = { 1: '🥇', 2: '🥈', 3: '🥉' };
        return icons[rank] || rank;
    }
};

// Auto-initialize
console.log('Gamification system loaded');

