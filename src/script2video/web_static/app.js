const elements = {
  version: document.querySelector("#version"),
  textMode: document.querySelector("#text-mode"),
  yamlMode: document.querySelector("#yaml-mode"),
  textSource: document.querySelector("#text-source"),
  yamlSource: document.querySelector("#yaml-source"),
  narrationText: document.querySelector("#narration-text"),
  textMessage: document.querySelector("#text-message"),
  characterCount: document.querySelector("#character-count"),
  scriptPath: document.querySelector("#script-path"),
  videoPath: document.querySelector("#video-path"),
  outputPath: document.querySelector("#output-path"),
  chooseScript: document.querySelector("#choose-script"),
  chooseVideo: document.querySelector("#choose-video"),
  chooseOutput: document.querySelector("#choose-output"),
  clearVideo: document.querySelector("#clear-video"),
  scriptMessage: document.querySelector("#script-message"),
  videoMessage: document.querySelector("#video-message"),
  scriptState: document.querySelector("#script-state"),
  languageSelect: document.querySelector("#language-select"),
  voiceSelect: document.querySelector("#voice-select"),
  fitToggle: document.querySelector("#fit-toggle"),
  alignToggle: document.querySelector("#align-toggle"),
  alignmentDescription: document.querySelector("#alignment-description"),
  generate: document.querySelector("#generate"),
  generateLabel: document.querySelector("#generate-label"),
  projectTitle: document.querySelector("#project-title"),
  sceneCount: document.querySelector("#scene-count"),
  wordCount: document.querySelector("#word-count"),
  summaryLanguage: document.querySelector("#language"),
  duration: document.querySelector("#duration"),
  deliveryMode: document.querySelector("#delivery-mode"),
  deliveryFiles: document.querySelector("#delivery-files"),
  previewTitle: document.querySelector("#preview-title"),
  previewPanel: document.querySelector(".preview-panel"),
  statusChip: document.querySelector("#status-chip"),
  jobPanel: document.querySelector("#job-panel"),
  jobMessage: document.querySelector("#job-message"),
  successPanel: document.querySelector("#success-panel"),
  successCopy: document.querySelector("#success-copy"),
  openOutput: document.querySelector("#open-output"),
  openCapCut: document.querySelector("#open-capcut"),
  quitStudio: document.querySelector("#quit-studio"),
  toast: document.querySelector("#toast"),
};

const state = {
  bootstrap: null,
  sourceMode: "text",
  script: null,
  textVoices: [],
  video: null,
  generating: false,
  output: "",
  toastTimer: null,
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Something went wrong");
  }
  return data;
}

async function initialize() {
  try {
    state.bootstrap = await api("/api/bootstrap");
    elements.version.textContent = `v${state.bootstrap.version}`;
    elements.outputPath.value = state.bootstrap.default_output;
    elements.scriptPath.value = state.bootstrap.default_script;
    populateLanguages();
    configureAlignment();
    await loadTextVoices();
  } catch (error) {
    showToast(error.message);
  }
  updateInterface();
}

function populateLanguages() {
  elements.languageSelect.replaceChildren();
  for (const language of state.bootstrap.languages) {
    elements.languageSelect.add(
      new Option(formatLanguageName(language), language),
    );
  }
  elements.languageSelect.value = state.bootstrap.default_language;
}

function formatLanguageName(language) {
  const [base, region] = language.split("-");
  try {
    const names = new Intl.DisplayNames([navigator.language], {
      type: "language",
    });
    const languageName = names.of(base) || language;
    return region ? `${languageName} · ${language}` : languageName;
  } catch {
    return language;
  }
}

async function loadTextVoices() {
  state.textVoices = [];
  elements.voiceSelect.replaceChildren(new Option("Loading voices…", ""));
  updateInterface();
  try {
    const result = await api("/api/voices", {
      method: "POST",
      body: JSON.stringify({
        engine: "kokoro",
        language: elements.languageSelect.value,
      }),
    });
    state.textVoices = result.voices;
    populateVoices();
  } catch (error) {
    showToast(error.message);
  }
  updateInterface();
}

function configureAlignment() {
  const available = state.bootstrap?.alignment_available;
  elements.alignToggle.checked = Boolean(available);
  if (!available) {
    elements.alignmentDescription.textContent =
      "Exact block timing is used on Windows and Intel Macs.";
  }
}

async function choose(kind) {
  setBusyPicker(kind, true);
  try {
    const result = await api("/api/pick", {
      method: "POST",
      body: JSON.stringify({ kind }),
    });
    if (!result.path) return;
    if (kind === "script") {
      elements.scriptPath.value = result.path;
      await inspectScript();
    } else if (kind === "video") {
      elements.videoPath.value = result.path;
      await inspectVideo();
    } else {
      elements.outputPath.value = result.path;
    }
    updateInterface();
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusyPicker(kind, false);
  }
}

function setBusyPicker(kind, busy) {
  const button = {
    script: elements.chooseScript,
    video: elements.chooseVideo,
    folder: elements.chooseOutput,
  }[kind];
  button.disabled = busy;
  button.textContent = busy ? "Opening…" : "Browse";
}

async function inspectScript() {
  const path = elements.scriptPath.value.trim();
  state.script = null;
  elements.scriptMessage.className = "field-message";
  elements.scriptMessage.textContent = "Reading script…";
  updateInterface();
  if (!path) {
    elements.scriptMessage.textContent =
      "A script defines your scenes, language, and default voice.";
    return;
  }
  try {
    state.script = await api("/api/inspect-script", {
      method: "POST",
      body: JSON.stringify({ path }),
    });
    elements.scriptMessage.className = "field-message success";
    elements.scriptMessage.textContent =
      `${state.script.scene_count} scenes · ${state.script.language} · ${state.script.engine}`;
    elements.languageSelect.replaceChildren(
      new Option(state.script.language, state.script.language),
    );
    populateVoices();
  } catch (error) {
    elements.scriptMessage.className = "field-message error";
    elements.scriptMessage.textContent = error.message;
  }
  updateInterface();
}

function populateVoices() {
  const previous = elements.voiceSelect.value;
  elements.voiceSelect.replaceChildren();
  const voices =
    state.sourceMode === "text" ? state.textVoices : state.script?.voices || [];
  if (state.sourceMode === "yaml" && state.script) {
    elements.voiceSelect.add(
      new Option(`Use script voice · ${state.script.voice}`, ""),
    );
  }
  for (const voice of voices) {
    elements.voiceSelect.add(new Option(`${voice.name} · ${voice.id}`, voice.id));
  }
  const hasPrevious = [...elements.voiceSelect.options].some(
    (option) => option.value === previous,
  );
  if (hasPrevious) {
    elements.voiceSelect.value = previous;
  } else if (state.sourceMode === "text") {
    const preferred = voices.find((voice) => voice.id === "af_heart");
    elements.voiceSelect.value = preferred?.id || voices[0]?.id || "";
  } else {
    elements.voiceSelect.value = "";
  }
}

function setSourceMode(mode) {
  if (mode === state.sourceMode || state.generating) return;
  state.sourceMode = mode;
  const textActive = mode === "text";
  elements.textMode.classList.toggle("active", textActive);
  elements.yamlMode.classList.toggle("active", !textActive);
  elements.textMode.setAttribute("aria-selected", String(textActive));
  elements.yamlMode.setAttribute("aria-selected", String(!textActive));
  elements.textSource.hidden = !textActive;
  elements.yamlSource.hidden = textActive;
  elements.successPanel.hidden = true;
  if (textActive) {
    populateLanguages();
    loadTextVoices();
  } else if (state.script) {
    elements.languageSelect.replaceChildren(
      new Option(state.script.language, state.script.language),
    );
    populateVoices();
  } else {
    populateLanguages();
    elements.voiceSelect.replaceChildren(
      new Option("Choose a YAML script first", ""),
    );
  }
  updateInterface();
}

function textStats() {
  const text = elements.narrationText.value.trim();
  const words = text ? text.split(/\s+/).length : 0;
  const scenes = text
    ? text.split(/\n\s*\n/).filter((paragraph) => paragraph.trim()).length
    : 0;
  const firstLine = text.split(/\n/).find((line) => line.trim())?.trim() || "";
  return { text, words, scenes, title: firstLine || "Paste text to begin" };
}

function updateTextSource() {
  const stats = textStats();
  elements.characterCount.textContent =
    `${stats.words} ${stats.words === 1 ? "word" : "words"}`;
  elements.textMessage.className = stats.text
    ? "field-message success"
    : "field-message";
  elements.textMessage.textContent = stats.text
    ? `${stats.scenes} ${stats.scenes === 1 ? "scene" : "scenes"} ready`
    : "Each paragraph automatically becomes a scene.";
  elements.successPanel.hidden = true;
  updateInterface();
}

async function inspectVideo() {
  const path = elements.videoPath.value.trim();
  state.video = null;
  elements.videoMessage.className = "field-message";
  updateInterface();
  if (!path) {
    elements.videoMessage.textContent =
      "Leave empty when you only need narration.";
    return;
  }
  elements.videoMessage.textContent = "Inspecting video…";
  try {
    state.video = await api("/api/inspect-video", {
      method: "POST",
      body: JSON.stringify({ path }),
    });
    const dimensions =
      state.video.width && state.video.height
        ? ` · ${state.video.width}×${state.video.height}`
        : "";
    elements.videoMessage.className = "field-message success";
    elements.videoMessage.textContent =
      `${formatDuration(state.video.duration_seconds)}${dimensions}`;
  } catch (error) {
    elements.videoMessage.className = "field-message error";
    elements.videoMessage.textContent = error.message;
  }
  updateInterface();
}

function clearVideo() {
  elements.videoPath.value = "";
  state.video = null;
  elements.videoMessage.className = "field-message";
  elements.videoMessage.textContent = "Leave empty when you only need narration.";
  elements.successPanel.hidden = true;
  updateInterface();
}

function updateInterface() {
  const hasVideoPath = Boolean(elements.videoPath.value.trim());
  const videoReady = !hasVideoPath || Boolean(state.video);
  const text = textStats();
  const sourceReady =
    state.sourceMode === "text"
      ? Boolean(text.text && state.textVoices.length && elements.voiceSelect.value)
      : Boolean(state.script);
  const ready =
    sourceReady &&
    videoReady &&
    Boolean(elements.outputPath.value.trim()) &&
    !state.generating;

  elements.clearVideo.hidden = !hasVideoPath;
  elements.narrationText.disabled = state.generating;
  elements.textMode.disabled = state.generating;
  elements.yamlMode.disabled = state.generating;
  elements.languageSelect.disabled =
    state.sourceMode === "yaml" || state.generating;
  elements.voiceSelect.disabled = !sourceReady || state.generating;
  elements.fitToggle.disabled = !state.video || state.generating;
  elements.alignToggle.disabled =
    !state.video ||
    !state.bootstrap?.alignment_available ||
    state.generating;
  elements.generate.disabled = !ready;
  elements.generateLabel.textContent = state.video
    ? "Generate CapCut package"
    : "Generate narration";
  elements.deliveryMode.textContent = state.video
    ? "Video + captions"
    : "Narration only";

  const textFile =
    state.sourceMode === "text"
      ? `<li><span class="file-type">TXT</span> Saved source text</li>`
      : "";
  elements.deliveryFiles.innerHTML = state.video
    ? `<li><span class="file-type">WAV</span> Fitted narration track</li>
       <li><span class="file-type">SRT</span> Editable subtitles</li>
       <li><span class="file-type">JSON</span> Timing manifest</li>
       ${textFile}`
    : `<li><span class="file-type">WAV</span> Narration track</li>
       <li><span class="file-type">JSON</span> Timing manifest</li>
       ${textFile}`;

  if (state.sourceMode === "text" && text.text) {
    elements.scriptState.textContent = "Ready";
    elements.scriptState.className = "step-state valid";
    elements.projectTitle.textContent =
      text.title.length > 60 ? `${text.title.slice(0, 57)}...` : text.title;
    elements.sceneCount.textContent = text.scenes;
    elements.wordCount.textContent = text.words;
    elements.summaryLanguage.textContent = elements.languageSelect.value;
  } else if (state.sourceMode === "yaml" && state.script) {
    elements.scriptState.textContent = "Ready";
    elements.scriptState.className = "step-state valid";
    elements.projectTitle.textContent = state.script.title;
    elements.sceneCount.textContent = state.script.scene_count;
    elements.wordCount.textContent = state.script.word_count;
    elements.summaryLanguage.textContent = state.script.language;
  } else {
    elements.scriptState.textContent = "Required";
    elements.scriptState.className = "step-state";
    elements.projectTitle.textContent =
      state.sourceMode === "text" ? "Paste text to begin" : "Choose a YAML script";
    elements.sceneCount.textContent = "—";
    elements.wordCount.textContent = "—";
    elements.summaryLanguage.textContent =
      state.sourceMode === "text" ? elements.languageSelect.value || "—" : "—";
  }
  elements.duration.textContent = state.video
    ? formatDuration(state.video.duration_seconds)
    : "--:--";

  if (!state.generating) {
    setStatus(
      ready ? "Ready" : "Setup",
      ready ? "ready" : "",
      ready ? "Ready to generate" : "Ready when you are",
    );
  }
}

async function generate() {
  if (elements.generate.disabled) return;
  state.generating = true;
  state.output = elements.outputPath.value.trim();
  elements.successPanel.hidden = true;
  elements.jobPanel.hidden = false;
  elements.jobMessage.textContent = "Preparing generation";
  elements.previewPanel.classList.add("running");
  setStatus("Working", "running", "Creating your voice track");
  updateInterface();

  try {
    const job = await api("/api/generate", {
      method: "POST",
      body: JSON.stringify({
        source_type: state.sourceMode,
        text:
          state.sourceMode === "text" ? elements.narrationText.value.trim() : "",
        script:
          state.sourceMode === "yaml" ? elements.scriptPath.value.trim() : "",
        language: elements.languageSelect.value,
        engine: state.sourceMode === "text" ? "kokoro" : state.script.engine,
        video: elements.videoPath.value.trim(),
        output: state.output,
        voice: elements.voiceSelect.value,
        fit: elements.fitToggle.checked,
        align: elements.alignToggle.checked,
      }),
    });
    pollJob(job.id);
  } catch (error) {
    finishWithError(error.message);
  }
}

async function pollJob(jobId) {
  try {
    const job = await api(`/api/jobs/${jobId}`);
    elements.jobMessage.textContent = job.message;
    if (job.status === "complete") {
      finishSuccessfully(job);
      return;
    }
    if (job.status === "failed") {
      finishWithError(job.error || "Generation failed");
      return;
    }
    window.setTimeout(() => pollJob(jobId), 900);
  } catch (error) {
    finishWithError(error.message);
  }
}

function finishSuccessfully(job) {
  state.generating = false;
  state.output = job.output;
  elements.jobPanel.hidden = true;
  elements.successPanel.hidden = false;
  elements.successCopy.textContent =
    `${job.files.length} files saved to ${job.output}`;
  elements.openCapCut.hidden = !state.video;
  elements.previewPanel.classList.remove("running");
  updateInterface();
  setStatus("Complete", "ready", "Your files are ready");
}

function finishWithError(message) {
  state.generating = false;
  elements.jobPanel.hidden = true;
  elements.previewPanel.classList.remove("running");
  updateInterface();
  setStatus("Error", "error", "Generation needs attention");
  showToast(message);
}

function setStatus(label, className, title) {
  elements.statusChip.className = `status-chip ${className}`.trim();
  elements.statusChip.innerHTML = `<span></span>${label}`;
  elements.previewTitle.textContent = title;
}

async function openAction(path, payload = {}) {
  try {
    await api(path, { method: "POST", body: JSON.stringify(payload) });
  } catch (error) {
    showToast(error.message);
  }
}

function showToast(message) {
  window.clearTimeout(state.toastTimer);
  elements.toast.textContent = message;
  elements.toast.hidden = false;
  state.toastTimer = window.setTimeout(() => {
    elements.toast.hidden = true;
  }, 5200);
}

function formatDuration(totalSeconds) {
  const rounded = Math.round(totalSeconds);
  const hours = Math.floor(rounded / 3600);
  const minutes = Math.floor((rounded % 3600) / 60);
  const seconds = rounded % 60;
  if (hours) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

elements.textMode.addEventListener("click", () => setSourceMode("text"));
elements.yamlMode.addEventListener("click", () => setSourceMode("yaml"));
elements.narrationText.addEventListener("input", updateTextSource);
elements.languageSelect.addEventListener("change", loadTextVoices);
elements.voiceSelect.addEventListener("change", updateInterface);
elements.chooseScript.addEventListener("click", () => choose("script"));
elements.chooseVideo.addEventListener("click", () => choose("video"));
elements.chooseOutput.addEventListener("click", () => choose("folder"));
elements.clearVideo.addEventListener("click", clearVideo);
elements.generate.addEventListener("click", generate);
elements.scriptPath.addEventListener("change", inspectScript);
elements.videoPath.addEventListener("change", inspectVideo);
elements.outputPath.addEventListener("input", updateInterface);
elements.openOutput.addEventListener("click", () =>
  openAction("/api/open-output", { path: state.output }),
);
elements.openCapCut.addEventListener("click", () =>
  openAction("/api/open-capcut"),
);
elements.quitStudio.addEventListener("click", async () => {
  if (!window.confirm("Quit Script2Video Studio?")) return;
  try {
    await api("/api/shutdown", {
      method: "POST",
      body: JSON.stringify({}),
    });
    document.body.innerHTML =
      '<main class="stopped-screen"><p class="eyebrow">Studio stopped</p>' +
      "<h1>You can close this tab.</h1></main>";
  } catch (error) {
    showToast(error.message);
  }
});

initialize();
