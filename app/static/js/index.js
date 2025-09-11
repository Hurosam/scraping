// --- START OF FILE app/static/js/index.js ---

document.addEventListener('DOMContentLoaded', () => {
    // --- State Management ---
    let state = {
        query: '',
        category: '',
        source: '',
        province: '',
        startDate: '',
        endDate: '',
        sortBy: 'published_at',
        showAll: false,
        veracityMin: 0,
        veracityMax: 100,
        civicMin: 0,
        civicMax: 100,
        relevanceMin: 0,
        relevanceMax: 100,
        currentPage: 1,
        itemsPerPage: 12,
        view: 'grid'
    };

    // --- DOM Element References ---
    const elements = {
        smartSearch: document.getElementById('smart-search'),
        suggestionsBox: document.getElementById('smart-suggestions'),
        advancedToggle: document.getElementById('advanced-toggle'),
        advancedFiltersPanel: document.getElementById('advanced-filters'),
        activeFiltersContainer: document.getElementById('active-filters'),
        categoryFilter: document.getElementById('category-filter'),
        sourceFilter: document.getElementById('source-filter'),
        provinceFilter: document.getElementById('province-filter'),
        sortFilter: document.getElementById('sort-filter'),
        dateStart: document.getElementById('date-start'),
        dateEnd: document.getElementById('date-end'),
        onlyAnalyzed: document.getElementById('only-analyzed'),
        applyFiltersBtn: document.getElementById('apply-filters'),
        resetFiltersBtn: document.getElementById('reset-filters'),
        newsContainer: document.getElementById('news-container'),
        resultsCounter: document.getElementById('results-counter'),
        gridViewBtn: document.getElementById('grid-view'),
        listViewBtn: document.getElementById('list-view'),
        paginationContainer: document.getElementById('pagination-container'),
        itemsPerPageSelect: document.getElementById('items-per-page'),
        paginationControls: document.getElementById('pagination-controls'),
        showingRange: document.getElementById('showing-range'),
        totalItems: document.getElementById('total-items'),
    };
    
    // --- Utility Functions ---
    const formatDate = (isoString) => {
        if (!isoString) return 'Fecha desconocida';
        const date = new Date(isoString);
        return date.toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' });
    };

    const debounce = (func, delay) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    };

    const getProxiedImageUrl = (originalUrl) => {
        const placeholder = 'https://via.placeholder.com/400x300.png?text=Sin+Imagen';
        if (!originalUrl || !originalUrl.startsWith('http')) {
            return originalUrl || placeholder;
        }
        return `/api/image_proxy?url=${encodeURIComponent(originalUrl)}`;
    };

    // --- State & UI Update Functions ---
    function updateStateFromUI() {
        state.query = elements.smartSearch.value;
        state.category = elements.categoryFilter.value;
        state.source = elements.sourceFilter.value;
        state.province = elements.provinceFilter.value;
        state.startDate = elements.dateStart.value;
        state.endDate = elements.dateEnd.value;
        state.sortBy = elements.sortFilter.value;
        state.showAll = !elements.onlyAnalyzed.checked;
        state.itemsPerPage = parseInt(elements.itemsPerPageSelect.value);
    }

    // --- API Call ---
    async function fetchNews() {
        elements.newsContainer.innerHTML = `<div class="text-center p-16"><div class="inline-block animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full"></div></div>`;
        elements.paginationContainer.classList.add('hidden');

        const params = new URLSearchParams({
            page: state.currentPage,
            limit: state.itemsPerPage,
            query: state.query,
            category: state.category,
            source: state.source,
            province: state.province,
            start_date: state.startDate,
            end_date: state.endDate,
            sortBy: state.sortBy,
            show_all: state.showAll,
        });
        
        try {
            const response = await fetch(`/api/filter_news?${params}`);
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();
            renderResults(data);
        } catch (error) {
            console.error('Fetch error:', error);
            elements.newsContainer.innerHTML = `<div class="text-center p-16 text-red-500">Error al cargar las noticias.</div>`;
        }
    }

    // --- Rendering Functions ---
    function renderResults(data) {
        if (!data.articles || data.articles.length === 0) {
            elements.newsContainer.innerHTML = `<div class="text-center p-16 bg-white/50 dark:bg-slate-800/50 rounded-3xl"><h2 class="text-2xl font-bold">No se encontraron noticias</h2><p class="text-slate-500 mt-2">Intenta ajustar tus filtros.</p></div>`;
            elements.paginationContainer.classList.add('hidden');
            elements.resultsCounter.innerHTML = `<span>0 resultados</span>`;
            return;
        }

        if (state.view === 'grid') {
            renderGridView(data.articles);
        } else {
            renderListView(data.articles);
        }
        
        renderPagination(data);
        updateResultsCounter(data);
    }

    function renderGridView(articles) {
        const gridHtml = articles.map(article => `
            <article class="news-card bg-white/70 dark:bg-slate-800/70 backdrop-blur-lg rounded-2xl shadow-xl overflow-hidden flex flex-col">
                <a href="/noticia/${article.id}" class="block h-48 overflow-hidden">
                    <img src="${getProxiedImageUrl(article.image_url)}" alt="${article.title}" class="w-full h-full object-cover transition-transform duration-300 hover:scale-105">
                </a>
                <div class="p-5 flex flex-col flex-grow">
                    <h3 class="font-bold text-lg mb-3 leading-snug text-slate-800 dark:text-slate-100"><a href="/noticia/${article.id}" class="hover:text-blue-600 dark:hover:text-blue-400">${article.title}</a></h3>
                    <div class="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mb-4">
                        <span class="font-semibold text-blue-600 dark:text-blue-400">${article.source_name}</span>
                        <span>${formatDate(article.published_at)}</span>
                    </div>
                    <div class="mt-auto pt-4 border-t border-slate-200 dark:border-slate-700 space-y-3">
                        ${renderScores(article)}
                    </div>
                </div>
            </article>
        `).join('');
        elements.newsContainer.innerHTML = `<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">${gridHtml}</div>`;
    }
    
    function renderListView(articles) {
         const listHtml = articles.map(article => `
            <article class="news-card bg-white/70 dark:bg-slate-800/70 backdrop-blur-lg rounded-2xl shadow-xl overflow-hidden flex flex-col md:flex-row mb-6">
                <a href="/noticia/${article.id}" class="block md:w-1/3 h-48 md:h-auto overflow-hidden">
                    <img src="${getProxiedImageUrl(article.image_url)}" alt="${article.title}" class="w-full h-full object-cover transition-transform duration-300 hover:scale-105">
                </a>
                <div class="p-5 flex flex-col flex-grow md:w-2/3">
                    <h3 class="font-bold text-xl mb-3 leading-snug text-slate-800 dark:text-slate-100"><a href="/noticia/${article.id}" class="hover:text-blue-600 dark:hover:text-blue-400">${article.title}</a></h3>
                    <p class="text-slate-600 dark:text-slate-300 text-sm mb-4 line-clamp-2">${article.excerpt || article.summary || ''}</p>
                    <div class="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mb-4">
                        <span class="font-semibold text-blue-600 dark:text-blue-400">${article.source_name}</span>
                        <span>${formatDate(article.published_at)}</span>
                        ${article.category_name ? `<span class="px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded-full">${article.category_name}</span>` : ''}
                    </div>
                    <div class="mt-auto pt-4 border-t border-slate-200 dark:border-slate-700 space-y-3">
                        ${renderScores(article)}
                    </div>
                </div>
            </article>
        `).join('');
        elements.newsContainer.innerHTML = `<div>${listHtml}</div>`;
    }

    function renderScores(article) {
        if (article.veracity_score === null || article.veracity_score === undefined) {
            return `<div class="text-sm text-slate-400 italic text-center py-2"><i class="fas fa-robot mr-2"></i>Análisis pendiente</div>`;
        }
        return `
            <div class="grid grid-cols-3 gap-4 text-center">
                <div>
                    <div class="text-sm font-bold text-green-500">${article.veracity_score}%</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400">Veracidad</div>
                </div>
                <div>
                    <div class="text-sm font-bold text-blue-500">${article.civic_impact_score}%</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400">I. Cívico</div>
                </div>
                <div>
                    <div class="text-sm font-bold text-yellow-500">${article.local_relevance_score}%</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400">I. Popular</div>
                </div>
            </div>
        `;
    }
    
    function renderPagination(data) {
        if (data.total_pages <= 1) {
            elements.paginationContainer.classList.add('hidden');
            return;
        }
        elements.paginationContainer.classList.remove('hidden');
        elements.showingRange.textContent = `${(data.current_page - 1) * data.items_per_page + 1}-${Math.min(data.current_page * data.items_per_page, data.total_results)}`;
        elements.totalItems.textContent = data.total_results;

        let paginationHtml = '';
        paginationHtml += `<button data-page="${data.current_page - 1}" class="px-3 py-2 rounded-lg ${data.current_page === 1 ? 'opacity-50 cursor-not-allowed' : 'hover:bg-blue-100 dark:hover:bg-blue-900'}" ${data.current_page === 1 ? 'disabled' : ''}><i class="fas fa-chevron-left"></i></button>`;
        
        for (let i = 1; i <= data.total_pages; i++) {
            if (i === data.current_page) {
                paginationHtml += `<button data-page="${i}" class="w-10 h-10 rounded-lg bg-blue-600 text-white font-bold">${i}</button>`;
            } else if (i === 1 || i === data.total_pages || (i >= data.current_page - 2 && i <= data.current_page + 1)) {
                paginationHtml += `<button data-page="${i}" class="w-10 h-10 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900">${i}</button>`;
            } else if (i === data.current_page - 2 || i === data.current_page + 2) {
                paginationHtml += `<span class="w-10 h-10 flex items-center justify-center">...</span>`;
            }
        }
        
        paginationHtml += `<button data-page="${data.current_page + 1}" class="px-3 py-2 rounded-lg ${data.current_page === data.total_pages ? 'opacity-50 cursor-not-allowed' : 'hover:bg-blue-100 dark:hover:bg-blue-900'}" ${data.current_page === data.total_pages ? 'disabled' : ''}><i class="fas fa-chevron-right"></i></button>`;
        
        elements.paginationControls.innerHTML = paginationHtml;
    }

    function updateResultsCounter(data) {
        elements.resultsCounter.innerHTML = `<span class="font-bold">${data.total_results}</span> noticias encontradas`;
    }

    // --- Initial Data Load ---
    // ✅ CAMBIO: La función ahora es asíncrona y llama a la API
    async function initializeDynamicFilters() {
        try {
            const response = await fetch('/api/filter_options');
            if (!response.ok) throw new Error('Could not fetch filter options');
            const data = await response.json();

            elements.categoryFilter.innerHTML = '<option value="">Todas las categorías</option>' + data.categories.map(c => `<option value="${c}">${c}</option>`).join('');
            elements.sourceFilter.innerHTML = '<option value="">Todas las fuentes</option>' + data.sources.map(s => `<option value="${s.value}">${s.name}</option>`).join('');
            elements.provinceFilter.innerHTML = '<option value="">Todas las provincias</option>' + data.provinces.map(p => `<option value="${p}">${p}</option>`).join('');
        } catch (error) {
            console.error("Error initializing dynamic filters:", error);
            // Dejar los selectores vacíos pero funcionales
            elements.categoryFilter.innerHTML = '<option value="">Error al cargar</option>';
            elements.sourceFilter.innerHTML = '<option value="">Error al cargar</option>';
            elements.provinceFilter.innerHTML = '<option value="">Error al cargar</option>';
        }
    }

    // --- Event Listeners ---
    function setupEventListeners() {
        elements.advancedToggle.addEventListener('click', () => {
            const panel = elements.advancedFiltersPanel;
            if (panel.style.maxHeight) {
                panel.style.maxHeight = null;
                setTimeout(() => { panel.classList.remove('p-6'); }, 500);
            } else {
                panel.classList.add('p-6');
                panel.style.maxHeight = panel.scrollHeight + "px";
            }
        });

        elements.applyFiltersBtn.addEventListener('click', () => {
            state.currentPage = 1;
            updateStateFromUI();
            fetchNews();
        });
        
        elements.smartSearch.addEventListener('keyup', debounce((e) => {
             if (e.key === 'Enter') {
                state.currentPage = 1;
                updateStateFromUI();
                fetchNews();
            }
        }, 300));

        elements.resetFiltersBtn.addEventListener('click', () => {
            elements.smartSearch.value = '';
            elements.categoryFilter.value = '';
            elements.sourceFilter.value = '';
            elements.provinceFilter.value = '';
            elements.sortFilter.value = 'published_at';
            elements.dateStart.value = '';
            elements.dateEnd.value = '';
            elements.onlyAnalyzed.checked = true;
            state.currentPage = 1;
            updateStateFromUI();
            fetchNews();
        });

        elements.gridViewBtn.addEventListener('click', () => setView('grid'));
        elements.listViewBtn.addEventListener('click', () => setView('list'));

        elements.itemsPerPageSelect.addEventListener('change', (e) => {
            state.itemsPerPage = parseInt(e.target.value);
            state.currentPage = 1;
            fetchNews();
        });
        
        elements.paginationControls.addEventListener('click', (e) => {
            const button = e.target.closest('button');
            if (button && button.dataset.page) {
                state.currentPage = parseInt(button.dataset.page);
                fetchNews();
            }
        });
    }

    function setView(view) {
        state.view = view;
        const gridBtn = elements.gridViewBtn;
        const listBtn = elements.listViewBtn;
        
        gridBtn.classList.toggle('bg-blue-600', view === 'grid');
        gridBtn.classList.toggle('text-white', view === 'grid');
        listBtn.classList.toggle('bg-blue-600', view === 'list');
        listBtn.classList.toggle('text-white', view === 'list');
        
        gridBtn.classList.toggle('text-slate-600', view !== 'grid');
        gridBtn.classList.toggle('dark:text-slate-300', view !== 'grid');
        listBtn.classList.toggle('text-slate-600', view !== 'list');
        listBtn.classList.toggle('dark:text-slate-300', view !== 'list');
        
        fetchNews();
    }
    
    // --- App Initialization ---
    async function initializeApp() {
        await initializeDynamicFilters(); // Esperar a que los filtros se carguen primero
        updateStateFromUI();
        fetchNews();
        setupEventListeners();
    }

    initializeApp();
});