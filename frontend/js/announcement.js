// Announcement functionality for admin and teacher panels

const AnnouncementUtils = {
    /**
     * Show announcement modal
     */
    showAnnouncementModal() {
        const modal = document.createElement('div');
        modal.id = 'announcementModal';
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';

        modal.innerHTML = `
            <div class="bg-white rounded-xl p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-xl font-bold text-gray-800">
                        <i class="fas fa-bullhorn text-purple-600 mr-2"></i>
                        Duyuru Gönder
                    </h3>
                    <button onclick="AnnouncementUtils.closeModal()" class="text-gray-500 hover:text-gray-700">
                        <i class="fas fa-times text-xl"></i>
                    </button>
                </div>
                
                <form id="announcementForm" onsubmit="AnnouncementUtils.sendAnnouncement(event)">
                    <!-- Target Selection -->
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            <i class="fas fa-users mr-1"></i> Hedef Kitle
                        </label>
                        <select id="announcementTarget" required
                            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent">
                            <option value="">Seçiniz...</option>
                            <option value="all">🌐 Tüm Kullanıcılar</option>
                            <option value="students">👨‍🎓 Tüm Öğrenciler</option>
                            <option value="teachers">👨‍🏫 Tüm Öğretmenler</option>
                            <option value="parents">👪 Tüm Veliler</option>
                            <option value="grade_2">📚 2. Sınıf Öğrencileri</option>
                            <option value="grade_3">📚 3. Sınıf Öğrencileri</option>
                            <option value="grade_4">📚 4. Sınıf Öğrencileri</option>
                        </select>
                    </div>
                    
                    <!-- Title -->
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            <i class="fas fa-heading mr-1"></i> Başlık
                        </label>
                        <input type="text" id="announcementTitle" required maxlength="100"
                            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                            placeholder="Duyuru başlığı...">
                    </div>
                    
                    <!-- Message -->
                    <div class="mb-6">
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            <i class="fas fa-comment-alt mr-1"></i> Mesaj
                        </label>
                        <textarea id="announcementMessage" required rows="4" maxlength="500"
                            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent resize-none"
                            placeholder="Duyuru içeriği..."></textarea>
                        <p class="text-xs text-gray-500 mt-1">
                            <span id="charCount">0</span>/500 karakter
                        </p>
                    </div>
                    
                    <!-- Buttons -->
                    <div class="flex space-x-3">
                        <button type="button" onclick="AnnouncementUtils.closeModal()"
                            class="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition">
                            İptal
                        </button>
                        <button type="submit" id="sendBtn"
                            class="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition flex items-center justify-center">
                            <i class="fas fa-paper-plane mr-2"></i>
                            Gönder
                        </button>
                    </div>
                </form>
            </div>
        `;

        document.body.appendChild(modal);

        // Character counter
        const messageInput = document.getElementById('announcementMessage');
        const charCount = document.getElementById('charCount');
        messageInput.addEventListener('input', () => {
            charCount.textContent = messageInput.value.length;
        });
    },

    /**
     * Close announcement modal
     */
    closeModal() {
        const modal = document.getElementById('announcementModal');
        if (modal) {
            modal.remove();
        }
    },

    /**
     * Send announcement
     */
    async sendAnnouncement(event) {
        event.preventDefault();

        const target = document.getElementById('announcementTarget').value;
        const title = document.getElementById('announcementTitle').value;
        const message = document.getElementById('announcementMessage').value;
        const sendBtn = document.getElementById('sendBtn');

        // Show loading
        sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Gönderiliyor...';
        sendBtn.disabled = true;

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${API_BASE_URL}/notifications/announcement`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ target, title, message })
            });

            const data = await response.json();

            if (response.ok) {
                this.closeModal();
                this.showToast(`✅ ${data.sent_count} kişiye duyuru gönderildi!`, 'success');
            } else {
                this.showToast(`❌ Hata: ${data.detail || 'Duyuru gönderilemedi'}`, 'error');
            }
        } catch (error) {
            console.error('Announcement error:', error);
            this.showToast('❌ Bir hata oluştu. Lütfen tekrar deneyin.', 'error');
        } finally {
            sendBtn.innerHTML = '<i class="fas fa-paper-plane mr-2"></i>Gönder';
            sendBtn.disabled = false;
        }
    },

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 ${type === 'success' ? 'bg-green-600' :
                type === 'error' ? 'bg-red-600' : 'bg-blue-600'
            } text-white`;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 4000);
    }
};

// Global function for easy access
function showAnnouncementModal() {
    AnnouncementUtils.showAnnouncementModal();
}

console.log('Announcement utilities loaded');

