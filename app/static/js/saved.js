// /app/static/js/saved.js

console.log('saved.js loaded');

let paperIdToDelete = null;
let paperCodeToDelete = null;

function openModal() {
    const modalOverlay = document.getElementById('delete-modal-overlay');
    if (modalOverlay) {
        modalOverlay.style.display = 'flex';
        console.log('Modal opened for paper:', paperCodeToDelete);
    } else {
        console.error('Modal overlay not found!');
    }
}

function closeModal() {
    const modalOverlay = document.getElementById('delete-modal-overlay');
    if (modalOverlay) {
        modalOverlay.style.display = 'none';
    }
    paperIdToDelete = null;
    paperCodeToDelete = null;
    console.log('Modal closed');
}

async function deletePaper() {
    if (!paperCodeToDelete) {
        console.error('No paper code to delete');
        alert('Error: Tidak ada paper yang dipilih');
        return;
    }

    console.log('Confirming delete for:', paperCodeToDelete);
    
    const url = `/saved/remove/${paperCodeToDelete}`;
    console.log('Fetching URL:', url);

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        });

        console.log('Response status:', response.status);
        
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Response is not JSON:', text);
            alert('Error: Server tidak mengembalikan response yang valid');
            closeModal();
            return;
        }

        const data = await response.json();
        console.log('Response data:', data);

        if (data.success) {
            console.log('Delete successful!');
            
            const cardToRemove = document.getElementById(`paper-item-${paperIdToDelete}`);
            if (cardToRemove) {
                cardToRemove.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                cardToRemove.style.opacity = '0';
                cardToRemove.style.transform = 'scale(0.95)';
                
                setTimeout(() => {
                    cardToRemove.remove();
                    
                    const remainingPapers = document.querySelectorAll('.paper-item');
                    console.log('Remaining papers:', remainingPapers.length);
                    
                    if (remainingPapers.length === 0) {
                        console.log('No papers left, reloading...');
                        window.location.reload();
                    }
                }, 300);
            }
            
            closeModal();
        } else {
            console.error('Delete failed:', data.error);
            alert(`Error: ${data.error || 'Gagal menghapus paper'}`);
            closeModal();
        }
    } catch (error) {
        console.error("Failed to remove paper:", error);
        alert("Terjadi kesalahan saat menghapus paper. Cek console untuk detail.");
        closeModal();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, setting up event listeners');
    
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
    const modalOverlay = document.getElementById('delete-modal-overlay');
    
    console.log('Modal elements found:', {
        confirmBtn: !!confirmDeleteBtn,
        cancelBtn: !!cancelDeleteBtn,
        overlay: !!modalOverlay
    });

    // Event delegation untuk tombol remove
    document.addEventListener('click', (e) => {
        const removeBtn = e.target.closest('.remove-paper-btn');
        if (removeBtn) {
            e.preventDefault();
            e.stopPropagation();
            paperIdToDelete = removeBtn.dataset.id;
            paperCodeToDelete = removeBtn.dataset.code;
            console.log('Delete requested for:', { id: paperIdToDelete, code: paperCodeToDelete });
            openModal();
            return;
        }
        
        // Handle confirm button
        if (e.target.id === 'confirm-delete-btn' || e.target.closest('#confirm-delete-btn')) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Confirm button clicked!');
            deletePaper();
            return;
        }
        
        // Handle cancel button
        if (e.target.id === 'cancel-delete-btn' || e.target.closest('#cancel-delete-btn')) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Cancel button clicked');
            closeModal();
            return;
        }
        
        // Handle overlay click
        if (e.target === modalOverlay) {
            console.log('Overlay clicked');
            closeModal();
        }
    });
});