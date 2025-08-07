// Minimal Admin JavaScript - No styling, just basic functionality

document.addEventListener('DOMContentLoaded', function() {
    // Only ensure links are properly styled - no fancy effects
    const adminLinks = document.querySelectorAll('.field-utterance_count a, .field-conversation_link a');
    adminLinks.forEach(function(link) {
        link.style.textDecoration = 'underline';
        link.style.color = getComputedStyle(document.documentElement).getPropertyValue('--link-fg');
    });
}); 