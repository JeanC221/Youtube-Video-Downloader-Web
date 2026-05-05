const API_BASE = import.meta.env.VITE_API_URL || '';

// DOM Elements
const form = document.getElementById('download-form');
const submitBtn = document.getElementById('submit-btn');
const urlInput = document.getElementById('url');

const feedbackContainer = document.getElementById('feedback-container');
const stateValidating = document.getElementById('state-validating');
const stateDownloading = document.getElementById('state-downloading');
const stateSuccess = document.getElementById('state-success');
const stateError = document.getElementById('state-error');
const errorMessage = document.getElementById('error-message');

const btnReset = document.getElementById('btn-reset');
const btnResetError = document.getElementById('btn-reset-error');

const helpBtn = document.getElementById('help-btn');
const helpModal = document.getElementById('help-modal');
const closeModalBtn = document.getElementById('close-modal-btn');
const closeModalBtnBottom = document.getElementById('close-modal-btn-bottom');
const helpModalBackdrop = document.getElementById('help-modal-backdrop');

const folderSelectionContainer = document.getElementById('folder-selection-container');
const selectFolderBtn = document.getElementById('select-folder-btn');
const folderNameDisplay = document.getElementById('folder-name-display');

// Global directory handle
let directoryHandle = null;

// Hide folder selection if not supported by the browser (e.g. Safari)
if (!('showDirectoryPicker' in window)) {
  folderSelectionContainer.style.display = 'none';
}

// --- MODAL LOGIC ---
function openModal() {
  helpModal.classList.remove('hidden');
}

function closeModal() {
  helpModal.classList.add('hidden');
}

helpBtn.addEventListener('click', openModal);
closeModalBtn.addEventListener('click', closeModal);
closeModalBtnBottom.addEventListener('click', closeModal);
helpModalBackdrop.addEventListener('click', closeModal);

// --- FOLDER PICKER LOGIC ---
selectFolderBtn.addEventListener('click', async () => {
  if ('showDirectoryPicker' in window) {
    try {
      directoryHandle = await window.showDirectoryPicker();
      folderNameDisplay.textContent = `Guardar en: ${directoryHandle.name}`;
      folderNameDisplay.classList.remove('text-slate-600', 'dark:text-slate-400');
      folderNameDisplay.classList.add('text-indigo-400', 'font-semibold');
    } catch (err) {
      console.log('Selección de carpeta cancelada');
    }
  }
});

// --- STATE MANAGEMENT ---
function showState(stateName) {
  // Hide all first
  [stateValidating, stateDownloading, stateSuccess, stateError].forEach(el => el.classList.add('hidden'));
  feedbackContainer.classList.remove('hidden');
  
  if (stateName === 'validating') stateValidating.classList.remove('hidden');
  if (stateName === 'downloading') stateDownloading.classList.remove('hidden');
  if (stateName === 'success') stateSuccess.classList.remove('hidden');
  if (stateName === 'error') stateError.classList.remove('hidden');
}

function hideFeedback() {
  feedbackContainer.classList.add('hidden');
}

function resetForm() {
  form.reset();
  hideFeedback();
  submitBtn.disabled = false;
  submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
  urlInput.focus();
}

btnReset.addEventListener('click', resetForm);
btnResetError.addEventListener('click', resetForm);

// --- DOWNLOAD LOGIC ---
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const url = urlInput.value.trim();
  const format = document.querySelector('input[name="format"]:checked').value;
  if (!url) return;

  submitBtn.disabled = true;
  submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
  showState('validating');

  const apiUrl = `${API_BASE}/api/download?url=${encodeURIComponent(url)}&type=${format}`;

  try {
    const response = await fetch(apiUrl);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'No se pudo procesar la descarga.');
    }

    const data = await response.json();
    const streamUrl = data.url;
    let filename = data.filename || 'descarga.mp4';

    showState('downloading');

    // Descargar el archivo real desde Cobalt
    const fileResponse = await fetch(streamUrl);
    if (!fileResponse.ok) {
      throw new Error('El enlace de descarga ha caducado o es inválido.');
    }

    const disposition = fileResponse.headers.get('content-disposition');
    if (disposition && disposition.indexOf('filename=') !== -1) {
        // Regex para extraer el nombre de archivo (con o sin comillas, manejando codificación UTF-8 básica)
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
        if (matches != null && matches[1]) {
            filename = matches[1].replace(/['"]/g, '');
        }
    }

    if (directoryHandle) {
      // Usar la carpeta previamente elegida
      const fileHandle = await directoryHandle.getFileHandle(filename, { create: true });
      const writable = await fileHandle.createWritable();
      await fileResponse.body.pipeTo(writable);
    } else if ('showSaveFilePicker' in window) {
      // Fallback nativo: Guardar como...
      try {
        const fileHandle = await window.showSaveFilePicker({
          suggestedName: filename,
          types: [{
            description: format === 'video' ? 'Video File' : 'Audio File',
            accept: {
              'video/*': ['.mp4', '.mkv', '.webm'],
              'audio/*': ['.mp3', '.m4a', '.wav']
            }
          }]
        });
        const writable = await fileHandle.createWritable();
        await fileResponse.body.pipeTo(writable);
      } catch (cancelError) {
        // Canceló el diálogo
        resetForm();
        return;
      }
    } else {
      // Fallback para Safari y navegadores antiguos
      const blob = await fileResponse.blob();
      const objectUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(objectUrl);
    }

    showState('success');

  } catch (err) {
    console.error(err);
    errorMessage.textContent = err.message || 'Error de conexión con el servidor.';
    showState('error');
  }
});
