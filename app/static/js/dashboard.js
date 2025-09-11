// --- START OF FILE app/static/js/dashboard.js ---

document.addEventListener('DOMContentLoaded', function() {
    // --- Referencias a Elementos del DOM ---
    const dashboardContainer = document.getElementById('dashboard-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    // Filtros
    const timeRangeButtons = document.querySelectorAll('.time-range-btn');
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const sourceFilterSelect = document.getElementById('sourceFilter');
    const showAllSwitch = document.getElementById('showAllSwitch');
    
    const themeToggleBtn = document.getElementById('theme-toggle');

    // --- Variables Globales ---
    const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6'];
    let charts = {}; // Para almacenar instancias de Chart.js y poder destruirlas

    // --- Funciones de Utilidad ---

    function saveFilters() {
        localStorage.setItem('dashboard_startDate', startDateInput.value);
        localStorage.setItem('dashboard_endDate', endDateInput.value);
        localStorage.setItem('dashboard_sourceFilter', sourceFilterSelect.value);
        localStorage.setItem('dashboard_showAll', showAllSwitch.checked);
    }

    function loadFiltersAndData() {
        startDateInput.value = localStorage.getItem('dashboard_startDate') || '';
        endDateInput.value = localStorage.getItem('dashboard_endDate') || '';
        sourceFilterSelect.value = localStorage.getItem('dashboard_sourceFilter') || '';
        showAllSwitch.checked = localStorage.getItem('dashboard_showAll') === 'true';
        
        if (!startDateInput.value || !endDateInput.value) {
            setDateRange(30, false);
        }
        
        loadDashboardData();
    }
    
    function setDateRange(days, shouldLoadData = true) {
        const endDate = new Date();
        const startDate = new Date();
        
        let startDateString = '';
        let endDateString = endDate.toISOString().split('T')[0];

        if (days !== null) { // Permite que 'Todo' (null) borre las fechas
            startDate.setDate(endDate.getDate() - (days - 1));
            startDateString = startDate.toISOString().split('T')[0];
        } else {
            endDateString = ''; // Borra la fecha final para "Todo"
        }
        
        startDateInput.value = startDateString;
        endDateInput.value = endDateString;
        
        timeRangeButtons.forEach(btn => {
            const btnDays = btn.dataset.days ? parseInt(btn.dataset.days) : null;
            const isActive = btnDays === days;
            btn.classList.toggle('bg-blue-600', isActive);
            btn.classList.toggle('text-white', isActive);
            btn.classList.toggle('bg-slate-200', !isActive);
            btn.classList.toggle('dark:bg-slate-700', !isActive);
        });
        
        if (shouldLoadData) {
            loadDashboardData();
        }
    }
    
    function calculateQualityIndex(stats) {
        const { veracity = 0, civic_impact = 0, popular_interest = 0 } = stats.avg_scores || {};
        return Math.round((veracity * 0.5) + (civic_impact * 0.3) + (popular_interest * 0.2));
    }

    function calculateSourceDiversity(sources) {
        if (!sources || !sources.values || sources.values.length <= 1) return 'N/A';
        const total = sources.values.reduce((a, b) => a + b, 0);
        if (total === 0) return 'N/A';
        const entropy = sources.values.reduce((e, count) => {
            const p = count / total;
            return e - (p > 0 ? p * Math.log2(p) : 0);
        }, 0);
        const maxEntropy = Math.log2(sources.values.length);
        if (maxEntropy === 0) return 'N/A';
        return `${Math.round((entropy / maxEntropy) * 100)}%`;
    }

    function destroyCharts() {
        Object.values(charts).forEach(chart => chart.destroy());
        charts = {};
    }

    function updateChartThemes() {
        const isDarkMode = document.documentElement.classList.contains('dark');
        const textColor = isDarkMode ? '#cbd5e1' : '#334155';
        const gridColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
        
        Object.values(charts).forEach(chart => {
            if (chart.options.scales && chart.options.scales.r) {
                chart.options.scales.r.pointLabels.color = textColor;
                chart.options.scales.r.ticks.color = textColor;
                chart.options.scales.r.grid.color = gridColor;
            }
            if (chart.options.scales && chart.options.scales.x) {
                chart.options.scales.x.ticks.color = textColor;
                chart.options.scales.y.ticks.color = textColor;
            }
            if (chart.options.plugins && chart.options.plugins.legend) {
                chart.options.plugins.legend.labels.color = textColor;
                if (chart.data.datasets[0]) {
                   chart.data.datasets[0].borderColor = isDarkMode ? '#1e293b' : '#ffffff';
                }
            }
            chart.update();
        });
    }

    async function loadDashboardData() {
        destroyCharts();
        dashboardContainer.style.display = 'none';
        loadingIndicator.style.display = 'block';
        saveFilters();

        const params = new URLSearchParams({ 
            start_date: startDateInput.value,
            end_date: endDateInput.value,
            source: sourceFilterSelect.value,
            show_all: showAllSwitch.checked
        });
        
        try {
            const response = await fetch(`/api/dashboard_stats?${params}`);
            if (!response.ok) throw new Error(`Error: ${response.statusText}`);
            const stats = await response.json();

            if (stats.date_range.min_date && stats.date_range.max_date) {
                startDateInput.min = stats.date_range.min_date;
                startDateInput.max = stats.date_range.max_date;
                endDateInput.min = stats.date_range.min_date;
                endDateInput.max = stats.date_range.max_date;
            }

            document.getElementById('total-news').textContent = (stats.total_articles || 0).toLocaleString();
            document.getElementById('quality-index').textContent = `${calculateQualityIndex(stats)}%`;
            document.getElementById('source-diversity').textContent = calculateSourceDiversity(stats.sources);
            document.getElementById('geo-coverage').textContent = `${(stats.top_locations?.length || 0)} prov.`;

            const isDarkMode = document.documentElement.classList.contains('dark');
            const textColor = isDarkMode ? '#cbd5e1' : '#334155';
            const gridColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
            
            charts.timeline = new Chart(document.getElementById('timelineChart').getContext('2d'), { type: 'line', data: { labels: stats.timeline.map(d => d.date), datasets: [{ label: 'Noticias', data: stats.timeline.map(d => d.count), borderColor: CHART_COLORS[0], backgroundColor: `${CHART_COLORS[0]}20`, fill: true, tension: 0.3 }] }, options: { responsive: true, maintainAspectRatio: false, scales: { x: { display: true, ticks: { color: textColor } }, y: { beginAtZero: true, ticks: { color: textColor } } }, plugins: { legend: { display: false } } } });
            
            charts.scores = new Chart(document.getElementById('scoresChart').getContext('2d'), { type: 'radar', data: { labels: ['Veracidad', 'Impacto Cívico', 'Interés Popular'], datasets: [{ label: 'Promedio', data: [stats.avg_scores.veracity, stats.avg_scores.civic_impact, stats.avg_scores.popular_interest], borderColor: CHART_COLORS[0], backgroundColor: `${CHART_COLORS[0]}40` }] }, options: { responsive: true, maintainAspectRatio: false, scales: { r: { beginAtZero: true, max: 100, grid: { color: gridColor }, pointLabels: { font: { size: 13 }, color: textColor }, ticks: { backdropColor: 'rgba(0,0,0,0)', color: textColor } } }, plugins: { legend: { display: false } } } });

            charts.categories = new Chart(document.getElementById('categoryChart').getContext('2d'), { type: 'pie', data: { labels: stats.categories.map(c => c.name), datasets: [{ data: stats.categories.map(c => c.count), backgroundColor: CHART_COLORS, borderColor: isDarkMode ? '#1e293b' : '#ffffff', borderWidth: 2 }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { color: textColor } } } } });

            const sourceComp = document.getElementById('sourceComparison');
            sourceComp.innerHTML = '';
            if (stats.sources && stats.sources.length > 0) {
                stats.sources.forEach(source => {
                    const perc = stats.total_articles > 0 ? ((source.count / stats.total_articles) * 100).toFixed(1) : 0;
                    sourceComp.innerHTML += `<div class="p-2 bg-slate-50 dark:bg-slate-700/50 rounded-lg"><div class="flex justify-between text-sm mb-1"><span class="font-semibold">${source.name}</span><span>${source.count} (${perc}%)</span></div><div class="w-full bg-slate-200 dark:bg-slate-600 h-2 rounded-full"><div class="bg-blue-500 h-2 rounded-full" style="width: ${perc}%"></div></div></div>`;
                });
            } else { sourceComp.innerHTML = '<p class="text-sm text-slate-400 italic text-center">No hay datos de fuentes para mostrar.</p>'; }
            
            const locationsList = document.getElementById('topLocationsList');
            locationsList.innerHTML = '';
            if (stats.top_locations && stats.top_locations.length > 0) {
                stats.top_locations.forEach(loc => {
                    locationsList.innerHTML += `<div class="flex justify-between items-center p-2 bg-slate-50 dark:bg-slate-700/50 rounded-lg"><div><i class="fas fa-map-marker-alt text-slate-400 mr-2"></i><span class="font-semibold text-sm">${loc.name}</span></div><span class="text-sm font-bold bg-slate-200 dark:bg-slate-600 px-2 py-0.5 rounded-md">${loc.count}</span></div>`;
                });
            } else { locationsList.innerHTML = '<p class="text-sm text-slate-400 italic text-center">No hay datos de ubicación para mostrar.</p>'; }

            const keywordsDiv = document.getElementById('keywordTrends');
            keywordsDiv.innerHTML = '';
            if(stats.top_tags && stats.top_tags.length > 0) {
                stats.top_tags.forEach(tag => {
                    keywordsDiv.innerHTML += `<span class="text-xs font-semibold bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 px-3 py-1 rounded-full">${tag.name} (${tag.count})</span>`;
                });
            } else { keywordsDiv.innerHTML = '<p class="text-sm text-slate-400 italic text-center">No hay palabras clave para mostrar.</p>'; }

            loadingIndicator.style.display = 'none';
            dashboardContainer.style.display = 'block';
            
            updateChartThemes();
        } catch (error) {
            console.error('Error al cargar datos del dashboard:', error);
            loadingIndicator.innerHTML = `<div class="text-center p-12 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 rounded-lg">Error al cargar los datos.</div>`;
        }
    }

    timeRangeButtons.forEach(button => {
        button.addEventListener('click', () => {
            const days = button.dataset.days ? parseInt(button.dataset.days) : null;
            setDateRange(days);
        });
    });

    [startDateInput, endDateInput, sourceFilterSelect, showAllSwitch].forEach(el => {
        el.addEventListener('change', () => {
            if (el === startDateInput || el === endDateInput) {
                timeRangeButtons.forEach(btn => {
                    btn.classList.remove('bg-blue-600', 'text-white');
                    btn.classList.add('bg-slate-200', 'dark:bg-slate-700');
                });
            }
            loadDashboardData();
        });
    });

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => setTimeout(updateChartThemes, 50));
    }

    loadFiltersAndData();
});