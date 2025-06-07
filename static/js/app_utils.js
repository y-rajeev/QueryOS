document.addEventListener('DOMContentLoaded', function() {
    // Function to show the loading overlay
    window.showLoading = function() {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex'; // Use flex to center spinner
        }
    };

    // Function to hide the loading overlay
    window.hideLoading = function() {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
    };

    // Hide loading overlay when the page finishes loading (in case it was shown before DOMContentLoaded)
    window.hideLoading();
});

// Show loading when navigating away (e.g., form submission, link click)
window.addEventListener('beforeunload', function() {
    window.showLoading();
}); 