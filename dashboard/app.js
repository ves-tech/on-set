document.addEventListener('DOMContentLoaded', () => {
    let rawData = {};
    let specsFlatList = []; // Nested specs flattened for easy filtering

    // State
    const state = {
        currentTab: 'Introduction',
        filters: {
            creators: new Set(),
            consumers: new Set(),
            scope: new Set(),
            vfxTypes: new Set(),
            search: ''
        }
    };

    // Lookup for scope descriptions
    const scopeDescriptions = new Map();

    // Helper: Normalize Scope values (Title Case, singularize simple "s")
    function normalizeScope(val) {
        if (!val) return '';
        let str = val.trim();
        // Capitalize first letter
        str = str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();

        // Simple plural handling
        if (str.endsWith('s') && str.length > 4 && !str.endsWith('ss')) {
            return str.slice(0, -1);
        }
        return str;
    }

    const dom = {
        grid: document.getElementById('content-grid'),
        sidebar: document.getElementById('sidebar'),
        specsHeader: document.getElementById('specs-header'),
        filterContainer: document.getElementById('filter-container'),
        creatorFilters: document.getElementById('creator-filters'),
        consumerFilters: document.getElementById('consumer-filters'),
        scopeFilters: document.getElementById('scope-filters'),
        vfxTypeFilters: document.getElementById('vfx-type-filters'),
        searchInput: document.getElementById('search-input'),
        stats: document.getElementById('stats-display'),
        tabs: document.querySelectorAll('.tab-btn'),
        printBtn: document.getElementById('print-btn'),
        tooltip: document.getElementById('tooltip'),
        resetBtn: document.getElementById('reset-filters-btn'),
        mobileFilterBtn: document.getElementById('mobile-filter-btn'),
        mobileFilterCloseBtn: document.getElementById('mobile-filter-close-btn')
    };

    // Reset Filters Logic
    if (dom.resetBtn) {
        dom.resetBtn.addEventListener('click', () => {
            state.filters.creators.clear();
            state.filters.consumers.clear();
            state.filters.scope.clear();
            state.filters.vfxTypes.clear();
            // Optional: state.filters.search = ''; dom.searchInput.value = '';

            updateUrlParams();
            renderFilters(); // Re-renders checkboxes to unchecked state
            renderDataSetsGrid(); // Shows all items
        });
    }

    // Mobile Filter Modal Logic
    if (dom.mobileFilterBtn) {
        dom.mobileFilterBtn.addEventListener('click', () => {
            dom.sidebar.classList.add('modal-open');
            document.body.classList.add('filter-modal-open');
        });
    }

    if (dom.mobileFilterCloseBtn) {
        dom.mobileFilterCloseBtn.addEventListener('click', () => {
            dom.sidebar.classList.remove('modal-open');
            document.body.classList.remove('filter-modal-open');
        });
    }

    // Tooltip Logic
    document.addEventListener('mouseover', (e) => {
        const target = e.target.closest('[data-tooltip]');
        if (target) {
            const text = target.dataset.tooltip;
            if (text) {
                dom.tooltip.textContent = text;
                dom.tooltip.classList.remove('hidden');
                dom.tooltip.classList.add('visible');
            }
        }
    });

    document.addEventListener('mousemove', (e) => {
        if (dom.tooltip.classList.contains('visible')) {
            const offset = 15;
            let left = e.clientX + offset;
            let top = e.clientY + offset;

            if (left + 350 > window.innerWidth) {
                left = e.clientX - 350 - offset;
            }
            if (top + dom.tooltip.offsetHeight > window.innerHeight) {
                top = e.clientY - dom.tooltip.offsetHeight - offset;
            }

            dom.tooltip.style.left = `${left}px`;
            dom.tooltip.style.top = `${top}px`;
        }
    });

    document.addEventListener('mouseout', (e) => {
        const target = e.target.closest('[data-tooltip]');
        if (target) {
            dom.tooltip.classList.remove('visible');
            dom.tooltip.classList.add('hidden');
        }
    });

    // URL Synchronization
    function updateUrlParams() {
        const params = new URLSearchParams();
        params.set('tab', state.currentTab);

        if (state.filters.search) {
            params.set('search', state.filters.search);
        }
        if (state.filters.creators.size > 0) {
            params.set('creators', Array.from(state.filters.creators).join(','));
        }
        if (state.filters.consumers.size > 0) {
            params.set('consumers', Array.from(state.filters.consumers).join(','));
        }
        if (state.filters.scope.size > 0) {
            params.set('scope', Array.from(state.filters.scope).join(','));
        }
        if (state.filters.vfxTypes.size > 0) {
            params.set('vfxTypes', Array.from(state.filters.vfxTypes).join(','));
        }

        const newUrl = `${window.location.pathname}?${params.toString()}`;
        window.history.replaceState({}, '', newUrl);
    }

    function loadStateFromUrl() {
        const params = new URLSearchParams(window.location.search);
        const tab = params.get('tab');
        if (tab && ['Introduction', 'Scope Definitions', 'Data Sets', 'Directory Structure', 'Reference Docs'].includes(tab)) {
            state.currentTab = tab;
        }

        const search = params.get('search');
        if (search) {
            state.filters.search = search;
            dom.searchInput.value = search;
        }

        const creators = params.get('creators');
        if (creators) creators.split(',').forEach(c => state.filters.creators.add(c));

        const consumers = params.get('consumers');
        if (consumers) consumers.split(',').forEach(c => state.filters.consumers.add(c));

        const scope = params.get('scope');
        if (scope) scope.split(',').forEach(s => state.filters.scope.add(s));

        const vfxTypes = params.get('vfxTypes');
        if (vfxTypes) vfxTypes.split(',').forEach(s => state.filters.vfxTypes.add(s));
    }

    // Initialize
    if (typeof ON_SET_DATA !== 'undefined') {
        rawData = ON_SET_DATA;

        // Parse Scope Definitions
        if (rawData['Scope Definitions']) {
            rawData['Scope Definitions'].forEach(item => {
                Object.entries(item).forEach(([key, value]) => {
                    if (key === 'html') return;
                    const normalized = normalizeScope(key);
                    if (normalized) {
                        scopeDescriptions.set(normalized.toLowerCase(), value);
                    }
                });
            });
        }

        // Inject Version and Date
        if (rawData.version && rawData.publishDate) {
            const versionInfo = document.getElementById('version-info');
            if (versionInfo) {
                versionInfo.textContent = `v${rawData.version} | ${rawData.publishDate}`;
            }
        }

        processSpecs();
        loadStateFromUrl();
        renderFilters();
        switchTab(state.currentTab);
    } else {
        console.error('Error: ON_SET_DATA not found.');
        dom.stats.textContent = 'Error loading data.';
    }

    // Tabs Event Listeners
    dom.tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            dom.tabs.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            switchTab(btn.dataset.tab);
        });
    });

    function switchTab(tabName) {
        state.currentTab = tabName;
        updateUrlParams();

        dom.tabs.forEach(btn => {
            if (btn.dataset.tab === tabName) btn.classList.add('active');
            else btn.classList.remove('active');
        });

        if (tabName === 'Data Sets') {
            dom.sidebar.classList.remove('hidden');
            dom.specsHeader.classList.remove('hidden');
            dom.filterContainer.classList.remove('hidden');
            if (dom.mobileFilterBtn) dom.mobileFilterBtn.classList.remove('hidden');
            renderDataSetsGrid();
        } else {
            dom.sidebar.classList.add('hidden');
            dom.specsHeader.classList.add('hidden');
            if (dom.mobileFilterBtn) dom.mobileFilterBtn.classList.add('hidden');
            renderSimpleView(tabName);
        }
    }

    // Render Simple View (Intro, Tree, Ref Docs, Scope)
    function renderSimpleView(sectionName) {
        dom.grid.innerHTML = '';
        dom.sidebar.classList.add('hidden');
        dom.specsHeader.classList.add('hidden');
        dom.filterContainer.classList.add('hidden');
        dom.grid.classList.remove('text-view-mode');

        const title = document.createElement('h1');
        title.textContent = sectionName;
        title.className = 'section-main-title';
        title.style.gridColumn = '1 / -1';
        title.style.marginBottom = '2rem';
        title.style.color = 'var(--text-primary)';
        dom.grid.appendChild(title);

        const data = rawData[sectionName] || [];

        // Directory Tree
        if (sectionName === "Directory Structure" && typeof DIRECTORY_DATA !== 'undefined') {
            const treeContainer = document.createElement('div');
            treeContainer.className = 'tree-view-container';

            // Add Control Bar
            const controls = document.createElement('div');
            controls.className = 'tree-controls';
            controls.style.marginBottom = '1rem';
            controls.style.display = 'flex';
            controls.style.gap = '1rem';
            controls.style.justifyContent = 'flex-end';

            // Simple Download Link (Best for HTTP Server)
            const downloadBtn = document.createElement('a');
            downloadBtn.className = 'action-btn';
            downloadBtn.textContent = 'Download YAML';
            downloadBtn.href = '/data/directory_structure.yaml'; // Absolute path from server root
            downloadBtn.setAttribute('download', 'directory_structure.yaml');
            downloadBtn.target = '_blank'; // Force new tab behavior if download fails to trigger
            downloadBtn.style.textDecoration = 'none';
            downloadBtn.style.display = 'inline-block';

            const printTreeBtn = document.createElement('button');
            printTreeBtn.className = 'action-btn';
            printTreeBtn.textContent = 'Print Tree';
            printTreeBtn.onclick = () => window.print();

            controls.appendChild(printTreeBtn);
            controls.appendChild(downloadBtn);

            dom.grid.appendChild(controls);

            const rootUl = document.createElement('ul');
            rootUl.className = 'tree-root';

            function buildTree(nodes, parentElement) {
                nodes.forEach(node => {
                    const li = document.createElement('li');
                    li.className = 'tree-node';
                    const hasChildren = node.children && node.children.length > 0;

                    const contentDiv = document.createElement('div');
                    contentDiv.className = 'tree-content';

                    const toggleSpan = document.createElement('span');
                    toggleSpan.className = `tree-toggle ${hasChildren ? '' : 'empty'}`;
                    toggleSpan.textContent = hasChildren ? '▼' : '•';

                    const iconSpan = document.createElement('span');
                    iconSpan.className = 'tree-icon';
                    iconSpan.textContent = hasChildren ? '📂' : '📄';

                    const nameSpan = document.createElement('span');
                    nameSpan.textContent = node.name;

                    contentDiv.appendChild(toggleSpan);
                    contentDiv.appendChild(iconSpan);
                    contentDiv.appendChild(nameSpan);
                    li.appendChild(contentDiv);

                    if (hasChildren) {
                        const childrenUl = document.createElement('ul');
                        childrenUl.className = 'tree-children';
                        buildTree(node.children, childrenUl);
                        li.appendChild(childrenUl);

                        contentDiv.addEventListener('click', (e) => {
                            e.stopPropagation();
                            const isHidden = childrenUl.style.display === 'none';
                            childrenUl.style.display = isHidden ? 'block' : 'none';
                            toggleSpan.textContent = isHidden ? '▼' : '▶';
                        });
                    }
                    parentElement.appendChild(li);
                });
            }

            buildTree(DIRECTORY_DATA, rootUl);
            treeContainer.appendChild(rootUl);
            dom.grid.appendChild(treeContainer);
            return;
        }

        // Scope Definitions (Grid + Cards)
        if (sectionName === "Scope Definitions") {
            data.forEach(item => {
                if (item.html) {
                    const div = document.createElement('div');
                    div.className = 'text-content intro-block';
                    div.style.gridColumn = '1 / -1';
                    div.style.maxWidth = '800px';
                    div.style.margin = '0 auto 2rem auto';
                    div.innerHTML = item.html;
                    dom.grid.appendChild(div);
                } else {
                    Object.entries(item).forEach(([key, value]) => {
                        if (key === 'html') return;
                        const card = document.createElement('div');
                        card.className = 'card';
                        card.style.marginBottom = '1.5rem';

                        const header = document.createElement('div');
                        header.className = 'card-header';
                        const titleDiv = document.createElement('div');
                        titleDiv.className = 'card-title';
                        titleDiv.textContent = key;
                        titleDiv.setAttribute('data-tooltip', key);
                        header.appendChild(titleDiv);

                        const body = document.createElement('div');
                        body.className = 'card-body';
                        const p = document.createElement('p');
                        p.style.whiteSpace = 'pre-wrap';
                        p.textContent = value;
                        body.appendChild(p);

                        card.appendChild(header);
                        card.appendChild(body);
                        dom.grid.appendChild(card);
                    });
                }
            });
            return;
        }

        // Text Blocks (Intro, Ref Docs, Feedback)
        if (['Introduction', 'Reference Docs', 'Feedback'].includes(sectionName)) {
            dom.grid.classList.add('text-view-mode');
            const container = document.createElement('div');
            container.className = 'text-content';
            data.forEach(item => {
                if (item.html) {
                    const div = document.createElement('div');
                    div.innerHTML = item.html;
                    container.appendChild(div);
                }
            });
            dom.grid.appendChild(container);
            return;
        }

        // Fallback
        data.forEach(item => {
            if (item.html) {
                if (item.type === "tree_view") {
                    const fallback = document.createElement('div');
                    fallback.textContent = "Directory Data not loaded.";
                    dom.grid.appendChild(fallback);
                    return;
                }
                const div = document.createElement('div');
                div.innerHTML = item.html;
                dom.grid.appendChild(div);
            }
        });
    }

    function processSpecs() {
        specsFlatList = [];
        const specs = rawData['Data Sets'] || rawData['Specs'] || []; // Support both names just in case

        specs.forEach(h1 => {
            h1.subsections.forEach(h2 => {
                h2.items.forEach(item => {
                    const creators = Array.isArray(item.Creator) ? item.Creator : (item.Creator ? [item.Creator] : []);
                    const consumers = Array.isArray(item.Consumer) ? item.Consumer : (item.Consumer ? [item.Consumer] : []);
                    let rawScope = Array.isArray(item.Scope) ? item.Scope : (item.Scope ? [item.Scope] : []);
                    const scope = rawScope.map(s => normalizeScope(s)).filter(s => s.length > 0);

                    const vfxTypes = Array.isArray(item.VFXTypes) ? item.VFXTypes : (item.VFXTypes ? [item.VFXTypes] : []);

                    specsFlatList.push({
                        h1Title: h1.title,
                        h2Title: h2.title,
                        creators: creators,
                        consumers: consumers,
                        scope: scope,
                        vfxTypes: vfxTypes,
                        original: item
                    });
                });
            });
        });
    }

    function renderFilters() {
        const allCreators = new Set();
        const allConsumers = new Set();
        const allScope = new Set();
        const allVfxTypes = new Set();

        specsFlatList.forEach(item => {
            item.creators.forEach(c => allCreators.add(c));
            item.consumers.forEach(c => allConsumers.add(c));
            item.scope.forEach(c => allScope.add(c));
            item.vfxTypes.forEach(c => allVfxTypes.add(c));
        });

        const renderGroup = (container, items, type) => {
            container.innerHTML = '';
            const sortedItems = Array.from(items).sort();
            const LIMIT = 5;
            const hasMore = sortedItems.length > LIMIT;

            sortedItems.forEach((value, index) => {
                const label = document.createElement('label');
                label.className = 'checkbox-label';
                if (index >= LIMIT) {
                    label.classList.add('hidden-filter-item');
                    label.style.display = 'none';
                }

                const input = document.createElement('input');
                input.type = 'checkbox';
                input.value = value;
                if (state.filters[type].has(value)) input.checked = true;

                input.addEventListener('change', (e) => {
                    if (e.target.checked) state.filters[type].add(value);
                    else state.filters[type].delete(value);
                    updateUrlParams();
                    renderDataSetsGrid();
                });

                label.appendChild(input);
                label.appendChild(document.createTextNode(value));
                if (type === 'scope') {
                    const desc = scopeDescriptions.get(value.toLowerCase());
                    if (desc) label.dataset.tooltip = desc;
                }
                container.appendChild(label);
            });

            if (hasMore) {
                const toggleBtn = document.createElement('button');
                toggleBtn.className = 'filter-toggle';
                toggleBtn.textContent = 'See more';
                let expanded = false;
                toggleBtn.addEventListener('click', () => {
                    expanded = !expanded;
                    const hiddenItems = container.querySelectorAll('.hidden-filter-item');
                    hiddenItems.forEach(item => item.style.display = expanded ? 'flex' : 'none');
                    toggleBtn.textContent = expanded ? 'See less' : 'See more';
                });
                container.appendChild(toggleBtn);
            }
        };

        renderGroup(dom.creatorFilters, allCreators, 'creators');
        renderGroup(dom.consumerFilters, allConsumers, 'consumers');
        renderGroup(dom.scopeFilters, allScope, 'scope');
        renderGroup(dom.vfxTypeFilters, allVfxTypes, 'vfxTypes');
    }

    dom.searchInput.addEventListener('input', (e) => {
        state.filters.search = e.target.value.toLowerCase();
        updateUrlParams();
        renderDataSetsGrid();
    });

    function renderDataSetsGrid() {
        dom.grid.innerHTML = '';
        dom.grid.classList.remove('text-view-mode');

        const title = document.createElement('div');
        title.innerHTML = '<h1 style="color: var(--text-primary);">Data Sets</h1>';
        title.style.gridColumn = '1 / -1';
        dom.grid.appendChild(title);

        const filteredItems = specsFlatList.filter(item => {
            if (state.filters.search) {
                const jsonStr = JSON.stringify(item.original).toLowerCase();
                if (!jsonStr.includes(state.filters.search)) return false;
            }
            if (state.filters.creators.size > 0 && !item.creators.some(c => state.filters.creators.has(c))) return false;
            if (state.filters.consumers.size > 0 && !item.consumers.some(c => state.filters.consumers.has(c))) return false;
            if (state.filters.scope.size > 0 && !item.scope.some(c => state.filters.scope.has(c))) return false;
            if (state.filters.vfxTypes.size > 0 && !item.vfxTypes.some(c => state.filters.vfxTypes.has(c))) return false;
            return true;
        });

        dom.stats.textContent = `Showing ${filteredItems.length} items`;

        const grouped = {};
        filteredItems.forEach(item => {
            if (!grouped[item.h1Title]) grouped[item.h1Title] = {};
            if (!grouped[item.h1Title][item.h2Title]) grouped[item.h1Title][item.h2Title] = [];
            grouped[item.h1Title][item.h2Title].push(item);
        });

        for (const [h1Title, h2Group] of Object.entries(grouped)) {
            const h1El = document.createElement('div');
            h1El.className = 'section-h1';
            h1El.innerHTML = `<h2>${h1Title}</h2>`;
            dom.grid.appendChild(h1El);

            for (const [h2Title, items] of Object.entries(h2Group)) {
                items.forEach(item => {
                    renderCard(item.original, dom.grid, item.creators, item.consumers, item.scope, item.vfxTypes, h2Title);
                });
            }
        }
    }

    function renderCard(itemData, container, creators, consumers, scope, vfxTypes, sectionTitle) {
        const card = document.createElement('div');
        card.className = 'card';
        const displayTitle = sectionTitle || 'Item';
        const creatorTags = creators.map(c => `<span class="tag">${c}</span>`).join('');
        const consumerTags = consumers.map(c => `<span class="tag">${c}</span>`).join('');
        const vfxTypeTags = vfxTypes ? vfxTypes.map(c => `<span class="tag" style="background: rgba(16, 185, 129, 0.1); color: #10b981;">${c}</span>`).join('') : ''; // Different color (Emerald-ish)
        const scopeTags = scope.map(s => {
            const desc = scopeDescriptions.get(s.toLowerCase()) || '';
            const tooltipAttr = desc ? ` data-tooltip="${desc.replace(/"/g, '&quot;')}"` : '';
            return `<span class="tag"${tooltipAttr}>${s}</span>`;
        }).join('');

        let bodyContent = '';
        const skipKeys = ['Creator', 'Consumer', 'Description', 'Scope', 'VFXTypes'];

        if (itemData.Description) {
            bodyContent += `<div class="field-item" style="color: var(--text-secondary); margin-bottom: 1rem;"><p>${itemData.Description}</p></div>`;
        }

        Object.entries(itemData).forEach(([key, value]) => {
            if (skipKeys.includes(key)) return;
            let valueHtml = '';
            if (Array.isArray(value)) valueHtml = `<ul style="margin: 0; padding-left: 1.2rem;">${value.map(v => `<li>${v}</li>`).join('')}</ul>`;
            else valueHtml = `<p>${value}</p>`;
            bodyContent += `<div class="field-group"><span class="field-label">${key}</span><div class="field-value">${valueHtml}</div></div>`;
        });

        card.innerHTML = `
        <div class="card-header"><div class="card-title">${displayTitle}</div></div>
        <div class="card-body">
            ${bodyContent}
            <div style="margin-top: 1rem; border-top: 1px solid var(--border-color); padding-top: 1rem; display: flex; flex-direction: column; gap: 0.5rem;">
                ${vfxTypes && vfxTypes.length ? `<div class="field-group"><span class="field-label">VFX Types</span><div class="tag-container">${vfxTypeTags}</div></div>` : ''}
                ${scope.length ? `<div class="field-group"><span class="field-label">Scope</span><div class="tag-container">${scopeTags}</div></div>` : ''}
                ${creators.length ? `<div class="field-group"><span class="field-label">Creators</span><div class="tag-container">${creatorTags}</div></div>` : ''}
                ${consumers.length ? `<div class="field-group"><span class="field-label">Consumers</span><div class="tag-container">${consumerTags}</div></div>` : ''}
            </div>
        </div>`;
        container.appendChild(card);
    }

    if (dom.printBtn) {
        dom.printBtn.addEventListener('click', () => window.print());
    }
});
