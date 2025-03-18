// static/logs.js
document.addEventListener('DOMContentLoaded', function() {
    const logContent = document.getElementById('log-content');
    const refreshBtn = document.getElementById('refresh-logs');
    const autoRefreshBtn = document.getElementById('auto-refresh');
    const clearLogsBtn = document.getElementById('clear-logs');
    
    let autoRefreshInterval = null;
    let autoRefreshEnabled = false;
    
    // Function to fetch logs
    function fetchLogs() {
        fetch('/api/logs')
            .then(response => response.json())
            .then(data => {
                logContent.textContent = data.logs.join('\n');
                // Auto-scroll to bottom
                logContent.scrollTop = logContent.scrollHeight;
            })
            .catch(error => {
                console.error('Error fetching logs:', error);
            });
    }
    
    // Initial fetch
    fetchLogs();
    
    // Manual refresh
    refreshBtn.addEventListener('click', fetchLogs);
    
    // Toggle auto refresh
    autoRefreshBtn.addEventListener('click', function() {
        autoRefreshEnabled = !autoRefreshEnabled;
        
        if (autoRefreshEnabled) {
            autoRefreshBtn.textContent = 'Auto Refresh: ON';
            autoRefreshInterval = setInterval(fetchLogs, 2000);
        } else {
            autoRefreshBtn.textContent = 'Auto Refresh: OFF';
            clearInterval(autoRefreshInterval);
        }
    });
    
    // Clear logs view
    clearLogsBtn.addEventListener('click', function() {
        logContent.textContent = '';
    });
});
