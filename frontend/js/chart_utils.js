// Chart.js utility functions for data visualization

// Color palette for charts
const chartColors = {
    primary: 'rgba(102, 126, 234, 0.8)',
    secondary: 'rgba(118, 75, 162, 0.8)',
    success: 'rgba(34, 197, 94, 0.8)',
    warning: 'rgba(251, 146, 60, 0.8)',
    danger: 'rgba(239, 68, 68, 0.8)',
    info: 'rgba(59, 130, 246, 0.8)',
    purple: 'rgba(168, 85, 247, 0.8)',
    pink: 'rgba(236, 72, 153, 0.8)'
};

// Default chart options
const defaultChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display: true,
            position: 'top',
        },
        tooltip: {
            mode: 'index',
            intersect: false,
        }
    }
};

// Create a line chart for progress trends
function createProgressLineChart(canvasId, labels, datasets) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets.map((dataset, index) => ({
                label: dataset.label,
                data: dataset.data,
                borderColor: Object.values(chartColors)[index % 8],
                backgroundColor: Object.values(chartColors)[index % 8].replace('0.8', '0.2'),
                tension: 0.4,
                fill: true
            }))
        },
        options: {
            ...defaultChartOptions,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

// Create a bar chart for comparisons
function createComparisonBarChart(canvasId, labels, data, label = 'Değer') {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: chartColors.primary,
                borderColor: chartColors.primary.replace('0.8', '1'),
                borderWidth: 1
            }]
        },
        options: {
            ...defaultChartOptions,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Create a doughnut chart for distribution
function createDoughnutChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    const colors = Object.values(chartColors).slice(0, labels.length);

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            ...defaultChartOptions,
            plugins: {
                ...defaultChartOptions.plugins,
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

// Create a radar chart for multi-dimensional comparison
function createRadarChart(canvasId, labels, datasets) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: datasets.map((dataset, index) => ({
                label: dataset.label,
                data: dataset.data,
                borderColor: Object.values(chartColors)[index % 8],
                backgroundColor: Object.values(chartColors)[index % 8].replace('0.8', '0.2'),
            }))
        },
        options: {
            ...defaultChartOptions,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

// Format data for student progress trend
function formatProgressTrendData(progressData) {
    const labels = progressData.map(p => new Date(p.date).toLocaleDateString('tr-TR', { month: 'short', day: 'numeric' }));
    const speedData = progressData.map(p => p.reading_speed || 0);
    const comprehensionData = progressData.map(p => p.comprehension_score || 0);

    return {
        labels,
        datasets: [
            { label: 'Okuma Hızı (kelime/dk)', data: speedData },
            { label: 'Anlama Puanı', data: comprehensionData }
        ]
    };
}

// Format data for class comparison
function formatClassComparisonData(studentsData) {
    const labels = studentsData.map(s => s.name);
    const avgScores = studentsData.map(s => s.average_score || 0);

    return { labels, data: avgScores };
}

// Destroy chart if exists (for updates)
function destroyChart(chartInstance) {
    if (chartInstance) {
        chartInstance.destroy();
    }
}

// Export for use in other files
window.ChartUtils = {
    colors: chartColors,
    createProgressLineChart,
    createComparisonBarChart,
    createDoughnutChart,
    createRadarChart,
    formatProgressTrendData,
    formatClassComparisonData,
    destroyChart
};

