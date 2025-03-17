document.addEventListener('DOMContentLoaded', function() {
    // Navbar scroll effect
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', () => {
        navbar.classList.toggle('scrolled', window.scrollY > 50);
    });

    // Auto-hide alerts
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => alert.remove(), 3000);
    });

    // Flip card functionality
    const flipCards = document.querySelectorAll('.flip-card');
    
    flipCards.forEach(card => {
        const inner = card.querySelector('.flip-card-inner');
        const numberElement = card.querySelector('.stat-number');

        // Format numbers
        if (numberElement) {
            const number = parseInt(numberElement.textContent);
            if (!isNaN(number)) {
                numberElement.textContent = number.toLocaleString();
            }
        }

        // Touch support
        card.addEventListener('touchstart', (e) => {
            e.preventDefault();
            inner.style.transform = 
                inner.style.transform === 'rotateY(180deg)' ? 
                'rotateY(0deg)' : 'rotateY(180deg)';
        });
    });
});