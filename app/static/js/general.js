document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatContainer = document.getElementById('chat-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    const newSessionButton = document.getElementById('new-session-button');
    const deleteSessionButtons = document.getElementsByClassName('delete-session-button');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    const sessionList = document.getElementById('session-list');
    const chatWrapper = document.querySelector('.chat-wrapper');
    const row = document.querySelector('.row');
    
    // Get current session ID from the URL or page context
    const currentSessionId = window.location.pathname.split('/').pop() || null;

    // Store original session items
    const originalSessionItems = Array.from(sessionList.children).map(item => ({
        title: item.querySelector('.session-title').outerHTML,
        deleteButton: item.querySelector('.delete-session-button').outerHTML,
        sessionId: item.querySelector('.session-title').dataset.sessionId
    }));

    // Sidebar toggle functionality
    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('sidebar-collapsed');
        row.classList.toggle('sidebar-collapsed-row');
        
        if (sidebar.classList.contains('sidebar-collapsed')) {
            sidebarToggle.innerHTML = '<i class="fas fa-history"></i>';
            // Replace New Session button with icon
            const newSessionContainer = document.querySelector('.new-session-container');
            newSessionContainer.innerHTML = '<i class="far fa-plus text-primary w-100 mb-4 new-session-icon" data-action="new-session"></i>';
            // Replace session titles with outline icons and remove delete buttons
            sessionList.innerHTML = originalSessionItems.map(item => `
                <li class="d-flex justify-content-center align-items-center p-2 rounded hover-bg-light">
                    <i class="far fa-comment text-primary session-icon" data-action="session" data-session-id="${item.sessionId}"></i>
                </li>
            `).join('');
        } else {
            sidebarToggle.innerHTML = '<i class="fas fa-times"></i>';
            // Restore New Session button
            const newSessionContainer = document.querySelector('.new-session-container');
            newSessionContainer.innerHTML = '<button id="new-session-button" class="btn btn-primary w-100 mb-4" data-action="new-session">New Session</button>';
            // Restore session titles with delete buttons
            sessionList.innerHTML = originalSessionItems.map(item => `
                <li class="d-flex justify-content-between align-items-center p-2 rounded hover-bg-light">
                    ${item.title}
                    ${item.deleteButton}
                </li>
            `).join('');
            // Reattach event listeners to restored elements
            attachNewSessionListener();
            attachSessionListeners();
            attachDeleteListeners();
        }
        // Reattach event listeners for icons
        attachIconListeners();
    });

    // Function to attach New Session listener
    function attachNewSessionListener() {
        const newSessionButton = document.getElementById('new-session-button');
        if (newSessionButton) {
            newSessionButton.addEventListener('click', handleNewSession);
        }
    }

    // Function to attach session link listeners
    function attachSessionListeners() {
        const sessionTitles = document.getElementsByClassName('session-title');
        Array.from(sessionTitles).forEach(title => {
            title.addEventListener('click', (e) => {
                e.preventDefault();
                window.location.href = `/general/${title.dataset.sessionId}`;
            });
        });
    }

    // Function to attach delete button listeners
    function attachDeleteListeners() {
        const deleteSessionButtons = document.getElementsByClassName('delete-session-button');
        Array.from(deleteSessionButtons).forEach(button => {
            button.addEventListener('click', handleDeleteSession);
        });
    }

    // Function to attach icon listeners
    function attachIconListeners() {
        const newSessionIcon = document.querySelector('.new-session-icon');
        if (newSessionIcon) {
            newSessionIcon.addEventListener('click', handleNewSession);
        }
        const sessionIcons = document.getElementsByClassName('session-icon');
        Array.from(sessionIcons).forEach(icon => {
            icon.addEventListener('click', () => {
                window.location.href = `/general/${icon.dataset.sessionId}`;
            });
        });
    }

    // Handle New Session
    async function handleNewSession() {
        const title = prompt('Enter a title for the new session:', 'New General Session');
        if (!title) return;

        try {
            const response = await fetch('/general/new_session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title })
            });
            const data = await response.json();

            if (data.session_id) {
                window.location.href = `/general/${data.session_id}`;
            } else {
                alert(data.error || 'Failed to create new session');
            }
        } catch (error) {
            alert('Error creating new session');
        }
    }

    // Handle Delete Session
    async function handleDeleteSession(e) {
        const sessionId = e.currentTarget.dataset.sessionId;
        if (confirm('Are you sure you want to delete this session?')) {
            try {
                const response = await fetch(`/general/delete_session/${sessionId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();

                if (data.message) {
                    window.location.href = '/general';
                } else {
                    alert(data.error || 'Failed to delete session');
                }
            } catch (error) {
                alert('Error deleting session');
            }
        }
    }

    // Initial event listeners
    attachNewSessionListener();
    attachSessionListeners();
    attachDeleteListeners();

    // Collapse sidebar by default on mobile
    if (window.innerWidth <= 768) {
        sidebar.classList.add('sidebar-collapsed');
        row.classList.add('sidebar-collapsed-row');
        sidebarToggle.innerHTML = '<i class="fas fa-history"></i>';
        const newSessionContainer = document.querySelector('.new-session-container');
        newSessionContainer.innerHTML = '<i class="far fa-plus text-primary w-100 mb-4 new-session-icon" data-action="new-session"></i>';
        sessionList.innerHTML = originalSessionItems.map(item => `
            <li class="d-flex justify-content-center align-items-center p-2 rounded hover-bg-light">
                <i class="far fa-comment text-primary session-icon" data-action="session" data-session-id="${item.sessionId}"></i>
            </li>
        `).join('');
        attachIconListeners();
    }

    sendButton.addEventListener('click', async () => {
        const message = messageInput.value.trim();
        if (!message || !currentSessionId) return;

        messageInput.disabled = true;
        sendButton.disabled = true;

        // Add user message
        const messageDiv = document.createElement('div');
        messageDiv.className = 'mb-4 flex justify-end animate-fade-in';
        messageDiv.innerHTML = `
            <div class="max-w-[75%] bg-blue-100 rounded-lg p-4 shadow-sm">
                <p class="text-muted small mb-2">${new Date().toLocaleString()}</p>
                <p class="fw-medium text-primary mb-1">You:</p>
                <div class="markdown-content text-dark text-sm">${message}</div>
            </div>
        `;
        chatContainer.appendChild(messageDiv);

        // Add "Sending..." placeholder
        const sendingDiv = document.createElement('div');
        sendingDiv.className = 'mb-4 flex justify-start animate-fade-in';
        sendingDiv.innerHTML = `
            <div class="max-w-[75%] bg-gray-100 rounded-lg p-4 shadow-sm">
                <p class="text-muted small mb-2">${new Date().toLocaleString()}</p>
                <p class="fw-medium text-primary mb-1">Viorama:</p>
                <div class="markdown-content text-dark text-sm">Sending...</div>
            </div>
        `;
        chatContainer.appendChild(sendingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // Show loading indicator
        loadingIndicator.style.display = 'flex';
        loadingIndicator.classList.add('active');

        // Ensure minimum loader visibility
        const minLoaderTime = new Promise(resolve => setTimeout(resolve, 500));

        try {
            const [response] = await Promise.all([
                fetch(`/general/chat/${currentSessionId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                }),
                minLoaderTime
            ]);
            const data = await response.json();

            // Remove sending placeholder
            sendingDiv.remove();

            // Hide loading indicator
            loadingIndicator.style.display = 'none';
            loadingIndicator.classList.remove('active');

            if (data.error) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'mb-4 flex justify-start animate-fade-in';
                errorDiv.innerHTML = `
                    <div class="max-w-[75%] bg-gray-100 rounded-lg p-4 shadow-sm">
                        <p class="text-muted small mb-2">${new Date().toLocaleString()}</p>
                        <p class="fw-medium text-primary mb-1">Viorama:</p>
                        <div class="markdown-content text-dark text-sm">${data.error}</div>
                    </div>
                `;
                chatContainer.appendChild(errorDiv);
            } else {
                const responseDiv = document.createElement('div');
                responseDiv.className = 'mb-4 flex justify-start animate-fade-in';
                responseDiv.innerHTML = `
                    <div class="max-w-[75%] bg-gray-100 rounded-lg p-4 shadow-sm">
                        <p class="text-muted small mb-2">${data.timestamp}</p>
                        <p class="fw-medium text-primary mb-1">Viorama:</p>
                        <div class="markdown-content text-dark text-sm">${data.response}</div>
                    </div>
                `;
                chatContainer.appendChild(responseDiv);
            }
        } catch (error) {
            // Remove sending placeholder
            sendingDiv.remove();

            // Hide loading indicator
            loadingIndicator.style.display = 'none';
            loadingIndicator.classList.remove('active');

            const errorDiv = document.createElement('div');
            errorDiv.className = 'mb-4 flex justify-start animate-fade-in';
            errorDiv.innerHTML = `
                <div class="max-w-[75%] bg-gray-100 rounded-lg p-4 shadow-sm">
                    <p class="text-muted small mb-2">${new Date().toLocaleString()}</p>
                    <p class="fw-medium text-primary mb-1">Viorama:</p>
                    <div class="markdown-content text-dark text-sm">Error: Unable to get response</div>
                </div>
            `;
            chatContainer.appendChild(errorDiv);
        }

        chatContainer.scrollTop = chatContainer.scrollHeight;
        messageInput.value = '';
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    });

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendButton.click();
    });

    // Scroll to bottom on initial load
    chatContainer.scrollTop = chatContainer.scrollHeight;
});

$(document).ready(function() {
    // Smooth scroll to chat container on new message
    const chatContainer = $('#chat-container');
    chatContainer.on('DOMSubtreeModified', function() {
        chatContainer.animate({
            scrollTop: chatContainer[0].scrollHeight
        }, 300);
    });

    // Fade-in animation for new chat sessions
    $('.neo-card').each(function(index) {
        $(this).css({ opacity: 0, position: 'relative', top: '20px' });
        $(this).delay(index * 100).animate({
            opacity: 1,
            top: 0
        }, 500, 'easeOutCubic');
    });
    
    // Auto-dismiss alerts after 7 seconds
    window.setTimeout(function() {
        $('.alert').not('.alert-success').fadeTo(500, 0).slideUp(500, function() {
            $(this).remove();
        });
    }, 7000);
});