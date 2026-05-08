// app/static/js/home.js

document.addEventListener('DOMContentLoaded', () => {
    // Animation untuk ilustrasi saat halaman dimuat
    const welcomeBanner = document.querySelector('.welcome-banner');
    if (welcomeBanner) {
        welcomeBanner.style.opacity = '0';
        welcomeBanner.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            welcomeBanner.style.transition = 'all 0.6s ease';
            welcomeBanner.style.opacity = '1';
            welcomeBanner.style.transform = 'translateY(0)';
        }, 100);
    }

    // Animation untuk feature cards
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 200 + (index * 100));
    });

    // Animation untuk sidebar
    const sidebar = document.querySelector('.sidebar-right');
    if (sidebar) {
        sidebar.style.opacity = '0';
        sidebar.style.transform = 'translateX(20px)';
        
        setTimeout(() => {
            sidebar.style.transition = 'all 0.6s ease';
            sidebar.style.opacity = '1';
            sidebar.style.transform = 'translateX(0)';
        }, 400);
    }
});