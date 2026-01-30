// API Base URL - Local Development
const API_BASE_URL = 'http://localhost:8000/api';

// Get auth token from localStorage
function getAuthToken() {
    return localStorage.getItem('token');
}

// Get current user from localStorage
function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

// Check if user is authenticated
function isAuthenticated() {
    return !!getAuthToken();
}

// Logout user
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login.html';
}

// Make authenticated API request
async function apiRequest(endpoint, options = {}) {
    const token = getAuthToken();

    const defaultOptions = {
        headers: {
            // Only add Content-Type if NOT FormData (browser sets it automatically for FormData)
            ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
            ...(token && { 'Authorization': `Bearer ${token}` })
        }
    };

    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, mergedOptions);

        // Handle 401 Unauthorized
        if (response.status === 401) {
            logout();
            return null;
        }

        return response;
    } catch (error) {
        console.error('API Request Error:', error);
        throw error;
    }
}

// API Methods
const API = {
    // Auth
    async login(email, password) {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Giriş başarısız');
        }
        return data;
    },

    async register(userData) {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Kayıt başarısız');
        }
        return data;
    },

    // Stories
    async getStories(gradeLevel = null, search = null, subject = null) {
        const params = new URLSearchParams();

        if (gradeLevel) params.append('sinif_duzeyi', gradeLevel);
        if (search) params.append('search', search);
        if (subject) params.append('ders', subject);

        const url = params.toString() ? `/stories?${params.toString()}` : '/stories';

        const response = await apiRequest(url);
        return response.json();
    },

    async getStory(storyId) {
        const response = await apiRequest(`/stories/${storyId}`);
        return response.json();
    },

    async getQuizQuestions(storyId) {
        const response = await apiRequest(`/stories/${storyId}/quiz`);
        return response.json();
    },

    async createStory(data) {
        const response = await apiRequest('/stories', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async updateStory(storyId, data) {
        const response = await apiRequest(`/stories/${storyId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async deleteStory(storyId) {
        const response = await apiRequest(`/stories/${storyId}`, {
            method: 'DELETE'
        });
        return response.json();
    },

    async uploadCover(storyId, file) {
        const formData = new FormData();
        formData.append('file', file);
        const response = await apiRequest(`/stories/${storyId}/cover`, {
            method: 'POST',
            body: formData
        });
        return response.json();
    },

    // Reading Activities
    async savePreReading(data) {
        const response = await apiRequest('/reading/pre-reading', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async savePractice(data) {
        const response = await apiRequest('/reading/practice', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async saveAnswers(data) {
        const response = await apiRequest('/reading/answers', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        if (!response) throw new Error('No response');
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Save failed');
        }
        return response.json();
    },

    async getProgress(storyId) {
        const response = await apiRequest(`/reading/progress/${storyId}`);
        return response.json();
    },

    async getMyProgress() {
        const response = await apiRequest('/reading/my-progress');
        return response.json();
    },

    // Speech Practice
    async saveSpeechPractice(data) {
        const response = await apiRequest('/reading/speech-practice', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async getSpeechHistory(storyId) {
        const response = await apiRequest(`/reading/speech-history/${storyId}`);
        return response.json();
    },

    // Teacher
    async getStudents(gradeLevel = null, search = null) {
        let url = '/teacher/students';
        const params = new URLSearchParams();

        if (gradeLevel) params.append('sinif_duzeyi', gradeLevel);
        if (search) params.append('search', search);

        if (params.toString()) url += `?${params.toString()}`;

        const response = await apiRequest(url);
        return response.json();
    },

    async getStudentProgress(studentId) {
        const response = await apiRequest(`/teacher/student/${studentId}/progress`);
        return response.json();
    },

    async getStudentAnswers(studentId, storyId) {
        const response = await apiRequest(`/teacher/student/${studentId}/story/${storyId}/answers`);
        return response.json();
    },

    async submitEvaluation(data) {
        const response = await apiRequest('/teacher/evaluate', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async assignStudent(email) {
        const response = await apiRequest('/teacher/assign-student', {
            method: 'POST',
            body: JSON.stringify({ student_email: email })
        });
        return response.json();
    },

    async getPendingReviews() {
        const response = await apiRequest('/teacher/pending-reviews');
        return response.json();
    },

    // Parent
    async getChildren() {
        const response = await apiRequest('/parent/children');
        return response.json();
    },

    async getChildProgress(childId) {
        const response = await apiRequest(`/parent/child/${childId}/progress`);
        return response.json();
    },

    async getTeacherComments(childId) {
        const response = await apiRequest(`/parent/child/${childId}/teacher-comments`);
        return response.json();
    },

    async getRecommendations(childId) {
        const response = await apiRequest(`/parent/child/${childId}/recommendations`);
        return response.json();
    },

    // Admin
    async getUsers(role = null) {
        const url = role ? `/admin/users?rol=${role}` : '/admin/users';
        const response = await apiRequest(url);
        return response.json();
    },

    async createUser(userData) {
        const response = await apiRequest('/admin/users', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
        return response.json();
    },

    async updateUser(userId, userData) {
        const response = await apiRequest(`/admin/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(userData)
        });
        return response.json();
    },

    async deleteUser(userId) {
        const response = await apiRequest(`/admin/users/${userId}`, {
            method: 'DELETE'
        });
        return response;
    },

    async getStatistics() {
        const response = await apiRequest('/admin/statistics');
        return response.json();
    },

    async uploadAudio(storyId, file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await apiRequest(`/stories/${storyId}/upload-audio`, {
            method: 'POST',
            body: formData
        });
        return response.json();
    },

    async getMyBadges() {
        const response = await apiRequest('/gamification/badges/me');
        return response.json();
    },

    // Admin
    async getPendingUsers() {
        const response = await apiRequest('/admin/users?pending=true');
        return response.json();
    },

    async approveUser(userId) {
        const response = await apiRequest(`/admin/users/${userId}/approve`, {
            method: 'POST'
        });
        return response.json();
    },

    // Assignments
    async createAssignment(storyId, studentIds, dueDate) {
        const response = await apiRequest('/assignments/', {
            method: 'POST',
            body: JSON.stringify({ story_id: storyId, student_ids: studentIds, due_date: dueDate })
        });
        return response.json();
    },

    async getMyAssignments() {
        const response = await apiRequest('/assignments/student/me');
        return response.json();
    },

    // Charts
    async getMyReadingSpeedChart(days = 30) {
        const response = await apiRequest(`/charts/reading-speed/me?days=${days}`);
        return response.json();
    },

    async getStudentReadingSpeedChart(studentId, days = 30) {
        const response = await apiRequest(`/charts/reading-speed/${studentId}?days=${days}`);
        return response.json();
    },

    async getMyStoryProgressChart() {
        const response = await apiRequest('/charts/story-progress/me');
        return response.json();
    },

    async getStudentStoryProgressChart(studentId) {
        const response = await apiRequest(`/charts/story-progress/${studentId}`);
        return response.json();
    },

    async getMyWeeklyActivityChart() {
        const response = await apiRequest('/charts/weekly-activity/me');
        return response.json();
    },

    // Gamification - Streak & XP
    async getMyStreak() {
        const response = await apiRequest('/gamification/streak/me');
        return response.json();
    },

    async getMyXP() {
        const response = await apiRequest('/gamification/xp/me');
        return response.json();
    },

    async addXP(action) {
        const response = await apiRequest(`/gamification/xp/add?action=${action}`, {
            method: 'POST'
        });
        return response.json();
    },

    async getMyGamificationStats() {
        const response = await apiRequest('/gamification/stats/me');
        return response.json();
    }
};

