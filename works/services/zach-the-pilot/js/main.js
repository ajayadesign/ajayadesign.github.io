/**
 * ZachThePilot — Main JavaScript
 * Property of AjayaDesign | Demo Purpose Only
 * AjayaDesign-Demo-ID: AD-ZTP-2026-DEMO
 */

document.addEventListener('DOMContentLoaded', () => {
  'use strict';

  // ── Navigation ──────────────────────────────────────────────
  const navbar = document.getElementById('navbar');
  const hamburger = document.getElementById('hamburger');
  const navLinks = document.getElementById('navLinks');

  // Scroll handling for navbar
  const handleScroll = () => {
    if (navbar) {
      navbar.classList.toggle('scrolled', window.scrollY > 50);
    }
    // Back to top button
    const backToTop = document.getElementById('backToTop');
    if (backToTop) {
      backToTop.classList.toggle('visible', window.scrollY > 400);
    }
  };

  window.addEventListener('scroll', handleScroll, { passive: true });
  handleScroll();

  // Hamburger menu
  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
      const isOpen = navLinks.classList.toggle('active');
      hamburger.classList.toggle('active');
      hamburger.setAttribute('aria-expanded', isOpen);
    });

    // Close menu on link click
    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('active');
        hamburger.classList.remove('active');
        hamburger.setAttribute('aria-expanded', 'false');
      });
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (!navbar.contains(e.target) && navLinks.classList.contains('active')) {
        navLinks.classList.remove('active');
        hamburger.classList.remove('active');
        hamburger.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // Back to top
  const backToTopBtn = document.getElementById('backToTop');
  if (backToTopBtn) {
    backToTopBtn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ── Scroll Animations ──────────────────────────────────────
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const animObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        animObserver.unobserve(entry.target);
      }
    });
  }, observerOptions);

  document.querySelectorAll('.fade-in, .slide-left, .slide-right').forEach(el => {
    animObserver.observe(el);
  });

  // ── FAQ Accordion ──────────────────────────────────────────
  document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.closest('.faq-item');
      const isOpen = item.classList.contains('active');

      // Close all
      document.querySelectorAll('.faq-item.active').forEach(openItem => {
        openItem.classList.remove('active');
        openItem.querySelector('.faq-question').setAttribute('aria-expanded', 'false');
      });

      // Open clicked (if it wasn't already open)
      if (!isOpen) {
        item.classList.add('active');
        btn.setAttribute('aria-expanded', 'true');
      }
    });
  });

  // ── Calendar System ────────────────────────────────────────
  const calendarGrid = document.getElementById('calendarGrid');
  const calendarMonth = document.getElementById('calendarMonth');
  const prevMonthBtn = document.getElementById('prevMonth');
  const nextMonthBtn = document.getElementById('nextMonth');
  const timeSlots = document.getElementById('timeSlots');
  const timeSlotsGrid = document.getElementById('timeSlotsGrid');
  const selectedDateDisplay = document.getElementById('selectedDateDisplay');
  const continueBooking = document.getElementById('continueBooking');

  if (calendarGrid) {
    let currentDate = new Date();
    let currentYear = currentDate.getFullYear();
    let currentMonth = currentDate.getMonth();
    let selectedDate = null;
    let selectedTime = null;

    const monthNames = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];

    const availableTimes = [
      '7:00 AM', '8:00 AM', '9:00 AM', '10:00 AM',
      '11:00 AM', '12:00 PM', '1:00 PM', '2:00 PM',
      '3:00 PM', '4:00 PM', '5:00 PM', '6:00 PM'
    ];

    function renderCalendar(year, month) {
      // Clear existing day cells (keep labels)
      const dayLabels = calendarGrid.querySelectorAll('.calendar-day-label');
      calendarGrid.innerHTML = '';
      dayLabels.forEach(label => calendarGrid.appendChild(label));

      calendarMonth.textContent = `${monthNames[month]} ${year}`;

      const firstDay = new Date(year, month, 1).getDay();
      const daysInMonth = new Date(year, month + 1, 0).getDate();
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      // Empty cells before first day
      for (let i = 0; i < firstDay; i++) {
        const empty = document.createElement('div');
        empty.className = 'calendar-day empty';
        calendarGrid.appendChild(empty);
      }

      // Day cells
      for (let day = 1; day <= daysInMonth; day++) {
        const cell = document.createElement('div');
        cell.className = 'calendar-day';
        cell.textContent = day;

        const cellDate = new Date(year, month, day);
        cellDate.setHours(0, 0, 0, 0);

        if (cellDate < today) {
          cell.classList.add('past');
        } else {
          // Sundays are unavailable
          if (cellDate.getDay() !== 0) {
            cell.classList.add('available');
            cell.addEventListener('click', () => selectDate(year, month, day));
          } else {
            cell.classList.add('past');
          }
        }

        if (cellDate.getTime() === today.getTime()) {
          cell.classList.add('today');
        }

        if (selectedDate &&
            selectedDate.getFullYear() === year &&
            selectedDate.getMonth() === month &&
            selectedDate.getDate() === day) {
          cell.classList.add('selected');
        }

        calendarGrid.appendChild(cell);
      }
    }

    function selectDate(year, month, day) {
      selectedDate = new Date(year, month, day);
      selectedTime = null;

      // Re-render to update selected state
      renderCalendar(year, month);

      // Show time slots
      if (timeSlots && selectedDateDisplay && timeSlotsGrid) {
        timeSlots.style.display = 'block';
        const dateStr = selectedDate.toLocaleDateString('en-US', {
          weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
        });
        selectedDateDisplay.textContent = dateStr;

        // Generate time slots with some randomly unavailable
        timeSlotsGrid.innerHTML = '';
        const seed = day + month;
        availableTimes.forEach((time, idx) => {
          const slot = document.createElement('div');
          slot.className = 'time-slot';
          slot.textContent = time;

          // Simulate some slots being taken (deterministic based on date)
          if ((seed + idx) % 5 === 0) {
            slot.classList.add('unavailable');
            slot.title = 'This slot is already booked';
          } else {
            slot.addEventListener('click', () => selectTimeSlot(slot, time));
          }
          timeSlotsGrid.appendChild(slot);
        });

        if (continueBooking) {
          continueBooking.disabled = true;
        }
      }
    }

    function selectTimeSlot(element, time) {
      selectedTime = time;
      timeSlotsGrid.querySelectorAll('.time-slot').forEach(s => s.classList.remove('selected'));
      element.classList.add('selected');

      if (continueBooking) {
        continueBooking.disabled = false;
      }

      updateBookingSummary();
    }

    function updateBookingSummary() {
      const summary = document.getElementById('bookingSummary');
      const summaryLesson = document.getElementById('summaryLesson');
      const summaryDate = document.getElementById('summaryDate');
      const summaryTime = document.getElementById('summaryTime');
      const lessonType = document.getElementById('lessonType');

      if (summary && selectedDate && selectedTime) {
        summary.style.display = 'block';
        if (summaryLesson && lessonType) {
          summaryLesson.textContent = lessonType.options[lessonType.selectedIndex].text;
        }
        if (summaryDate) {
          summaryDate.textContent = selectedDate.toLocaleDateString('en-US', {
            weekday: 'short', month: 'long', day: 'numeric', year: 'numeric'
          });
        }
        if (summaryTime) {
          summaryTime.textContent = selectedTime;
        }
      }
    }

    // Navigation
    if (prevMonthBtn) {
      prevMonthBtn.addEventListener('click', () => {
        const today = new Date();
        // Don't go before current month
        if (currentYear > today.getFullYear() ||
           (currentYear === today.getFullYear() && currentMonth > today.getMonth())) {
          currentMonth--;
          if (currentMonth < 0) {
            currentMonth = 11;
            currentYear--;
          }
          renderCalendar(currentYear, currentMonth);
        }
      });
    }

    if (nextMonthBtn) {
      nextMonthBtn.addEventListener('click', () => {
        currentMonth++;
        if (currentMonth > 11) {
          currentMonth = 0;
          currentYear++;
        }
        renderCalendar(currentYear, currentMonth);
      });
    }

    // Continue to booking form
    if (continueBooking) {
      continueBooking.addEventListener('click', () => {
        if (selectedDate && selectedTime) {
          openBookingModal();
        }
      });
    }

    // Initial render
    renderCalendar(currentYear, currentMonth);
  }

  // ── Booking Modal ──────────────────────────────────────────
  const bookingModal = document.getElementById('bookingModal');
  const closeModalBtn = document.getElementById('closeModal');
  const bookingForm = document.getElementById('bookingForm');
  const bookingSuccess = document.getElementById('bookingSuccess');

  function openBookingModal() {
    if (!bookingModal) return;

    const lessonType = document.getElementById('lessonType');
    const modalLesson = document.getElementById('modalLesson');
    const modalDate = document.getElementById('modalDate');
    const modalTime = document.getElementById('modalTime');
    const summaryDate = document.getElementById('summaryDate');
    const summaryTime = document.getElementById('summaryTime');

    if (modalLesson && lessonType) {
      modalLesson.textContent = lessonType.options[lessonType.selectedIndex].text;
    }
    if (modalDate && summaryDate) {
      modalDate.textContent = summaryDate.textContent;
    }
    if (modalTime && summaryTime) {
      modalTime.textContent = summaryTime.textContent;
    }

    bookingModal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    if (bookingModal) {
      bookingModal.classList.remove('active');
      document.body.style.overflow = '';
    }
  }

  if (closeModalBtn) {
    closeModalBtn.addEventListener('click', closeModal);
  }

  if (bookingModal) {
    bookingModal.addEventListener('click', (e) => {
      if (e.target === bookingModal) closeModal();
    });
  }

  // Handle booking form submission
  if (bookingForm) {
    bookingForm.addEventListener('submit', (e) => {
      e.preventDefault();
      // In a real application, this would send data to a server
      bookingForm.style.display = 'none';
      if (bookingSuccess) {
        bookingSuccess.classList.add('show');
      }
    });
  }

  // ── Contact Form ───────────────────────────────────────────
  const contactForm = document.getElementById('contactForm');
  const contactSuccess = document.getElementById('contactSuccess');

  if (contactForm) {
    contactForm.addEventListener('submit', (e) => {
      e.preventDefault();
      // In a real application, this would send data to a server
      contactForm.style.display = 'none';
      if (contactSuccess) {
        contactSuccess.classList.add('show');
      }
    });
  }

  // ── Keyboard Navigation ────────────────────────────────────
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeModal();
      // Close mobile nav
      if (navLinks && navLinks.classList.contains('active')) {
        navLinks.classList.remove('active');
        if (hamburger) {
          hamburger.classList.remove('active');
          hamburger.setAttribute('aria-expanded', 'false');
        }
      }
    }
  });

  // ── AjayaDesign Fingerprint (hidden) ───────────────────────
  // This website is the intellectual property of AjayaDesign.
  // Built for demonstration purposes only. Unauthorized reproduction prohibited.
  // AjayaDesign-Demo-Verification: AD-ZTP-2026-DEMO-JS
  Object.defineProperty(window, '__ajayaDesign', {
    value: Object.freeze({
      property: 'AjayaDesign',
      type: 'demo',
      id: 'AD-ZTP-2026',
      notice: 'This website is the intellectual property of AjayaDesign and is for demonstration purposes only.'
    }),
    writable: false,
    configurable: false
  });
});
