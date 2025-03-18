// static/config.js
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('config-form');
    const message = document.getElementById('message');
    const countdown = document.getElementById('countdown');
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        
        fetch('/config', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            message.classList.remove('hidden', 'success', 'error');
            if (data.success) {
                message.classList.add('success');
                message.textContent = data.message;
                
                // Show countdown for reload
                let secondsLeft = 5;
                countdown.classList.remove('hidden');
                countdown.textContent = `Page will reload in ${secondsLeft} seconds...`;
                
                const interval = setInterval(() => {
                    secondsLeft--;
                    countdown.textContent = `Page will reload in ${secondsLeft} seconds...`;
                    
                    if (secondsLeft <= 0) {
                        clearInterval(interval);
                        window.location.reload();
                    }
                }, 1000);
            } else {
                message.classList.add('error');
                message.textContent = data.message;
            }
        })
        .catch(error => {
            message.classList.remove('hidden');
            message.classList.add('error');
            message.textContent = 'An error occurred. Service might be restarting.';
            
            // Try to reload page after a delay
            setTimeout(() => {
                window.location.reload();
            }, 3000);
        });
    });
});
