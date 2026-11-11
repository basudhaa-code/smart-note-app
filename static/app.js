/**
 * SmartNote AI - Client Application Logic
 */

// Application State
const state = {
  currentDocId: null,
  currentDoc: null,
  activeTab: 'tab-upload',
  practiceMode: 'quiz',
  topicsView: 'cards',
  topicsFilter: 'all',
  
  // Practice state
  quizAnswers: {}, // { questionId: selectedIndex }
  flashcards: [],
  flashcardIndex: 0,
  flashcardFlipped: false,
  masteredCards: new Set(),
  
  // Chat state
  chatHistory: [],
  isGenerating: false,
  activeCitation: null
};

// Initialize Application on DOM Ready
document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  setupKeyboardShortcuts();
  setupSuggestedQuestions();
  await checkSystemStatus();
  lucide.createIcons();
});

// -----------------------------------------------------------------------------
// EVENT LISTENERS & SHORTCUTS
// -----------------------------------------------------------------------------
function setupEventListeners() {
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('pdfFileInput');

  if (dropZone && fileInput) {
    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        uploadPdfFile(e.target.files[0]);
      }
    });

    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropZone.classList.add('border-brand-500', 'bg-slate-900/90');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-brand-500', 'bg-slate-900/90');
      }, false);
    });

    dropZone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files && files[0]) {
        uploadPdfFile(files[0]);
      }
    });
  }
}

function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Only apply in practice tab and flashcards mode
    if (state.activeTab === 'tab-practice' && state.practiceMode === 'flashcards') {
      if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
        e.preventDefault();
        flipFlashcard();
      } else if (e.code === 'ArrowRight') {
        nextFlashcard();
      } else if (e.code === 'ArrowLeft') {
        prevFlashcard();
      }
    }
  });
}

// -----------------------------------------------------------------------------
// NAVIGATION & TABS
// -----------------------------------------------------------------------------
function switchTab(tabId) {
  state.activeTab = tabId;

  // Update nav buttons
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('bg-slate-800', 'text-white', 'shadow-sm');
    btn.classList.add('text-slate-400');
  });

  const activeBtn = document.getElementById(`nav-${tabId}`);
  if (activeBtn) {
    activeBtn.classList.remove('text-slate-400');
    activeBtn.classList.add('bg-slate-800', 'text-white', 'shadow-sm');
  }

  // Hide all contents
  document.querySelectorAll('.tab-content').forEach(section => {
    section.classList.add('hidden');
    section.classList.remove('block');
  });

  // Show active tab
  const activeSection = document.getElementById(tabId);
  if (activeSection) {
    activeSection.classList.remove('hidden');
    activeSection.classList.add('block');
  }

  // Refresh icons
  lucide.createIcons();
}

// -----------------------------------------------------------------------------
// SYSTEM STATUS & API KEY CONFIGURATION
// -----------------------------------------------------------------------------
async function checkSystemStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    
    const pill = document.getElementById('apiStatusPill');
    const pillText = document.getElementById('apiStatusText');
    
    if (data.gemini_configured) {
      pill.className = "flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition cursor-pointer";
      pillText.textContent = `${data.active_model} Connected`;
    } else {
      pill.className = "flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition cursor-pointer";
      pillText.textContent = "Offline / Extractive Mode";
    }

    // Populate Document Switcher Dropdown
    if (data.documents) {
      updateDocDropdown(data.documents);
    }

  } catch (err) {
    console.error("Status check failed:", err);
  }
}

function toggleDocDropdown() {
  const menu = document.getElementById('docDropdownMenu');
  if (menu) {
    menu.classList.toggle('hidden');
  }
}

function updateDocDropdown(docs) {
  const list = document.getElementById('docDropdownList');
  if (!list) return;
  const badge = document.getElementById('activeDocBadge');
  if (docs && docs.length > 0) {
    badge.classList.remove('hidden');
    if (!state.currentDocId) {
      document.getElementById('activeDocTitle').textContent = 'Select a document';
      document.getElementById('activeDocPages').textContent = '';
    }
  } else if (!state.currentDocId) {
    badge.classList.add('hidden');
  }

  list.innerHTML = '';
  if (!docs || docs.length === 0) {
    list.innerHTML = `<div class="px-3 py-2 text-xs text-slate-500">No documents uploaded yet</div>`;
    return;
  }
  docs.forEach(doc => {
    const isCurrent = doc.doc_id === state.currentDocId;
    const item = document.createElement('button');
    item.className = `w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-slate-800 transition ${isCurrent ? 'bg-brand-500/10 text-brand-300 font-semibold' : 'text-slate-300'}`;
    item.innerHTML = `
      <div class="truncate pr-2">
        <div class="truncate">${escapeHtml(doc.title)}</div>
        <div class="text-[10px] text-slate-500">${doc.total_pages} pages · ${doc.total_words ? doc.total_words.toLocaleString() + ' words' : ''}</div>
      </div>
      ${isCurrent ? '<i data-lucide="check" class="w-3.5 h-3.5 text-brand-400 shrink-0"></i>' : ''}
    `;
    item.onclick = async () => {
      document.getElementById('docDropdownMenu').classList.add('hidden');
      await loadDocument(doc.doc_id);
    };
    list.appendChild(item);
  });
  lucide.createIcons();
}

// Close document dropdown when clicking outside
document.addEventListener('click', (e) => {
  const badge = document.getElementById('activeDocBadge');
  const menu = document.getElementById('docDropdownMenu');
  if (menu && !menu.classList.contains('hidden') && badge) {
    if (!badge.contains(e.target) && !menu.contains(e.target)) {
      menu.classList.add('hidden');
    }
  }
});

function openApiKeyModal() {
  document.getElementById('apiKeyModal').classList.remove('hidden');
  document.getElementById('inputApiKey').focus();
}

function closeApiKeyModal() {
  document.getElementById('apiKeyModal').classList.add('hidden');
  document.getElementById('apiKeyStatusAlert').classList.add('hidden');
}

async function saveApiKey() {
  const input = document.getElementById('inputApiKey');
  const key = input.value.trim();
  const alertBox = document.getElementById('apiKeyStatusAlert');
  const btn = document.getElementById('btnSaveApiKey');

  if (!key) {
    showToast("Please enter an API Key", "error");
    return;
  }

  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Verifying...</span>`;
  lucide.createIcons();

  try {
    const res = await fetch('/api/config/key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: key, persist: true })
    });
    const result = await res.json();

    if (result.status === 'success') {
      alertBox.className = "text-xs p-3 rounded-lg border bg-emerald-500/10 border-emerald-500/20 text-emerald-400 block";
      alertBox.textContent = result.message;
      showToast("Gemini API connected successfully!", "success");
      setTimeout(() => {
        closeApiKeyModal();
        checkSystemStatus();
      }, 1200);
    } else {
      alertBox.className = "text-xs p-3 rounded-lg border bg-amber-500/10 border-amber-500/20 text-amber-300 block";
      alertBox.textContent = result.message || "Key saved with warnings.";
      checkSystemStatus();
    }
  } catch (err) {
    alertBox.className = "text-xs p-3 rounded-lg border bg-rose-500/10 border-rose-500/20 text-rose-300 block";
    alertBox.textContent = `Error: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="check" class="w-4 h-4"></i><span>Save & Verify Key</span>`;
    lucide.createIcons();
  }
}

// -----------------------------------------------------------------------------
// DOCUMENT UPLOADING & INGESTION
// -----------------------------------------------------------------------------
async function uploadPdfFile(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    showToast("Please select a valid PDF file", "error");
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  showToast(`Uploading and analyzing "${file.name}"...`, "info");

  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Upload failed");
    }

    const data = await res.json();
    showToast(`Parsed ${data.total_pages} pages successfully!`, "success");
    await loadDocument(data.doc_id);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadDocument(docId) {
  try {
    const res = await fetch(`/api/document/${docId}`);
    if (!res.ok) throw new Error("Document not found");
    const doc = await res.json();

    state.currentDocId = doc.doc_id;
    state.currentDoc = doc;

    // Update Topbar Badge
    const badge = document.getElementById('activeDocBadge');
    badge.classList.remove('hidden');
    document.getElementById('activeDocTitle').textContent = doc.title;
    document.getElementById('activeDocPages').textContent = `(${doc.total_pages} pages)`;

    // Update Overview Stats
    document.getElementById('docOverviewSection').classList.remove('hidden');
    document.getElementById('docDetailTitle').textContent = doc.title;
    document.getElementById('docDetailFilename').textContent = doc.filename || "Uploaded Lecture";
    document.getElementById('statTotalPages').textContent = doc.total_pages;
    document.getElementById('statTotalWords').textContent = doc.total_words.toLocaleString();
    document.getElementById('statReadingTime').textContent = `~${doc.reading_time_min} mins`;
    document.getElementById('statChunksCount').textContent = doc.pages ? `${doc.pages.length * 4}+ indexed` : '-';

    // Render Page-by-Page Accordion
    renderPagesAccordion(doc.pages || []);

    // Render Notes if existing
    if (doc.notes) {
      renderNotes(doc.notes);
    } else {
      document.getElementById('notesEmptyState').classList.remove('hidden');
      document.getElementById('renderedNotesBody').classList.add('hidden');
      const banner = document.getElementById('notesCoverageBanner');
      if (banner) banner.classList.add('hidden');
    }

    // Render Topics if existing
    if (doc.topics && doc.topics.length > 0) {
      renderTopics(doc.topics, doc.mindmap);
    } else {
      document.getElementById('topicsEmptyState').classList.remove('hidden');
      document.getElementById('topicsCardsView').classList.add('hidden');
      document.getElementById('topicsMindmapView').classList.add('hidden');
    }

    // Render Practice if existing
    if (doc.practice && (doc.practice.mcqs || doc.practice.flashcards)) {
      renderPractice(doc.practice);
    } else {
      document.getElementById('practiceEmptyState').classList.remove('hidden');
      document.getElementById('practiceQuizMode').classList.add('hidden');
      document.getElementById('practiceFlashcardsMode').classList.add('hidden');
      document.getElementById('practiceShortAnswerMode').classList.add('hidden');
    }

    lucide.createIcons();
  } catch (err) {
    showToast(`Error loading document: ${err.message}`, "error");
  }
}

function renderPagesAccordion(pages) {
  const container = document.getElementById('pagesListContainer');
  container.innerHTML = '';

  pages.forEach(p => {
    const item = document.createElement('div');
    item.className = "border border-slate-800 rounded-xl overflow-hidden bg-slate-900/40";
    item.innerHTML = `
      <button onclick="togglePageAccordion(${p.page_num})" class="w-full px-4 py-3 text-left flex items-center justify-between text-xs font-semibold text-slate-300 hover:bg-slate-800/50 transition">
        <span class="flex items-center space-x-2">
          <span class="px-2 py-0.5 rounded bg-brand-500/20 text-brand-300">Page ${p.page_num}</span>
          <span>${p.word_count} words (${p.char_count} characters)</span>
        </span>
        <i data-lucide="chevron-down" id="accordion-icon-${p.page_num}" class="w-4 h-4 transition-transform duration-200"></i>
      </button>
      <div id="accordion-body-${p.page_num}" class="hidden p-4 bg-slate-950/70 border-t border-slate-800 text-xs text-slate-300 font-mono whitespace-pre-wrap max-h-60 overflow-y-auto">
        ${escapeHtml(p.text)}
      </div>
    `;
    container.appendChild(item);
  });
}

function togglePageAccordion(pageNum) {
  const body = document.getElementById(`accordion-body-${pageNum}`);
  const icon = document.getElementById(`accordion-icon-${pageNum}`);
  if (body) {
    const isHidden = body.classList.contains('hidden');
    body.classList.toggle('hidden', !isHidden);
    if (icon) {
      icon.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
    }
  }
}

// -----------------------------------------------------------------------------
// GENERATION HANDLERS (NOTES, TOPICS, PRACTICE, GENERATE ALL)
// -----------------------------------------------------------------------------
async function generateAll() {
  if (!state.currentDocId) {
    showToast("Please upload or load a lecture PDF first", "error");
    return;
  }

  const btn = document.getElementById('btnGenerateAll');
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-5 h-5 animate-spin"></i><span>Synthesizing Full Study Suite...</span>`;
  lucide.createIcons();

  showToast("Analyzing lecture: generating notes, topics, and practice exam...", "info");

  try {
    const res = await fetch(`/api/generate-all/${state.currentDocId}`, { method: 'POST' });
    const data = await res.json();
    
    // Update active document state
    state.currentDoc.notes = data.notes;
    state.currentDoc.topics = data.topics;
    state.currentDoc.mindmap = data.mindmap;
    state.currentDoc.practice = data.practice;

    renderNotes(data.notes);
    renderTopics(data.topics, data.mindmap);
    renderPractice(data.practice);

    showToast("Lecture analysis complete! Notes, topics, and quizzes ready.", "success");
    switchTab('tab-notes');
  } catch (err) {
    showToast(`Generation failed: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="sparkles" class="w-5 h-5"></i><span>Generate All (Notes + Topics + Practice)</span>`;
    lucide.createIcons();
  }
}

async function generateNotes() {
  if (!state.currentDocId) {
    showToast("Please upload a lecture PDF first", "error");
    return;
  }

  const btn = document.getElementById('btnRegenNotes');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>Generating Notes...</span>`;
    lucide.createIcons();
  }

  showToast("Synthesizing structured notes...", "info");

  try {
    const res = await fetch(`/api/generate-notes/${state.currentDocId}`, { method: 'POST' });
    const data = await res.json();
    state.currentDoc.notes = data.notes;
    renderNotes(data.notes);
    showToast("Structured notes synthesized!", "success");
  } catch (err) {
    showToast(`Failed to generate notes: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i><span>Regenerate Notes</span>`;
      lucide.createIcons();
    }
  }
}

function renderNotes(markdownText) {
  document.getElementById('notesEmptyState').classList.add('hidden');
  const container = document.getElementById('renderedNotesBody');
  container.classList.remove('hidden');

  // Update Coverage & Status Banner
  const banner = document.getElementById('notesCoverageBanner');
  if (banner) {
    banner.classList.remove('hidden');
    const meta = (state.currentDoc && state.currentDoc.notes_meta) || {};
    const engineBadge = document.getElementById('notesEngineBadge');
    const coverageText = document.getElementById('notesCoverageText');
    const apiKeyPrompt = document.getElementById('notesApiKeyPrompt');

    if (engineBadge) {
      engineBadge.textContent = meta.generated_by || "Built-in Structural Knowledge Engine";
    }
    if (coverageText && state.currentDoc) {
      coverageText.textContent = meta.coverage || `100% Comprehensive Coverage (${state.currentDoc.total_pages} pages)`;
    }
    if (apiKeyPrompt) {
      if (meta.generated_by && meta.generated_by.includes("Gemini")) {
        apiKeyPrompt.classList.add('hidden');
      } else {
        apiKeyPrompt.classList.remove('hidden');
      }
    }
  }

  // Parse markdown
  container.innerHTML = marked.parse(markdownText);

  // Render KaTeX math equations
  if (window.renderMathInElement) {
    renderMathInElement(container, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '$', right: '$', display: false },
        { left: '\\(', right: '\\)', display: false },
        { left: '\\[', right: '\\]', display: true }
      ],
      throwOnError: false
    });
  }

  lucide.createIcons();
}

function copyNotesMarkdown() {
  if (!state.currentDoc || !state.currentDoc.notes) {
    showToast("No notes to copy", "error");
    return;
  }
  navigator.clipboard.writeText(state.currentDoc.notes);
  showToast("Notes markdown copied to clipboard!", "success");
}

function downloadNotesMarkdown() {
  if (!state.currentDoc || !state.currentDoc.notes) {
    showToast("No notes to export", "error");
    return;
  }
  window.open(`/api/export/${state.currentDocId}/markdown`, '_blank');
}

function openPrintableHtml() {
  if (!state.currentDoc || !state.currentDoc.notes) {
    showToast("No notes to print", "error");
    return;
  }
  window.open(`/api/export/${state.currentDocId}/html`, '_blank');
}

// -----------------------------------------------------------------------------
// IMPORTANT TOPICS & CONCEPT MINDMAP
// -----------------------------------------------------------------------------
async function generateTopics() {
  if (!state.currentDocId) {
    showToast("Please upload a lecture PDF first", "error");
    return;
  }

  const btn = document.getElementById('btnRegenTopics');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>Analyzing Topics...</span>`;
    lucide.createIcons();
  }

  showToast("Extracting core concepts and relationships...", "info");

  try {
    const res = await fetch(`/api/generate-topics/${state.currentDocId}`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Topic re-analysis failed");
    }

    state.currentDoc.topics = data.topics;
    state.currentDoc.mindmap = data.mindmap;
    renderTopics(data.topics, data.mindmap);
    document.getElementById('topicsMetaBadge').textContent =
      `Re-analyzed with ${data.generated_by || "the study engine"}.`;
    showToast(`Topics re-analyzed with ${data.generated_by || "the study engine"}.`, "success");
  } catch (err) {
    showToast(`Failed to analyze topics: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i><span>Re-Analyze Topics</span>`;
      lucide.createIcons();
    }
  }
}

function renderTopics(topics, mindmap) {
  document.getElementById('topicsEmptyState').classList.add('hidden');
  
  if (state.topicsView === 'cards') {
    document.getElementById('topicsCardsView').classList.remove('hidden');
    document.getElementById('topicsMindmapView').classList.add('hidden');
  } else {
    document.getElementById('topicsCardsView').classList.add('hidden');
    document.getElementById('topicsMindmapView').classList.remove('hidden');
  }

  // 1. Render Cards
  const grid = document.getElementById('topicsGrid');
  grid.innerHTML = '';

  topics.forEach(t => {
    let impBadge = 'bg-slate-800 text-slate-300';
    if (t.importance === 'High') {
      impBadge = 'bg-rose-500/10 text-rose-400 border border-rose-500/20';
    } else if (t.importance === 'Medium') {
      impBadge = 'bg-amber-500/10 text-amber-400 border border-amber-500/20';
    } else if (t.importance === 'Foundational') {
      impBadge = 'bg-sky-500/10 text-sky-400 border border-sky-500/20';
    }

    const card = document.createElement('div');
    card.className = "topic-card glass-panel rounded-xl p-5 border border-slate-800 flex flex-col justify-between";
    card.dataset.importance = t.importance;

    const pagesHtml = (t.pages || []).map(p => `
      <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-mono">Page ${p}</span>
    `).join('');

    const keywordsHtml = (t.keywords || []).map(k => `
      <span class="px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 text-[10px] font-medium">#${k}</span>
    `).join('');

    card.innerHTML = `
      <div>
        <div class="flex items-center justify-between gap-2 mb-2">
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold ${impBadge}">
            ${t.importance} Priority
          </span>
          <div class="flex items-center space-x-1">${pagesHtml}</div>
        </div>

        <h3 class="text-base font-bold text-white mb-1.5">${t.title}</h3>
        <p class="text-xs text-slate-300 leading-relaxed mb-3">${t.description}</p>
        
        <div class="bg-slate-900/70 rounded-lg p-2.5 border border-slate-800/80 mb-3">
          <span class="text-[10px] font-bold uppercase tracking-wider text-amber-400 block mb-0.5">Why it's tested:</span>
          <p class="text-[11px] text-slate-400 leading-snug">${t.why_important}</p>
        </div>
      </div>

      <div class="pt-3 border-t border-slate-800/80 flex flex-wrap gap-1.5 items-center justify-between">
        <div class="flex flex-wrap gap-1">${keywordsHtml}</div>
        <button onclick="askAboutTopic('${escapeHtml(t.title)}')" class="text-xs text-brand-400 hover:text-brand-300 font-semibold flex items-center space-x-1">
          <span>Ask Tutor</span>
          <i data-lucide="arrow-right" class="w-3.5 h-3.5"></i>
        </button>
      </div>
    `;
    grid.appendChild(card);
  });

  // 2. Render Mindmap
  if (mindmap) {
    document.getElementById('mindmapRootTitle').textContent = mindmap.root || state.currentDoc.title;
    const treeContainer = document.getElementById('mindmapTreeContainer');
    treeContainer.innerHTML = '';

    (mindmap.branches || []).forEach((b, idx) => {
      const branchDiv = document.createElement('div');
      branchDiv.className = "mindmap-branch";
      
      const subtopicsHtml = (b.subtopics || []).map(sub => `
        <div class="bg-slate-900/80 rounded-lg px-3 py-2 text-xs text-slate-300 border border-slate-800/60 flex items-center space-x-2">
          <span class="w-1.5 h-1.5 rounded-full bg-brand-400"></span>
          <span>${sub}</span>
        </div>
      `).join('');

      branchDiv.innerHTML = `
        <div class="mindmap-node inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-xl font-bold text-sm text-white shadow-sm mb-3">
          <i data-lucide="git-branch" class="w-4 h-4 text-purple-400"></i>
          <span>${b.name}</span>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 pl-4">
          ${subtopicsHtml}
        </div>
      `;
      treeContainer.appendChild(branchDiv);
    });
  }

  lucide.createIcons();
}

function switchTopicsView(viewType) {
  state.topicsView = viewType;
  const btnCards = document.getElementById('btnViewCards');
  const btnMindmap = document.getElementById('btnViewMindmap');
  const cardsView = document.getElementById('topicsCardsView');
  const mindmapView = document.getElementById('topicsMindmapView');

  if (viewType === 'cards') {
    btnCards.className = "px-3 py-1 rounded-md bg-brand-600 text-white font-medium transition";
    btnMindmap.className = "px-3 py-1 rounded-md text-slate-400 hover:text-white transition";
    cardsView.classList.remove('hidden');
    mindmapView.classList.add('hidden');
  } else {
    btnMindmap.className = "px-3 py-1 rounded-md bg-purple-600 text-white font-medium transition";
    btnCards.className = "px-3 py-1 rounded-md text-slate-400 hover:text-white transition";
    cardsView.classList.add('hidden');
    mindmapView.classList.remove('hidden');
  }
}

function filterTopics(importance) {
  state.topicsFilter = importance;
  document.querySelectorAll('.topic-filter-btn').forEach(btn => {
    if (btn.dataset.filter === importance) {
      btn.className = "topic-filter-btn px-2.5 py-1 rounded-md bg-brand-600 text-white font-semibold";
    } else {
      btn.className = "topic-filter-btn px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 hover:bg-slate-700";
    }
  });

  document.querySelectorAll('.topic-card').forEach(card => {
    if (importance === 'all' || card.dataset.importance === importance) {
      card.classList.remove('hidden');
    } else {
      card.classList.add('hidden');
    }
  });
}

function askAboutTopic(topicTitle) {
  switchTab('tab-chat');
  const input = document.getElementById('chatInput');
  input.value = `Can you explain the key concepts and formulas for "${topicTitle}" from our lecture notes?`;
  document.getElementById('chatSendBtn').click();
}

// -----------------------------------------------------------------------------
// PRACTICE HUB (INTERACTIVE QUIZ, FLASHCARDS, SHORT ANSWER)
// -----------------------------------------------------------------------------
async function generatePractice() {
  if (!state.currentDocId) {
    showToast("Please upload a lecture PDF first", "error");
    return;
  }

  const btn = document.getElementById('btnRegenPractice');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>Generating Questions...</span>`;
    lucide.createIcons();
  }

  showToast("Generating a fresh quiz, flashcard, and practice set...", "info");

  try {
    const res = await fetch(`/api/generate-practice/${state.currentDocId}`, { method: 'POST' });
    const data = await res.json();
    state.currentDoc.practice = data.practice;
    renderPractice(data.practice);
    showToast("New practice set generated!", "success");
  } catch (err) {
    showToast(`Failed to generate practice: ${err.message}`, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i><span>Regenerate Questions</span>`;
      lucide.createIcons();
    }
  }
}

function renderPractice(practiceData) {
  document.getElementById('practiceEmptyState').classList.add('hidden');
  
  // Update Quiz Mode
  if (practiceData.mcqs && practiceData.mcqs.length > 0) {
    renderQuiz(practiceData.mcqs);
  }

  // Update Flashcards Mode
  if (practiceData.flashcards && practiceData.flashcards.length > 0) {
    state.flashcards = practiceData.flashcards;
    state.flashcardIndex = 0;
    state.flashcardFlipped = false;
    updateFlashcardUI();
  }

  // Update Short Answer Mode
  if (practiceData.short_answer && practiceData.short_answer.length > 0) {
    renderShortAnswer(practiceData.short_answer);
  }

  switchPracticeMode(state.practiceMode);
  lucide.createIcons();
}

function switchPracticeMode(mode) {
  state.practiceMode = mode;

  // Toggle button states
  const modes = ['quiz', 'flashcards', 'short_answer'];
  modes.forEach(m => {
    const btn = document.getElementById(`btnMode${capitalize(m)}`);
    const container = document.getElementById(`practice${capitalize(m)}Mode`);
    
    if (m === mode) {
      btn.className = "px-3 py-1 rounded-md bg-emerald-600 text-white font-medium transition flex items-center space-x-1.5";
      container.classList.remove('hidden');
    } else {
      btn.className = "px-3 py-1 rounded-md text-slate-400 hover:text-white transition flex items-center space-x-1.5";
      container.classList.add('hidden');
    }
  });

  lucide.createIcons();
}

// --- QUIZ IMPLEMENTATION ---
function renderQuiz(mcqs) {
  const container = document.getElementById('quizListContainer');
  container.innerHTML = '';
  state.quizAnswers = {};

  mcqs.forEach((mcq, qIdx) => {
    const card = document.createElement('div');
    card.id = `mcq-card-${qIdx}`;
    card.className = "glass-panel rounded-xl p-5 border border-slate-800 space-y-3";

    const optionsHtml = mcq.options.map((opt, oIdx) => `
      <button 
        onclick="selectQuizAnswer(${qIdx}, ${oIdx})" 
        id="opt-${qIdx}-${oIdx}"
        class="w-full text-left px-4 py-3 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800/80 text-xs sm:text-sm text-slate-200 transition flex items-center justify-between group"
      >
        <span class="flex items-center space-x-3">
          <span class="w-6 h-6 rounded-full bg-slate-800 text-slate-400 font-bold text-xs flex items-center justify-center shrink-0 group-hover:bg-brand-500/20 group-hover:text-brand-300">
            ${String.fromCharCode(65 + oIdx)}
          </span>
          <span>${opt}</span>
        </span>
        <span id="opt-icon-${qIdx}-${oIdx}" class="shrink-0 ml-2"></span>
      </button>
    `).join('');

    card.innerHTML = `
      <div class="flex items-center justify-between text-xs text-slate-400">
        <span class="font-bold text-emerald-400 uppercase tracking-wider">Question ${qIdx + 1} of ${mcqs.length}</span>
        <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">Ref: Page ${mcq.page_ref || 1}</span>
      </div>

      <p class="text-sm sm:text-base font-semibold text-white">${mcq.question}</p>

      <div class="space-y-2 pt-1" id="opts-group-${qIdx}">
        ${optionsHtml}
      </div>

      <div id="explanation-${qIdx}" class="hidden p-3.5 rounded-xl text-xs leading-relaxed border"></div>
    `;

    container.appendChild(card);
  });

  updateQuizScoreBanner();
}

function selectQuizAnswer(qIdx, selectedOptIdx) {
  // If already answered, ignore
  if (state.quizAnswers[qIdx] !== undefined) return;

  const mcqs = state.currentDoc.practice.mcqs;
  const mcq = mcqs[qIdx];
  const isCorrect = selectedOptIdx === mcq.correct_index;

  state.quizAnswers[qIdx] = selectedOptIdx;

  // Highlight options
  mcq.options.forEach((_, optIdx) => {
    const btn = document.getElementById(`opt-${qIdx}-${optIdx}`);
    const iconSpan = document.getElementById(`opt-icon-${qIdx}-${optIdx}`);
    btn.disabled = true;

    if (optIdx === mcq.correct_index) {
      btn.className = "w-full text-left px-4 py-3 rounded-xl border border-emerald-500 bg-emerald-500/10 text-emerald-200 text-xs sm:text-sm font-semibold flex items-center justify-between";
      iconSpan.innerHTML = `<i data-lucide="check-circle" class="w-4 h-4 text-emerald-400"></i>`;
    } else if (optIdx === selectedOptIdx && !isCorrect) {
      btn.className = "w-full text-left px-4 py-3 rounded-xl border border-rose-500 bg-rose-500/10 text-rose-200 text-xs sm:text-sm flex items-center justify-between";
      iconSpan.innerHTML = `<i data-lucide="x-circle" class="w-4 h-4 text-rose-400"></i>`;
    } else {
      btn.classList.add('opacity-40');
    }
  });

  // Reveal Explanation
  const expBox = document.getElementById(`explanation-${qIdx}`);
  expBox.classList.remove('hidden');
  if (isCorrect) {
    expBox.className = "p-3.5 rounded-xl text-xs leading-relaxed border bg-emerald-500/10 border-emerald-500/20 text-emerald-200";
    expBox.innerHTML = `<strong>Correct!</strong> ${mcq.explanation}`;
  } else {
    expBox.className = "p-3.5 rounded-xl text-xs leading-relaxed border bg-rose-500/10 border-rose-500/20 text-rose-200";
    expBox.innerHTML = `<strong>Incorrect.</strong> ${mcq.explanation}`;
  }

  updateQuizScoreBanner();
  lucide.createIcons();
}

function updateQuizScoreBanner() {
  const mcqs = (state.currentDoc && state.currentDoc.practice) ? state.currentDoc.practice.mcqs || [] : [];
  if (mcqs.length === 0) return;

  const answeredCount = Object.keys(state.quizAnswers).length;
  let correctCount = 0;

  mcqs.forEach((mcq, qIdx) => {
    if (state.quizAnswers[qIdx] === mcq.correct_index) {
      correctCount++;
    }
  });

  const label = document.getElementById('quizScoreLabel');
  const icon = document.getElementById('quizScoreIcon');

  if (answeredCount === 0) {
    label.textContent = `0 of ${mcqs.length} answered. Select an option to start!`;
    icon.textContent = "🎯";
  } else {
    const pct = Math.round((correctCount / answeredCount) * 100);
    label.textContent = `Score: ${correctCount}/${answeredCount} (${pct}%) — ${mcqs.length - answeredCount} remaining`;
    
    if (answeredCount === mcqs.length) {
      if (pct >= 80) {
        label.textContent = `Mastery Achieved! Final Score: ${correctCount}/${mcqs.length} (${pct}%) 🎉`;
        icon.textContent = "🏆";
        if (window.confetti) {
          confetti({ particleCount: 120, spread: 70, origin: { y: 0.6 } });
        }
      } else {
        label.textContent = `Quiz Complete! Score: ${correctCount}/${mcqs.length} (${pct}%). Review explanations above!`;
        icon.textContent = "📚";
      }
    }
  }
}

function resetQuiz() {
  if (state.currentDoc && state.currentDoc.practice && state.currentDoc.practice.mcqs) {
    renderQuiz(state.currentDoc.practice.mcqs);
    showToast("Quiz reset! Ready to test again.", "info");
  }
}

// --- FLASHCARDS IMPLEMENTATION ---
function updateFlashcardUI() {
  if (!state.flashcards || state.flashcards.length === 0) return;

  const card = state.flashcards[state.flashcardIndex];
  const inner = document.getElementById('flashcardInner');
  
  // Reset flip to front
  state.flashcardFlipped = false;
  inner.classList.remove('rotate-y-180');

  // Text contents
  document.getElementById('flashcardCounter').textContent = `Card ${state.flashcardIndex + 1} of ${state.flashcards.length}`;
  document.getElementById('flashcardCategoryBadge').textContent = card.category || "Concept";
  document.getElementById('flashcardFrontPage').textContent = `Page ${card.page_ref || 1}`;
  document.getElementById('flashcardBackPage').textContent = `Page ${card.page_ref || 1}`;

  document.getElementById('flashcardFrontText').textContent = card.front;
  document.getElementById('flashcardBackText').textContent = card.back;

  // Mastered state
  const isMastered = state.masteredCards.has(card.id || state.flashcardIndex);
  const btnMastered = document.getElementById('btnMastered');
  const label = document.getElementById('btnMasteredLabel');
  
  if (isMastered) {
    btnMastered.className = "px-4 py-2 rounded-xl bg-emerald-600/30 text-xs font-semibold text-emerald-400 transition flex items-center space-x-1.5 border border-emerald-500/30";
    label.textContent = "Mastered ✓";
  } else {
    btnMastered.className = "px-4 py-2 rounded-xl bg-slate-800/80 hover:bg-emerald-600/30 text-xs font-semibold text-slate-300 hover:text-emerald-400 transition flex items-center space-x-1.5 border border-slate-700";
    label.textContent = "Mark as Mastered";
  }

  lucide.createIcons();
}

function flipFlashcard() {
  const inner = document.getElementById('flashcardInner');
  state.flashcardFlipped = !state.flashcardFlipped;
  inner.classList.toggle('rotate-y-180', state.flashcardFlipped);
}

function nextFlashcard() {
  if (state.flashcards.length === 0) return;
  state.flashcardIndex = (state.flashcardIndex + 1) % state.flashcards.length;
  updateFlashcardUI();
}

function prevFlashcard() {
  if (state.flashcards.length === 0) return;
  state.flashcardIndex = (state.flashcardIndex - 1 + state.flashcards.length) % state.flashcards.length;
  updateFlashcardUI();
}

function shuffleFlashcards() {
  if (state.flashcards.length === 0) return;
  state.flashcards.sort(() => Math.random() - 0.5);
  state.flashcardIndex = 0;
  updateFlashcardUI();
  showToast("Flashcard deck shuffled!", "info");
}

function toggleMasteredFlashcard() {
  const card = state.flashcards[state.flashcardIndex];
  const cardId = card.id || state.flashcardIndex;

  if (state.masteredCards.has(cardId)) {
    state.masteredCards.delete(cardId);
    showToast("Removed from mastered list", "info");
  } else {
    state.masteredCards.add(cardId);
    showToast("Card marked as mastered! 🌟", "success");
  }
  updateFlashcardUI();
}

// --- SHORT ANSWER / CONCEPTUAL QUESTIONS ---
function renderShortAnswer(questions) {
  const container = document.getElementById('shortAnswerListContainer');
  container.innerHTML = '';

  questions.forEach((q, idx) => {
    const card = document.createElement('div');
    card.className = "glass-panel rounded-xl p-5 border border-slate-800 space-y-3";

    const keyPointsHtml = (q.key_points || []).map(pt => `
      <li class="flex items-start space-x-2 text-xs text-slate-300">
        <span class="text-emerald-400 font-bold">•</span>
        <span>${pt}</span>
      </li>
    `).join('');

    card.innerHTML = `
      <div class="flex items-center justify-between text-xs text-slate-400">
        <span class="font-bold text-sky-400 uppercase tracking-wider">Conceptual Problem ${idx + 1}</span>
        <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">Ref: Page ${q.page_ref || 1}</span>
      </div>

      <h4 class="text-sm sm:text-base font-bold text-white">${q.question}</h4>

      <button onclick="toggleModelAnswer(${idx})" id="btnToggleSa-${idx}" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-brand-300 hover:text-white transition flex items-center space-x-1.5 border border-slate-700">
        <i data-lucide="eye" class="w-3.5 h-3.5"></i>
        <span>Reveal Model Answer & Rubric</span>
      </button>

      <div id="saAnswerBox-${idx}" class="hidden p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
        <div>
          <span class="text-[11px] font-bold uppercase tracking-wider text-emerald-400">Comprehensive Model Answer:</span>
          <p class="text-xs text-slate-200 mt-1 leading-relaxed">${q.model_answer}</p>
        </div>

        ${keyPointsHtml ? `
        <div class="pt-2 border-t border-slate-800/80">
          <span class="text-[11px] font-bold uppercase tracking-wider text-amber-400">Grading Rubric Key Points:</span>
          <ul class="mt-1 space-y-1">${keyPointsHtml}</ul>
        </div>
        ` : ''}
      </div>
    `;

    container.appendChild(card);
  });

  lucide.createIcons();
}

function toggleModelAnswer(idx) {
  const box = document.getElementById(`saAnswerBox-${idx}`);
  const btn = document.getElementById(`btnToggleSa-${idx}`);
  if (box) {
    const isHidden = box.classList.contains('hidden');
    box.classList.toggle('hidden', !isHidden);
    btn.innerHTML = isHidden 
      ? `<i data-lucide="eye-off" class="w-3.5 h-3.5"></i><span>Hide Model Answer</span>`
      : `<i data-lucide="eye" class="w-3.5 h-3.5"></i><span>Reveal Model Answer & Rubric</span>`;
    lucide.createIcons();
  }
}

// -----------------------------------------------------------------------------
// STUDENT Q&A (GEMINI CHAT)
// -----------------------------------------------------------------------------
function setupSuggestedQuestions() {
  const container = document.getElementById('suggestedChipsContainer');
  container.innerHTML = '';

  const suggestions = [
    "Explain a difficult concept in simple terms",
    "Can you give me a worked example?",
    "Help me prepare for an exam",
    "What should I learn next?"
  ];

  suggestions.forEach(q => {
    const chip = document.createElement('button');
    chip.className = "px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-brand-600/30 text-slate-300 hover:text-white border border-slate-700/60 whitespace-nowrap transition";
    chip.textContent = q;
    chip.onclick = () => {
      document.getElementById('chatInput').value = q;
      document.getElementById('chatSendBtn').click();
    };
    container.appendChild(chip);
  });
}

async function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById('chatInput');
  const query = input.value.trim();

  if (!query || state.isGenerating) return;

  input.value = '';
  appendUserMessage(query);

  state.isGenerating = true;
  const sendBtn = document.getElementById('chatSendBtn');
  sendBtn.disabled = true;

  // Append thinking bubble
  const thinkingId = appendThinkingBubble();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query,
        history: state.chatHistory.slice(-6)
      })
    });

    const data = await res.json();
    removeThinkingBubble(thinkingId);
    if (!res.ok) {
      throw new Error(data.detail || `Request failed (${res.status})`);
    }

    // Append AI response
    appendAIMessage(data.answer, data.citations, data.model);

    // Update conversation history
    state.chatHistory.push({ role: 'user', content: query });
    state.chatHistory.push({ role: 'assistant', content: data.answer });

    // Update dynamic suggested questions
    if (data.suggested_questions && data.suggested_questions.length > 0) {
      updateDynamicSuggestions(data.suggested_questions);
    }

  } catch (err) {
    removeThinkingBubble(thinkingId);
    appendAIMessage(`I encountered an issue answering your question: ${err.message}`, [], "System");
  } finally {
    state.isGenerating = false;
    sendBtn.disabled = false;
    lucide.createIcons();
  }
}

function appendUserMessage(text) {
  const container = document.getElementById('chatMessages');
  const msg = document.createElement('div');
  msg.className = "flex items-start justify-end space-x-3";
  msg.innerHTML = `
    <div class="bg-brand-600 text-white rounded-2xl rounded-tr-sm p-4 text-sm max-w-xl shadow-md">
      <p class="leading-relaxed">${escapeHtml(text)}</p>
    </div>
    <div class="w-8 h-8 rounded-lg bg-slate-800 text-slate-300 flex items-center justify-center shrink-0 mt-0.5">
      <i data-lucide="user" class="w-4 h-4"></i>
    </div>
  `;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
  lucide.createIcons();
}

function appendThinkingBubble() {
  const id = `thinking-${Date.now()}`;
  const container = document.getElementById('chatMessages');
  const msg = document.createElement('div');
  msg.id = id;
  msg.className = "flex items-start space-x-3 max-w-2xl animate-pulse";
  msg.innerHTML = `
    <div class="w-8 h-8 rounded-lg bg-brand-600/20 text-brand-400 flex items-center justify-center shrink-0 mt-0.5">
      <i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i>
    </div>
    <div class="bg-slate-900/80 rounded-2xl rounded-tl-sm p-4 border border-slate-800 text-xs text-slate-400">
      Searching lecture excerpts and reasoning...
    </div>
  `;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
  lucide.createIcons();
  return id;
}

function removeThinkingBubble(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function appendAIMessage(markdownText, citations, modelName) {
  const container = document.getElementById('chatMessages');
  const msg = document.createElement('div');
  msg.className = "flex items-start space-x-3 max-w-2xl";

  const citationsHtml = (citations || []).map((c, idx) => `
    <button 
      onclick="openCitationModal(${c.page}, '${escapeHtml(c.snippet)}', ${c.score})" 
      class="px-2 py-0.5 rounded-md bg-brand-500/10 hover:bg-brand-500/20 text-brand-300 border border-brand-500/20 text-[11px] font-semibold flex items-center space-x-1 transition"
    >
      <i data-lucide="bookmark" class="w-3 h-3"></i>
      <span>Page ${c.page}</span>
    </button>
  `).join('');

  msg.innerHTML = `
    <div class="w-8 h-8 rounded-lg bg-brand-600/30 text-brand-300 flex items-center justify-center shrink-0 mt-0.5">
      <i data-lucide="sparkles" class="w-4 h-4"></i>
    </div>
    <div class="bg-slate-900/90 rounded-2xl rounded-tl-sm p-5 border border-slate-800 text-sm text-slate-200 space-y-3 shadow-md w-full">
      
      <!-- Model Badge & Copy -->
      <div class="flex items-center justify-between text-[11px] text-slate-500 border-b border-slate-800/80 pb-2">
        <span class="flex items-center space-x-1">
          <i data-lucide="shield" class="w-3.5 h-3.5 text-brand-400"></i>
          <span>${modelName || 'Grounded Academic Tutor'}</span>
        </span>
        <button onclick="copyElementText(this)" class="hover:text-slate-300 transition flex items-center space-x-1">
          <i data-lucide="copy" class="w-3 h-3"></i>
          <span>Copy</span>
        </button>
      </div>

      <!-- Markdown Answer Content -->
      <div class="markdown-body leading-relaxed">
        ${marked.parse(markdownText)}
      </div>

      <!-- Source Citations Bar -->
      ${citations && citations.length > 0 ? `
      <div class="pt-2 border-t border-slate-800/80 flex flex-wrap items-center gap-1.5">
        <span class="text-[11px] text-slate-400 font-semibold mr-1">Sources Cited:</span>
        ${citationsHtml}
      </div>
      ` : ''}

    </div>
  `;

  container.appendChild(msg);

  // Render LaTeX math inside the message
  if (window.renderMathInElement) {
    renderMathInElement(msg, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '$', right: '$', display: false },
        { left: '\\(', right: '\\)', display: false },
        { left: '\\[', right: '\\]', display: true }
      ],
      throwOnError: false
    });
  }

  container.scrollTop = container.scrollHeight;
  lucide.createIcons();
}

function updateDynamicSuggestions(questions) {
  const container = document.getElementById('suggestedChipsContainer');
  container.innerHTML = '';

  questions.forEach(q => {
    const chip = document.createElement('button');
    chip.className = "px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-brand-600/30 text-slate-300 hover:text-white border border-slate-700/60 whitespace-nowrap transition text-xs";
    chip.textContent = q;
    chip.onclick = () => {
      document.getElementById('chatInput').value = q;
      document.getElementById('chatSendBtn').click();
    };
    container.appendChild(chip);
  });
}

function clearChat() {
  const container = document.getElementById('chatMessages');
  container.innerHTML = `
    <div class="flex items-start space-x-3 max-w-2xl">
      <div class="w-8 h-8 rounded-lg bg-brand-600/30 text-brand-300 flex items-center justify-center shrink-0 mt-0.5">
        <i data-lucide="sparkles" class="w-4 h-4"></i>
      </div>
      <div class="bg-slate-900/80 rounded-2xl rounded-tl-sm p-4 border border-slate-800 text-sm text-slate-200">
        <p class="font-medium text-white mb-1">Chat history cleared.</p>
        <p class="text-slate-300">Ask Gemini another question about any topic!</p>
      </div>
    </div>
  `;
  state.chatHistory = [];
  lucide.createIcons();
}

// -----------------------------------------------------------------------------
// CITATION MODAL
// -----------------------------------------------------------------------------
function openCitationModal(pageNum, snippet, score) {
  document.getElementById('citationModalPage').textContent = `Lecture Source Excerpt - Page ${pageNum}`;
  document.getElementById('citationModalText').textContent = snippet;
  document.getElementById('citationModal').classList.remove('hidden');
}

function closeCitationModal() {
  document.getElementById('citationModal').classList.add('hidden');
}

// -----------------------------------------------------------------------------
// UTILITIES & NOTIFICATIONS
// -----------------------------------------------------------------------------
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  
  let bg = "bg-slate-900 border-slate-700 text-white";
  let icon = "info";
  if (type === 'success') {
    bg = "bg-emerald-950/90 border-emerald-500/40 text-emerald-200";
    icon = "check-circle";
  } else if (type === 'error') {
    bg = "bg-rose-950/90 border-rose-500/40 text-rose-200";
    icon = "alert-circle";
  }

  toast.className = `p-3.5 rounded-xl border ${bg} text-xs shadow-xl flex items-center space-x-2.5 transition-all duration-300 transform translate-y-2 pointer-events-auto`;
  toast.innerHTML = `
    <i data-lucide="${icon}" class="w-4 h-4 shrink-0"></i>
    <span class="font-medium">${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  lucide.createIcons();

  requestAnimationFrame(() => {
    toast.classList.remove('translate-y-2');
  });

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function capitalize(s) {
  if (!s) return '';
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function copyElementText(btn) {
  const text = btn.closest('.bg-slate-900\\/90').querySelector('.markdown-body').innerText;
  navigator.clipboard.writeText(text);
  showToast("Answer copied to clipboard!", "success");
}
