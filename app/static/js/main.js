document.addEventListener('DOMContentLoaded', function() {
    // Flash message close functionality
    document.querySelectorAll('.flash-close').forEach(button => {
        button.addEventListener('click', function() {
            this.parentElement.style.opacity = '0';
            setTimeout(() => {
                this.parentElement.remove();
            }, 200);
        });
    });

    // Auto-dismiss flash messages after 5 seconds
    setTimeout(() => {
        document.querySelectorAll('.flash-message').forEach(message => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.remove();
            }, 200);
        });
    }, 5000);

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // Mobile menu toggle (if needed in future)
    const mobileMenuToggle = document.createElement('button');
    mobileMenuToggle.className = 'mobile-menu-toggle';
    mobileMenuToggle.innerHTML = '<i class="fas fa-bars"></i>';
    mobileMenuToggle.addEventListener('click', function() {
        document.querySelector('.main-nav').classList.toggle('active');
    });

    if (window.innerWidth <= 768) {
        document.querySelector('.header-container').appendChild(mobileMenuToggle);
    }

    window.addEventListener('resize', function() {
        if (window.innerWidth <= 768 && !document.querySelector('.mobile-menu-toggle')) {
            document.querySelector('.header-container').appendChild(mobileMenuToggle);
        } else if (window.innerWidth > 768 && document.querySelector('.mobile-menu-toggle')) {
            document.querySelector('.mobile-menu-toggle').remove();
            document.querySelector('.main-nav').classList.remove('active');
        }
    });
});