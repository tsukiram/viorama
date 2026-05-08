// /app/static/js/general.js - COMPLETE FILE

document.addEventListener('DOMContentLoaded', () => {
    console.log('[INIT] Page loaded - Starting general.js');
    
    // === Selektor Elemen DOM ===
    const chatSidebar = document.getElementById('chat-sidebar');
    const minimizeBtn = document.getElementById('minimize-sidebar-btn');
    const maximizeBtn = document.getElementById('maximize-sidebar-btn');
    const chatLayout = document.querySelector('.chat-layout');
    let chatDisplay = document.getElementById('chat-display');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const newChatBtn = document.getElementById('new-chat-btn');
    const newChatBtnMinimized = document.getElementById('new-chat-btn-minimized');
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
    
    // Debug: Check if modal elements exist
    console.log('[MODAL DEBUG] Delete Modal:', deleteModalOverlay);
    console.log('[MODAL DEBUG] Rename Modal:', renameModalOverlay);
    console.log('[MODAL DEBUG] Confirm Delete Btn:', confirmDeleteBtn);
    console.log('[MODAL DEBUG] Confirm Rename Btn:', confirmRenameBtn);
    
    let sessionToDeleteId = null;
    let sessionToRenameId = null;
    let activeDropdown = null;
    let isProcessingMessage = false;

    // === FUNGSI HELPER UNTUK MODAL ===
    const showModal = (modalElement) => {
        console.log('[MODAL] Showing modal:', modalElement);
        if (modalElement) {
            modalElement.classList.remove('hidden');
            modalElement.classList.add('visible');
            document.body.style.overflow = 'hidden';
            console.log('[MODAL] Modal classes after show:', modalElement.className);
        } else {
            console.error('[MODAL] Modal element is null!');
        }
    };

    const hideModal = (modalElement) => {
        console.log('[MODAL] Hiding modal:', modalElement);
        if (modalElement) {
            modalElement.classList.remove('visible');
            modalElement.classList.add('hidden');
            document.body.style.overflow = '';
            console.log('[MODAL] Modal classes after hide:', modalElement.className);
        }
    };

    // === Logika Toggle Sidebar ===
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
            // Event khusus HANYA untuk tombol minimize/panah
            if (minimizeBtn && !minimizeBtn.dataset.mobileListenerAdded) {
                minimizeBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('[Mobile] Toggle button clicked');
                    chatSidebar.classList.toggle('expanded');
                });
                minimizeBtn.dataset.mobileListenerAdded = 'true';
                console.log('[Mobile] Event listener added to minimize button');
            }
            
            // Tutup sidebar saat klik di luar
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


    // === Fungsi Bantuan untuk Interaksi UI ===
    const scrollToBottom = () => {
        const display = document.getElementById('chat-display');
        if (display) {
            display.scrollTop = display.scrollHeight;
        }
    };

    const setInputHeight = () => {
        if (!messageInput) return;
        messageInput.style.height = 'auto';
        messageInput.style.height = `${messageInput.scrollHeight}px`;
    };

    const toggleSendButton = () => {
        if (sendButton) {
            sendButton.disabled = messageInput.value.trim() === '' || isProcessingMessage;
        }
    }; 

    const showTypingIndicator = () => {
        const display = document.getElementById('chat-display');
        if (!display) return;
        
        const indicatorDiv = document.createElement('div');
        indicatorDiv.id = 'typing-indicator';
        indicatorDiv.className = 'message is-ai typing-indicator';

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        bubbleDiv.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';

        indicatorDiv.appendChild(bubbleDiv);
        display.appendChild(indicatorDiv);
        scrollToBottom();
    };

    const removeTypingIndicator = () => {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    };

    const ensureChatContainer = () => {
        const welcomeScreen = document.querySelector('.welcome-banner');
        const suggestions = document.querySelector('.suggestion-cards-grid');
        if (welcomeScreen) welcomeScreen.remove();
        if (suggestions) suggestions.remove();

        let container = document.getElementById('chat-display');
        if (!container) {
            const mainContent = document.querySelector('.chat-main');
            const placeholder = mainContent.querySelector('.chat-container-placeholder');
            if (placeholder) placeholder.remove();

            const activeContainer = document.createElement('div');
            activeContainer.className = 'chat-container-active neo-card';

            container = document.createElement('div');
            container.id = 'chat-display';
            container.className = 'chat-display';

            activeContainer.appendChild(container);
            mainContent.insertBefore(activeContainer, mainContent.querySelector('.chat-input-area'));
        }
        return container;
    };

    const appendMessage = (content, type) => {
        const container = ensureChatContainer();

        const messageDiv = document.createElement('div');
        messageDiv.className = `message is-${type}`;

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';

        if (type === 'ai') {
            bubbleDiv.innerHTML = marked.parse(content);
        } else {
            const textNode = document.createTextNode(content);
            bubbleDiv.appendChild(textNode);
        }

        messageDiv.appendChild(bubbleDiv);

        if (type === 'ai') {
            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-btn';
            copyBtn.title = 'Copy text';
            copyBtn.innerHTML = '<i class="far fa-copy"></i><i class="fas fa-check"></i>';
            messageDiv.appendChild(copyBtn);
        }

        container.appendChild(messageDiv);
        scrollToBottom();
        return messageDiv;
    };

    const createStreamingAiMessage = () => {
        const container = ensureChatContainer();

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message is-ai is-streaming';

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        bubbleDiv.innerHTML = '<span class="stream-cursor"></span>';

        messageDiv.appendChild(bubbleDiv);
        container.appendChild(messageDiv);
        scrollToBottom();
        return { messageDiv, bubbleDiv };
    };

    const finalizeStreamingMessage = (messageDiv, bubbleDiv, fullText) => {
        messageDiv.classList.remove('is-streaming');
        bubbleDiv.innerHTML = marked.parse(fullText || '');

        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.title = 'Copy text';
        copyBtn.innerHTML = '<i class="far fa-copy"></i><i class="fas fa-check"></i>';
        messageDiv.appendChild(copyBtn);
    };

    const addSessionToSidebar = (sessionId, title) => {
        if (!sessionList) return;

        const emptyHistory = sessionList.querySelector('.empty-history');
        if (emptyHistory) emptyHistory.remove();

        sessionList.querySelectorAll('.session-item.active').forEach((el) => el.classList.remove('active'));

        const li = document.createElement('li');
        li.className = 'session-item active';
        li.dataset.sessionId = sessionId;
        li.innerHTML = `
            <a href="/general/${sessionId}" class="session-link">
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
            </div>
        `;
        li.querySelector('.session-title').textContent = title || 'New Chat';
        sessionList.insertBefore(li, sessionList.firstChild);
    };

    // Typewriter: server-side chunks bisa besar (puluhan kata sekaligus).
    // Kita buffer di client lalu render karakter demi karakter dengan kecepatan stabil.
    const createTypewriter = (bubbleDiv, onUpdate) => {
        let pending = '';      // teks yang belum ditampilkan
        let displayed = '';    // teks yang sudah ditampilkan
        let streamEnded = false;
        let rafId = null;
        let lastTick = 0;
        let resolveDone = null;
        const donePromise = new Promise((res) => { resolveDone = res; });

        // Kecepatan: ~120 char/detik saat normal, dipercepat kalau buffer besar
        const baseCharsPerSec = 120;

        const tick = (ts) => {
            if (!lastTick) lastTick = ts;
            const dt = ts - lastTick;
            lastTick = ts;

            // Adaptive: kalau buffer menumpuk (mis. > 200 char), naikkan speed
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
                bubbleDiv.innerHTML =
                    marked.parse(displayed) +
                    (streamEnded && pending.length === 0
                        ? ''
                        : '<span class="stream-cursor"></span>');
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
                // Tampilkan sisa langsung tanpa delay
                if (pending.length > 0) {
                    displayed += pending;
                    pending = '';
                    bubbleDiv.innerHTML = marked.parse(displayed);
                }
                streamEnded = true;
                if (rafId) cancelAnimationFrame(rafId);
                rafId = null;
                if (resolveDone) resolveDone(displayed);
                return displayed;
            },
            getDisplayed() { return displayed; },
        };
    };

    const handleSendMessage = async (message) => {
        if (isProcessingMessage) {
            console.log('[handleSendMessage] Already processing, ignoring...');
            return;
        }

        isProcessingMessage = true;
        toggleSendButton();

        const currentSessionId = getCurrentSessionId();
        appendMessage(message, 'user');
        showTypingIndicator();

        let streaming = null;
        let typewriter = null;
        let accumulated = '';
        let activeSessionId = currentSessionId;

        const ensureStreamingBubble = () => {
            if (!streaming) {
                removeTypingIndicator();
                streaming = createStreamingAiMessage();
                typewriter = createTypewriter(streaming.bubbleDiv, () => scrollToBottom());
            }
        };

        try {
            const response = await fetch('/general/chat_stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    session_id: currentSessionId
                })
            });

            if (!response.ok || !response.body) {
                let errMsg = `HTTP ${response.status}`;
                try {
                    const errJson = await response.json();
                    if (errJson.error) errMsg = errJson.error;
                } catch (_) {}
                throw new Error(errMsg);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                let sepIdx;
                while ((sepIdx = buffer.indexOf('\n\n')) !== -1) {
                    const rawEvent = buffer.slice(0, sepIdx);
                    buffer = buffer.slice(sepIdx + 2);

                    const dataLine = rawEvent.split('\n').find((l) => l.startsWith('data:'));
                    if (!dataLine) continue;

                    const payload = dataLine.replace(/^data:\s*/, '').trim();
                    if (!payload) continue;

                    let evt;
                    try {
                        evt = JSON.parse(payload);
                    } catch (e) {
                        console.warn('[stream] non-JSON payload:', payload);
                        continue;
                    }

                    if (evt.type === 'meta') {
                        activeSessionId = evt.session_id;
                        if (evt.new_session) {
                            addSessionToSidebar(evt.session_id, evt.session_title);
                            try {
                                window.history.replaceState({}, '', `/general/${evt.session_id}`);
                            } catch (_) {}
                        }
                    } else if (evt.type === 'chunk') {
                        ensureStreamingBubble();
                        accumulated += evt.text || '';
                        typewriter.push(evt.text || '');
                    } else if (evt.type === 'error') {
                        ensureStreamingBubble();
                        const msg = `\n\n_${evt.message || 'Terjadi kesalahan saat streaming.'}_`;
                        accumulated += msg;
                        typewriter.push(msg);
                    } else if (evt.type === 'done') {
                        // handled after loop
                    }
                }
            }

            // Tunggu typewriter habis menyelesaikan buffer
            if (typewriter) {
                await typewriter.end();
            }

            removeTypingIndicator();
            if (streaming) {
                finalizeStreamingMessage(streaming.messageDiv, streaming.bubbleDiv, accumulated);
            } else if (accumulated) {
                appendMessage(accumulated, 'ai');
            }
        } catch (error) {
            console.error('[handleSendMessage] stream error:', error);
            if (typewriter) typewriter.flushNow();
            removeTypingIndicator();
            if (streaming) {
                finalizeStreamingMessage(
                    streaming.messageDiv,
                    streaming.bubbleDiv,
                    accumulated + `\n\n**Error:** ${error.message || 'Terjadi kesalahan.'}`
                );
            } else {
                appendMessage(`**Error:** ${error.message || 'Terjadi kesalahan.'}`, 'ai');
            }
        } finally {
            isProcessingMessage = false;
            toggleSendButton();
        }
    };

    // === Three-dot Menu Logic ===
    const closeAllDropdowns = () => {
        document.querySelectorAll('.session-menu-dropdown').forEach(dropdown => {
            dropdown.classList.remove('active');
        });
        activeDropdown = null;
    };

    if (sessionList) {
        sessionList.addEventListener('click', (e) => {
            console.log('[SESSION LIST] Click detected:', e.target);
            
            const menuBtn = e.target.closest('.session-menu-btn');
            if (menuBtn) {
                e.preventDefault();
                e.stopPropagation();
                console.log('[SESSION LIST] Menu button clicked');
                
                const sessionItem = menuBtn.closest('.session-item');
                const dropdown = sessionItem.querySelector('.session-menu-dropdown');
                
                if (activeDropdown && activeDropdown !== dropdown) {
                    activeDropdown.classList.remove('active');
                }
                
                dropdown.classList.toggle('active');
                activeDropdown = dropdown.classList.contains('active') ? dropdown : null;
                console.log('[SESSION LIST] Dropdown active:', activeDropdown !== null);
                return;
            }
            
            const renameBtn = e.target.closest('.rename-session-btn');
            if (renameBtn) {
                e.preventDefault();
                e.stopPropagation();
                console.log('[SESSION LIST] Rename button clicked');
                
                const sessionItem = renameBtn.closest('.session-item');
                sessionToRenameId = sessionItem.dataset.sessionId;
                const currentTitle = sessionItem.querySelector('.session-title').textContent;
                
                console.log('[SESSION LIST] Session to rename:', sessionToRenameId);
                console.log('[SESSION LIST] Current title:', currentTitle);
                
                renameInput.value = currentTitle;
                showModal(renameModalOverlay);
                closeAllDropdowns();
                
                setTimeout(() => {
                    if (renameInput) {
                        renameInput.focus();
                        renameInput.select();
                    }
                }, 100);
                return;
            }
            
            const deleteBtn = e.target.closest('.delete-session-btn');
            if (deleteBtn) {
                e.preventDefault();
                e.stopPropagation();
                console.log('[SESSION LIST] Delete button clicked');
                
                sessionToDeleteId = deleteBtn.closest('.session-item').dataset.sessionId;
                console.log('[SESSION LIST] Session to delete:', sessionToDeleteId);
                
                showModal(deleteModalOverlay);
                closeAllDropdowns();
                return;
            }
        });
    }

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.session-item')) {
            closeAllDropdowns();
        }
    });

    // === Modal Logic - Delete ===
    const closeDeleteModal = () => {
        console.log('[DELETE MODAL] Closing');
        hideModal(deleteModalOverlay);
        sessionToDeleteId = null;
    };

    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener('click', (e) => {
            e.preventDefault();
            console.log('[DELETE MODAL] Cancel clicked');
            closeDeleteModal();
        });
    }

    if (deleteModalOverlay) {
        deleteModalOverlay.addEventListener('click', (e) => {
            if (e.target === deleteModalOverlay) {
                console.log('[DELETE MODAL] Overlay clicked');
                closeDeleteModal();
            }
        });
    }

    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', async () => {
            console.log('[DELETE MODAL] Confirm clicked');
            if (!sessionToDeleteId) return;
            
            confirmDeleteBtn.disabled = true;
            confirmDeleteBtn.textContent = 'Deleting...';
            
            try {
                const response = await fetch(`/general/delete_session/${sessionToDeleteId}`, {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (data.success) {
                    const currentSessionId = getCurrentSessionId();
                    if (sessionToDeleteId === currentSessionId) {
                        window.location.href = '/general';
                    } else {
                        const itemToRemove = document.querySelector(`.session-item[data-session-id="${sessionToDeleteId}"]`);
                        if (itemToRemove) {
                            itemToRemove.remove();
                        }
                        closeDeleteModal();
                    }
                } else {
                    alert(`Error: ${data.error}`);
                    closeDeleteModal();
                }
            } catch (error) {
                console.error('Delete error:', error);
                alert("An error occurred while deleting the session.");
                closeDeleteModal();
            } finally {
                confirmDeleteBtn.disabled = false;
                confirmDeleteBtn.textContent = 'Delete';
            }
        });
    }

    // === Modal Logic - Rename ===
    const closeRenameModal = () => {
        console.log('[RENAME MODAL] Closing');
        hideModal(renameModalOverlay);
        sessionToRenameId = null;
        if (renameInput) renameInput.value = '';
    };

    if (cancelRenameBtn) {
        cancelRenameBtn.addEventListener('click', (e) => {
            e.preventDefault();
            console.log('[RENAME MODAL] Cancel clicked');
            closeRenameModal();
        });
    }

    if (renameModalOverlay) {
        renameModalOverlay.addEventListener('click', (e) => {
            if (e.target === renameModalOverlay) {
                console.log('[RENAME MODAL] Overlay clicked');
                closeRenameModal();
            }
        });
    }

    if (renameInput) {
        renameInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (confirmRenameBtn) confirmRenameBtn.click();
            }
        });
    }

    if (confirmRenameBtn) {
        confirmRenameBtn.addEventListener('click', async () => {
            console.log('[RENAME MODAL] Confirm clicked');
            if (!sessionToRenameId) return;
            
            const newTitle = renameInput.value.trim();
            if (!newTitle) {
                alert('Title cannot be empty');
                renameInput.focus();
                return;
            }
            
            confirmRenameBtn.disabled = true;
            confirmRenameBtn.textContent = 'Renaming...';
            
            try {
                const response = await fetch(`/general/rename_session/${sessionToRenameId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: newTitle })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const sessionItem = document.querySelector(`.session-item[data-session-id="${sessionToRenameId}"]`);
                    if (sessionItem) {
                        const titleElement = sessionItem.querySelector('.session-title');
                        if (titleElement) {
                            titleElement.textContent = data.new_title;
                        }
                    }
                    closeRenameModal();
                } else {
                    alert(`Error: ${data.error}`);
                }
            } catch (error) {
                console.error('Rename error:', error);
                alert("An error occurred while renaming the session.");
            } finally {
                confirmRenameBtn.disabled = false;
                confirmRenameBtn.textContent = 'Rename';
            }
        });
    }

    // Escape key untuk close modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (deleteModalOverlay && !deleteModalOverlay.classList.contains('hidden')) {
                closeDeleteModal();
            }
            if (renameModalOverlay && !renameModalOverlay.classList.contains('hidden')) {
                closeRenameModal();
            }
        }
    });

    // === Event Listeners ===
    if (messageInput) {
        messageInput.addEventListener('input', () => {
            setInputHeight();
            toggleSendButton();
        });
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!isProcessingMessage) {
                    chatForm.requestSubmit();
                }
            }
        });
    }

    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (isProcessingMessage) {
                console.log('[chatForm] Already processing, ignoring submit');
                return;
            }
            
            const message = messageInput.value.trim();
            if (!message) return;
            
            messageInput.value = '';
            setInputHeight();
            toggleSendButton();
            
            await handleSendMessage(message);
        });
    }

    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => {
            window.location.href = '/general';
        });
    }

    if (newChatBtnMinimized) {
        newChatBtnMinimized.addEventListener('click', () => {
            window.location.href = '/general';
        });
    }

    document.body.addEventListener('click', async (e) => {
        const suggestionCard = e.target.closest('.suggestion-card');
        if (suggestionCard && !isProcessingMessage) {
            const prompt = suggestionCard.dataset.prompt;
            messageInput.value = prompt;
            toggleSendButton();
            await handleSendMessage(prompt);
            messageInput.value = '';
            toggleSendButton();
        }
    });

    document.body.addEventListener('click', (e) => {
        const copyBtn = e.target.closest('.copy-btn');
        if (copyBtn) {
            const messageBubble = copyBtn.previousElementSibling;
            if (messageBubble) {
                const textToCopy = messageBubble.innerText;
                navigator.clipboard.writeText(textToCopy).then(() => {
                    copyBtn.classList.add('copied');
                    setTimeout(() => {
                        copyBtn.classList.remove('copied');
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy text: ', err);
                });
            }
        }
    });

    // === Inisialisasi ===
    const aiAvatar = document.querySelector('.ai-avatar');
    if (aiAvatar) {
        document.body.dataset.botAvatarUrl = aiAvatar.src;
    }
    scrollToBottom();
    toggleSendButton();
    if (messageInput) messageInput.focus();
    
    console.log('[INIT] general.js initialization complete');
});