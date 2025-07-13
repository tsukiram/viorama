// app/static/js/paper.js

document.addEventListener('DOMContentLoaded', () => {
    const bookmarkButton = document.getElementById('bookmark-button');
    const modal = document.getElementById('bookmark-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalMessage = document.getElementById('modal-message');
    const closeModalButton = document.getElementById('close-modal');

    bookmarkButton.addEventListener('click', async () => {
        const code = bookmarkButton.dataset.code;
        const isSaved = bookmarkButton.dataset.saved === 'true';
        const endpoint = isSaved ? `/paper/remove/${code}` : `/paper/save/${code}`;

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();

            modalTitle.textContent = data.error ? 'Error' : 'Success';
            modalMessage.textContent = data.error || data.message;
            modal.classList.remove('hidden');

            if (!data.error) {
                bookmarkButton.dataset.saved = isSaved ? 'false' : 'true';
                bookmarkButton.textContent = isSaved ? 'Save to My List' : 'Remove from Saved';
                bookmarkButton.className = isSaved ? 'bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700' : 'bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700';
            }
        } catch (error) {
            modalTitle.textContent = 'Error';
            modalMessage.textContent = 'Failed to process request';
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