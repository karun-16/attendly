// Attendly — Frontend Controller
const $ = (id) => document.getElementById(id);
const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

// Internal state for the Semester Review and Builder
let currentSchedule = {
  semester_start: "",
  last_working_day: "",
  no_class_dates: [],
  special_classes: [],
  weekdays: {
    Monday: [],
    Tuesday: [],
    Wednesday: [],
    Thursday: [],
    Friday: [],
    Saturday: [],
    Sunday: [],
  },
  subjects: [],
  notes: [],
};

let activeWeekdayTab = "Monday";

function localISODate(date = new Date()) {
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 10);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function showError(id, message) {
  const box = $(id);
  box.textContent = message;
  box.classList.remove("hidden");
}

function clearError(id) {
  const box = $(id);
  box.classList.add("hidden");
  box.textContent = "";
}

function formatDate(dateText) {
  if (!dateText) return "Not set";
  const date = new Date(`${dateText}T12:00:00`);
  return Number.isNaN(date.getTime())
    ? dateText
    : date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

// Set Today Chip & default start date
$("today-label").textContent = new Date().toLocaleDateString(undefined, {
  weekday: "short",
  day: "numeric",
  month: "short",
  year: "numeric",
});
$("start-date").value = localISODate();
const tomorrow = new Date();
tomorrow.setDate(tomorrow.getDate() + 1);
$("future-start-date").value = localISODate(tomorrow);

// ---------------------------------------------------------------------------
// Workflow Navigation Tabs
// ---------------------------------------------------------------------------
function activateTab(id) {
  document.querySelectorAll(".mode-tab").forEach((tab) =>
    tab.classList.toggle("selected", tab.dataset.tab === id)
  );
  if (id === "manual-panel" || id === "planner-panel") {
    $(id).scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

document.querySelectorAll(".mode-tab").forEach((tab) =>
  tab.addEventListener("click", () => activateTab(tab.dataset.tab))
);

document.querySelectorAll(".nav-item").forEach((button) =>
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    const target = button.dataset.scroll;
    if (target === "top") window.scrollTo({ top: 0, behavior: "smooth" });
    else $(target).scrollIntoView({ behavior: "smooth", block: "start" });
  })
);

// ---------------------------------------------------------------------------
// Quick Calculator Logic
// ---------------------------------------------------------------------------
function getTargetPercentage(selectId, customInputId) {
  const val = $(selectId).value;
  if (val === "custom") {
    const customVal = Number($(customInputId).value.trim());
    if (!customVal || customVal <= 0 || customVal > 100) {
      throw new Error("Please enter a valid custom attendance target percentage between 1 and 100.");
    }
    return customVal;
  }
  return Number(val);
}

$("manual-target-select").addEventListener("change", (e) => {
  $("manual-custom-target-wrap").classList.toggle("hidden", e.target.value !== "custom");
});

$("semester-target-select").addEventListener("change", (e) => {
  $("semester-custom-target-wrap").classList.toggle("hidden", e.target.value !== "custom");
});

$("manual-calculate").addEventListener("click", async () => {
  const results = $("manual-results");
  results.classList.add("hidden");

  try {
    const presentRaw = $("manual-present").value.trim();
    const totalRaw = $("manual-total").value.trim();
    const futureRaw = $("manual-future").value.trim();

    if (!presentRaw || !Number.isInteger(Number(presentRaw)) || Number(presentRaw) < 0) {
      throw new Error("Classes attended so far must be a non-negative whole number.");
    }
    if (!totalRaw || !Number.isInteger(Number(totalRaw)) || Number(totalRaw) < 0) {
      throw new Error("Total classes conducted must be a whole number of zero or more.");
    }
    if (!futureRaw || !Number.isInteger(Number(futureRaw)) || Number(futureRaw) < 0) {
      throw new Error("Expected future classes must be a whole number of zero or more.");
    }

    const present = Number(presentRaw);
    const total = Number(totalRaw);
    const future = Number(futureRaw);
    const target = getTargetPercentage("manual-target-select", "manual-custom-target");

    if (present > total) {
      throw new Error("Classes attended (P) cannot exceed total classes conducted (T).");
    }

    // Call backend API for strictly validated calculation
    const response = await fetch("/api/calculate-quick", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        present,
        total,
        future,
        target_percentage: target,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Calculation error.");
    }

    const achievable = data.achievable;
    const canSkip = data.max_future_classes_can_skip;
    const toAttend = data.min_future_classes_to_attend;

    results.innerHTML = `
      <div class="result-header">
        <div>
          <h4>Your Attendance Outlook</h4>
          <p>Based on ${data.total} classes held and ${data.future} future classes scheduled.</p>
        </div>
        <span class="result-target">${data.target_percentage}% Target</span>
      </div>
      <div class="result-grid">
        <div class="result-metric">
          <span>Current Attendance</span>
          <strong class="${data.current_percentage >= data.target_percentage ? "metric-green" : "metric-purple"}">
            ${data.current_percentage.toFixed(2)}%
          </strong>
          <small>${data.present} of ${data.total} classes</small>
        </div>
        <div class="result-metric">
          <span>Attend at least</span>
          <strong class="${achievable ? "metric-green" : "metric-red"}">
            ${toAttend}
          </strong>
          <small>of the ${data.future} future classes</small>
        </div>
        <div class="result-metric">
          <span>Maximum classes to skip</span>
          <strong class="${canSkip > 0 ? "metric-orange" : "metric-purple"}">
            ${canSkip}
          </strong>
          <small>${achievable ? "While maintaining target" : "Target unachievable"}</small>
        </div>
      </div>
      <div class="result-note ${!achievable ? "metric-red" : ""}">
        ${escapeHtml(data.status_message)}
        <br><small>If you attend all future classes, your final attendance will be ${data.projected_percentage_if_attend_all.toFixed(2)}% (${data.present + data.future}/${data.final_total_classes} classes).</small>
      </div>`;
    results.classList.remove("hidden");
  } catch (error) {
    results.innerHTML = `<div class="error-box">${escapeHtml(error.message)}</div>`;
    results.classList.remove("hidden");
  }
});

$("manual-reset").addEventListener("click", () => {
  $("manual-present").value = "";
  $("manual-total").value = "";
  $("manual-future").value = "";
  $("manual-results").classList.add("hidden");
});

// ---------------------------------------------------------------------------
// Document Upload & Visual Review
// ---------------------------------------------------------------------------
for (const [inputId, nameId] of [
  ["calendar-file", "calendar-name"],
  ["timetable-file", "timetable-name"],
]) {
  $(inputId).addEventListener("change", () => {
    $(nameId).textContent =
      $(inputId).files[0]?.name ||
      (inputId === "calendar-file" ? "Choose calendar file" : "Choose timetable file");
  });
}

function renderWeekdaySchedule(day) {
  activeWeekdayTab = day;
  document.querySelectorAll(".weekday-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.day === day);
  });

  const container = $("weekday-schedule-container");
  const periods = currentSchedule.weekdays[day] || [];

  if (periods.length === 0) {
    container.innerHTML = `<div style="padding: 12px; font-size: 11px; color: var(--muted); text-align: center; background: #fff; border-radius: 8px; border: 1px dashed #dce0ec;">No classes scheduled on ${day}. Click "+ Add period" to add one.</div>`;
    return;
  }

  container.innerHTML = periods
    .map(
      (item, idx) => `
      <div class="period-row" data-index="${idx}">
        <input type="text" value="${escapeHtml(item.subject)}" placeholder="Subject name" class="period-subject-input" aria-label="Subject name" />
        <label style="display:flex; align-items:center; gap:4px; font-size:11px; color:#6b7280;">
          <input type="number" min="1" max="6" value="${item.periods || 1}" class="period-count-input" title="Periods (e.g. 2 for labs)" style="width:50px;" />
          <span>periods</span>
        </label>
        <button type="button" class="remove-period-btn" title="Delete period" data-day="${day}" data-index="${idx}">×</button>
      </div>`
    )
    .join("");

  // Attach change listeners to inputs
  container.querySelectorAll(".period-row").forEach((row) => {
    const idx = Number(row.dataset.index);
    const subInput = row.querySelector(".period-subject-input");
    const countInput = row.querySelector(".period-count-input");

    subInput.addEventListener("input", (e) => {
      currentSchedule.weekdays[day][idx].subject = e.target.value.trim();
      syncSubjectsFromTimetable();
    });

    countInput.addEventListener("input", (e) => {
      const p = Math.max(1, Math.min(6, parseInt(e.target.value, 10) || 1));
      currentSchedule.weekdays[day][idx].periods = p;
    });
  });

  container.querySelectorAll(".remove-period-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const idx = Number(e.currentTarget.dataset.index);
      currentSchedule.weekdays[day].splice(idx, 1);
      renderWeekdaySchedule(day);
      syncSubjectsFromTimetable();
    });
  });
}

$("weekday-tabs").addEventListener("click", (e) => {
  const day = e.target.closest(".weekday-tab")?.dataset?.day;
  if (day) renderWeekdaySchedule(day);
});

$("add-period-btn").addEventListener("click", () => {
  if (!currentSchedule.weekdays[activeWeekdayTab]) {
    currentSchedule.weekdays[activeWeekdayTab] = [];
  }
  currentSchedule.weekdays[activeWeekdayTab].push({
    subject: "New Subject",
    periods: 1,
  });
  renderWeekdaySchedule(activeWeekdayTab);
  syncSubjectsFromTimetable();
});

function renderHolidays() {
  const cloud = $("holidays-tag-cloud");
  if (!currentSchedule.no_class_dates.length) {
    cloud.innerHTML = `<span style="font-size:11px; color:var(--muted);">No holidays or non-teaching dates added yet.</span>`;
    return;
  }

  cloud.innerHTML = currentSchedule.no_class_dates
    .map(
      (d, idx) => `
      <span class="holiday-tag">
        <strong>${formatDate(d)}</strong>
        <button type="button" data-index="${idx}" title="Remove date">×</button>
      </span>`
    )
    .join("");

  cloud.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const idx = Number(e.currentTarget.dataset.index);
      currentSchedule.no_class_dates.splice(idx, 1);
      renderHolidays();
    });
  });
}

$("add-holiday-btn").addEventListener("click", () => {
  const dateVal = $("new-holiday-date").value;
  if (!dateVal) return;
  if (!currentSchedule.no_class_dates.includes(dateVal)) {
    currentSchedule.no_class_dates.push(dateVal);
    currentSchedule.no_class_dates.sort();
    renderHolidays();
  }
  $("new-holiday-date").value = "";
  $("new-holiday-name").value = "";
});

function canonicalAttendanceSubject(subject) {
  // Normalize theory and lab labels into a single attendance subject.
  // Handle variants such as "ML LAB", "Machine-Learning Lab", and extra whitespace.
  const normalized = String(subject || "")
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[._-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\s+lab(?:oratory)?$/i, "")
    .trim();

  const aliases = {
    "wt": "Web Technologies",
    "web tech": "Web Technologies",
    "web technologies": "Web Technologies",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "toc": "Theory of Computation",
    "theory of computation": "Theory of Computation",
    "lrre": "Logical Reasoning and Recruitment Essentials",
    "logical reasoning": "Logical Reasoning and Recruitment Essentials",
    "logical reasoning and recruitment essentials": "Logical Reasoning and Recruitment Essentials",
    "cdct": "Campus Recruitment Training",
    "campus recruitment training": "Campus Recruitment Training",
  };
  return aliases[normalized] || String(subject || "").trim();
}

function getUniqueTimetableSubjects() {
  const set = new Set();
  for (const day of weekdays) {
    for (const p of currentSchedule.weekdays[day] || []) {
      if (p.subject && p.subject.trim()) set.add(canonicalAttendanceSubject(p.subject));
    }
  }
  return Array.from(set);
}

function syncSubjectsFromTimetable() {
  const currentSubs = getUniqueTimetableSubjects();
  // Preserve existing present/total inputs
  const existingMap = new Map();
  document.querySelectorAll(".subject-row").forEach((row) => {
    const name = row.dataset.subject;
    const p = row.querySelector('[data-kind="present"]')?.value;
    const t = row.querySelector('[data-kind="total"]')?.value;
    if (name) existingMap.set(canonicalAttendanceSubject(name), { present: p, total: t });
  });

  const container = $("subject-inputs");
  if (!currentSubs.length) {
    container.innerHTML = `<div style="font-size:11px; color:var(--muted); padding:10px; background:#fff; border-radius:8px;">No subjects defined in the timetable yet. Add periods above or click "+ Add new subject".</div>`;
    return;
  }

  container.innerHTML = currentSubs
    .map((name) => {
      const state = existingMap.get(name) || { present: 0, total: 1 };
      return `
      <div class="subject-row" data-subject="${escapeHtml(name)}">
        <div class="subject-name">${escapeHtml(name)}</div>
        <label>
          <span>Present</span>
          <input type="number" min="0" step="1" value="${state.present}" data-kind="present" aria-label="${escapeHtml(name)} present" />
        </label>
        <label>
          <span>Total held</span>
          <input type="number" min="0" step="1" value="${state.total}" data-kind="total" aria-label="${escapeHtml(name)} total" />
        </label>
        <button type="button" class="remove-sub-btn" data-subject="${escapeHtml(name)}" title="Remove subject">×</button>
      </div>`;
    })
    .join("");

  container.querySelectorAll(".remove-sub-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const subName = e.currentTarget.dataset.subject;
      // Remove from all weekdays
      for (const day of weekdays) {
        currentSchedule.weekdays[day] = (currentSchedule.weekdays[day] || []).filter(
          (p) => p.subject !== subName
        );
      }
      renderWeekdaySchedule(activeWeekdayTab);
      syncSubjectsFromTimetable();
    });
  });
}

$("add-subject-btn").addEventListener("click", () => {
  const name = prompt("Enter new subject name:");
  if (name && name.trim()) {
    const clean = name.trim();
    if (!currentSchedule.weekdays[activeWeekdayTab]) {
      currentSchedule.weekdays[activeWeekdayTab] = [];
    }
    currentSchedule.weekdays[activeWeekdayTab].push({
      subject: clean,
      periods: 1,
    });
    renderWeekdaySchedule(activeWeekdayTab);
    syncSubjectsFromTimetable();
  }
});

function displayReview(data) {
  currentSchedule = {
    semester_start: data.semester_start || localISODate(),
    last_working_day: data.last_working_day || "",
    no_class_dates: Array.isArray(data.no_class_dates) ? data.no_class_dates : [],
    special_classes: Array.isArray(data.special_classes) ? data.special_classes : [],
    weekdays: data.weekdays || {
      Monday: [],
      Tuesday: [],
      Wednesday: [],
      Thursday: [],
      Friday: [],
      Saturday: [],
      Sunday: [],
    },
    subjects: Array.isArray(data.subjects) ? data.subjects : [],
    notes: Array.isArray(data.notes) ? data.notes : [],
  };

  $("start-date").value = currentSchedule.semester_start || localISODate();
  $("end-date").value = currentSchedule.last_working_day || "";
  const nextDay = new Date();
  nextDay.setDate(nextDay.getDate() + 1);
  $("future-start-date").value = localISODate(nextDay);

  renderWeekdaySchedule("Monday");
  renderHolidays();
  syncSubjectsFromTimetable();

  const notesBox = $("extraction-notes-box");
  if (currentSchedule.notes.length) {
    notesBox.innerHTML = `<strong>Document Extraction Notes &amp; Assumptions:</strong><br>${currentSchedule.notes.map((n) => `• ${escapeHtml(n)}`).join("<br>")}`;
    notesBox.classList.remove("hidden");
  } else {
    notesBox.classList.add("hidden");
  }

  $("review-area").classList.remove("hidden");
  $("review-area").scrollIntoView({ behavior: "smooth", block: "start" });
}

// "Enter schedule manually" workflow
$("manual-entry-btn").addEventListener("click", () => {
  clearError("analyze-error");
  const fallbackData = {
    semester_start: localISODate(),
    last_working_day: "",
    no_class_dates: [],
    special_classes: [],
    weekdays: {
      Monday: [{ subject: "Subject 1", periods: 1 }],
      Tuesday: [{ subject: "Subject 2", periods: 1 }],
      Wednesday: [{ subject: "Subject 3", periods: 1 }],
      Thursday: [{ subject: "Subject 1", periods: 1 }],
      Friday: [{ subject: "Subject 2", periods: 1 }],
      Saturday: [],
      Sunday: [],
    },
    subjects: ["Subject 1", "Subject 2", "Subject 3"],
    notes: ["Manual schedule initialization. Customize subjects and periods above."],
  };
  displayReview(fallbackData);
});

$("analyze-btn").addEventListener("click", async () => {
  clearError("analyze-error");
  $("review-area").classList.add("hidden");
  const cal = $("calendar-file").files[0];
  const tt = $("timetable-file").files[0];

  if (!cal || !tt) {
    showError("analyze-error", "Please select both an Academic Calendar file and a Weekly Timetable file first.");
    return;
  }

  const btn = $("analyze-btn");
  btn.disabled = true;
  btn.innerHTML = 'Extracting schedule… <span>◌</span>';
  $("analyze-status").textContent = "Processing documents locally...";

  try {
    const formData = new FormData();
    formData.append("calendar_file", cal);
    formData.append("timetable_file", tt);

    const res = await fetch("/api/analyze", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Document extraction failed.");
    }

    displayReview(data);
    const hasSubjects = (data.subjects && data.subjects.length > 0);
    const hasDates = Boolean(data.semester_start && data.last_working_day);
    const requiredDays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
    const hasWeekdaySchedule = Boolean(data.weekdays) && requiredDays.every((day) =>
      Array.isArray(data.weekdays[day]) && data.weekdays[day].length > 0
    );
    if (hasSubjects && hasDates && hasWeekdaySchedule) {
      $("analyze-status").innerHTML = `<span style="color:var(--green); font-weight:600;">✓ Extraction succeeded (${data.processing_time_seconds || 0}s).</span> Please review and verify.`;
    } else {
      $("analyze-status").innerHTML = `<span style="color:var(--orange); font-weight:600;">⚠ Partial extraction (${data.processing_time_seconds || 0}s).</span> Please verify subjects or dates below.`;
    }
  } catch (err) {
    showError("analyze-error", err.message || "Failed to parse documents.");
    $("analyze-status").innerHTML = `<span style="color:var(--red);">Extraction failed.</span>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Extract schedule from documents <span>▤</span>';
  }
});

$("reset-review-btn").addEventListener("click", () => {
  $("review-area").classList.add("hidden");
  $("semester-results").classList.add("hidden");
});

// ---------------------------------------------------------------------------
// Semester Projection Calculation
// ---------------------------------------------------------------------------
function collectSubjectStates() {
  const rows = document.querySelectorAll(".subject-row");
  const list = [];
  rows.forEach((row) => {
    const name = row.dataset.subject;
    const pVal = row.querySelector('[data-kind="present"]')?.value.trim();
    const tVal = row.querySelector('[data-kind="total"]')?.value.trim();

    if (!pVal || isNaN(Number(pVal)) || Number(pVal) < 0) {
      throw new Error(`Subject '${name}': Present classes must be a valid whole number >= 0.`);
    }
    if (!tVal || isNaN(Number(tVal)) || Number(tVal) < 0) {
      throw new Error(`Subject '${name}': Total classes held must be a valid whole number >= 0.`);
    }

    const present = Number(pVal);
    const total = Number(tVal);
    if (present > total) {
      throw new Error(`Subject '${name}': Present classes (${present}) cannot exceed total classes conducted (${total}).`);
    }

    list.push({ name, present, total });
  });
  return list;
}

$("project-btn").addEventListener("click", async () => {
  clearError("project-error");
  const resContainer = $("semester-results");
  resContainer.classList.add("hidden");

  try {
    const startDate = $("start-date").value;
    const endDate = $("end-date").value;
    const futureStartDate = $("future-start-date").value;

    if (!startDate || !endDate || !futureStartDate) {
      throw new Error("Please specify the semester start date, future-start date, and semester last working day.");
    }
    if (endDate < startDate) {
      throw new Error("The semester last working day must be on or after the semester start date.");
    }
    if (futureStartDate < startDate || futureStartDate > endDate) {
      throw new Error("The future-start date must be within the semester dates.");
    }

    const subjects = collectSubjectStates();
    if (!subjects.length) {
      throw new Error("No subjects defined. Please add at least one subject to your schedule.");
    }

    const target = getTargetPercentage("semester-target-select", "semester-custom-target");

    const payload = {
      target_percentage: target,
      start_date: startDate,
      future_start_date: futureStartDate,
      end_date: endDate,
      weekdays: currentSchedule.weekdays,
      no_class_dates: currentSchedule.no_class_dates,
      special_working_days: currentSchedule.special_classes || [],
      subjects: subjects,
    };

    const btn = $("project-btn");
    btn.disabled = true;
    btn.innerHTML = 'Calculating semester projections… <span>◌</span>';

    const response = await fetch("/api/project", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Semester projection calculation failed.");
    }

    renderSemesterResults(data);
    resContainer.classList.remove("hidden");
    resContainer.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (err) {
    showError("project-error", err.message || "An error occurred while calculating projections.");
  } finally {
    const btn = $("project-btn");
    btn.disabled = false;
    btn.innerHTML = 'Calculate semester attendance plan <span>→</span>';
  }
});

function renderSemesterResults(data) {
  const container = $("semester-results");

  const cardsHtml = data.subjects
    .map((sub) => {
      const attainable = sub.achievable;
      const currentPct = sub.current_percentage;
      const pillClass = attainable
        ? currentPct >= data.target_percentage
          ? "pill-good"
          : "pill-warn"
        : "pill-danger";

      const lastClassText = sub.last_scheduled_class_date
        ? formatDate(sub.last_scheduled_class_date)
        : "None scheduled";

      return `
      <article class="subject-result">
        <div class="subject-result-top">
          <div>
            <strong>${escapeHtml(sub.name)}</strong>
            <small style="display:block; color:var(--muted); font-size:10px; margin-top:2px;">
              Last class: ${lastClassText}
            </small>
          </div>
          <span class="pct-pill ${pillClass}">
            ${currentPct.toFixed(1)}% now
          </span>
        </div>

        <div class="progress-track">
          <div class="progress-fill" style="width: ${Math.min(100, Math.max(0, currentPct))}%"></div>
        </div>

        <div class="subject-stats">
          <div>
            <span>Future periods</span>
            <strong>${sub.future_classes}</strong>
          </div>
          <div>
            <span>Need to attend</span>
            <strong class="${attainable ? "metric-green" : "metric-red"}">${sub.classes_to_attend}</strong>
          </div>
          <div>
            <span>Can safely skip</span>
            <strong class="${sub.classes_can_skip > 0 ? "metric-orange" : "metric-purple"}">${sub.classes_can_skip}</strong>
          </div>
          <div>
            <span>If attend all</span>
            <strong>${sub.projected_if_attend_all.toFixed(1)}%</strong>
          </div>
        </div>

        ${
          !attainable
            ? `<div class="result-note" style="border-left-color: var(--red); color: var(--red); background: #fff5f5; margin-top:10px;">
                <strong>Target Unachievable:</strong> Even with 100% attendance in all ${sub.future_classes} remaining classes,
                your maximum possible attendance will be ${sub.projected_if_attend_all.toFixed(2)}%.
              </div>`
            : ""
        }
        ${sub.warning ? `<div class="result-note" style="margin-top:10px;">${escapeHtml(sub.warning)}</div>` : ""}
      </article>`;
    })
    .join("");

  container.innerHTML = `
    <div class="result-header">
      <div>
        <h4>Semester Attendance Outlook</h4>
        <p>${formatDate(data.start_date)} through ${formatDate(data.end_date)} · ${data.total_teaching_days} instructional days simulated</p>
      </div>
      <span class="result-target">${data.target_percentage}% Minimum Target</span>
    </div>
    <div class="subject-result-list">
      ${cardsHtml}
    </div>
    <div class="result-note" style="margin-top:16px;">
      <strong>Mathematical projection note:</strong> These numbers represent mathematical attendance boundaries based on your reviewed timetable. Always verify departmental attendance policies, medical leave exemptions, and practical exam regulations.
    </div>`;
}
