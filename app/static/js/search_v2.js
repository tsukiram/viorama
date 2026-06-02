// app/static/js/search_v2.js
//
// Paper Search v2 frontend.
// - POST /search-v2/chat untuk discuss agent.
// - POST /search-v2/search_process/<chat_id> untuk kick off keyword search.
// - GET /search-v2/check_status/<chat_id>?after=N untuk polling event.
// - Events di-render sebagai section header / keyword block (collapsible).

document.addEventListener('DOMContentLoaded', () => {
    console.log('[INIT-V2] search_v2.js loaded');

    // ===== DOM refs =====
    const chatSidebar = document.getElementById('chat-sidebar');
    const minimizeBtn = document.getElementById('minimize-sidebar-btn');
    const maximizeBtn = document.getElementById('maximize-sidebar-btn');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const newChatBtn = document.getElementById('new-chat-btn');
    const sessionList = document.getElementById('session-list');
    const inputArea = document.querySelector('.chat-input-area');
    const processingBanner = document.getElementById('processing-banner');

    // Modals
    const deleteModalOverlay = document.getElementById('delete-modal-overlay');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
    const renameModalOverlay = document.getElementById('rename-modal-overlay');
    const confirmRenameBtn = document.getElementById('confirm-rename-btn');
    const cancelRenameBtn = document.getElementById('cancel-rename-btn');
    const renameInput = document.getElementById('rename-input');

    // ===== State =====
    let sessionToDeleteId = null;
    let sessionToRenameId = null;
    let activeDropdown = null;
    let isProcessing = false;
    let currentChatId = null;
    let pollingInterval = null;

    // Filter state — dikirim bersama setiap pencarian.
    const filterState = {
        yearFrom:    '',       // YYYY (string), kosong = tidak filter
        yearTo:      '',
        paperType:   '',       // '' | 'skripsi' | 'tesis' | 'article' | 'book' | dst.
    };

    const buildFilterPayload = () => ({
        date_from:   filterState.yearFrom ? `${filterState.yearFrom}-01-01` : '',
        date_to:     filterState.yearTo   ? `${filterState.yearTo}-12-31`   : '',
        paper_type:  filterState.paperType,
    });

    // ===== Helpers =====
    const showModal = (m) => { if (m) { m.classList.add('visible'); document.body.style.overflow = 'hidden'; } };
    const hideModal = (m) => { if (m) { m.classList.remove('visible'); document.body.style.overflow = ''; } };

    const getCurrentSessionId = () => {
        const active = sessionList?.querySelector('.session-item.active');
        return active ? active.dataset.sessionId : null;
    };

    const scrollToBottom = () => {
        const display = document.getElementById('chat-display');
        if (display) display.scrollTop = display.scrollHeight;
    };

    const setInputHeight = () => {
        if (!messageInput) return;
        messageInput.style.height = 'auto';
        messageInput.style.height = `${messageInput.scrollHeight}px`;
    };

    const escapeHtml = (s) => {
        if (s == null) return '';
        return String(s).replace(/[&<>"']/g, (c) => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        })[c]);
    };

    // ===== Input lock state =====
    const lockInput = () => {
        isProcessing = true;
        if (messageInput) messageInput.disabled = true;
        if (sendButton) {
            sendButton.disabled = true;
            sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        }
        if (inputArea) inputArea.classList.add('v2-locked');
        if (processingBanner) processingBanner.style.display = 'flex';
    };

    const unlockInput = () => {
        isProcessing = false;
        if (messageInput) {
            messageInput.disabled = false;
            messageInput.focus();
        }
        if (sendButton) {
            sendButton.disabled = (messageInput?.value.trim() === '');
            sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
        }
        if (inputArea) inputArea.classList.remove('v2-locked');
        if (processingBanner) processingBanner.style.display = 'none';
    };

    const toggleSendButton = () => {
        if (sendButton && messageInput) {
            sendButton.disabled = messageInput.value.trim() === '' || isProcessing;
        }
    };

    // ===== Filter popup (di kanan textarea, expand ke atas) =====
    const filterTrigger = document.getElementById('v2-filter-trigger');
    const filterPopup   = document.getElementById('v2-filter-popup');
    const filterBadges  = document.getElementById('v2-filter-badges');
    const dateFromInp   = document.getElementById('v2-date-from');
    const dateToInp     = document.getElementById('v2-date-to');
    const typeSelect    = document.getElementById('v2-filter-type');
    const filterReset   = document.getElementById('v2-filter-reset');

    const _renderFilterBadges = () => {
        if (!filterBadges) return;
        const tags = [];
        if (filterState.yearFrom || filterState.yearTo) {
            const f = filterState.yearFrom || '...';
            const t = filterState.yearTo   || '...';
            tags.push(`${f}–${t}`);
        }
        if (filterState.paperType) {
            // Pakai label dari <option> agar nama yg ditampilkan rapi (mis. "Artikel Jurnal")
            const opt = typeSelect?.querySelector(`option[value="${filterState.paperType}"]`);
            tags.push(opt ? opt.textContent : filterState.paperType);
        }
        filterBadges.innerHTML = tags.length
            ? tags.map(t => `<span class="v2-filter-badge">${t}</span>`).join('')
            : '';
        if (filterTrigger) {
            filterTrigger.classList.toggle('has-badges', tags.length > 0);
        }
    };

    const _toggleFilterPopup = (force) => {
        if (!filterPopup || !filterTrigger) return;
        const isOpen = !filterPopup.hidden;
        const next = typeof force === 'boolean' ? force : !isOpen;
        filterPopup.hidden = !next;
        filterTrigger.setAttribute('aria-expanded', next ? 'true' : 'false');
        filterTrigger.classList.toggle('is-open', next);
    };

    if (filterTrigger) {
        filterTrigger.addEventListener('click', (e) => {
            e.stopPropagation();
            _toggleFilterPopup();
        });
    }
    document.addEventListener('click', (e) => {
        if (!filterPopup || filterPopup.hidden) return;
        if (!e.target.closest('#v2-filter-bar')) _toggleFilterPopup(false);
    });

    // Year inputs (from/to)
    const _onYearChange = () => {
        filterState.yearFrom = (dateFromInp?.value || '').trim();
        filterState.yearTo   = (dateToInp?.value   || '').trim();
        _renderFilterBadges();
    };
    if (dateFromInp) dateFromInp.addEventListener('input', _onYearChange);
    if (dateToInp)   dateToInp.addEventListener('input', _onYearChange);

    // Tipe karya dropdown
    if (typeSelect) {
        typeSelect.addEventListener('change', () => {
            filterState.paperType = typeSelect.value;
            _renderFilterBadges();
        });
    }

    // Reset filter
    if (filterReset) {
        filterReset.addEventListener('click', () => {
            filterState.yearFrom = '';
            filterState.yearTo = '';
            filterState.paperType = '';
            if (dateFromInp) dateFromInp.value = '';
            if (dateToInp)   dateToInp.value = '';
            if (typeSelect)  typeSelect.value = '';
            _renderFilterBadges();
        });
    }

    // ===== Sidebar toggle =====
    if (chatSidebar && minimizeBtn && maximizeBtn) {
        if (localStorage.getItem('sidebarMinimized') === 'true') {
            chatSidebar.classList.add('minimized');
        }
        minimizeBtn.addEventListener('click', () => {
            chatSidebar.classList.add('minimized');
            localStorage.setItem('sidebarMinimized', 'true');
        });
        maximizeBtn.addEventListener('click', () => {
            chatSidebar.classList.remove('minimized');
            localStorage.setItem('sidebarMinimized', 'false');
        });
    }

    // ===== Mobile sidebar toggle (tap header or arrow to expand/collapse) =====
    const sidebarHeader = document.querySelector('.sidebar-header');
    if (sidebarHeader && chatSidebar) {
        sidebarHeader.addEventListener('click', (e) => {
            if (window.innerWidth > 768) return;
            chatSidebar.classList.toggle('expanded');
        });
    }

    // ===== Render helpers =====
    const ensureChatDisplay = () => {
        let container = document.getElementById('chat-display');

        // Kalau chat-display sudah punya wrapper kotak putih (.chat-container-active),
        // tinggal pakai (kasus halaman dengan current_session).
        if (container && container.closest('.chat-container-active')) {
            container.style.display = 'flex';
            return container;
        }

        // Kalau ada chat-display tanpa wrapper (placeholder kosong di halaman baru),
        // buang dulu beserta placeholder-nya supaya bisa kita ganti dengan kotak putih.
        if (container) {
            container.closest('.chat-container-placeholder')?.remove();
            container.remove();
            container = null;
        }

        // First message — hapus welcome banner & suggestion cards
        document.querySelector('.welcome-banner')?.remove();
        document.querySelector('.suggestion-cards-grid')?.remove();

        const main = document.querySelector('.chat-main');
        main?.querySelector('.chat-container-placeholder')?.remove();

        // Bikin kotak putih + chat-display di dalamnya
        const active = document.createElement('div');
        active.className = 'chat-container-active neo-card';
        container = document.createElement('div');
        container.id = 'chat-display';
        container.className = 'chat-display';
        active.appendChild(container);

        const inputAreaEl = main?.querySelector('.chat-input-area');
        if (inputAreaEl) main.insertBefore(active, inputAreaEl);
        else if (main) main.appendChild(active);

        container.style.display = 'flex';
        return container;
    };

    const appendUserMessage = (text) => {
        const container = ensureChatDisplay();
        const div = document.createElement('div');
        div.className = 'message is-user';
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.textContent = text;
        div.appendChild(bubble);
        container.appendChild(div);
        scrollToBottom();
    };

    const appendAiMessage = (markdownText, chatId) => {
        const container = ensureChatDisplay();
        const div = document.createElement('div');
        div.className = 'message is-ai';
        if (chatId) div.dataset.chatId = chatId;
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        try {
            bubble.innerHTML = (typeof marked !== 'undefined')
                ? marked.parse(markdownText || '', { breaks: true })
                : (markdownText || '').replace(/\n/g, '<br>');
        } catch (e) {
            bubble.innerHTML = (markdownText || '').replace(/\n/g, '<br>');
        }
        div.appendChild(bubble);

        // Copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.title = 'Copy text';
        copyBtn.innerHTML = '<i class="far fa-copy"></i><i class="fas fa-check"></i>';
        div.appendChild(copyBtn);

        container.appendChild(div);
        scrollToBottom();
        return div;
    };

    const appendLoadingBubble = (text = 'Memproses...') => {
        const container = ensureChatDisplay();
        const div = document.createElement('div');
        div.className = 'message is-ai v2-loading-bubble';
        div.innerHTML = `<div class="message-bubble"><i class="fas fa-spinner fa-spin"></i> ${escapeHtml(text)}</div>`;
        container.appendChild(div);
        scrollToBottom();
        return div;
    };

    // Typing indicator (3 dot animation) — mirip general inquiries.
    const showTypingIndicator = () => {
        const container = ensureChatDisplay();
        // Hindari duplikat indikator
        const existing = document.getElementById('typing-indicator');
        if (existing) return existing;

        const div = document.createElement('div');
        div.id = 'typing-indicator';
        div.className = 'message is-ai typing-indicator';
        div.innerHTML = '<div class="message-bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>';
        container.appendChild(div);
        scrollToBottom();
        return div;
    };

    const removeTypingIndicator = () => {
        document.getElementById('typing-indicator')?.remove();
    };

    // Typewriter: tampilkan teks per-karakter walau server kirim chunk besar.
    const createTypewriter = (bubbleDiv, onUpdate) => {
        let pending = '';
        let displayed = '';
        let streamEnded = false;
        let rafId = null;
        let lastTick = 0;
        let resolveDone = null;
        const donePromise = new Promise((res) => { resolveDone = res; });
        const baseCharsPerSec = 120;

        const renderBubble = () => {
            const cursor = (streamEnded && pending.length === 0) ? '' : '<span class="stream-cursor"></span>';
            try {
                bubbleDiv.innerHTML = (typeof marked !== 'undefined')
                    ? marked.parse(displayed, { breaks: true }) + cursor
                    : escapeHtml(displayed).replace(/\n/g, '<br>') + cursor;
            } catch {
                bubbleDiv.innerHTML = escapeHtml(displayed).replace(/\n/g, '<br>') + cursor;
            }
        };

        const tick = (ts) => {
            if (!lastTick) lastTick = ts;
            const dt = ts - lastTick;
            lastTick = ts;

            const backlog = pending.length;
            let cps = baseCharsPerSec;
            if (backlog > 600) cps = baseCharsPerSec * 6;
            else if (backlog > 300) cps = baseCharsPerSec * 3;
            else if (backlog > 120) cps = baseCharsPerSec * 1.8;

            let chars = Math.max(1, Math.floor((cps * dt) / 1000));
            if (chars > pending.length) chars = pending.length;

            if (chars > 0) {
                displayed += pending.slice(0, chars);
                pending = pending.slice(chars);
                renderBubble();
                if (onUpdate) onUpdate(displayed);
            }

            if (streamEnded && pending.length === 0) {
                rafId = null;
                if (resolveDone) resolveDone(displayed);
                return;
            }
            rafId = requestAnimationFrame(tick);
        };

        const start = () => {
            if (rafId == null) {
                lastTick = 0;
                rafId = requestAnimationFrame(tick);
            }
        };

        return {
            push(text) {
                if (!text) return;
                pending += text;
                start();
            },
            end() {
                streamEnded = true;
                start();
                return donePromise;
            },
            flushNow() {
                if (pending.length > 0) {
                    displayed += pending;
                    pending = '';
                    renderBubble();
                }
                streamEnded = true;
                if (rafId) cancelAnimationFrame(rafId);
                rafId = null;
                renderBubble();
                if (resolveDone) resolveDone(displayed);
                return displayed;
            },
            getDisplayed() { return displayed; },
        };
    };

    const addSessionToSidebar = (sessionId, title) => {
        if (!sessionList) return;
        const empty = sessionList.querySelector('.empty-history');
        if (empty) empty.remove();
        sessionList.querySelectorAll('.session-item.active').forEach((el) => el.classList.remove('active'));

        const li = document.createElement('li');
        li.className = 'session-item active';
        li.dataset.sessionId = sessionId;
        li.innerHTML = `
            <a href="/search-v2/${sessionId}" class="session-link">
                <span class="session-title"></span>
            </a>
            <button class="session-menu-btn" title="Options">
                <i class="fas fa-ellipsis-h"></i>
            </button>
            <div class="session-menu-dropdown">
                <button class="menu-item rename-session-btn">
                    <i class="fas fa-edit"></i>
                    <span>Rename</span>
                </button>
                <button class="menu-item delete-session-btn">
                    <i class="fas fa-trash-alt"></i>
                    <span>Delete</span>
                </button>
            </div>`;
        li.querySelector('.session-title').textContent = title || 'New Search';
        sessionList.insertBefore(li, sessionList.firstChild);
    };

    // ===== Search results UI inside an AI message =====
    const ensureResultsContainer = (aiMessageDiv) => {
        let results = aiMessageDiv.querySelector('.v2-search-results');
        if (!results) {
            results = document.createElement('div');
            results.className = 'v2-search-results';
            aiMessageDiv.querySelector('.message-bubble')?.appendChild(results);
        }
        return results;
    };

    const ensureCancelBar = (aiMessageDiv, chatId) => {
        let bar = aiMessageDiv.querySelector('.v2-search-status-bar');
        if (bar) return bar;
        bar = document.createElement('div');
        bar.className = 'v2-search-status-bar';
        bar.innerHTML = `
            <div class="v2-search-status-text">
                <span class="v2-search-pulse"></span>
                <span>Sedang mencari di Digilib</span>
            </div>
            <button class="v2-cancel-btn" type="button" title="Batalkan pencarian">
                <i class="fas fa-times"></i>
                <span>Berhenti</span>
            </button>`;
        // Insert SEBELUM v2-search-results biar tampil di atas
        const bubble = aiMessageDiv.querySelector('.message-bubble');
        const results = bubble?.querySelector('.v2-search-results');
        if (bubble && results) bubble.insertBefore(bar, results);
        else if (bubble) bubble.appendChild(bar);

        const btn = bar.querySelector('.v2-cancel-btn');
        btn.addEventListener('click', async () => {
            if (!chatId) return;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Berhenti...</span>';
            try {
                await fetch(`/search-v2/cancel_search/${chatId}`, { method: 'POST' });
            } catch (e) { console.error(e); }
        });
        return bar;
    };

    const removeCancelBar = (aiMessageDiv) => {
        aiMessageDiv?.querySelector('.v2-search-status-bar')?.remove();
    };

    const renderSectionHeader = (resultsContainer, sectionName) => {
        // Avoid duplicate section header
        const exists = resultsContainer.querySelector(`.v2-section-header[data-section="${sectionName}"]`);
        if (exists) return exists;

        const header = document.createElement('div');
        header.className = 'v2-section-header' + (sectionName === 'tambahan' ? ' is-tambahan' : '');
        header.dataset.section = sectionName;
        const label = sectionName === 'utama' ? 'Kata Kunci Utama' : 'Kata Kunci Tambahan';
        const icon = sectionName === 'utama' ? 'fa-star' : 'fa-plus-circle';
        header.innerHTML = `<i class="fas ${icon}"></i> <span>${label}</span>`;
        resultsContainer.appendChild(header);
        scrollToBottom();
        return header;
    };

    // Helper: cari blok keyword yg sudah ada di DOM (untuk dimorph dari "searching" ke result).
    const findKeywordBlock = (resultsContainer, keyword) => {
        const blocks = resultsContainer.querySelectorAll('.v2-keyword-block');
        for (const b of blocks) {
            if (b.dataset.keyword === keyword) return b;
        }
        return null;
    };

    // Helper: trigger entry animation sekali, lalu auto-remove class supaya
    // tidak ikut re-trigger saat class lain diubah.
    const _triggerEnterAnim = (el) => {
        el.classList.add('v2-block-enter');
        setTimeout(() => el.classList.remove('v2-block-enter'), 450);
    };

    // State 1: keyword baru mulai dicari — tampilkan placeholder dengan spinner.
    const renderKeywordStart = (resultsContainer, event) => {
        const { keyword, kw_type } = event;
        if (findKeywordBlock(resultsContainer, keyword)) return;

        const block = document.createElement('div');
        block.className = 'v2-keyword-block is-searching' + (kw_type === 'tambahan' ? ' is-tambahan' : '');
        block.dataset.keyword = keyword;

        const summary = document.createElement('div');
        summary.className = 'v2-kw-summary';

        const text = document.createElement('div');
        text.className = 'v2-kw-summary-text';
        text.innerHTML = `
            <span class="v2-spinner"></span>
            <span class="v2-kw-label">Mencari kata kunci</span>
            <span class="kw-quote">${escapeHtml(keyword)}</span>
        `;
        summary.appendChild(text);
        block.appendChild(summary);

        resultsContainer.appendChild(block);
        _triggerEnterAnim(block);
        scrollToBottom();
        return block;
    };

    // State 2: hasil keyword diterima — morph blok jadi state "selesai".
    const renderKeywordBlock = (resultsContainer, kr) => {
        const { keyword, kw_type, count, results } = kr;

        // Cari blok yg sudah ada (dari keyword_start) — kalau ada, morph; kalau tidak, bikin baru.
        let block = findKeywordBlock(resultsContainer, keyword);

        if (!block) {
            block = document.createElement('div');
            block.dataset.keyword = keyword;
            resultsContainer.appendChild(block);
            // Block baru (mis. dari restorePersistedResults) — kasih entry animation
            _triggerEnterAnim(block);
        }

        block.className = 'v2-keyword-block is-done'
            + (kw_type === 'tambahan' ? ' is-tambahan' : '')
            + (count > 0 ? ' has-results' : ' no-results');

        // Wipe & re-render
        block.innerHTML = '';

        const summary = document.createElement('div');
        summary.className = 'v2-kw-summary';

        const text = document.createElement('div');
        text.className = 'v2-kw-summary-text';
        if (count > 0) {
            text.innerHTML = `
                <span class="v2-status-icon is-success"><i class="fas fa-check"></i></span>
                <span class="kw-quote">${escapeHtml(keyword)}</span>
                <span class="v2-kw-count">${count} karya tulis</span>
            `;
        } else {
            text.innerHTML = `
                <span class="v2-status-icon is-empty"><i class="far fa-circle"></i></span>
                <span class="kw-quote">${escapeHtml(keyword)}</span>
                <span class="v2-kw-count is-zero">tidak ditemukan</span>
            `;
        }
        summary.appendChild(text);

        if (count > 0) {
            const toggle = document.createElement('button');
            toggle.className = 'v2-kw-toggle';
            toggle.type = 'button';
            toggle.innerHTML = `<i class="fas fa-chevron-down chevron"></i>`;
            summary.appendChild(toggle);
        }
        block.appendChild(summary);

        if (count > 0 && Array.isArray(results) && results.length > 0) {
            const list = document.createElement('ul');
            list.className = 'v2-paper-list';
            results.forEach((p) => {
                const li = document.createElement('li');
                li.className = 'v2-paper-item';
                const cite = escapeHtml(p.citation || 'Tanpa sitasi');
                const code = p.code || '';
                let html = `<div class="v2-paper-cite">${cite}</div>`;
                if (code) {
                    html += `<a class="v2-paper-link" href="/paper/${encodeURIComponent(code)}" target="_blank">
                                <i class="fas fa-external-link-alt"></i> Buka detail paper
                             </a>`;
                }
                li.innerHTML = html;
                list.appendChild(li);
            });
            block.appendChild(list);

            block.querySelector('.v2-kw-summary').addEventListener('click', (e) => {
                if (e.target.closest('.v2-paper-link')) return;
                block.classList.toggle('expanded');
            });
        }

        scrollToBottom();
        return block;
    };

    // ===== Event queue: render satu per satu dengan jeda kecil =====
    // Walau backend kirim banyak event sekaligus dari polling (sering terjadi
    // di production karena backend cepat), queue ini memastikan tampilan
    // muncul one-by-one dengan animasi rapi.
    const _eventQueue = [];
    let _queueRunning = false;

    // Delay PER tipe event — keyword_start ditahan lebih lama biar narasi
    // "sedang mencari kata kunci X" benar-benar terbaca user. Kalau backend
    // di VPS sangat cepat dan event datang barengan, queue ini yang melebar.
    const _eventDelay = (evt) => {
        switch (evt && evt.type) {
            case 'section':         return 300;
            case 'keyword_start':   return 1000;  // searching state visible 1 detik penuh
            case 'keyword_result':  return 400;
            case 'cancelled':       return 200;
            default:                return 0;
        }
    };

    const _enqueue = (task) => {
        _eventQueue.push(task);
        if (!_queueRunning) _processQueue();
    };

    const _processQueue = async () => {
        _queueRunning = true;
        while (_eventQueue.length > 0) {
            const task = _eventQueue.shift();
            try { await task(); } catch (e) { console.error('[v2 queue]', e); }
        }
        _queueRunning = false;
    };

    const _waitQueueDrain = () => {
        return new Promise((resolve) => {
            const tick = () => {
                if (!_queueRunning && _eventQueue.length === 0) resolve();
                else setTimeout(tick, 60);
            };
            tick();
        });
    };

    const renderEvent = (aiMessageDiv, event) => {
        const results = ensureResultsContainer(aiMessageDiv);
        if (event.type === 'section') {
            renderSectionHeader(results, event.section);
        } else if (event.type === 'keyword_start') {
            renderKeywordStart(results, event);
        } else if (event.type === 'keyword_result') {
            renderKeywordBlock(results, event);
        } else if (event.type === 'cancelled') {
            const note = document.createElement('div');
            note.className = 'v2-keyword-block no-results';
            note.innerHTML = `<div class="v2-kw-summary"><div class="v2-kw-summary-text"><i class="fas fa-ban" style="color:#C62828;"></i> Pencarian dibatalkan.</div></div>`;
            results.appendChild(note);
        } else if (event.type === 'error') {
            const note = document.createElement('div');
            note.className = 'v2-keyword-block no-results';
            note.innerHTML = `<div class="v2-kw-summary"><div class="v2-kw-summary-text"><i class="fas fa-exclamation-triangle" style="color:#C62828;"></i> ${escapeHtml(event.msg || 'Terjadi kesalahan')}</div></div>`;
            results.appendChild(note);
        }
    };

    // ===== Final response handling =====
    // Render summary text setelah pencarian selesai.
    // - animate=true (default): tampilkan loader "Membuat ringkasan..." dulu,
    //   lalu typewriter teks summary-nya (seperti chat AI).
    // - animate=false: render langsung (dipakai saat restorasi halaman).
    const renderFinalNote = (aiMessageDiv, finalText, allEmpty, animate = true) => {
        if (!finalText) return;
        if (aiMessageDiv.querySelector('.v2-final-note')) return; // anti dup

        const note = document.createElement('div');
        note.className = 'v2-final-note' + (allEmpty ? ' is-empty' : '');
        aiMessageDiv.querySelector('.message-bubble')?.appendChild(note);
        _triggerEnterAnim(note);

        const renderInstant = () => {
            try {
                note.innerHTML = (typeof marked !== 'undefined')
                    ? marked.parse(finalText, { breaks: true })
                    : escapeHtml(finalText).replace(/\n/g, '<br>');
            } catch {
                note.innerHTML = escapeHtml(finalText).replace(/\n/g, '<br>');
            }
            scrollToBottom();
        };

        if (!animate) {
            renderInstant();
            return;
        }

        // Step 1: tampilkan loader dengan spinner
        note.classList.add('is-generating');
        note.innerHTML = `
            <div class="v2-summary-loading">
                <span class="v2-spinner"></span>
                <span>Membuat ringkasan</span>
                <span class="v2-summary-dots"><span></span><span></span><span></span></span>
            </div>
        `;
        scrollToBottom();

        // Step 2: setelah jeda singkat, typewriter teks asli
        setTimeout(() => {
            note.classList.remove('is-generating');
            note.innerHTML = ''; // bersihkan loader
            const typewriter = createTypewriter(note, () => scrollToBottom());
            typewriter.push(finalText);
            typewriter.end();
        }, 700);
    };

    // ===== Polling =====
    const _stopPolling = () => {
        if (pollingInterval) { clearInterval(pollingInterval); pollingInterval = null; }
    };

    const _pollProgress = (chatId, aiMessageDiv, startAfter) => {
        _stopPolling();
        const POLL_MS = 700;
        const MAX_TOTAL_MS = 5 * 60 * 1000;
        const MAX_IDLE_MS = 90 * 1000;
        const MAX_FAIL = 5;

        let lastStep = startAfter || 0;
        let fails = 0;
        const startedAt = Date.now();
        let lastProgressAt = Date.now();

        const failFast = (msg) => {
            _stopPolling();
            renderEvent(aiMessageDiv, { type: 'error', msg });
            removeCancelBar(aiMessageDiv);
            unlockInput();
        };

        pollingInterval = setInterval(async () => {
            const now = Date.now();
            if (now - startedAt > MAX_TOTAL_MS) return failFast('Pencarian terlalu lama, dihentikan.');
            if (now - lastProgressAt > MAX_IDLE_MS) return failFast('Pencarian macet, dihentikan.');

            try {
                const r = await fetch(`/search-v2/check_status/${chatId}?after=${lastStep}`);
                if (!r.ok) {
                    fails++;
                    if (fails >= MAX_FAIL) failFast('Koneksi gagal.');
                    return;
                }
                fails = 0;
                const data = await r.json();

                if (Array.isArray(data.new_events) && data.new_events.length > 0) {
                    // Enqueue tiap event sebagai task — delay per tipe event
                    data.new_events.forEach((evt) => {
                        _enqueue(async () => {
                            renderEvent(aiMessageDiv, evt);
                            const d = _eventDelay(evt);
                            if (d > 0) await new Promise((r) => setTimeout(r, d));
                        });
                    });
                    lastStep = data.latest_step_number;
                    lastProgressAt = now;
                }

                if (data.is_completed) {
                    _stopPolling();
                    // Tunggu queue habis dulu supaya keyword blocks selesai render sebelum final note
                    await _waitQueueDrain();
                    removeCancelBar(aiMessageDiv);
                    if (data.result) {
                        if (data.result.final_response) {
                            renderFinalNote(
                                aiMessageDiv,
                                data.result.final_response,
                                !!data.result.all_empty,
                            );
                        }
                        // Persist search_steps to data attribute for restoration
                        try {
                            aiMessageDiv.dataset.searchSteps = JSON.stringify({
                                summary: data.result.summary || [],
                                all_empty: !!data.result.all_empty,
                                final_response: data.result.final_response || '',
                            });
                        } catch (e) { /* ignore */ }
                    }
                    unlockInput();
                    return;
                }
                if (data.is_error) return failFast(data.error || 'Pencarian gagal.');
                if (data.is_cancelled) {
                    _stopPolling();
                    await _waitQueueDrain();
                    removeCancelBar(aiMessageDiv);
                    if (!aiMessageDiv.querySelector('.v2-search-results .v2-keyword-block.no-results .fa-ban')) {
                        renderEvent(aiMessageDiv, { type: 'cancelled' });
                    }
                    unlockInput();
                    return;
                }
            } catch (e) {
                console.error(e);
                fails++;
                if (fails >= MAX_FAIL) failFast('Koneksi gagal.');
            }
        }, POLL_MS);
    };

    const startSearchProcess = async (chatId, systemOutput, aiMessageDiv) => {
        currentChatId = chatId;
        ensureCancelBar(aiMessageDiv, chatId);
        try {
            const r = await fetch(
                `/search-v2/search_process/${chatId}?system_output=${encodeURIComponent(systemOutput)}`,
                { method: 'POST' }
            );
            if (!r.ok) {
                renderEvent(aiMessageDiv, { type: 'error', msg: 'Gagal memulai pencarian.' });
                removeCancelBar(aiMessageDiv);
                unlockInput();
                return;
            }
            const data = await r.json().catch(() => ({}));
            if (data.error) {
                renderEvent(aiMessageDiv, { type: 'error', msg: data.error });
                removeCancelBar(aiMessageDiv);
                unlockInput();
                return;
            }
            _pollProgress(chatId, aiMessageDiv, 0);
        } catch (e) {
            console.error(e);
            renderEvent(aiMessageDiv, { type: 'error', msg: 'Network error.' });
            removeCancelBar(aiMessageDiv);
            unlockInput();
        }
    };

    // ===== Send message (streaming) =====
    const handleSend = async (msg) => {
        if (isProcessing) return;
        const sessionId = getCurrentSessionId();
        lockInput();
        appendUserMessage(msg);
        showTypingIndicator();

        let aiMessageDiv = null;
        let bubbleDiv = null;
        let typewriter = null;
        let accumulated = '';
        let chatId = null;
        let needsSearch = false;
        let searchStarted = false;
        let errorMsg = null;

        const ensureStreamingBubble = () => {
            if (aiMessageDiv) return;
            removeTypingIndicator();
            const container = ensureChatDisplay();
            aiMessageDiv = document.createElement('div');
            aiMessageDiv.className = 'message is-ai is-streaming';
            bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'message-bubble';
            bubbleDiv.innerHTML = '<span class="stream-cursor"></span>';
            aiMessageDiv.appendChild(bubbleDiv);
            container.appendChild(aiMessageDiv);
            scrollToBottom();
            typewriter = createTypewriter(bubbleDiv, () => scrollToBottom());
        };

        try {
            const response = await fetch('/search-v2/chat_stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: msg,
                    session_id: sessionId,
                    filters: buildFilterPayload(),
                }),
            });

            if (!response.ok || !response.body) {
                let em = `HTTP ${response.status}`;
                try {
                    const j = await response.json();
                    if (j.error) em = j.error;
                } catch (_) {}
                throw new Error(em);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });

                let sep;
                while ((sep = buffer.indexOf('\n\n')) !== -1) {
                    const raw = buffer.slice(0, sep);
                    buffer = buffer.slice(sep + 2);
                    const dataLine = raw.split('\n').find((l) => l.startsWith('data:'));
                    if (!dataLine) continue;
                    const payload = dataLine.replace(/^data:\s*/, '').trim();
                    if (!payload) continue;

                    let evt;
                    try { evt = JSON.parse(payload); } catch { continue; }

                    if (evt.type === 'meta') {
                        if (evt.new_session) {
                            addSessionToSidebar(evt.session_id, evt.session_title);
                            try { window.history.replaceState({}, '', `/search-v2/${evt.session_id}`); } catch (_) {}
                        }
                    } else if (evt.type === 'title_update') {
                        const item = document.querySelector(`.session-item[data-session-id="${evt.session_id}"] .session-title`);
                        if (item) item.textContent = evt.title;
                    } else if (evt.type === 'chunk') {
                        ensureStreamingBubble();
                        accumulated += evt.text || '';
                        typewriter.push(evt.text || '');
                    } else if (evt.type === 'error') {
                        errorMsg = evt.message || 'Terjadi kesalahan';
                        ensureStreamingBubble();
                        const note = `\n\n_${errorMsg}_`;
                        accumulated += note;
                        typewriter.push(note);
                    } else if (evt.type === 'done') {
                        chatId = evt.chat_id;
                        needsSearch = !!evt.needs_search;
                        searchStarted = !!evt.search_started;
                    }
                }
            }

            if (typewriter) await typewriter.end();
            removeTypingIndicator();

            // Finalize bubble: render markdown bersih, tambah copy button + dataset chat_id
            if (aiMessageDiv) {
                aiMessageDiv.classList.remove('is-streaming');
                if (chatId) aiMessageDiv.dataset.chatId = chatId;
                try {
                    bubbleDiv.innerHTML = (typeof marked !== 'undefined')
                        ? marked.parse(accumulated || '', { breaks: true })
                        : (accumulated || '').replace(/\n/g, '<br>');
                } catch {
                    bubbleDiv.innerHTML = (accumulated || '').replace(/\n/g, '<br>');
                }
                const copyBtn = document.createElement('button');
                copyBtn.className = 'copy-btn';
                copyBtn.title = 'Copy text';
                copyBtn.innerHTML = '<i class="far fa-copy"></i><i class="fas fa-check"></i>';
                aiMessageDiv.appendChild(copyBtn);
            } else if (accumulated) {
                aiMessageDiv = appendAiMessage(accumulated, chatId);
            }

            if (needsSearch && chatId && aiMessageDiv) {
                currentChatId = chatId;
                ensureCancelBar(aiMessageDiv, chatId);
                _pollProgress(chatId, aiMessageDiv, 0);
            } else {
                unlockInput();
            }
        } catch (e) {
            console.error('[V2 stream] error:', e);
            if (typewriter) typewriter.flushNow();
            removeTypingIndicator();
            if (aiMessageDiv) {
                aiMessageDiv.classList.remove('is-streaming');
                bubbleDiv.innerHTML = `<strong>Error:</strong> ${escapeHtml(e.message || 'Terjadi kesalahan.')}`;
            } else {
                appendAiMessage(`**Error:** ${e.message || 'Terjadi kesalahan.'}`, null);
            }
            unlockInput();
        }
    };

    // ===== Restore on page load =====
    const restorePersistedResults = () => {
        document.querySelectorAll('.message.is-ai[data-search-steps]').forEach((aiDiv) => {
            try {
                const raw = aiDiv.dataset.searchSteps;
                if (!raw) return;
                const parsed = JSON.parse(raw);
                const summary = parsed.summary || [];
                if (!Array.isArray(summary) || summary.length === 0) return;

                // Reset any pre-existing results (defensive)
                aiDiv.querySelector('.v2-search-results')?.remove();

                let lastSection = null;
                summary.forEach((entry) => {
                    if (entry.kw_type !== lastSection) {
                        renderEvent(aiDiv, { type: 'section', section: entry.kw_type });
                        lastSection = entry.kw_type;
                    }
                    renderEvent(aiDiv, {
                        type: 'keyword_result',
                        keyword: entry.keyword,
                        kw_type: entry.kw_type,
                        count: entry.count,
                        results: entry.results || [],
                    });
                });

                if (parsed.final_response) {
                    // Restorasi (reload page) — render langsung, tidak perlu animasi
                    renderFinalNote(aiDiv, parsed.final_response, !!parsed.all_empty, false);
                }
            } catch (e) {
                console.warn('[V2] restore failed:', e);
            }
        });
    };

    const checkProcessingOnLoad = async () => {
        const aiMessages = document.querySelectorAll('.message.is-ai[data-chat-id]');
        if (aiMessages.length === 0) return;
        const last = aiMessages[aiMessages.length - 1];
        const chatId = last.dataset.chatId;
        if (!chatId) return;

        try {
            const r = await fetch(`/search-v2/check_status/${chatId}?after=0`);
            if (!r.ok) return;
            const data = await r.json();
            if (data.is_processing) {
                lockInput();
                ensureCancelBar(last, chatId);
                // Replay any new_events received so far
                if (Array.isArray(data.new_events)) {
                    data.new_events.forEach((evt) => renderEvent(last, evt));
                }
                _pollProgress(chatId, last, data.latest_step_number || 0);
            }
        } catch (e) {
            console.error('[V2] checkProcessingOnLoad error:', e);
        }
    };

    restorePersistedResults();
    checkProcessingOnLoad();

    // ===== Event listeners =====
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const msg = messageInput.value.trim();
            if (!msg || isProcessing) return;
            handleSend(msg);
            messageInput.value = '';
            setInputHeight();
            toggleSendButton();
        });
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
        messageInput.addEventListener('input', () => { setInputHeight(); toggleSendButton(); });
    }

    if (newChatBtn) newChatBtn.addEventListener('click', () => window.location.href = '/search-v2');
    const newChatBtnMin = document.getElementById('new-chat-btn-minimized');
    if (newChatBtnMin) newChatBtnMin.addEventListener('click', () => window.location.href = '/search-v2');

    // Suggestion cards
    document.querySelectorAll('.suggestion-card').forEach((card) => {
        card.addEventListener('click', () => {
            const prompt = card.dataset.prompt;
            if (prompt && !isProcessing) handleSend(prompt);
        });
    });

    // Copy buttons
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.copy-btn');
        if (!btn) return;
        const bubble = btn.closest('.message')?.querySelector('.message-bubble');
        if (!bubble) return;
        const text = bubble.innerText || bubble.textContent || '';
        navigator.clipboard?.writeText(text).then(() => {
            btn.classList.add('copied');
            setTimeout(() => btn.classList.remove('copied'), 1500);
        }).catch(() => {});
    });

    // Session list dropdowns / modals
    if (sessionList) {
        sessionList.addEventListener('click', (e) => {
            const menuBtn = e.target.closest('.session-menu-btn');
            if (menuBtn) {
                e.preventDefault(); e.stopPropagation();
                const dropdown = menuBtn.closest('.session-item').querySelector('.session-menu-dropdown');
                if (activeDropdown && activeDropdown !== dropdown) activeDropdown.classList.remove('active');
                dropdown.classList.toggle('active');
                activeDropdown = dropdown.classList.contains('active') ? dropdown : null;
            }
            const renBtn = e.target.closest('.rename-session-btn');
            if (renBtn) {
                e.preventDefault(); e.stopPropagation();
                const item = renBtn.closest('.session-item');
                sessionToRenameId = item.dataset.sessionId;
                renameInput.value = item.querySelector('.session-title').textContent;
                showModal(renameModalOverlay);
                if (activeDropdown) { activeDropdown.classList.remove('active'); activeDropdown = null; }
            }
            const delBtn = e.target.closest('.delete-session-btn');
            if (delBtn) {
                e.preventDefault(); e.stopPropagation();
                sessionToDeleteId = delBtn.closest('.session-item').dataset.sessionId;
                showModal(deleteModalOverlay);
                if (activeDropdown) { activeDropdown.classList.remove('active'); activeDropdown = null; }
            }
        });
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.session-item') && activeDropdown) {
                activeDropdown.classList.remove('active'); activeDropdown = null;
            }
        });
    }

    if (cancelDeleteBtn) cancelDeleteBtn.addEventListener('click', () => hideModal(deleteModalOverlay));
    if (deleteModalOverlay) deleteModalOverlay.addEventListener('click', (e) => {
        if (e.target === deleteModalOverlay) hideModal(deleteModalOverlay);
    });
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', async () => {
            if (!sessionToDeleteId) return;
            confirmDeleteBtn.disabled = true;
            try {
                const r = await fetch(`/search-v2/delete_session/${sessionToDeleteId}`, { method: 'POST' });
                const d = await r.json();
                if (d.success) {
                    if (sessionToDeleteId === getCurrentSessionId()) {
                        window.location.href = '/search-v2';
                    } else {
                        document.querySelector(`.session-item[data-session-id="${sessionToDeleteId}"]`)?.remove();
                        hideModal(deleteModalOverlay);
                    }
                } else { alert(d.error || 'Delete failed'); }
            } catch (e) { alert('Error deleting'); }
            finally { confirmDeleteBtn.disabled = false; }
        });
    }

    if (cancelRenameBtn) cancelRenameBtn.addEventListener('click', () => hideModal(renameModalOverlay));
    if (renameModalOverlay) renameModalOverlay.addEventListener('click', (e) => {
        if (e.target === renameModalOverlay) hideModal(renameModalOverlay);
    });
    if (confirmRenameBtn) {
        confirmRenameBtn.addEventListener('click', async () => {
            if (!sessionToRenameId) return;
            const t = renameInput.value.trim();
            if (!t) return;
            confirmRenameBtn.disabled = true;
            try {
                const r = await fetch(`/search-v2/rename_session/${sessionToRenameId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: t }),
                });
                const d = await r.json();
                if (d.success) {
                    const el = document.querySelector(`.session-item[data-session-id="${sessionToRenameId}"] .session-title`);
                    if (el) el.textContent = t;
                    hideModal(renameModalOverlay);
                } else { alert(d.error || 'Rename failed'); }
            } catch { alert('Error renaming'); }
            finally { confirmRenameBtn.disabled = false; }
        });
    }
});
