document.addEventListener("DOMContentLoaded", () => {
    // Typing animation (unchanged)
    const element = document.getElementById('typing-animation');
    const text = "hi, i'm namay ";
    let index = 0;
    let isDeleting = false;
    const typingSpeed = 150;
    const deletingSpeed = 100;
    const delay = 2000; // 2 seconds delay at the end of typing

    function type() {
        const currentText = text.slice(0, index);
        element.textContent = currentText + '\u00A0'.repeat(text.length - currentText.length);

        if (!isDeleting && index < text.length) {
            index++;
            setTimeout(type, typingSpeed);
        } else if (isDeleting && index > 0) {
            index--;
            setTimeout(type, deletingSpeed);
        } else if (index === text.length) {
            isDeleting = true;
            setTimeout(type, delay);
        } else if (index === 0) {
            isDeleting = false;
            setTimeout(type, typingSpeed);
        }
    }

    type();

    // Dot animation (modified)
    const dot = document.querySelector('.dot');
    let isAnimating = false;
    let animationId;
    let x, y, dx, dy;

    // Define color array (replace with your desired hex codes)
    const colors = ['#FFB726', '#E63946', '#8AFAFF', '#DAFF7D', '#02CDAE'];
    let currentColorIndex = 0;

    // Speed control
    const speed = 4; // Constant speed
    const clickRadius = 150; // Radius around the ball for click detection

    function initPosition() {
        const rect = dot.getBoundingClientRect();
        x = rect.left + rect.width / 2;
        y = rect.top + rect.height / 2;
        const angle = Math.random() * 2 * Math.PI;
        dx = Math.cos(angle) * speed;
        dy = Math.sin(angle) * speed;
    }

    function animate() {
        if (!isAnimating) return;

        x += dx;
        y += dy;

        // Bounce off edges and change color
        if (x <= 10 || x >= window.innerWidth - 10) {
            dx = -dx;
            x = Math.max(10, Math.min(x, window.innerWidth - 10));
            changeColor();
        }
        if (y <= 10 || y >= window.innerHeight - 10) {
            dy = -dy;
            y = Math.max(10, Math.min(y, window.innerHeight - 10));
            changeColor();
        }

        dot.style.left = `${x - 10}px`;
        dot.style.top = `${y - 10}px`;

        animationId = requestAnimationFrame(animate);
    }

    function changeColor() {
        currentColorIndex = (currentColorIndex + 1) % colors.length;
        dot.style.backgroundColor = colors[currentColorIndex];
    }

    function startAnimation() {
        if (!isAnimating) {
            isAnimating = true;
            initPosition();
            dot.style.animation = 'none';
            dot.style.position = 'fixed';
            animate();
        }
    }

    function handleResize() {
        if (isAnimating) {
            x = Math.min(x, window.innerWidth - 10);
            y = Math.min(y, window.innerHeight - 10);
        }
    }

    function changeDirection() {
        const angle = Math.random() * 2 * Math.PI;
        dx = Math.cos(angle) * speed;
        dy = Math.sin(angle) * speed;
        changeColor();
    }

    dot.addEventListener('mouseenter', startAnimation);

    window.addEventListener('click', (event) => {
        if (isAnimating) {
            const dx = event.clientX - x;
            const dy = event.clientY - y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance <= clickRadius) {
                changeDirection();
            }
        }
    });
    
    window.addEventListener('resize', handleResize);

    const cursor = document.querySelector('.custom-cursor');
    const body = document.body;

    // Add the custom-cursor-page class to the body
    body.classList.add('custom-cursor-page');

    // Add the animated class to start color changing
    cursor.classList.add('animated');

    // Update cursor position
    document.addEventListener('mousemove', (e) => {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
    });

    const hamburger = document.querySelector('.hamburger-menu');
    const navLinks = document.querySelector('.nav-links');

    hamburger.addEventListener('click', () => {
        navLinks.classList.toggle('active');
    });

    // Close menu when a link is clicked
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', () => {
            navLinks.classList.remove('active');
        });
    });
    
});