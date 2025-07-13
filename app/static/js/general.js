document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatContainer = document.getElementById('chat-container');
    const newSessionButton = document.getElementById('new-session-button');
    const deleteSessionButtons = document.getElementsByClassName('delete-session-button');
    
    // Get current session ID from the URL or page context
    const currentSessionId = window.location.pathname.split('/').pop() || null;

    newSessionButton.addEventListener('click', async () => {
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
    });

    Array.from(deleteSessionButtons).forEach(button => {
        button.addEventListener('click', async () => {
            const sessionId = button.dataset.sessionId;
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
        });
    });

    sendButton.addEventListener('click', async () => {
        const message = messageInput.value.trim();
        if (!message || !currentSessionId) return;

        messageInput.disabled = true;
        sendButton.disabled = true;

        const messageDiv = document.createElement('div');
        messageDiv.className = 'mb-4';
        messageDiv.innerHTML = `
            <p class="text-sm text-gray-500">${new Date().toLocaleString()}</p>
            <p class="font-semibold text-blue-600">You:</p>
            <p class="text-gray-800">${message}</p>
            <p class="font-semibold text-blue-600 mt-2">Viorama:</p>
            <p class="text-gray-800">...</p>
        `;
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        try {
            const response = await fetch(`/general/chat/${currentSessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            const data = await response.json();

            if (data.error) {
                messageDiv.querySelector('p:last-child').textContent = data.error;
            } else {
                messageDiv.innerHTML = `
                    <p class="text-sm text-gray-500">${data.timestamp}</p>
                    <p class="font-semibold text-blue-600">You:</p>
                    <p class="text-gray-800">${message}</p>
                    <p class="font-semibold text-blue-600 mt-2">Viorama:</p>
                    <p class="text-gray-800">${data.response}</p>
                `;
            }
        } catch (error) {
            messageDiv.querySelector('p:last-child').textContent = 'Error: Unable to get response';
        }

        messageInput.value = '';
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    });

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendButton.click();
    });
});