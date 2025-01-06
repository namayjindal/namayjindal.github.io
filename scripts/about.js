document.addEventListener('DOMContentLoaded', () => {
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
});

// VSCO Embed
function loadVSCOEmbed() {
    // Replace this with your actual VSCO embed code
    document.getElementById('vsco-embed').innerHTML = '<iframe src="https://vsco.co/embed/collection/1" style="width: 100%; height: 600px;" frameborder="0"></iframe>';
}

// Spotify Embed
function loadSpotifyEmbed() {
    // You'll need to regularly update this with your current top track
    const spotifyPlaylistId = '2yWXBmpJWZzLiPzpNwnNDJ'; // Example track ID
    const embedCode = `<iframe src="https://open.spotify.com/embed/playlist/${spotifyPlaylistId}" width="800" height="600" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>`;
    document.getElementById('spotify-embed').innerHTML = embedCode;
}

// Call these functions when the page loads
window.onload = function() {
    // loadVSCOEmbed();
    loadSpotifyEmbed();
};

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