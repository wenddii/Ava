/* ================================================================
   AVA'S GLOW STUDIO — Interactions, Counters & Smooth Animations
   ================================================================ */

document.addEventListener('DOMContentLoaded', () => {

    // ────────────────────────────────────────────────────────────
    // 1. REVEAL ANIMATIONS (IntersectionObserver with Stagger)
    // ────────────────────────────────────────────────────────────
    const revealSelectors = '.reveal, .reveal-left, .reveal-right, .reveal-scale';
    const revealItems = document.querySelectorAll(revealSelectors);

    if ('IntersectionObserver' in window) {
        const revealObserver = new IntersectionObserver((entries, obs) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    const delay = parseInt(entry.target.dataset.delay || 0, 10);
                    setTimeout(() => {
                        entry.target.classList.add('is-visible');
                    }, delay);
                    obs.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.12,
            rootMargin: '0px 0px -8% 0px',
        });

        revealItems.forEach((item) => revealObserver.observe(item));
    } else {
        revealItems.forEach((item) => item.classList.add('is-visible'));
    }

    // ────────────────────────────────────────────────────────────
    // 2. HEADER — Translucent to solid blur on scroll
    // ────────────────────────────────────────────────────────────
    const header = document.getElementById('site-header');
    if (header) {
        const onScroll = () => {
            header.classList.toggle('header-scrolled', window.scrollY > 40);
        };
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }

    // ────────────────────────────────────────────────────────────
    // 3. MOBILE NAV — Drawer toggle
    // ────────────────────────────────────────────────────────────
    const navToggle = document.getElementById('nav-toggle');
    const mobileNav = document.getElementById('mobile-nav');

    if (navToggle && mobileNav) {
        navToggle.addEventListener('click', () => {
            const isOpen = mobileNav.classList.toggle('is-open');
            navToggle.setAttribute('aria-expanded', isOpen);
            document.body.style.overflow = isOpen ? 'hidden' : '';
        });

        mobileNav.querySelectorAll('a').forEach((link) => {
            link.addEventListener('click', () => {
                mobileNav.classList.remove('is-open');
                navToggle.setAttribute('aria-expanded', 'false');
                document.body.style.overflow = '';
            });
        });
    }

    // ────────────────────────────────────────────────────────────
    // 4. ACTIVE NAV LINK — Scroll Spy
    // ────────────────────────────────────────────────────────────
    const navLinks = document.querySelectorAll('.nav-links a');
    const sections = [];

    navLinks.forEach((link) => {
        const href = link.getAttribute('href') || '';
        const hashIndex = href.indexOf('#');
        if (hashIndex !== -1) {
            const id = href.slice(hashIndex + 1);
            if (id && id !== 'top') {
                const section = document.getElementById(id);
                if (section) sections.push({ el: section, link });
            }
        }
    });

    if (sections.length > 0 && 'IntersectionObserver' in window) {
        const spyObserver = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    navLinks.forEach((l) => l.classList.remove('active'));
                    const match = sections.find((s) => s.el === entry.target);
                    if (match) match.link.classList.add('active');
                }
            });
        }, {
            threshold: 0.2,
            rootMargin: '-20% 0px -60% 0px',
        });

        sections.forEach((s) => spyObserver.observe(s.el));
    }

    // ────────────────────────────────────────────────────────────
    // 5. ANIMATED COUNTERS — Stats Section
    // ────────────────────────────────────────────────────────────
    const counters = document.querySelectorAll('[data-count]');

    if (counters.length > 0 && 'IntersectionObserver' in window) {
        const counterObserver = new IntersectionObserver((entries, obs) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.4 });

        counters.forEach((el) => counterObserver.observe(el));
    }

    function animateCounter(el) {
        const target = parseFloat(el.dataset.count);
        if (isNaN(target)) return;

        const decimals = parseInt(el.dataset.decimals || 0, 10);
        const duration = 1600;
        const startTime = performance.now();

        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            const eased = 1 - Math.pow(1 - progress, 3);
            const current = eased * target;

            if (decimals > 0) {
                el.textContent = current.toFixed(decimals);
            } else {
                el.textContent = Math.floor(current) + (target >= 100 ? '+' : '+');
            }

            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                if (decimals > 0) {
                    el.textContent = target.toFixed(decimals);
                } else {
                    el.textContent = target + (target >= 100 ? '+' : '+');
                }
            }
        }

        requestAnimationFrame(update);
    }

    // ────────────────────────────────────────────────────────────
    // 6. SMOOTH SCROLL — Anchor links
    // ────────────────────────────────────────────────────────────
    document.querySelectorAll('a[href*="#"]').forEach((anchor) => {
        anchor.addEventListener('click', (e) => {
            const href = anchor.getAttribute('href') || '';
            const hashIndex = href.indexOf('#');
            if (hashIndex === -1) return;

            const targetPath = href.slice(0, hashIndex);
            const targetId = href.slice(hashIndex);

            if (targetPath && targetPath !== window.location.pathname && targetPath !== '/') return;
            if (targetId === '#' || targetId === '#top') {
                if (targetId === '#top') {
                    e.preventDefault();
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }
                return;
            }

            try {
                const targetEl = document.querySelector(targetId);
                if (targetEl) {
                    e.preventDefault();
                    const headerHeight = header ? header.offsetHeight : 0;
                    const top = targetEl.getBoundingClientRect().top + window.scrollY - headerHeight - 12;

                    window.scrollTo({
                        top,
                        behavior: 'smooth',
                    });
                }
            } catch (err) {
                // Ignore selector error
            }
        });
    });
});