// Custom Admin JavaScript for Humanlike Chatbot

document.addEventListener('DOMContentLoaded', function() {
    // Add custom styling classes to admin elements
    const adminInterface = document.querySelector('#container');
    if (adminInterface) {
        adminInterface.classList.add('admin-interface');
    }
    
    // Enhance table styling
    const tables = document.querySelectorAll('#result_list, #changelist table');
    tables.forEach(function(table) {
        table.classList.add('admin-table');
    });
    
    // Add hover effects to table rows
    const tableRows = document.querySelectorAll('#result_list tbody tr, #changelist table tbody tr');
    tableRows.forEach(function(row) {
        row.addEventListener('mouseenter', function() {
            this.style.transition = 'background-color 0.2s ease';
        });
    });
    
    // Enhance form styling
    const formRows = document.querySelectorAll('.form-row');
    formRows.forEach(function(row) {
        row.classList.add('enhanced-form-row');
    });
    
    // Add focus effects to form inputs
    const inputs = document.querySelectorAll('input, textarea, select');
    inputs.forEach(function(input) {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });
    });
    
    // Enhance pagination styling
    const pagination = document.querySelector('.paginator');
    if (pagination) {
        pagination.classList.add('enhanced-pagination');
    }
    
    // Add loading states for better UX
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function() {
            const submitButton = this.querySelector('input[type="submit"], button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.value = 'Saving...';
                submitButton.textContent = 'Saving...';
            }
        });
    });
    
    // Enhance message previews
    const messagePreviews = document.querySelectorAll('.message-preview');
    messagePreviews.forEach(function(preview) {
        preview.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-1px)';
        });
        
        preview.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // Add responsive behavior
    function handleResize() {
        const isMobile = window.innerWidth <= 768;
        const adminContainer = document.querySelector('#container');
        
        if (adminContainer) {
            if (isMobile) {
                adminContainer.classList.add('mobile-view');
            } else {
                adminContainer.classList.remove('mobile-view');
            }
        }
    }
    
    // Listen for window resize
    window.addEventListener('resize', handleResize);
    handleResize(); // Initial call
    
    console.log('Custom admin JavaScript loaded successfully');
}); 