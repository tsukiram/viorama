// app\static\js\saved.js
document.addEventListener('DOMContentLoaded', () => {
    const removeButtons = document.getElementsByClassName('remove-paper-button');
    const modal = document.getElementById('bookmark-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalMessage = document.getElementById('modal-message');
    const closeModalButton = document.getElementById('close-modal');

    Array.from(removeButtons).forEach(button => {
        button.addEventListener('click', async () => {
            const code = button.dataset.code;
            try {
                const response = await fetch(`/paper/remove/${code}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();

                modalTitle.textContent = data.error ? 'Error' : 'Success';
                modalMessage.textContent = data.error || data.message;
                modal.classList.remove('hidden');

                if (!data.error) {
                    button.parentElement.remove();
                }
            } catch (error) {
                modalTitle.textContent = 'Error';
                modalMessage.textContent = 'Failed to remove paper';
                modal.classList.remove('hidden');
            }
        });
    });

    closeModalButton.addEventListener('click', () => {
        modal.classList.add('hidden');
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
    });
});