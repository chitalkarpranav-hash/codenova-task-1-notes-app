const form = document.querySelector('#note-form');
const titleInput = document.querySelector('#note-title');
const contentInput = document.querySelector('#note-content');
const searchInput = document.querySelector('#search-input');
const notesGrid = document.querySelector('#notes-grid');
const emptyState = document.querySelector('#empty-state');
const noteCount = document.querySelector('#note-count');
const saveButton = document.querySelector('#save-button');
const cancelEdit = document.querySelector('#cancel-edit');
const formKicker = document.querySelector('#form-kicker');
const formTitle = document.querySelector('#form-title');
const characterCount = document.querySelector('#character-count');
const toast = document.querySelector('#toast');
const todayLabel = document.querySelector('#today-label');
const libraryStatus = document.querySelector('#library-status');

let notes = [];
let editingId = null;
let searchTimer;
let toastTimer;
const palettes = [
  ['#e9e3ff', '#c8c6ff'], ['#d8f7e5', '#b7e9dc'], ['#ffe9cf', '#ffc8d7'],
  ['#cfeaff', '#c8d6ff'], ['#fff5b9', '#ffe0b5'], ['#ffdceb', '#e2c9ff']
];

todayLabel.textContent = new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric' }).format(new Date());

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
  } catch {
    throw new Error('Unable to reach the server. Check that it is running and try again.');
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || 'Something went wrong. Please try again.');
  return payload;
}

function showToast(message, isError = false) {
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.toggle('error', isError);
  toast.classList.add('show');
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3600);
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(new Date(value));
}

function escapeHtml(text) {
  const node = document.createElement('div');
  node.textContent = text;
  return node.innerHTML;
}

function renderNotes() {
  notesGrid.innerHTML = notes.map((note, index) => {
    const [colorA, colorB] = palettes[(note.id + index) % palettes.length];
    return `
    <article class="note-card" style="--card-a:${colorA};--card-b:${colorB};animation-delay:${index * 55}ms">
      <div>
        <p class="eyebrow">NOTE</p>
        <h3>${escapeHtml(note.title)}</h3>
        <p>${escapeHtml(note.content)}</p>
      </div>
      <footer class="card-footer">
        <time datetime="${note.updated_at}">Updated ${formatDate(note.updated_at)}</time>
        <div class="actions">
          <button class="icon-button" type="button" data-action="edit" data-id="${note.id}">Edit</button>
          <button class="icon-button delete" type="button" data-action="delete" data-id="${note.id}">Delete</button>
        </div>
      </footer>
    </article>`;
  }).join('');
  noteCount.textContent = notes.length;
  libraryStatus.textContent = notes.length ? `${notes.length} idea${notes.length === 1 ? '' : 's'} in your nest` : 'Your ideas are safely saved';
  emptyState.classList.toggle('hidden', notes.length > 0);
  notesGrid.classList.toggle('hidden', notes.length === 0);
}

async function loadNotes() {
  const query = encodeURIComponent(searchInput.value.trim());
  try {
    const data = await api(`/api/notes?q=${query}`);
    notes = data.notes;
    renderNotes();
  } catch (error) {
    showToast(error.message, true);
  }
}

function resetForm() {
  editingId = null;
  form.reset();
  formKicker.textContent = 'NEW NOTE';
  formTitle.textContent = "What's on your mind?";
  saveButton.innerHTML = 'Save note <span aria-hidden="true">↗</span>';
  cancelEdit.classList.add('hidden');
  characterCount.textContent = '0 / 10,000';
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  const title = titleInput.value.trim();
  const content = contentInput.value.trim();
  if (!title || !content) return showToast('Add both a title and some note content first.', true);
  saveButton.disabled = true;
  saveButton.textContent = 'Saving...';
  try {
    const method = editingId ? 'PUT' : 'POST';
    const path = editingId ? `/api/notes/${editingId}` : '/api/notes';
    await api(path, { method, body: JSON.stringify({ title, content }) });
    const action = editingId ? 'updated' : 'saved';
    resetForm();
    await loadNotes();
    showToast(`Note ${action} successfully.`);
  } catch (error) {
    showToast(error.message, true);
    saveButton.innerHTML = editingId
      ? 'Update note <span aria-hidden="true">↗</span>'
      : 'Save note <span aria-hidden="true">↗</span>';
  } finally {
    saveButton.disabled = false;
  }
});

notesGrid.addEventListener('click', async event => {
  const button = event.target.closest('button[data-action]');
  if (!button) return;
  const note = notes.find(item => item.id === Number(button.dataset.id));
  if (!note) return;
  if (button.dataset.action === 'edit') {
    editingId = note.id;
    titleInput.value = note.title;
    contentInput.value = note.content;
    characterCount.textContent = `${note.content.length} / 10,000`;
    formKicker.textContent = 'EDITING NOTE';
    formTitle.textContent = 'Refine your thought';
    saveButton.innerHTML = 'Update note <span aria-hidden="true">↗</span>';
    cancelEdit.classList.remove('hidden');
    titleInput.focus();
    return;
  }
  if (!window.confirm(`Delete “${note.title}”? This cannot be undone.`)) return;
  try {
    await api(`/api/notes/${note.id}`, { method: 'DELETE' });
    await loadNotes();
    showToast('Note deleted.');
  } catch (error) {
    showToast(error.message, true);
  }
});

searchInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadNotes, 180);
});
contentInput.addEventListener('input', () => {
  characterCount.textContent = `${contentInput.value.length.toLocaleString()} / 10,000`;
});
cancelEdit.addEventListener('click', resetForm);
loadNotes();

