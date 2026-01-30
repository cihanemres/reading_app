// Export utilities for downloading student progress reports

const ExportUtils = {
    /**
     * Export student progress as Excel
     */
    async exportStudentExcel(studentId, studentName, btn = null) {
        try {
            const token = localStorage.getItem('token');

            // Show loading
            if (btn) {
                btn.dataset.originalHtml = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>İndiriliyor...';
                btn.disabled = true;
            }

            const response = await fetch(`${API_BASE_URL}/export/student/${studentId}/progress`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Export failed');
            }

            // Get blob and create download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ogrenci_${studentName.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            // Restore button
            if (btn) {
                btn.innerHTML = btn.dataset.originalHtml;
                btn.disabled = false;
            }

            this.showNotification('✅ Excel raporu başarıyla indirildi!', 'success');
        } catch (error) {
            console.error('Export error:', error);
            this.showNotification('❌ Rapor indirilemedi. Lütfen tekrar deneyin.', 'error');

            if (btn) {
                btn.innerHTML = btn.dataset.originalHtml || '<i class="fas fa-file-excel mr-2"></i>Excel İndir';
                btn.disabled = false;
            }
        }
    },

    /**
     * Export student progress as PDF
     */
    async exportStudentPDF(studentId, studentName, btn = null) {
        try {
            const token = localStorage.getItem('token');

            if (btn) {
                btn.dataset.originalHtml = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>İndiriliyor...';
                btn.disabled = true;
            }

            const response = await fetch(`${API_BASE_URL}/export/student/${studentId}/progress/pdf`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Export failed');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ogrenci_${studentName.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            if (btn) {
                btn.innerHTML = btn.dataset.originalHtml;
                btn.disabled = false;
            }

            this.showNotification('✅ PDF raporu başarıyla indirildi!', 'success');
        } catch (error) {
            console.error('Export error:', error);
            this.showNotification('❌ PDF indirilemedi. Lütfen tekrar deneyin.', 'error');

            if (btn) {
                btn.innerHTML = btn.dataset.originalHtml || '<i class="fas fa-file-pdf mr-2"></i>PDF İndir';
                btn.disabled = false;
            }
        }
    },

    /**
     * Export class progress as Excel
     */
    async exportClassExcel(grade, btn = null) {
        try {
            const token = localStorage.getItem('token');

            if (btn) {
                btn.dataset.originalHtml = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>İndiriliyor...';
                btn.disabled = true;
            }

            const response = await fetch(`${API_BASE_URL}/export/class/${grade}/progress`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Export failed');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${grade}_sinif_raporu_${new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            if (btn) {
                btn.innerHTML = btn.dataset.originalHtml;
                btn.disabled = false;
            }

            this.showNotification('✅ Sınıf Excel raporu başarıyla indirildi!', 'success');
        } catch (error) {
            console.error('Export error:', error);
            this.showNotification('❌ Rapor indirilemedi. Lütfen tekrar deneyin.', 'error');

            if (btn) {
                btn.innerHTML = btn.dataset.originalHtml || '<i class="fas fa-file-excel mr-2"></i>Sınıf Raporu İndir';
                btn.disabled = false;
            }
        }
    },

    /**
     * Export class progress as PDF
     */
    async exportClassPDF(grade, btn = null) {
        try {
            const token = localStorage.getItem('token');

            if (btn) {
                btn.dataset.originalHtml = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>İndiriliyor...';
                btn.disabled = true;
            }

            const response = await fetch(`${API_BASE_URL}/export/class/${grade}/progress/pdf`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Export failed');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${grade}_sinif_raporu_${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            if (btn) {
                btn.innerHTML = btn.dataset.originalHtml;
                btn.disabled = false;
            }

            this.showNotification('✅ Sınıf PDF raporu başarıyla indirildi!', 'success');
        } catch (error) {
            console.error('Export error:', error);
            this.showNotification('❌ PDF indirilemedi. Lütfen tekrar deneyin.', 'error');

            if (btn) {
                btn.innerHTML = btn.dataset.originalHtml || '<i class="fas fa-file-pdf mr-2"></i>PDF İndir';
                btn.disabled = false;
            }
        }
    },

    /**
     * Generic class report export (used by teacher dashboard)
     */
    async exportClassReport(grade = null) {
        const selectedGrade = grade || document.getElementById('gradeFilter')?.value || '3';
        await this.exportClassExcel(selectedGrade);
    },

    /**
     * Show export options modal
     */
    showExportOptions(type, id = null, name = null) {
        const modal = document.createElement('div');
        modal.id = 'exportModal';
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';

        let title = type === 'student' ? 'Öğrenci Raporu İndir' : 'Sınıf Raporu İndir';

        modal.innerHTML = `
            <div class="bg-white rounded-xl p-6 max-w-md w-full mx-4">
                <h3 class="text-xl font-bold text-gray-800 mb-4">${title}</h3>
                <p class="text-gray-600 mb-6">Hangi formatta indirmek istiyorsunuz?</p>
                <div class="flex flex-col space-y-3">
                    <button onclick="ExportUtils.handleExport('${type}', '${id}', '${name}', 'excel')"
                        class="flex items-center justify-center bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition">
                        <i class="fas fa-file-excel mr-3 text-xl"></i>
                        <span>Excel (.xlsx)</span>
                    </button>
                    <button onclick="ExportUtils.handleExport('${type}', '${id}', '${name}', 'pdf')"
                        class="flex items-center justify-center bg-red-600 text-white px-6 py-3 rounded-lg hover:bg-red-700 transition">
                        <i class="fas fa-file-pdf mr-3 text-xl"></i>
                        <span>PDF (.pdf)</span>
                    </button>
                    <button onclick="ExportUtils.closeExportModal()"
                        class="text-gray-600 hover:text-gray-800 py-2">
                        İptal
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    },

    /**
     * Handle export from modal
     */
    async handleExport(type, id, name, format) {
        this.closeExportModal();

        if (type === 'student') {
            if (format === 'excel') {
                await this.exportStudentExcel(id, name);
            } else {
                await this.exportStudentPDF(id, name);
            }
        } else {
            if (format === 'excel') {
                await this.exportClassExcel(id);
            } else {
                await this.exportClassPDF(id);
            }
        }
    },

    /**
     * Close export modal
     */
    closeExportModal() {
        const modal = document.getElementById('exportModal');
        if (modal) {
            modal.remove();
        }
    },

    /**
     * Show notification toast
     */
    showNotification(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 ${type === 'success' ? 'bg-green-600' :
                type === 'error' ? 'bg-red-600' : 'bg-blue-600'
            } text-white`;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
};

// Legacy support - keep old function names working
async function exportStudentProgress(studentId, studentName) {
    await ExportUtils.exportStudentExcel(studentId, studentName, event?.target);
}

async function exportClassProgress(grade) {
    await ExportUtils.exportClassExcel(grade, event?.target);
}

console.log('Export utilities loaded');

