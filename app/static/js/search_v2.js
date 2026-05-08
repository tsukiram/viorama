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

    // ===== Render helpers =====
    const ensureChatDisplay = () => {
        let container = document.getElementById('chat-display');
        if (container && container.style.display !== 'none') return container;

        // First message — promote welcome → active
        const welcomeBanner = document.querySelector('.welcome-banner');
        const suggestionsGrid = document.querySelector('.suggestion-cards-grid');
        if (welcomeBanner) welcomeBanner.remove();
        if (suggestionsGrid) suggestionsGrid.remove();

        if (!container) {
            const main = document.querySelector('.chat-main');
            const placeholder = main?.querySelector('.chat-container-placeholder');
            if (placeholder) placeholder.remove();
            const active = document.createElement('div');
            active.className = 'chat-container-active neo-card';
            container = document.createElement('div');
            container.id = 'chat-display';
            container.className = 'chat-display';
            active.appendChild(container);
            const inputAreaEl = main?.querySelector('.chat-input-area');
            if (inputAreaEl) main.insertBefore(active, inputAreaEl);
            else if (main) main.appendChild(active);
        }
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
        let bar = aiMessageDiv.querySelector('.v2-cancel-bar');
        if (bar) return bar;
        bar = document.createElement('div');
        bar.className = 'v2-cancel-bar';
        bar.style.cssText = 'display:flex;justify-content:flex-end;margin-top:6px;';
        bar.innerHTML = `
            <button class="v2-cancel-btn" type="button">
                <i class="fas fa-times"></i> Cancel
            </button>`;
        aiMessageDiv.querySelector('.message-bubble')?.appendChild(bar);
        const btn = bar.querySelector('.v2-cancel-btn');
        btn.addEventListener('click', async () => {
            if (!chatId) return;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cancelling...';
            try {
                await fetch(`/search-v2/cancel_search/${chatId}`, { method: 'POST' });
            } catch (e) { console.error(e); }
        });
        return bar;
    };

    const removeCancelBar = (aiMessageDiv) => {
        aiMessageDiv?.querySelector('.v2-cancel-bar')?.remove();
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

    const renderKeywordBlock = (resultsContainer, kr) => {
        const { keyword, kw_type, count, results } = kr;
        const block = document.createElement('div');
        block.className = 'v2-keyword-block' + (kw_type === 'tambahan' ? ' is-tambahan' : '');
        block.classList.add(count > 0 ? 'has-results' : 'no-results');
        block.dataset.keyword = keyword;

        const summary = document.createElement('div');
        summary.className = 'v2-kw-summary';

        const text = document.createElement('div');
        text.className = 'v2-kw-summary-text';
        if (count > 0) {
            text.innerHTML = `Saya menemukan <strong>${count} paper</strong> dengan kata kunci <span class="kw-quote">${escapeHtml(keyword)}</span>`;
        } else {
            text.innerHTML = `Saya menemukan <strong>0 paper</strong> dengan kata kunci <span class="kw-quote">${escapeHtml(keyword)}</span>`;
        }
        summary.appendChild(text);

        if (count > 0) {
            const toggle = document.createElement('button');
            toggle.className = 'v2-kw-toggle';
            toggle.type = 'button';
            toggle.innerHTML = `lihat detail <i class="fas fa-chevron-down chevron"></i>`;
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

            // Toggle handler
            block.querySelector('.v2-kw-summary').addEventListener('click', (e) => {
                if (e.target.closest('.v2-paper-link')) return;
                block.classList.toggle('expanded');
            });
        }

        resultsContainer.appendChild(block);
        scrollToBottom();
        return block;
    };

    const renderEvent = (aiMessageDiv, event) => {
        const results = ensureResultsContainer(aiMessageDiv);
        if (event.type === 'section') {
            renderSectionHeader(results, event.section);
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

    // ===== Final response handling (e.g. all_empty fallback) =====
    const renderFinalNote = (aiMessageDiv, finalText, allEmpty) => {
        if (!finalText || !allEmpty) return;
        // Append fallback message as a separate bubble below results.
        const note = document.createElement('div');
        note.className = 'v2-final-note';
        note.style.cssText = 'margin-top:10px;padding:10px 12px;background:#FFF8E1;border-radius:8px;border-left:3px solid #FBC02D;color:#5D4037;';
        try {
            note.innerHTML = (typeof marked !== 'undefined')
                ? marked.parse(finalText, { breaks: true })
                : escapeHtml(finalText).replace(/\n/g, '<br>');
        } catch {
            note.innerHTML = escapeHtml(finalText).replace(/\n/g, '<br>');
        }
        aiMessageDiv.querySelector('.message-bubble')?.appendChild(note);
        scrollToBottom();
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
                    data.new_events.forEach((evt) => renderEvent(aiMessageDiv, evt));
                    lastStep = data.latest_step_number;
                    lastProgressAt = now;
                }

                if (data.is_completed) {
                    _stopPolling();
                    removeCancelBar(aiMessageDiv);
                    if (data.result) {
                        if (data.result.all_empty && data.result.final_response) {
                            renderFinalNote(aiMessageDiv, data.result.final_response, true);
                        }
                        // Persist search_steps to data attribute for restoration
                        try {
                            aiMessageDiv.dataset.searchSteps = JSON.stringify({
                                summary: data.result.summary || [],
                                all_empty: !!data.result.all_empty,
                            });
                        } catch (e) { /* ignore */ }
                    }
                    unlockInput();
                    return;
                }
                if (data.is_error) return failFast(data.error || 'Pencarian gagal.');
                if (data.is_cancelled) {
                    _stopPolling();
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

    // ===== Send message =====
    const handleSend = async (msg) => {
        if (isProcessing) return;
        const sessionId = getCurrentSessionId();
        lockInput();
        appendUserMessage(msg);
        const loadingBubble = appendLoadingBubble('Memproses pesan...');

        try {
            const r = await fetch('/search-v2/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg, session_id: sessionId }),
            });
            const data = await r.json();

            loadingBubble?.remove();

            if (data.error) {
                appendAiMessage(`**Error:** ${data.error}`, null);
                unlockInput();
                return;
            }

            if (data.new_session_id && data.new_session_id !== 'null') {
                // Show "redirecting" then go to session URL
                const redir = document.createElement('div');
                redir.className = 'message is-ai';
                redir.innerHTML = `<div class="message-bubble"><i class="fas fa-check-circle" style="color:#66BB6A;"></i> Sesi siap, mengalihkan...</div>`;
                document.getElementById('chat-display')?.appendChild(redir);
                window.location.replace(`/search-v2/${data.new_session_id}`);
                return;
            }

            const aiDiv = appendAiMessage(data.initial_response || '', data.chat_id);

            if (data.needs_search && data.chat_id) {
                if (data.search_started) {
                    // Backend already kicked off the search — just attach UI and poll.
                    currentChatId = data.chat_id;
                    ensureCancelBar(aiDiv, data.chat_id);
                    _pollProgress(data.chat_id, aiDiv, 0);
                } else if (data.system_output) {
                    // Fallback: explicitly start search via dedicated endpoint.
                    await startSearchProcess(data.chat_id, data.system_output, aiDiv);
                } else {
                    unlockInput();
                }
            } else {
                unlockInput();
            }
        } catch (e) {
            console.error(e);
            loadingBubble?.remove();
            appendAiMessage('Error mengirim pesan. Silakan refresh halaman.', null);
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

                if (parsed.all_empty && parsed.final_response) {
                    renderFinalNote(aiDiv, parsed.final_response, true);
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
