// Minimal Admin JavaScript - Functional Only

document.addEventListener('DOMContentLoaded', function() {
    // Ensure proper text overflow handling
    const tableCells = document.querySelectorAll('#result_list td, #changelist table td');
    tableCells.forEach(function(cell) {
        if (cell.textContent.length > 50) {
            cell.title = cell.textContent; // Show full text on hover
        }
    });
    
    // Ensure links are properly styled
    const adminLinks = document.querySelectorAll('.field-utterance_count a, .field-conversation_link a');
    adminLinks.forEach(function(link) {
        link.style.textDecoration = 'underline';
        link.style.color = getComputedStyle(document.documentElement).getPropertyValue('--link-fg');
    });
    
    // Simple form validation feedback
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function() {
            const submitButton = this.querySelector('input[type="submit"], button[type="submit"]');
            if (submitButton && !submitButton.disabled) {
                submitButton.disabled = true;
                if (submitButton.type === 'submit') {
                    submitButton.value = 'Saving...';
                } else {
                    submitButton.textContent = 'Saving...';
                }
            }
        });
    });
}); 