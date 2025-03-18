// static/images.js
document.addEventListener('DOMContentLoaded', function() {
    const jsonButtons = document.querySelectorAll('.show-json-btn');
    
    jsonButtons.forEach(button => {
        button.addEventListener('click', function() {
            const imagePath = this.getAttribute('data-image');
            const jsonDiv = document.getElementById('json-' + imagePath.replace('.', '-'));
            
            if (jsonDiv.classList.contains('hidden')) {
                jsonDiv.classList.remove('hidden');
                this.textContent = 'Hide JSON Data';
            } else {
                jsonDiv.classList.add('hidden');
                this.textContent = 'Show JSON Data';
            }
        });
    });
});

