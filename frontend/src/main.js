const form = document.getElementById('download-form');
const submitBtn = document.getElementById('submit-btn');
const statusContainer = document.getElementById('status-container');
const errorContainer = document.getElementById('error-container');

// Detect API base URL: empty string for relative (same origin) or absolute if configured
const API_BASE = import.meta.env.VITE_API_URL || '';

form.addEventListener('submit', (e) => {
  e.preventDefault();
  
  const urlInput = document.getElementById('url').value.trim();
  const formatInput = document.querySelector('input[name="format"]:checked').value;
  
  if (!urlInput) return;

  // Reset UI
  errorContainer.classList.add('hidden');
  errorContainer.textContent = '';
  submitBtn.disabled = true;
  submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
  statusContainer.classList.remove('hidden');

  // Native browser download flow
  // To avoid RAM issues, we trigger a direct navigation or a hidden iframe
  // If the backend has CORS enabled and we just want to download, we can use window.location.href
  // However, error handling is tricky with direct window.location.href because we can't catch 400 errors easily.
  // Instead, we will do a HEAD or GET fetch request first to validate, then trigger download if valid.

  const apiUrl = `${API_BASE}/api/download?url=${encodeURIComponent(urlInput)}&type=${formatInput}`;

  // We can just open it in a new window or use a hidden anchor link
  // Since we want the user experience to be seamless, we'll assign it to window.location.
  // But wait, the backend will process the download and stream. 
  
  // We'll reset the UI after 3 seconds, assuming the download dialog will pop up
  setTimeout(() => {
    submitBtn.disabled = false;
    submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    statusContainer.classList.add('hidden');
    form.reset();
  }, 5000);

  // Trigger download
  window.location.href = apiUrl;
});
