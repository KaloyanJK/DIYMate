(function () {
    var modal = document.getElementById('app-loading-modal');
    var messageNode = document.getElementById('app-loading-modal-message');

    if (!modal || !messageNode) {
        return;
    }

    function showModal(message) {
        messageNode.textContent = message || 'Generating drawing...';
        modal.hidden = false;
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('modal-open');
    }

    function hideModal() {
        modal.hidden = true;
        modal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('modal-open');
    }

    window.DIYMateLoadingModal = {
        show: showModal,
        hide: hideModal
    };

    document.addEventListener('submit', function (event) {
        var form = event.target.closest('form.js-ai-modal-form');
        if (!form) {
            return;
        }

        var message = form.getAttribute('data-loading-message') || 'Generating drawing...';
        showModal(message);

        var buttons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
        buttons.forEach(function (button) {
            button.disabled = true;
        });
    });
})();

(function () {
    var storageKey = 'diymate-theme';
    var root = document.documentElement;
    var body = document.body;
    var toggle = document.getElementById('themeToggle');
    var icon = document.getElementById('themeIcon');

    if (!toggle || !icon) {
        return;
    }

    function applyTheme(theme) {
        var isLight = theme === 'light';
        body.classList.toggle('light-mode', isLight);
        root.setAttribute('data-bs-theme', isLight ? 'light' : 'dark');
        icon.textContent = isLight ? '☀' : '🌙';
        toggle.setAttribute('aria-label', isLight ? 'Switch to dark mode' : 'Switch to light mode');
    }

    var savedTheme = localStorage.getItem(storageKey);
    applyTheme(savedTheme === 'light' ? 'light' : 'dark');

    toggle.addEventListener('click', function () {
        var nextTheme = body.classList.contains('light-mode') ? 'dark' : 'light';
        localStorage.setItem(storageKey, nextTheme);
        applyTheme(nextTheme);
    });
})();

(function () {
    var navToggle = document.getElementById('navToggle');
    var navLinks = document.getElementById('primaryNavLinks');
    if (!navToggle || !navLinks) {
        return;
    }

    var mobileMediaQuery = window.matchMedia('(max-width: 900px)');

    function closeMenu() {
        navLinks.classList.remove('open');
        navToggle.setAttribute('aria-expanded', 'false');
        navToggle.setAttribute('aria-label', 'Open navigation menu');
        document.body.classList.remove('nav-open');
    }

    function openMenu() {
        navLinks.classList.add('open');
        navToggle.setAttribute('aria-expanded', 'true');
        navToggle.setAttribute('aria-label', 'Close navigation menu');
        document.body.classList.add('nav-open');
    }

    navToggle.addEventListener('click', function () {
        if (navLinks.classList.contains('open')) {
            closeMenu();
        } else {
            openMenu();
        }
    });

    navLinks.addEventListener('click', function (event) {
        if (!mobileMediaQuery.matches) {
            return;
        }

        var clickedLink = event.target.closest('a');
        if (clickedLink) {
            closeMenu();
        }
    });

    mobileMediaQuery.addEventListener('change', function (event) {
        if (!event.matches) {
            closeMenu();
        }
    });
})();
