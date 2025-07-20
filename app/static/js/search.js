// app\static\js\search.js - Fixed version to resolve blur issue
document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatContainer = document.getElementById('chat-container');
    const modal = document.getElementById('search-steps-modal');
    const closeModalButton = document.getElementById('close-modal');
    const stepsContent = document.getElementById('search-steps-content');
    const newSessionButton = document.getElementById('new-session-button');
    const deleteSessionButtons = document.getElementsByClassName('delete-session-button');
    
    const currentSessionId = window.location.pathname.split('/').pop() || null;

    // FIXED: Ensure modal is properly hidden on page load
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('visible');
        modal.style.display = 'none';
    }

    // FIXED: Remove any lingering backdrop-filter effects
    function clearBlurEffects() {
        document.body.style.overflow = '';
        document.body.style.filter = '';
        document.documentElement.style.filter = '';
        
        // Remove any modal overlays
        const allModals = document.querySelectorAll('.modal');
        allModals.forEach(m => {
            m.classList.add('hidden');
            m.classList.remove('visible');
            m.style.display = 'none';
        });
    }

    // Call on page load to ensure clean state
    clearBlurEffects();

    // Function to convert URLs in text to clickable links
    function convertUrlsToLinks(text) {
        const urlRegex = /(https?:\/\/[^\s<>"]+)/gi;
        return text.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">$1</a>');
    }

    // Function to make links clickable in dynamically added content
    function makeLinksClickable(container) {
        const paperLinks = container.querySelectorAll('a[href^="/paper/"]');
        paperLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const href = link.getAttribute('href');
                window.open(href, '_blank');
            });
        });

        const httpLinks = container.querySelectorAll('a[href^="http"]');
        httpLinks.forEach(link => {
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.classList.add('text-blue-600', 'hover:underline');
        });

        const walker = document.createTreeWalker(
            container,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );

        const textNodes = [];
        let node;
        while (node = walker.nextNode()) {
            if (!node.parentElement.closest('a')) {
                textNodes.push(node);
            }
        }

        textNodes.forEach(textNode => {
            const text = textNode.textContent;
            const urlRegex = /(https?:\/\/[^\s<>"]+)/gi;
            if (urlRegex.test(text)) {
                const newHTML = convertUrlsToLinks(text);
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = newHTML;
                
                const fragment = document.createDocumentFragment();
                while (tempDiv.firstChild) {
                    fragment.appendChild(tempDiv.firstChild);
                }
                textNode.parentNode.replaceChild(fragment, textNode);
            }
        });
    }

    // Function to parse and create HTML from response
    function createHTMLFromResponse(response) {
        if (!response) {
            console.error('Response is empty or null');
            return '<div class="text-red-700">Error: No response received</div>';
        }
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = response;
        makeLinksClickable(tempDiv);
        return tempDiv.innerHTML;
    }

    // Function to format timestamp consistently
    function formatTimestamp(date = new Date()) {
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        }).replace(/(\d+)\/(\d+)\/(\d+),\s*(.*)/, '$3-$1-$2 $4');
    }

    // Function to create user message with consistent design
    function createUserMessage(message, timestamp = new Date()) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message user';
        messageDiv.innerHTML = `
            <div class="message-bubble user">
                <p class="message-timestamp">${formatTimestamp(timestamp)}</p>
                <p class="message-sender">You:</p>
                <div class="message-content">${convertUrlsToLinks(message)}</div>
            </div>
        `;
        return messageDiv;
    }

    // Function to create bot message with consistent design
    function createBotMessage(response, timestamp = new Date(), showSteps = false, searchSteps = []) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message bot';
        
        let stepsButton = '';
        if (showSteps && searchSteps.length > 0) {
            stepsButton = `<button class="show-steps-button" data-steps='${JSON.stringify(searchSteps)}'>Show Search Process</button>`;
        }
        
        messageDiv.innerHTML = `
            <div class="message-bubble bot">
                <p class="message-timestamp">${formatTimestamp(timestamp)}</p>
                <p class="message-sender">Viorama:</p>
                <div class="message-content">${createHTMLFromResponse(response)}</div>
                ${stepsButton}
            </div>
        `;
        return messageDiv;
    }

    // Function to create search progress container with consistent design
    function createSearchProgressContainer(timestamp = new Date()) {
        const progressDiv = document.createElement('div');
        progressDiv.className = 'chat-message bot';
        progressDiv.id = 'search-progress-container';
        progressDiv.innerHTML = `
            <div class="message-bubble bot">
                <p class="message-timestamp">${formatTimestamp(timestamp)}</p>
                <p class="message-sender">Viorama:</p>
                <div class="message-content">
                    <div class="search-process-container">
                        <div class="search-process-header">
                            <strong>🔍 Search Process:</strong>
                        </div>
                        <div id="search-progress-content" class="search-process-content">
                            <div class="search-step animate-pulse">🚀 Initializing search...</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        chatContainer.appendChild(progressDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return progressDiv;
    }

    // Function to update search progress
    function updateSearchProgress(update) {
        const progressContent = document.getElementById('search-progress-content');
        if (progressContent) {
            const updateDiv = document.createElement('div');
            updateDiv.className = 'search-step';
            updateDiv.innerHTML = `📋 ${update}`;
            progressContent.appendChild(updateDiv);
            
            const initialPulse = progressContent.querySelector('.animate-pulse');
            if (initialPulse) initialPulse.remove();
            
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }

    // Function to show typing indicator with consistent design
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-message bot';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="message-bubble bot">
                <p class="message-timestamp">${formatTimestamp()}</p>
                <p class="message-sender">Viorama:</p>
                <div class="message-content">
                    <div class="typing-indicator-content">
                        <div class="typing-dots">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                        <span class="typing-text">Thinking...</span>
                    </div>
                </div>
            </div>
        `;
        chatContainer.appendChild(typingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Function to remove typing indicator
    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    // Make existing links clickable on page load
    makeLinksClickable(document);

    // FIXED: Improved modal handling
    function showModal(content) {
        if (!modal) return;
        
        // Clear any existing blur effects first
        clearBlurEffects();
        
        // Set content
        if (stepsContent && content) {
            stepsContent.innerHTML = content;
            makeLinksClickable(stepsContent);
        }
        
        // Show modal with proper styling
        modal.style.display = 'flex';
        modal.classList.remove('hidden');
        modal.classList.add('visible');
        
        // Prevent body scroll only when modal is open
        document.body.style.overflow = 'hidden';
    }

    function hideModal() {
        if (!modal) return;
        
        modal.classList.add('hidden');
        modal.classList.remove('visible');
        modal.style.display = 'none';
        
        // Restore body scroll and clear any blur effects
        clearBlurEffects();
    }

    // FIXED: Session management with blur fix
    newSessionButton.addEventListener('click', async () => {
        // Clear blur effects before prompt
        clearBlurEffects();
        
        const title = prompt('Enter a title for the new session:', 'New Search Session');
        if (!title) return;

        try {
            const response = await fetch('/search/new_session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title })
            });
            const data = await response.json();

            if (data.session_id) {
                window.location.href = `/search/${data.session_id}`;
            } else {
                alert(data.error || 'Failed to create new session');
            }
        } catch (error) {
            alert('Error creating new session');
        }
    });

    Array.from(deleteSessionButtons).forEach(button => {
        button.addEventListener('click', async () => {
            // Clear blur effects before confirm
            clearBlurEffects();
            
            const sessionId = button.dataset.sessionId;
            if (confirm('Are you sure you want to delete this session?')) {
                try {
                    const response = await fetch(`/search/delete_session/${sessionId}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const data = await response.json();

                    if (data.message) {
                        window.location.href = '/search';
                    } else {
                        alert(data.error || 'Failed to delete session');
                    }
                } catch (error) {
                    alert('Error deleting session');
                }
            }
        });
    });

    // FIXED: Main search functionality with blur prevention
    sendButton.addEventListener('click', async () => {
        const message = messageInput.value.trim();
        if (!message || !currentSessionId) return;

        // FIXED: Clear any blur effects before starting search
        clearBlurEffects();

        // Disable input during processing
        messageInput.disabled = true;
        sendButton.disabled = true;
        sendButton.textContent = 'Processing...';

        // Add user message with consistent design
        const userMessageDiv = createUserMessage(message);
        chatContainer.appendChild(userMessageDiv);
        makeLinksClickable(userMessageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        try {
            // Get initial response
            showTypingIndicator();
            const response = await fetch(`/search/chat/${currentSessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            const data = await response.json();
            removeTypingIndicator();

            if (!response.ok) {
                throw new Error(data.error || 'Server error');
            }

            // Add initial response with consistent design
            const initialResponseDiv = createBotMessage(
                data.initial_response, 
                new Date(data.timestamp)
            );
            chatContainer.appendChild(initialResponseDiv);
            makeLinksClickable(initialResponseDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;

            // If search is needed, show search progress with SSE
            if (data.needs_search && data.system_output) {
                createSearchProgressContainer();
                
                const sseUrl = `/search/search_process/${data.chat_id}?system_output=${encodeURIComponent(data.system_output)}`;
                console.log('Initiating SSE request (GET):', sseUrl);
                
                const source = new EventSource(sseUrl);
                
                source.onmessage = (event) => {
                    try {
                        const searchData = JSON.parse(event.data);
                        console.log('SSE data received:', searchData);
                        
                        if (searchData.update) {
                            updateSearchProgress(searchData.update);
                        }
                        
                        if (searchData.complete) {
                            source.close();
                            const progressContainer = document.getElementById('search-progress-container');
                            if (progressContainer) {
                                progressContainer.remove();
                            }
                            
                            const finalResponseDiv = createBotMessage(
                                searchData.enhanced_response || 'No enhanced response received.',
                                new Date(searchData.timestamp),
                                true,
                                searchData.search_updates || []
                            );
                            chatContainer.appendChild(finalResponseDiv);
                            makeLinksClickable(finalResponseDiv);
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                    } catch (parseError) {
                        console.error('Error parsing SSE data:', parseError);
                        updateSearchProgress(`Error processing search updates: ${parseError.message}`);
                    }
                };
                
                source.onerror = () => {
                    console.error('SSE connection error');
                    source.close();
                    updateSearchProgress('❌ Search failed: Connection error');
                    
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'chat-message bot';
                    errorDiv.innerHTML = `
                        <div class="message-bubble bot error">
                            <p class="message-timestamp">${formatTimestamp()}</p>
                            <p class="message-sender">System:</p>
                            <div class="message-content">
                                <div class="error-content">
                                    ❌ Failed to complete search. Please try again.
                                </div>
                            </div>
                        </div>
                    `;
                    chatContainer.appendChild(errorDiv);
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                };
            }

        } catch (error) {
            removeTypingIndicator();
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'chat-message bot';
            errorDiv.innerHTML = `
                <div class="message-bubble bot error">
                    <p class="message-timestamp">${formatTimestamp()}</p>
                    <p class="message-sender">System:</p>
                    <div class="message-content">
                        <div class="error-content">
                            ❌ ${error.message}
                        </div>
                    </div>
                </div>
            `;
            chatContainer.appendChild(errorDiv);
            console.error('Fetch error:', error);
        } finally {
            // FIXED: Always clear blur effects when search completes
            setTimeout(() => {
                clearBlurEffects();
            }, 100);
        }

        // Re-enable input
        messageInput.value = '';
        messageInput.disabled = false;
        sendButton.disabled = false;
        sendButton.textContent = 'Search';
        messageInput.focus();
    });

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            // Clear blur effects before search
            clearBlurEffects();
            sendButton.click();
        }
    });

    // FIXED: Modal event handling
    chatContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('show-steps-button')) {
            try {
                const steps = JSON.parse(e.target.dataset.steps);
                const formattedSteps = steps.map((step, index) => 
                    `<div class="search-step-modal">
                        <span class="step-number">${index + 1}.</span>
                        <span class="step-content">${convertUrlsToLinks(step)}</span>
                    </div>`
                ).join('');
                
                const content = `
                    <div class="search-steps-list">
                        <h4 class="steps-title">🔍 Search Process Steps:</h4>
                        ${formattedSteps}
                    </div>
                `;
                
                showModal(content);
            } catch (error) {
                console.error('Error parsing search steps:', error);
                showModal(`
                    <div class="error-content">
                        ❌ Error loading search steps
                    </div>
                `);
            }
        }
    });

    if (closeModalButton) {
        closeModalButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            hideModal();
        });
    }

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                hideModal();
            }
        });
    }

    // FIXED: Escape key handler with blur prevention
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hideModal();
            clearBlurEffects();
        }
    });

    // FIXED: Window focus/blur handlers to prevent stuck blur effects
    window.addEventListener('focus', () => {
        clearBlurEffects();
    });

    window.addEventListener('beforeunload', () => {
        clearBlurEffects();
    });

    // FIXED: Periodic cleanup to prevent stuck blur effects
    setInterval(() => {
        if (!modal || !modal.classList.contains('visible')) {
            clearBlurEffects();
        }
    }, 5000);
});