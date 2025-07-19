// app\static\js\search.js
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

    // Function to convert URLs in text to clickable links
    function convertUrlsToLinks(text) {
        // Regular expression to match URLs
        const urlRegex = /(https?:\/\/[^\s<>"]+)/gi;
        return text.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">$1</a>');
    }

    // Function to make links clickable in dynamically added content
    function makeLinksClickable(container) {
        // Handle existing /paper/ links
        const paperLinks = container.querySelectorAll('a[href^="/paper/"]');
        paperLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const href = link.getAttribute('href');
                window.open(href, '_blank');
            });
        });

        // Handle HTTP/HTTPS links
        const httpLinks = container.querySelectorAll('a[href^="http"]');
        httpLinks.forEach(link => {
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.classList.add('text-blue-600', 'hover:underline');
        });

        // Convert plain text URLs to clickable links in text nodes
        const walker = document.createTreeWalker(
            container,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );

        const textNodes = [];
        let node;
        while (node = walker.nextNode()) {
            // Skip text nodes that are already inside links
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
                
                // Replace the text node with the new HTML
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

    // Function to create search progress container
    function createSearchProgressContainer() {
        const progressDiv = document.createElement('div');
        progressDiv.className = 'mb-4 flex justify-start';
        progressDiv.id = 'search-progress-container';
        progressDiv.innerHTML = `
            <div class="max-w-[75%] bg-gray-50 border border-gray-200 rounded-lg p-4 shadow-sm">
                <p class="text-xs text-gray-500 mb-2">${new Date().toLocaleString()}</p>
                <p class="text-sm font-semibold text-blue-600 mb-2">Search Process:</p>
                <div id="search-progress-content" class="text-gray-700 text-sm font-mono">
                    <div class="animate-pulse">Initializing search...</div>
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
            updateDiv.className = 'mb-1';
            updateDiv.textContent = update;
            progressContent.appendChild(updateDiv);
            const initialPulse = progressContent.querySelector('.animate-pulse');
            if (initialPulse) initialPulse.remove();
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }

    // Function to show typing indicator
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'mb-4 flex justify-start';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="max-w-[75%] bg-gray-100 rounded-lg p-4 shadow-sm">
                <div class="flex items-center space-x-2">
                    <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    <span class="text-sm text-gray-600">Viorama is thinking...</span>
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

    newSessionButton.addEventListener('click', async () => {
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

    sendButton.addEventListener('click', async () => {
        const message = messageInput.value.trim();
        if (!message || !currentSessionId) return;

        // Disable input during processing
        messageInput.disabled = true;
        sendButton.disabled = true;
        sendButton.textContent = 'Processing...';

        // Add user message
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'mb-4 flex justify-end';
        userMessageDiv.id = `message-${Date.now()}`;
        userMessageDiv.innerHTML = `
            <div class="max-w-[75%] bg-blue-100 rounded-lg p-4 shadow-sm">
                <p class="text-xs text-gray-500 mb-2">${new Date().toLocaleString()}</p>
                <p class="text-sm font-semibold text-blue-600 mb-1">You:</p>
                <div class="markdown-content text-gray-800 text-sm">${convertUrlsToLinks(message)}</div>
            </div>
        `;
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

            // Add initial response
            const initialResponseDiv = document.createElement('div');
            initialResponseDiv.className = 'mb-4 flex justify-start';
            initialResponseDiv.id = `initial-response-${data.chat_id}`;
            initialResponseDiv.innerHTML = `
                <div class="max-w-[75%] bg-gray-100 rounded-lg p-4 shadow-sm">
                    <p class="text-xs text-gray-500 mb-2">${data.timestamp}</p>
                    <p class="text-sm font-semibold text-blue-600 mb-1">Viorama:</p>
                    <div class="markdown-content text-gray-800 text-sm">${createHTMLFromResponse(data.initial_response)}</div>
                </div>
            `;
            chatContainer.appendChild(initialResponseDiv);
            makeLinksClickable(initialResponseDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;

            // If search is needed, show search progress with SSE
            if (data.needs_search && data.system_output) {
                createSearchProgressContainer();
                
                // Log the SSE URL for debugging
                const sseUrl = `/search/search_process/${data.chat_id}?system_output=${encodeURIComponent(data.system_output)}`;
                console.log('Initiating SSE request (GET):', sseUrl);
                
                // Use EventSource for real-time updates
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
                            
                            // Display enhanced response or fallback
                            const finalResponseDiv = document.createElement('div');
                            finalResponseDiv.className = 'mb-4 flex justify-start';
                            finalResponseDiv.id = `enhanced-response-${data.chat_id}`;
                            finalResponseDiv.innerHTML = `
                                <div class="max-w-[75%] bg-gray-100 rounded-lg p-4 shadow-sm">
                                    <p class="text-xs text-gray-500 mb-2">${searchData.timestamp}</p>
                                    <p class="text-sm font-semibold text-blue-600 mb-1">Viorama (Search Result):</p>
                                    <div class="markdown-content text-gray-800 text-sm">${createHTMLFromResponse(searchData.enhanced_response || 'No enhanced response received.')}</div>
                                    <button class="show-steps-button text-xs text-blue-600 hover:underline mt-2 block" data-steps='${JSON.stringify(searchData.search_updates || [])}'>Show Search Process</button>
                                </div>
                            `;
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
                    updateSearchProgress('Search failed: Connection error');
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'mb-4 flex justify-start';
                    errorDiv.innerHTML = `
                        <div class="max-w-[75%] bg-red-100 border border-red-300 rounded-lg p-4 shadow-sm">
                            <p class="text-xs text-red-500 mb-2">${new Date().toLocaleString()}</p>
                            <p class="text-sm font-semibold text-red-600 mb-1">Error:</p>
                            <div class="text-red-700 text-sm">Failed to complete search. Please try again.</div>
                        </div>
                    `;
                    chatContainer.appendChild(errorDiv);
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                };
            }

        } catch (error) {
            removeTypingIndicator();
            const errorDiv = document.createElement('div');
            errorDiv.className = 'mb-4 flex justify-start';
            errorDiv.innerHTML = `
                <div class="max-w-[75%] bg-red-100 border border-red-300 rounded-lg p-4 shadow-sm">
                    <p class="text-xs text-red-500 mb-2">${new Date().toLocaleString()}</p>
                    <p class="text-sm font-semibold text-red-600 mb-1">Error:</p>
                    <div class="text-red-700 text-sm">${error.message}</div>
                </div>
            `;
            chatContainer.appendChild(errorDiv);
            console.error('Fetch error:', error);
        }

        // Re-enable input
        messageInput.value = '';
        messageInput.disabled = false;
        sendButton.disabled = false;
        sendButton.textContent = 'Search';
        messageInput.focus();
    });

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendButton.click();
    });

    chatContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('show-steps-button')) {
            try {
                const steps = JSON.parse(e.target.dataset.steps);
                stepsContent.innerHTML = steps.map(step => `<p class="text-sm mb-1">${convertUrlsToLinks(step)}</p>`).join('');
                makeLinksClickable(stepsContent);
                modal.classList.remove('hidden');
            } catch (error) {
                console.error('Error parsing search steps:', error);
                stepsContent.innerHTML = '<p class="text-sm mb-1">Error loading search steps</p>';
                modal.classList.remove('hidden');
            }
        }
    });

    closeModalButton.addEventListener('click', () => {
        modal.classList.add('hidden');
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
    });
});