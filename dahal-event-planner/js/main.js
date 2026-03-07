/* ============================================
   DAHAL EVENT PLANNER — JavaScript
   Interactive features & animations
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    // === Navigation ===
    initNavigation();

    // === Hero Counter Animation ===
    initCounters();

    // === Celebration Particles ===
    initCelebrationCanvas();

    // === Cost Calculator ===
    initCalculator();

    // === Testimonials Carousel ===
    initTestimonials();

    // === Portfolio Filter ===
    initPortfolioFilter();

    // === Scroll Reveal Animations ===
    initScrollReveal();

    // === Contact Form ===
    initContactForm();

    // === Smooth Scroll ===
    initSmoothScroll();
});

/* ============================================
   NAVIGATION
   ============================================ */
function initNavigation() {
    const header = document.getElementById('header');
    const toggle = document.getElementById('nav-toggle');
    const navLinks = document.getElementById('nav-links');

    // Scroll effect
    let lastScroll = 0;
    window.addEventListener('scroll', () => {
        const scrollY = window.scrollY;
        header.classList.toggle('scrolled', scrollY > 50);
        lastScroll = scrollY;
    }, { passive: true });

    // Mobile menu toggle
    toggle.addEventListener('click', () => {
        const isOpen = navLinks.classList.toggle('open');
        toggle.classList.toggle('active');
        toggle.setAttribute('aria-expanded', isOpen);
    });

    // Close mobile menu on link click
    navLinks.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            navLinks.classList.remove('open');
            toggle.classList.remove('active');
            toggle.setAttribute('aria-expanded', 'false');
        });
    });

    // Close menu on outside click
    document.addEventListener('click', (e) => {
        if (!navLinks.contains(e.target) && !toggle.contains(e.target)) {
            navLinks.classList.remove('open');
            toggle.classList.remove('active');
            toggle.setAttribute('aria-expanded', 'false');
        }
    });
}

/* ============================================
   ANIMATED COUNTERS
   ============================================ */
function initCounters() {
    const counters = document.querySelectorAll('[data-count]');
    if (!counters.length) return;

    const animateCounter = (el) => {
        const target = parseInt(el.dataset.count, 10);
        const duration = 2000;
        const startTime = performance.now();

        const update = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Ease out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.round(target * eased);

            if (progress < 1) {
                requestAnimationFrame(update);
            }
        };

        requestAnimationFrame(update);
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounter(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    counters.forEach(c => observer.observe(c));
}

/* ============================================
   CELEBRATION PARTICLES CANVAS
   ============================================ */
function initCelebrationCanvas() {
    const canvas = document.getElementById('celebration-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let particles = [];
    let animationId;

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize, { passive: true });

    class Particle {
        constructor(x, y) {
            this.x = x;
            this.y = y;
            this.size = Math.random() * 8 + 3;
            this.speedX = (Math.random() - 0.5) * 12;
            this.speedY = Math.random() * -15 - 5;
            this.gravity = 0.5;
            this.opacity = 1;
            this.decay = Math.random() * 0.02 + 0.01;
            this.rotation = Math.random() * 360;
            this.rotationSpeed = (Math.random() - 0.5) * 10;
            this.colors = ['#c2185b', '#7c4dff', '#ff6d00', '#ffd700', '#f06292', '#4caf50', '#00bcd4'];
            this.color = this.colors[Math.floor(Math.random() * this.colors.length)];
            this.shape = Math.floor(Math.random() * 3); // 0: circle, 1: square, 2: star
        }

        update() {
            this.speedY += this.gravity;
            this.x += this.speedX;
            this.y += this.speedY;
            this.opacity -= this.decay;
            this.rotation += this.rotationSpeed;
            this.speedX *= 0.98;
        }

        draw() {
            ctx.save();
            ctx.globalAlpha = Math.max(0, this.opacity);
            ctx.translate(this.x, this.y);
            ctx.rotate((this.rotation * Math.PI) / 180);
            ctx.fillStyle = this.color;

            if (this.shape === 0) {
                ctx.beginPath();
                ctx.arc(0, 0, this.size, 0, Math.PI * 2);
                ctx.fill();
            } else if (this.shape === 1) {
                ctx.fillRect(-this.size / 2, -this.size / 2, this.size, this.size);
            } else {
                // Star shape
                const spikes = 5;
                const outerR = this.size;
                const innerR = this.size / 2;
                ctx.beginPath();
                for (let i = 0; i < spikes * 2; i++) {
                    const radius = i % 2 === 0 ? outerR : innerR;
                    const angle = (i * Math.PI) / spikes - Math.PI / 2;
                    if (i === 0) ctx.moveTo(Math.cos(angle) * radius, Math.sin(angle) * radius);
                    else ctx.lineTo(Math.cos(angle) * radius, Math.sin(angle) * radius);
                }
                ctx.closePath();
                ctx.fill();
            }

            ctx.restore();
        }
    }

    function createBurst(x, y, count) {
        for (let i = 0; i < count; i++) {
            particles.push(new Particle(x, y));
        }
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles = particles.filter(p => p.opacity > 0);
        particles.forEach(p => {
            p.update();
            p.draw();
        });
        if (particles.length > 0) {
            animationId = requestAnimationFrame(animate);
        }
    }

    // Confetti burst on page load (delayed for impact)
    setTimeout(() => {
        const centerX = window.innerWidth / 2;
        const topY = window.innerHeight * 0.3;
        createBurst(centerX, topY, 80);
        createBurst(centerX - 200, topY + 50, 40);
        createBurst(centerX + 200, topY + 50, 40);
        animate();
    }, 1500);

    // Confetti on CTA button click
    document.querySelectorAll('.btn-primary, .btn-glow').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const rect = btn.getBoundingClientRect();
            createBurst(rect.left + rect.width / 2, rect.top, 30);
            if (!animationId || particles.length === 0) animate();
        });
    });
}

/* ============================================
   COST CALCULATOR
   ============================================ */
function initCalculator() {
    const form = document.getElementById('cost-calculator');
    const result = document.getElementById('calc-result');
    if (!form || !result) return;

    const steps = form.querySelectorAll('.calc-step');
    const prevBtn = form.querySelector('.calc-prev');
    const nextBtn = form.querySelector('.calc-next');
    const progressBar = form.querySelector('.calc-progress-bar');
    const guestSlider = document.getElementById('guest-count');
    const guestDisplay = document.getElementById('guest-display');
    const restartBtn = document.getElementById('calc-restart');

    let currentStep = 0;

    // Guest slider
    if (guestSlider && guestDisplay) {
        guestSlider.addEventListener('input', () => {
            guestDisplay.textContent = guestSlider.value;
        });
    }

    function showStep(index) {
        steps.forEach((step, i) => {
            step.classList.toggle('active', i === index);
        });
        prevBtn.disabled = index === 0;
        nextBtn.textContent = index === steps.length - 1 ? 'See Estimate →' : 'Next →';
        progressBar.style.width = `${((index + 1) / steps.length) * 100}%`;
    }

    nextBtn.addEventListener('click', () => {
        // Validate current step
        const currentStepEl = steps[currentStep];
        const radios = currentStepEl.querySelectorAll('input[type="radio"]');
        if (radios.length > 0) {
            const checked = currentStepEl.querySelector('input[type="radio"]:checked');
            if (!checked) {
                // Shake the options
                const options = currentStepEl.querySelector('.calc-options');
                options.style.animation = 'none';
                options.offsetHeight; // Trigger reflow
                options.style.animation = 'shake 0.5s ease';
                return;
            }
        }

        if (currentStep < steps.length - 1) {
            currentStep++;
            showStep(currentStep);
        } else {
            calculateResult();
        }
    });

    prevBtn.addEventListener('click', () => {
        if (currentStep > 0) {
            currentStep--;
            showStep(currentStep);
        }
    });

    if (restartBtn) {
        restartBtn.addEventListener('click', () => {
            currentStep = 0;
            showStep(0);
            form.style.display = '';
            result.hidden = true;
            form.reset();
            if (guestDisplay) guestDisplay.textContent = '100';
        });
    }

    function calculateResult() {
        const eventType = form.querySelector('[name="event-type"]:checked')?.value;
        const guests = parseInt(guestSlider?.value || 100, 10);
        const style = form.querySelector('[name="style"]:checked')?.value;

        // Base costs per event type
        const baseCosts = {
            'wedding': 5000,
            'engagement': 1500,
            'birthday': 800,
            'corporate': 3000,
            'baby-shower': 600,
            'other': 1000
        };

        // Per-guest costs
        const guestCosts = {
            'wedding': 120,
            'engagement': 60,
            'birthday': 40,
            'corporate': 80,
            'baby-shower': 35,
            'other': 50
        };

        // Style multipliers
        const styleMultipliers = {
            'intimate': 0.8,
            'classic': 1.2,
            'luxury': 2.0
        };

        const base = baseCosts[eventType] || 1000;
        const perGuest = guestCosts[eventType] || 50;
        const multiplier = styleMultipliers[style] || 1;

        const total = (base + (perGuest * guests)) * multiplier;
        const low = Math.round(total * 0.85 / 100) * 100;
        const high = Math.round(total * 1.15 / 100) * 100;

        document.getElementById('result-low').textContent = `$${low.toLocaleString()}`;
        document.getElementById('result-high').textContent = `$${high.toLocaleString()}`;

        form.style.display = 'none';
        result.hidden = false;
    }
}

/* ============================================
   TESTIMONIALS CAROUSEL
   ============================================ */
function initTestimonials() {
    const track = document.querySelector('.testimonial-track');
    const cards = document.querySelectorAll('.testimonial-card');
    const prevBtn = document.getElementById('testimonial-prev');
    const nextBtn = document.getElementById('testimonial-next');
    const dotsContainer = document.getElementById('testimonial-dots');

    if (!track || !cards.length) return;

    let current = 0;
    const total = cards.length;

    // Create dots
    for (let i = 0; i < total; i++) {
        const dot = document.createElement('span');
        dot.classList.add('dot');
        if (i === 0) dot.classList.add('active');
        dot.addEventListener('click', () => goTo(i));
        dotsContainer.appendChild(dot);
    }

    const dots = dotsContainer.querySelectorAll('.dot');

    function goTo(index) {
        current = index;
        track.style.transform = `translateX(-${current * 100}%)`;
        dots.forEach((d, i) => d.classList.toggle('active', i === current));
    }

    prevBtn.addEventListener('click', () => goTo(current > 0 ? current - 1 : total - 1));
    nextBtn.addEventListener('click', () => goTo(current < total - 1 ? current + 1 : 0));

    // Auto-play
    let autoplay = setInterval(() => goTo(current < total - 1 ? current + 1 : 0), 5000);

    // Pause on hover
    const carousel = document.getElementById('testimonials-carousel');
    carousel.addEventListener('mouseenter', () => clearInterval(autoplay));
    carousel.addEventListener('mouseleave', () => {
        autoplay = setInterval(() => goTo(current < total - 1 ? current + 1 : 0), 5000);
    });

    // Touch support
    let touchStartX = 0;
    let touchEndX = 0;

    track.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    track.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        const diff = touchStartX - touchEndX;
        if (Math.abs(diff) > 50) {
            if (diff > 0) goTo(current < total - 1 ? current + 1 : 0);
            else goTo(current > 0 ? current - 1 : total - 1);
        }
    }, { passive: true });
}

/* ============================================
   PORTFOLIO FILTER
   ============================================ */
function initPortfolioFilter() {
    const filterBtns = document.querySelectorAll('.filter-btn');
    const items = document.querySelectorAll('.portfolio-item');

    if (!filterBtns.length) return;

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const filter = btn.dataset.filter;

            // Update active state
            filterBtns.forEach(b => {
                b.classList.remove('active');
                b.setAttribute('aria-selected', 'false');
            });
            btn.classList.add('active');
            btn.setAttribute('aria-selected', 'true');

            // Filter items
            items.forEach(item => {
                const category = item.dataset.category;
                const show = filter === 'all' || category === filter;
                item.classList.toggle('hidden', !show);

                if (show) {
                    item.style.animation = 'fadeInUp 0.5s ease-out forwards';
                }
            });
        });
    });
}

/* ============================================
   SCROLL REVEAL ANIMATIONS
   ============================================ */
function initScrollReveal() {
    // Add reveal class to sections
    const sections = document.querySelectorAll('.section-header, .service-card, .why-feature, .portfolio-card, .process-step, .faq-item');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                // Stagger the animation
                setTimeout(() => {
                    entry.target.classList.add('visible');
                }, index * 100);
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    sections.forEach(section => {
        section.classList.add('reveal');
        observer.observe(section);
    });
}

/* ============================================
   CONTACT FORM
   ============================================ */
function initContactForm() {
    const form = document.getElementById('contact-form');
    if (!form) return;

    form.addEventListener('submit', (e) => {
        e.preventDefault();

        // Basic validation
        const name = form.querySelector('#contact-name');
        const email = form.querySelector('#contact-email');
        const message = form.querySelector('#contact-message');

        if (!name.value.trim() || !email.value.trim() || !message.value.trim()) {
            return;
        }

        // Show success state
        const wrapper = form.closest('.contact-form-wrapper');
        wrapper.innerHTML = `
            <div class="form-success">
                <span class="form-success-emoji">🎉</span>
                <h3>Message Sent!</h3>
                <p>Thank you for reaching out! We'll get back to you within 24 hours with your free quote. In the meantime, start dreaming big — we'll handle the rest!</p>
            </div>
        `;

        // Trigger celebration
        const canvas = document.getElementById('celebration-canvas');
        if (canvas) {
            const rect = wrapper.getBoundingClientRect();
            const event = new CustomEvent('celebrate', {
                detail: { x: rect.left + rect.width / 2, y: rect.top }
            });
            document.dispatchEvent(event);
        }
    });
}

/* ============================================
   SMOOTH SCROLL
   ============================================ */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
            const targetId = anchor.getAttribute('href');
            if (targetId === '#') return;

            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

/* ============================================
   SHAKE ANIMATION (for calculator validation)
   ============================================ */
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-10px); }
        75% { transform: translateX(10px); }
    }
`;
document.head.appendChild(style);
