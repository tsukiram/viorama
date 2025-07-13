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

        messageInput.disabled = true;
        sendButton.disabled = true;

        const messageDiv = document.createElement('div');
        messageDiv.className = 'mb-4';
        messageDiv.innerHTML = `
            <p class="text-sm text-gray-500">${new Date().toLocaleString()}</p>
            <p class="font-semibold text-blue-600">You:</p>
            <p class="text-gray-800">${message}</p>
            <p class="font-semibold text-blue-600 mt-2">Viorama:</p>
            <p class="text-gray-800 response-text">...</p>
        `;
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        try {
            const response = await fetch(`/search/chat/${currentSessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            const data = await response.json();

            if (data.error) {
                messageDiv.querySelector('.response-text').textContent = data.error;
            } else {
                messageDiv.innerHTML = `
                    <p class="text-sm text-gray-500">${data.timestamp}</p>
                    <p class="font-semibold text-blue-600">You:</p>
                    <p class="text-gray-800">${message}</p>
                    <p class="font-semibold text-blue-600 mt-2">Viorama:</p>
                    <p class="text-gray-800 response-text">${data.response}</p>
                    ${data.search_steps.length ? `<button class="show-steps-button text-sm text-blue-600 hover:underline mt-2 block" data-steps='${JSON.stringify(data.search_steps)}'>Show Search Process</button>` : ''}
                `;
            }
        } catch (error) {
            messageDiv.querySelector('.response-text').textContent = 'Error: Unable to get response';
        }

        messageInput.value = '';
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    });

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendButton.click();
    });

    chatContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('show-steps-button')) {
            const steps = JSON.parse(e.target.dataset.steps);
            stepsContent.innerHTML = steps.map(step => `<p>${step}</p>`).join('');
            modal.classList.remove('hidden');
        }
    });

    closeModalButton.addEventListener('click', () => {
        modal.classList.add('hidden');
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
    });
});