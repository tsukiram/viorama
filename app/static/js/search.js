
document.addEventListener('DOMContentLoaded', () => {
    console.log('[INIT] Page loaded - Starting search.js');

    // === Selektor Elemen DOM ===
    const chatSidebar = document.getElementById('chat-sidebar');
    const minimizeBtn = document.getElementById('minimize-sidebar-btn');
    const maximizeBtn = document.getElementById('maximize-sidebar-btn');
    let chatDisplay = document.getElementById('chat-display');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const newChatBtn = document.getElementById('new-chat-btn');
    const sessionList = document.getElementById('session-list');

    // Modal Elements - Delete
    const deleteModalOverlay = document.getElementById('delete-modal-overlay');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    const cancelDeleteBtn = document.getElementById('cancel-delete-btn');

    // Modal Elements - Rename
    const renameModalOverlay = document.getElementById('rename-modal-overlay');
    const confirmRenameBtn = document.getElementById('confirm-rename-btn');
    const cancelRenameBtn = document.getElementById('cancel-rename-btn');
    const renameInput = document.getElementById('rename-input');

    // Modal Elements - Steps
    const stepsModalOverlay = document.getElementById('steps-modal-overlay');
    const closeStepsBtn = document.getElementById('close-steps-btn');
    const stepsContent = document.getElementById('steps-content');

    let sessionToDeleteId = null;
    let sessionToRenameId = null;
    let activeDropdown = null;
    let isProcessingMessage = false;
    let currentProcessingChatId = null;
    let pollingInterval = null;

    // === FUNGSI HELPER UNTUK MODAL ===
    const showModal = (modalElement) => {
        if (modalElement) {
            modalElement.classList.add('visible');
            document.body.style.overflow = 'hidden';
        }
    };

    const hideModal = (modalElement) => {
        if (modalElement) {
            modalElement.classList.remove('visible');
            document.body.style.overflow = '';
        }
    };

    // === Extract chat IDs from DOM ===
    const getChatIdsFromDOM = () => {
        const chatIds = [];
        const aiMessages = document.querySelectorAll('.message.is-ai[data-chat-id]');
        aiMessages.forEach(msg => {
            const chatId = msg.dataset.chatId;
            if (chatId) chatIds.push(parseInt(chatId));
        });
        return chatIds;
    };

    // === Logika Toggle Sidebar (Desktop) ===
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

    // === Helper untuk Mendapatkan ID Sesi Saat Ini ===
    const getCurrentSessionId = () => {
        const activeItem = sessionList?.querySelector('.session-item.active');
        return activeItem ? activeItem.dataset.sessionId : null;
    };

    // === Mobile sidebar toggle handler ===
    const handleMobileSidebarToggle = () => {
        if (window.innerWidth <= 991.98) {
            if (minimizeBtn && !minimizeBtn.dataset.mobileListenerAdded) {
                minimizeBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    chatSidebar.classList.toggle('expanded');
                });
                minimizeBtn.dataset.mobileListenerAdded = 'true';
            }
            const outsideClickListener = (e) => {
                if (window.innerWidth <= 991.98) {
                    if (!e.target.closest('.chat-sidebar') && chatSidebar.classList.contains('expanded')) {
                        chatSidebar.classList.remove('expanded');
                    }
                }
            };
            if (!document.body.dataset.outsideClickAdded) {
                document.addEventListener('click', outsideClickListener);
                document.body.dataset.outsideClickAdded = 'true';
            }
        }
    };
    if (chatSidebar) {
        handleMobileSidebarToggle();
        window.addEventListener('resize', handleMobileSidebarToggle);
    }

    // === UI Helpers ===
    const scrollToBottom = () => {
        const display = document.getElementById('chat-display');
        if (display) display.scrollTop = display.scrollHeight;
    };

    const setInputHeight = () => {
        if (!messageInput) return;
        messageInput.style.height = 'auto';
        messageInput.style.height = `${messageInput.scrollHeight}px`;
    };

    const toggleSendButton = () => {
        if (sendButton && messageInput) {
            sendButton.disabled = messageInput.value.trim() === '' || isProcessingMessage;
        }
    };

    const showTypingIndicator = () => {
        const display = document.getElementById('chat-display');
        if (!display) return;
        const indicatorDiv = document.createElement('div');
        indicatorDiv.id = 'typing-indicator';
        indicatorDiv.className = 'message is-ai typing-indicator';
        indicatorDiv.innerHTML = '<div class="message-bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>';
        display.appendChild(indicatorDiv);
        scrollToBottom();
    };

    const removeTypingIndicator = () => {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) indicator.remove();
    };

    // === NEW: Search Progress Logic (Structured) ===
    const showSearchProgressContainer = () => {
        const display = document.getElementById('chat-display');
        if (!display) return;
        removeTypingIndicator();
        const progressDiv = document.createElement('div');
        progressDiv.id = 'search-progress-container';
        progressDiv.className = 'message is-ai';
        progressDiv.innerHTML = `
            <div class="message-bubble">
                <div class="search-process-wrapper">
                    <div class="search-process-header">
                        <span><i class="fas fa-search"></i> <strong>Search Process</strong></span>
                        <button id="cancel-search-btn" class="cancel-search-btn" title="Cancel search">
                            <i class="fas fa-times"></i> Cancel
                        </button>
                    </div>
                    <div id="search-progress-content" class="search-process-content">
                        <div class="search-step active"><i class="fas fa-spinner fa-spin"></i> <span>Initializing search...</span></div>
                    </div>
                </div>
            </div>`;
        display.appendChild(progressDiv);
        scrollToBottom();

        const cancelBtn = document.getElementById('cancel-search-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', async () => {
                if (!currentProcessingChatId) return;
                cancelBtn.disabled = true;
                cancelBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cancelling...';
                try {
                    await fetch(`/search/cancel_search/${currentProcessingChatId}`, { method: 'POST' });
                    updateSearchProgress({ msg: "Cancelling search...", status: "warning" });
                } catch (e) { console.error(e); }
            });
        }
    };

    const getStepIcon = (status) => {
        if (status === 'processing') return '<i class="fas fa-spinner fa-spin"></i>';
        if (status === 'completed') return '<i class="fas fa-check-circle" style="color: #66BB6A;"></i>';
        if (status === 'warning') return '<i class="fas fa-exclamation-circle" style="color: #FFA726;"></i>';
        if (status === 'error') return '<i class="fas fa-times-circle" style="color: #EF5350;"></i>';
        return '<i class="fas fa-circle-notch"></i>';
    };

    const updateSearchProgress = (updateData) => {
        const progressContent = document.getElementById('search-progress-content');
        if (!progressContent) return;

        if (typeof updateData === 'string') updateData = { msg: updateData, status: 'processing' };
        const msg = updateData.msg || updateData.message || "Processing...";
        const status = updateData.status || 'processing';

        // Find currently active step and mark as completed IF new step is processing
        const activeStep = progressContent.querySelector('.search-step.active');
        if (activeStep) {
            activeStep.classList.remove('active');
            const spinner = activeStep.querySelector('.fa-spinner');
            if (spinner) {
                // If it was a spinner, change to checkmark
                spinner.className = 'fas fa-check-circle';
                spinner.style.color = '#66BB6A';
            }
        }

        const stepDiv = document.createElement('div');
        stepDiv.className = `search-step ${status === 'processing' ? 'active' : ''}`;
        stepDiv.innerHTML = `${getStepIcon(status)} <span>${msg}</span>`;
        progressContent.appendChild(stepDiv);
        scrollToBottom();
    };


    const completeSearchProgress = () => {
        const progressContent = document.getElementById('search-progress-content');
        if (!progressContent) return;

        progressContent.querySelectorAll('.search-step').forEach(step => {
            step.classList.remove('active');
            const spinner = step.querySelector('.fa-spinner');
            if (spinner) {
                spinner.className = 'fas fa-check-circle';
                spinner.style.color = '#66BB6A';
            }
        });

        const completionDiv = document.createElement('div');
        completionDiv.className = 'search-step';
        completionDiv.innerHTML = `<i class="fas fa-check-circle" style="color: #66BB6A;"></i> <span><strong>Search completed successfully!</strong></span>`;
        progressContent.appendChild(completionDiv);
        scrollToBottom();
    };

    const removeSearchProgressContainer = () => {
        const container = document.getElementById('search-progress-container');
        if (container) {
            container.style.opacity = '0';
            setTimeout(() => container.remove(), 300);
        }
    };

    const restoreAndPollSearchProgress = async (chatId) => {
        try {
            const resp = await fetch(`/search/check_search_status/${chatId}?after=0`);
            const data = await resp.json();

            if (data.is_completed || !data.is_processing) return;

            showSearchProgressContainer();
            const content = document.getElementById('search-progress-content');
            const existingSteps = data.new_steps || [];

            if (content && existingSteps.length > 0) {
                content.innerHTML = '';
                existingSteps.forEach(step => {
                    const div = document.createElement('div');
                    div.className = `search-step ${step.status === 'processing' ? 'active' : ''}`;
                    div.innerHTML = `${getStepIcon(step.status)} <span>${step.msg}</span>`;
                    content.appendChild(div);
                });
            }

            isProcessingMessage = true; toggleSendButton();
            _pollForProgress(chatId, data.latest_step_number || 0);
        } catch (e) { console.error(e); }
    };

    // === Append Message ===
    const appendMessage = (content, type, searchSteps = null) => {
        // Explicitly remove welcome elements on first chat
        const welcomeBanner = document.querySelector('.welcome-banner');
        const suggestionsGrid = document.querySelector('.suggestion-cards-grid');
        if (welcomeBanner) welcomeBanner.remove();
        if (suggestionsGrid) suggestionsGrid.remove();

        let container = document.getElementById('chat-display');
        if (!container) {
            // Dynamically create container if missing (first chat on welcome page)
            const mainContent = document.querySelector('.chat-main');
            const placeholder = mainContent?.querySelector('.chat-container-placeholder');
            if (placeholder) placeholder.remove();

            const activeContainer = document.createElement('div');
            activeContainer.className = 'chat-container-active neo-card';

            container = document.createElement('div');
            container.id = 'chat-display';
            container.className = 'chat-display';

            activeContainer.appendChild(container);

            const inputArea = mainContent?.querySelector('.chat-input-area');
            if (inputArea) {
                mainContent.insertBefore(activeContainer, inputArea);
            } else if (mainContent) {
                mainContent.appendChild(activeContainer);
            }
        }

        // Ensure container is visible
        container.style.display = 'flex';

        const msgDiv = document.createElement('div');
        msgDiv.className = `message is-${type}`;
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        if (type === 'ai') {
            try {
                if (typeof marked !== 'undefined') bubble.innerHTML = marked.parse(content, { breaks: true });
                else bubble.innerHTML = content.replace(/\n/g, '<br>');
            } catch (e) { bubble.innerHTML = content.replace(/\n/g, '<br>'); }
        } else {
            bubble.textContent = content;
        }
        msgDiv.appendChild(bubble);

        if (type === 'ai') {
            // Copy Button
            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-btn';
            copyBtn.innerHTML = '<i class="far fa-copy"></i>';
            msgDiv.appendChild(copyBtn);

            if (searchSteps && searchSteps.length > 0) {
                const stepsBtn = document.createElement('button');
                stepsBtn.className = 'show-steps-btn';
                stepsBtn.title = 'Show search process';
                stepsBtn.innerHTML = '<i class="fas fa-list-ul"></i>';
                stepsBtn.dataset.steps = JSON.stringify(searchSteps);
                msgDiv.appendChild(stepsBtn);
            }
        }
        container.appendChild(msgDiv);
        scrollToBottom();
    };

    // === Handle Send Message ===
    const handleSendMessage = async (message) => {
        if (isProcessingMessage) return;
        isProcessingMessage = true; toggleSendButton();

        const sessionId = getCurrentSessionId();

        // UX: Disable input and show loading state strictly
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');

        if (messageInput) messageInput.disabled = true;
        if (sendButton) {
            sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            sendButton.disabled = true;
        }

        appendMessage(message, 'user');

        // Add temporary loading bubble
        const loadingId = 'loading-' + Date.now();
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message is-ai';
        loadingDiv.id = loadingId;
        loadingDiv.innerHTML = `<div class="message-bubble"><i class="fas fa-spinner fa-spin"></i> Creating search session...</div>`;

        const chatDisplayContainer = document.getElementById('chat-display');
        if (chatDisplayContainer) {
            chatDisplayContainer.style.display = 'flex'; // Ensure visible
            chatDisplayContainer.appendChild(loadingDiv);
        }
        scrollToBottom();

        // showTypingIndicator(); // Replaced by bubble above

        try {
            const resp = await fetch('/search/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, session_id: sessionId })
            });
            const data = await resp.json();

            // Remove loading bubble
            const loadingBubble = document.getElementById(loadingId);
            if (loadingBubble) loadingBubble.remove();

            removeTypingIndicator();

            if (data.error) {
                appendMessage(`<strong>Error:</strong> ${data.error}`, 'ai');
                isProcessingMessage = false;
                toggleSendButton();
                // Restore input state on error
                if (messageInput) { messageInput.disabled = false; messageInput.focus(); }
                if (sendButton) sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
            } else if (data.new_session_id && data.new_session_id !== 'null') {
                console.log('[handleSendMessage] New session created, redirecting to:', data.new_session_id);

                // UX: Show redirecting message and keep disabled
                const redirectDiv = document.createElement('div');
                redirectDiv.className = 'message is-ai';
                redirectDiv.innerHTML = `<div class="message-bubble"><i class="fas fa-check-circle" style="color: green;"></i> Session ready! Redirecting...</div>`;
                const chatDisplayContainer2 = document.getElementById('chat-display');
                if (chatDisplayContainer2) chatDisplayContainer2.appendChild(redirectDiv);

                // Use replace to avoid back-button loop
                window.location.replace(`/search/${data.new_session_id}`);
                return;
            } else {
                appendMessage(data.initial_response, 'ai', data.search_steps);

                // Restore input state if staying on same page
                if (messageInput) { messageInput.disabled = false; messageInput.focus(); }
                if (sendButton) sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';

                if (data.needs_search && data.system_output && data.chat_id) {
                    currentProcessingChatId = data.chat_id;
                    showSearchProgressContainer();
                    startSearchProcess(data.chat_id, data.system_output);
                } else {
                    isProcessingMessage = false; toggleSendButton();
                }
            }
        } catch (e) {
            removeTypingIndicator();
            const loadingBubble = document.getElementById(loadingId);
            if (loadingBubble) loadingBubble.remove();

            appendMessage("Error sending message. Please refresh.", 'ai');
            isProcessingMessage = false; toggleSendButton();
            // Restore input state on error
            if (messageInput) { messageInput.disabled = false; messageInput.focus(); }
            if (sendButton) sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
        }
    };

    // === Shared polling logic (used by both startSearchProcess and restoreAndPollSearchProgress) ===
    const _pollForProgress = (chatId, startAfter) => {
        if (pollingInterval) { clearInterval(pollingInterval); pollingInterval = null; }

        const POLL_INTERVAL_MS = 600;
        const MAX_TOTAL_MS = 5 * 60 * 1000;
        const MAX_IDLE_MS = 90 * 1000;
        const MAX_POLL_FAILURES = 5;

        let lastStepNumber = startAfter;
        let pollFailures = 0;
        const startedAt = Date.now();
        let lastProgressAt = Date.now();

        const failFast = (msg) => {
            if (pollingInterval) { clearInterval(pollingInterval); pollingInterval = null; }
            updateSearchProgress({ msg, status: "error" });
            setTimeout(() => {
                removeSearchProgressContainer(); isProcessingMessage = false; toggleSendButton();
            }, 2000);
        };

        pollingInterval = setInterval(async () => {
            const now = Date.now();
            if (now - startedAt > MAX_TOTAL_MS) { failFast("Search took too long and was aborted."); return; }
            if (now - lastProgressAt > MAX_IDLE_MS) { failFast("Search appears stuck. Please try again."); return; }

            try {
                const resp = await fetch(`/search/check_search_status/${chatId}?after=${lastStepNumber}`);
                if (!resp.ok) {
                    pollFailures++;
                    if (pollFailures >= MAX_POLL_FAILURES) failFast("Connection failed.");
                    return;
                }
                pollFailures = 0;
                const data = await resp.json();

                if (data.new_steps && data.new_steps.length > 0) {
                    data.new_steps.forEach(s => updateSearchProgress({ msg: s.msg, status: s.status }));
                    lastStepNumber = data.latest_step_number;
                    lastProgressAt = now;
                }

                if (data.status === 'complete' && data.result) {
                    clearInterval(pollingInterval); pollingInterval = null;
                    completeSearchProgress();
                    setTimeout(() => {
                        removeSearchProgressContainer();
                        if (data.result.enhanced_response) {
                            appendMessage(data.result.enhanced_response, 'ai', data.result.search_updates);
                        }
                        isProcessingMessage = false; toggleSendButton();
                    }, 1500);
                    return;
                }
                if (data.status === 'error' || data.is_error) {
                    failFast(data.error || "Search failed.");
                    return;
                }
                if (data.status === 'cancelled' || data.is_cancelled) {
                    if (data.result && data.result.enhanced_response) {
                        // Thread finished generating cancelled response.
                        if (pollingInterval) { clearInterval(pollingInterval); pollingInterval = null; }
                        updateSearchProgress({ msg: "Search cancelled.", status: "warning" });
                        setTimeout(() => {
                            removeSearchProgressContainer();
                            appendMessage(data.result.enhanced_response, 'ai', data.result.search_updates);
                            isProcessingMessage = false; toggleSendButton();
                        }, 1500);
                        return;
                    }
                    // Thread hasn't finished processing cancellation yet — keep polling.
                    return;
                }
            } catch (e) {
                console.error(e);
                pollFailures++;
                if (pollFailures >= MAX_POLL_FAILURES) failFast("Connection failed.");
            }
        }, POLL_INTERVAL_MS);
    };

    // === Start Search Process ===
    const startSearchProcess = async (chatId, systemOutput) => {
        if (pollingInterval) { clearInterval(pollingInterval); pollingInterval = null; }
        currentProcessingChatId = chatId;

        const failFast = (msg) => {
            updateSearchProgress({ msg, status: "error" });
            setTimeout(() => {
                removeSearchProgressContainer(); isProcessingMessage = false; toggleSendButton();
            }, 2000);
        };

        try {
            const startResp = await fetch(
                `/search/search_process/${chatId}?system_output=${encodeURIComponent(systemOutput)}`,
                { method: 'POST' }
            );
            if (!startResp.ok) { failFast("Failed to start search."); return; }
            const startData = await startResp.json().catch(() => ({}));
            if (startData.error) { failFast(startData.error); return; }
        } catch (e) {
            failFast("Network error while starting search.");
            return;
        }

        _pollForProgress(chatId, 0);
    };

    // === Check Restore on Load ===
    const checkAndRestoreOnLoad = async () => {
        const ids = getChatIdsFromDOM();
        if (ids.length === 0) return;
        await restoreAndPollSearchProgress(ids[ids.length - 1]);
        if (pollingInterval) { isProcessingMessage = true; toggleSendButton(); }
    };
    checkAndRestoreOnLoad();

    // === Event Listeners ===
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const msg = messageInput.value.trim();
            if (msg) {
                handleSendMessage(msg);
                messageInput.value = '';
                setInputHeight();
            }
        });
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); chatForm.dispatchEvent(new Event('submit')); }
        });
        messageInput.addEventListener('input', () => { setInputHeight(); toggleSendButton(); });
    }
    if (newChatBtn) newChatBtn.addEventListener('click', () => window.location.href = '/search');

    // === Modals Logic (Delete & Rename) ===
    if (cancelDeleteBtn) cancelDeleteBtn.addEventListener('click', () => hideModal(deleteModalOverlay));
    if (deleteModalOverlay) deleteModalOverlay.addEventListener('click', (e) => { if (e.target === deleteModalOverlay) hideModal(deleteModalOverlay); });
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', async () => {
            if (!sessionToDeleteId) return;
            try {
                confirmDeleteBtn.disabled = true;
                const r = await fetch(`/search/delete_session/${sessionToDeleteId}`, { method: 'POST' });
                const d = await r.json();
                if (d.success) {
                    if (sessionToDeleteId === getCurrentSessionId()) window.location.href = '/search';
                    else { document.querySelector(`.session-item[data-session-id="${sessionToDeleteId}"]`)?.remove(); hideModal(deleteModalOverlay); }
                } else alert(d.error);
            } catch (e) { alert('Error deleting session'); }
            finally { confirmDeleteBtn.disabled = false; }
        });
    }

    if (cancelRenameBtn) cancelRenameBtn.addEventListener('click', () => hideModal(renameModalOverlay));
    if (renameModalOverlay) renameModalOverlay.addEventListener('click', (e) => { if (e.target === renameModalOverlay) hideModal(renameModalOverlay); });
    if (confirmRenameBtn) {
        confirmRenameBtn.addEventListener('click', async () => {
            if (!sessionToRenameId) return;
            try {
                const newTitle = renameInput.value.trim();
                if (!newTitle) return;
                confirmRenameBtn.disabled = true;
                const r = await fetch(`/search/rename_session/${sessionToRenameId}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: newTitle }) });
                const d = await r.json();
                if (d.success) {
                    const el = document.querySelector(`.session-item[data-session-id="${sessionToRenameId}"] .session-title`);
                    if (el) el.textContent = newTitle;
                    hideModal(renameModalOverlay);
                } else alert(d.error);
            } catch (e) { alert('Error renaming'); }
            finally { confirmRenameBtn.disabled = false; }
        });
    }

    // === Steps Modal Logic ===
    if (closeStepsBtn) closeStepsBtn.addEventListener('click', () => hideModal(stepsModalOverlay));
    if (stepsModalOverlay) stepsModalOverlay.addEventListener('click', (e) => { if (e.target === stepsModalOverlay) hideModal(stepsModalOverlay); });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.show-steps-btn');
        if (btn && stepsContent && stepsModalOverlay) {
            const raw = btn.dataset.steps || '[]';
            let steps = [];
            try {
                const parsed = JSON.parse(raw);
                if (Array.isArray(parsed)) steps = parsed;
                else if (parsed && Array.isArray(parsed.steps)) steps = parsed.steps;
            } catch (e) { steps = []; }
            stepsContent.innerHTML = '';
            steps.forEach(step => {
                let msg = step, status = 'completed';
                if (typeof step === 'object') { msg = step.msg || step.message; status = step.status || 'completed'; }
                const div = document.createElement('div');
                div.className = 'search-step';
                div.innerHTML = `${getStepIcon(status)} <span>${msg}</span>`;
                stepsContent.appendChild(div);
            });
            showModal(stepsModalOverlay);
        }
    });


    // Suggestion Cards Logic
    const suggestionCards = document.querySelectorAll('.suggestion-card');
    if (suggestionCards) {
        suggestionCards.forEach(card => {
            card.addEventListener('click', () => {
                const prompt = card.dataset.prompt;
                if (prompt) {
                    handleSendMessage(prompt);
                }
            });
        });
    }

    // Session List Dropdowns
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
        document.addEventListener('click', (e) => { if (!e.target.closest('.session-item') && activeDropdown) { activeDropdown.classList.remove('active'); activeDropdown = null; } });
    }
});
