// /app/static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    
    console.log('✓ DOM fully loaded. Initializing all scripts...');

    // ============================================
    // FLASH MESSAGES
    // ============================================
    
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

    // ============================================
    // SMOOTH SCROLL
    // ============================================
    
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // ============================================
    // LOGOUT MODAL
    // ============================================
    
    const logoutBtn = document.getElementById('logout-btn');
    const logoutModal = document.getElementById('logout-modal-overlay');
    const cancelLogoutBtn = document.getElementById('cancel-logout-btn');

    console.log('Logout elements:', {
        button: !!logoutBtn,
        modal: !!logoutModal,
        cancelBtn: !!cancelLogoutBtn
    });

    const openLogoutModal = () => {
        console.log('→ Opening logout modal...');
        if (logoutModal) {
            logoutModal.classList.add('visible');
            document.body.style.overflow = 'hidden'; // Prevent background scroll
        } else {
            console.error('✗ Logout modal element not found!');
        }
    };

    const closeLogoutModal = () => {
        console.log('→ Closing logout modal...');
        if (logoutModal) {
            logoutModal.classList.remove('visible');
            document.body.style.overflow = ''; // Restore scroll
        }
    };

    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            console.log('✓ Logout button clicked');
            openLogoutModal();
        });
    }

    if (cancelLogoutBtn) {
        cancelLogoutBtn.addEventListener('click', closeLogoutModal);
    }

    if (logoutModal) {
        // Close modal when clicking overlay
        logoutModal.addEventListener('click', (e) => {
            if (e.target === logoutModal) {
                console.log('✓ Clicked outside modal - closing');
                closeLogoutModal();
            }
        });

        // Close modal with ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && logoutModal.classList.contains('visible')) {
                closeLogoutModal();
            }
        });
    }

    // ============================================
    // RESPONSIVE NAVBAR (MOBILE MENU)
    // ============================================
    
    const initMobileNavbar = () => {
        const navbar = document.querySelector('.neo-navbar');
        const navbarContainer = document.querySelector('.neo-navbar .container-fluid');
        
        if (!navbar || !navbarContainer) return;

        // Check if already initialized
        if (navbar.querySelector('.navbar-toggle')) return;

        const navbarBrand = navbarContainer.querySelector('.navbar-brand');
        const navLinks = navbarContainer.querySelectorAll('.d-flex.align-items-center.gap-3:not(:first-child)');
        
        if (!navbarBrand || navLinks.length === 0) return;

        // Create wrapper for brand + toggle
        const brandWrapper = document.createElement('div');
        brandWrapper.className = 'navbar-brand-wrapper';
        
        // Create hamburger toggle button
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'navbar-toggle';
        toggleBtn.setAttribute('aria-label', 'Toggle navigation');
        toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
        
        // Wrap brand and add toggle next to it
        navbarBrand.parentNode.insertBefore(brandWrapper, navbarBrand);
        brandWrapper.appendChild(navbarBrand);
        brandWrapper.appendChild(toggleBtn);
        
        // Set initial state for mobile
        if (window.innerWidth <= 768) {
            navbar.classList.add('navbar-collapsed');
        }
        
        // Toggle functionality
        toggleBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            const isCollapsed = navbar.classList.contains('navbar-collapsed');
            
            if (isCollapsed) {
                navbar.classList.remove('navbar-collapsed');
                navbar.classList.add('navbar-expanded');
                this.innerHTML = '<i class="fas fa-times"></i>';
                console.log('✓ Navbar expanded');
            } else {
                navbar.classList.add('navbar-collapsed');
                navbar.classList.remove('navbar-expanded');
                this.innerHTML = '<i class="fas fa-bars"></i>';
                console.log('✓ Navbar collapsed');
            }
        });

        // Close mobile menu when clicking a nav link
        navLinks.forEach(navGroup => {
            navGroup.querySelectorAll('.nav-link, #logout-btn').forEach(link => {
                link.addEventListener('click', () => {
                    if (window.innerWidth <= 768 && navbar.classList.contains('navbar-expanded')) {
                        navbar.classList.remove('navbar-expanded');
                        navbar.classList.add('navbar-collapsed');
                        toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
                        console.log('✓ Navbar closed after link click');
                    }
                });
            });
        });

        // Close mobile menu when clicking outside
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && 
                navbar.classList.contains('navbar-expanded') && 
                !navbar.contains(e.target)) {
                navbar.classList.remove('navbar-expanded');
                navbar.classList.add('navbar-collapsed');
                toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
                console.log('✓ Navbar closed - clicked outside');
            }
        });

        console.log('✓ Mobile navbar initialized');
    };

    // ============================================
    // ACTIVE NAV LINK HIGHLIGHTING
    // ============================================
    
    const setActiveNavLink = () => {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            const linkPath = new URL(link.href, window.location.origin).pathname;
            
            if (linkPath === currentPath || 
                (currentPath.startsWith(linkPath) && linkPath !== '/')) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
        
        console.log('✓ Active nav link set for:', currentPath);
    };

    // ============================================
    // RESPONSIVE HANDLER
    // ============================================
    
    const handleResize = () => {
        const navbar = document.querySelector('.neo-navbar');
        const toggleBtn = navbar?.querySelector('.navbar-toggle');
        
        if (window.innerWidth > 768) {
            // Desktop view
            if (navbar) {
                navbar.classList.remove('navbar-collapsed', 'navbar-expanded');
            }
            if (toggleBtn) {
                toggleBtn.style.display = 'none';
            }
        } else {
            // Mobile view
            if (navbar && !navbar.classList.contains('navbar-collapsed') && 
                !navbar.classList.contains('navbar-expanded')) {
                navbar.classList.add('navbar-collapsed');
            }
            if (toggleBtn) {
                toggleBtn.style.display = 'block';
            }
        }
    };

    // ============================================
    // INITIALIZATION
    // ============================================
    
    // Initialize features
    initMobileNavbar();
    setActiveNavLink();
    
    // Handle window resize
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            handleResize();
            console.log('✓ Window resized - layout adjusted');
        }, 250);
    });
    
    // Initial resize check
    handleResize();

    console.log('✓ All scripts initialized successfully');

});

// ============================================
// UTILITY FUNCTIONS (Global scope if needed)
// ============================================

// Show toast notification (can be used globally)
window.showToast = function(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 100);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
    }, 3000);
};

// Smooth scroll to element (can be used globally)
window.scrollToElement = function(elementId, offset = 100) {
    const element = document.getElementById(elementId);
    if (element) {
        const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
        window.scrollTo({
            top: elementPosition - offset,
            behavior: 'smooth'
        });
    }
};