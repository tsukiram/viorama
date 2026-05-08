// /app/static/js/paper.js

document.addEventListener('DOMContentLoaded', () => {
    // === Selektor Elemen DOM ===
    const bookmarkBtn = document.getElementById('bookmark-btn');
    
    // Modal Elements
    const confirmModal = document.getElementById('confirm-modal-overlay');
    const confirmBtn = document.getElementById('confirm-btn');
    const cancelBtn = document.getElementById('cancel-btn');

    // Toast Notification Elements
    const toast = document.getElementById('toast-notification');
    const toastIcon = document.getElementById('toast-icon');
    const toastMessage = document.getElementById('toast-message');

    let isProcessing = false; // Mencegah klik ganda

    // === Fungsi Bantuan untuk UI ===

    /**
     * Menampilkan notifikasi toast dengan pesan dan tipe (success/error).
     * @param {string} message - Pesan yang akan ditampilkan.
     * @param {string} type - 'success' or 'error'.
     */
    const showToast = (message, type = 'success') => {
        if (!toast || !toastIcon || !toastMessage) return;

        // Atur ikon dan kelas berdasarkan tipe
        toastIcon.innerHTML = type === 'success' ? '<i class="fas fa-check-circle"></i>' : '<i class="fas fa-times-circle"></i>';
        toast.className = `toast-notification ${type}`;
        toastMessage.textContent = message;

        // Tampilkan toast
        toast.classList.add('show');

        // Sembunyikan setelah 3 detik
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    };

    /**
     * Memperbarui tampilan tombol bookmark.
     * @param {boolean} isSaved - Status baru paper (apakah tersimpan atau tidak).
     */
    const updateBookmarkButton = (isSaved) => {
        const btnIcon = bookmarkBtn.querySelector('.btn-icon i');
        const btnText = bookmarkBtn.querySelector('.btn-text');

        bookmarkBtn.dataset.isSaved = isSaved;
        if (isSaved) {
            bookmarkBtn.classList.add('saved');
            btnIcon.className = 'fas fa-check';
            btnText.textContent = 'Tersimpan di Koleksi';
        } else {
            bookmarkBtn.classList.remove('saved');
            btnIcon.className = 'fas fa-bookmark';
            btnText.textContent = 'Simpan ke Koleksi';
        }
    };

    const openConfirmModal = () => {
        if (confirmModal) confirmModal.style.display = 'flex';
    };

    const closeConfirmModal = () => {
        if (confirmModal) confirmModal.style.display = 'none';
    };

    // === Logika Utama ===

    if (bookmarkBtn) {
        bookmarkBtn.addEventListener('click', async () => {
            if (isProcessing) return;

            const isSaved = bookmarkBtn.dataset.isSaved === 'true';

            // Jika sudah tersimpan, TANYAKAN untuk menghapus
            if (isSaved) {
                // Untuk UX yang lebih baik, kita tidak perlu modal untuk menghapus dari sini
                // Jika ingin modal, panggil openConfirmModal();
                await removePaper(); 
            } else {
                // Jika belum, langsung simpan
                await savePaper();
            }
        });
    }

    const savePaper = async () => {
        isProcessing = true;
        const code = bookmarkBtn.dataset.code;
        const endpoint = `/paper/save/${code}`;

        try {
            const response = await fetch(endpoint, { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                showToast(data.message, 'success');
                updateBookmarkButton(true); // Update tombol ke status "tersimpan"
            } else {
                showToast(data.error || 'Gagal menyimpan paper.', 'error');
            }
        } catch (error) {
            showToast('Terjadi kesalahan koneksi.', 'error');
        } finally {
            isProcessing = false;
        }
    };

    const removePaper = async () => {
        isProcessing = true;
        closeConfirmModal();
        const code = bookmarkBtn.dataset.code;
        const endpoint = `/paper/remove/${code}`;

        try {
            const response = await fetch(endpoint, { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                showToast(data.message, 'success');
                updateBookmarkButton(false); // Update tombol ke status "tidak tersimpan"
            } else {
                showToast(data.error || 'Gagal menghapus paper.', 'error');
            }
        } catch (error) {
            showToast('Terjadi kesalahan koneksi.', 'error');
        } finally {
            isProcessing = false;
        }
    };

    // === Event Listeners untuk Modal ===
    if (confirmBtn) confirmBtn.addEventListener('click', removePaper);
    if (cancelBtn) cancelBtn.addEventListener('click', closeConfirmModal);
    if (confirmModal) confirmModal.addEventListener('click', (e) => {
        if (e.target === confirmModal) {
            closeConfirmModal();
        }
    });
});