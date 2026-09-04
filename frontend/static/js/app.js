/* ════════════════════════════════════════════════════════════════
   BAYANUL LISAN - TELEGRAM MINI APP INTERACTIVE CLIENT
   ════════════════════════════════════════════════════════════════ */

// State
let tg = window.Telegram ? window.Telegram.WebApp : null;
let currentUser = null;
let categories = [];
let activeCategory = null;
let currentCourse = null;
let currentLesson = null;
let activeTab = 'home';

// Speech Recognition State
let recognition = null;
let isRecording = false;

// ─── Initialize Application ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    initTelegramApp();
    await authenticateUser();
    await loadCategories();
    await loadCourses();
    setupSpeechRecognition();
});

function initTelegramApp() {
    if (tg) {
        tg.ready();
        tg.expand();
        // Set header color
        try {
            tg.setHeaderColor('#0b0f19');
            tg.setBackgroundColor('#0b0f19');
        } catch (e) {}
    }
}

// ─── Authentication ────────────────────────────────────────────────
async function authenticateUser() {
    let payload = {};
    if (tg && tg.initData) {
        payload.initData = tg.initData;
    } else {
        // Fallback for browser dev testing
        let storedId = localStorage.getItem('bayan_user_id');
        if (!storedId) {
            storedId = '6017983119'; // Default dev admin test ID
            localStorage.setItem('bayan_user_id', storedId);
        }
        payload.userId = storedId;
        payload.name = "Dilmurod";
    }

    try {
        const res = await fetch('/api/webapp/auth', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            currentUser = data.user;
            renderUserBadge();
            if (currentUser.isAdmin) {
                document.getElementById('nav-admin-tab').style.display = 'flex';
            }
        }
    } catch (err) {
        console.error("Auth error:", err);
    }
}

function renderUserBadge() {
    const el = document.getElementById('user-badge-container');
    if (!el || !currentUser) return;
    el.innerHTML = `
        <div class="user-badge" onclick="switchTab('profile')">
            <span>👤 ${currentUser.name}</span>
            <span class="score">⭐ ${currentUser.score || 0}</span>
        </div>
    `;
}

// ─── Categories & Courses ──────────────────────────────────────────
async function loadCategories() {
    try {
        const res = await fetch('/api/webapp/categories');
        const data = await res.json();
        if (data.success) {
            categories = data.categories;
            renderCategoriesBar();
        }
    } catch (e) {
        console.error("Categories load failed:", e);
    }
}

function renderCategoriesBar() {
    const bar = document.getElementById('categories-bar');
    if (!bar) return;

    let html = `
        <div class="cat-chip ${!activeCategory ? 'active' : ''}" onclick="selectCategory(null)">
            ✨ Barcha kurslar
        </div>
    `;

    categories.forEach(cat => {
        const isAct = activeCategory === cat.id ? 'active' : '';
        html += `
            <div class="cat-chip ${isAct}" onclick="selectCategory('${cat.id}')">
                ${cat.icon} ${cat.title}
            </div>
        `;
    });

    bar.innerHTML = html;
}

function selectCategory(catId) {
    activeCategory = catId;
    renderCategoriesBar();
    loadCourses(catId);
}

async function loadCourses(catId = null) {
    const grid = document.getElementById('courses-grid');
    if (!grid) return;

    grid.innerHTML = '<div style="color:var(--text-secondary); grid-column:1/-1; text-align:center; padding:40px;">⏳ Kurslar yuklanmoqda...</div>';

    let url = '/api/webapp/courses';
    const params = new URLSearchParams();
    if (catId) params.append('category', catId);
    if (currentUser) params.append('userId', currentUser.id);

    if (params.toString()) url += '?' + params.toString();

    try {
        const res = await fetch(url);
        const data = await res.json();
        if (data.success) {
            renderCoursesGrid(data.courses);
        } else {
            grid.innerHTML = '<div style="color:var(--danger); grid-column:1/-1; text-align:center;">Kurslarni yuklashda xatolik yuz berdi.</div>';
        }
    } catch (e) {
        grid.innerHTML = '<div style="color:var(--danger); grid-column:1/-1; text-align:center;">Server bilan aloqa uzildi.</div>';
    }
}

function renderCoursesGrid(courses) {
    const grid = document.getElementById('courses-grid');
    if (!grid) return;

    if (!courses || courses.length === 0) {
        grid.innerHTML = `
            <div style="grid-column:1/-1; text-align:center; padding:40px; background:var(--bg-card); border-radius:var(--radius-md);">
                <p style="color:var(--text-secondary); margin-bottom:12px;">Ushbu bo'limda hozircha kurslar mavjud emas.</p>
                <button class="btn-sm btn-primary" onclick="switchTab('quizzes')">📝 Testlarni yechish</button>
            </div>
        `;
        return;
    }

    grid.innerHTML = courses.map(c => {
        const badge = c.hasAccess 
            ? '<span class="course-badge badge-unlocked">✅ Ochiq</span>' 
            : '<span class="course-badge badge-locked">🔒 ' + formatPrice(c.price) + ' UZS</span>';

        const thumb = c.thumbnail || 'https://images.unsplash.com/photo-1584286595398-a59f21d313f5?w=600&auto=format&fit=crop&q=80';

        return `
            <div class="course-card" onclick="openCourse('${c.id}')">
                <div class="course-thumb-box">
                    <img src="${thumb}" alt="${c.title}" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1584286595398-a59f21d313f5?w=600&auto=format&fit=crop&q=80'">
                    ${badge}
                </div>
                <div class="course-body">
                    <h3>${c.courseNumber}-kurs: ${c.title}</h3>
                    <p>${c.description || "Arab tili grammatikasi va nutq darslari"}</p>
                    <div class="course-footer">
                        <span class="course-price">${formatPrice(c.price)} UZS</span>
                        <button class="btn-sm ${c.hasAccess ? 'btn-primary' : 'btn-gold'}">
                            ${c.hasAccess ? "Darslarni ko'rish &rarr;" : "Sotib olish 💳"}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ─── Course Detail & Lessons ───────────────────────────────────────
async function openCourse(courseId) {
    try {
        let url = `/api/webapp/courses/${courseId}`;
        if (currentUser) url += `?userId=${currentUser.id}`;

        const res = await fetch(url);
        const data = await res.json();
        if (!data.success) {
            showToast(data.error || "Kurs topilmadi");
            return;
        }

        currentCourse = data.course;
        renderCourseDetailView();
        switchView('course-detail-view');
    } catch (e) {
        showToast("Yuklashda xatolik");
    }
}

function renderCourseDetailView() {
    const c = currentCourse;
    if (!c) return;

    document.getElementById('cd-title').textContent = c.title;
    document.getElementById('cd-desc').textContent = c.description || "Ushbu kurs video darslar, talaffuz mashqlari va amaliy testlardan iborat.";
    
    // Payment banner if locked
    const payBox = document.getElementById('cd-pay-box');
    if (!c.hasAccess) {
        payBox.style.display = 'block';
        payBox.innerHTML = `
            <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); border: 1px solid #6366f1; border-radius: var(--radius-md); padding: 16px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div>
                    <h4 style="color:#fff; margin-bottom:4px;">🔒 Kurs to'liq yopiq</h4>
                    <p style="color:#c7d2fe; font-size:13px;">Barcha video darslar va uyga vazifalarga kirish uchun to'lov qiling.</p>
                </div>
                <button class="btn-sm btn-gold" onclick="openCheckoutModal('${c.id}', ${c.price}, '${c.title.replace(/'/g, "\\'")}')">
                    💳 To'lov qilish (${formatPrice(c.price)} UZS)
                </button>
            </div>
        `;
    } else {
        payBox.style.display = 'none';
    }

    // Lessons list
    const listEl = document.getElementById('cd-lessons-list');
    if (!c.lessons || c.lessons.length === 0) {
        listEl.innerHTML = '<div style="color:var(--text-secondary); padding:20px 0;">Darslar tez orada yuklanadi.</div>';
        return;
    }

    listEl.innerHTML = c.lessons.map(l => {
        const isLocked = l.isLocked;
        return `
            <div style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px 18px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; cursor:${isLocked ? 'not-allowed' : 'pointer'}; opacity:${isLocked ? '0.7' : '1'}; transition:border-color 0.2s;" onclick="${isLocked ? `openCheckoutModal('${c.id}', ${c.price}, '${c.title}')` : `openLesson('${c.id}', ${l.lessonNumber})`}">
                <div>
                    <div style="font-weight:700; font-size:15px; margin-bottom:3px;">
                        ${isLocked ? '🔒' : '▶️'} ${l.lessonNumber}-dars: ${l.title}
                    </div>
                    <div style="font-size:12px; color:var(--text-secondary);">
                        ${l.description || (isLocked ? 'To\'lovdan so\'ng ochiladi' : 'Video va ovozli talaffuz mashqi')}
                    </div>
                </div>
                <button class="btn-sm ${isLocked ? 'btn-gold' : 'btn-primary'}" style="white-space:nowrap;">
                    ${isLocked ? 'Qulfni ochish' : 'Boshlash &rarr;'}
                </button>
            </div>
        `;
    }).join('');
}

// ─── Lesson Player & Arabic Speech Practice ─────────────────────────
async function openLesson(courseId, lessonNum) {
    try {
        let url = `/api/webapp/lessons/${courseId}/${lessonNum}`;
        if (currentUser) url += `?userId=${currentUser.id}`;

        const res = await fetch(url);
        const data = await res.json();
        if (!data.success) {
            showToast(data.error || "Dars ochilmadi");
            if (data.locked) openCheckoutModal(courseId, 150000, "Kurs");
            return;
        }

        currentLesson = data.lesson;
        renderLessonPlayerView();
        switchView('lesson-player-view');
    } catch (e) {
        showToast("Darsni yuklashda xatolik");
    }
}

function renderLessonPlayerView() {
    const l = currentLesson;
    if (!l) return;

    document.getElementById('lp-title').textContent = `${l.lessonNumber}-dars: ${l.title}`;
    document.getElementById('lp-course-name').textContent = l.courseTitle;
    document.getElementById('lp-desc').textContent = l.description || "";

    // Video Player
    const videoBox = document.getElementById('lp-video-box');
    if (l.videoUrl) {
        videoBox.style.display = 'block';
        let src = l.videoUrl;
        if (src.includes('youtube.com/watch?v=')) {
            src = src.replace('watch?v=', 'embed/');
        }
        videoBox.innerHTML = `<iframe src="${src}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`;
    } else {
        videoBox.style.display = 'none';
    }

    // Speech Recognition Phrase
    const phrase = l.phrase || "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ";
    const trans = l.translation || "Mehribon va rahmli Alloh nomi bilan";
    document.getElementById('speech-expected-phrase').textContent = phrase;
    document.getElementById('speech-translation').textContent = trans;
    document.getElementById('speech-result').style.display = 'none';
}

// ─── Web Speech Recognition (Nutq mashqi) ───────────────────────────
function setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn("Speech recognition is not supported in this browser.");
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'ar-SA';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
        isRecording = true;
        const micBtn = document.getElementById('mic-btn');
        if (micBtn) micBtn.classList.add('recording');
        const resEl = document.getElementById('speech-result');
        resEl.style.display = 'block';
        resEl.className = 'speech-result-box';
        resEl.innerHTML = '🎙 <i>Tinglanmoqda... Arabcha talaffuz qiling!</i>';
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        checkPronunciation(transcript);
    };

    recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        const resEl = document.getElementById('speech-result');
        resEl.style.display = 'block';
        resEl.className = 'speech-result-box speech-result-retry';
        resEl.innerHTML = '❌ Ovoz aniqlanmadi. Qaytadan urinib ko\'ring.';
    };

    recognition.onend = () => {
        isRecording = false;
        const micBtn = document.getElementById('mic-btn');
        if (micBtn) micBtn.classList.remove('recording');
    };
}

function toggleRecording() {
    if (!recognition) {
        showToast("Brauzeringiz ovozli tanib olishni qo'llab-quvvatlamaydi");
        return;
    }

    if (isRecording) {
        recognition.stop();
    } else {
        try {
            recognition.start();
        } catch (e) {
            recognition.stop();
        }
    }
}

function checkPronunciation(spokenText) {
    const expected = (currentLesson?.phrase || "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ");
    
    // Normalize Arabic text (remove harakat/diacritics and punctuation)
    const cleanSpoken = cleanArabicText(spokenText);
    const cleanExpected = cleanArabicText(expected);

    const isMatch = cleanSpoken.includes(cleanExpected) || cleanExpected.includes(cleanSpoken) || (cleanSpoken.length > 0 && cleanExpected.length > 0 && similarity(cleanSpoken, cleanExpected) > 0.6);

    const resEl = document.getElementById('speech-result');
    resEl.style.display = 'block';

    if (isMatch) {
        resEl.className = 'speech-result-box speech-result-success';
        resEl.innerHTML = `
            <div>✅ <b>Mashalloh! Talaffuz to'g'ri!</b></div>
            <div class="font-arabic" style="font-size:20px; margin-top:4px;">Siz aytdingiz: "${spokenText}"</div>
        `;
        if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
    } else {
        resEl.className = 'speech-result-box speech-result-retry';
        resEl.innerHTML = `
            <div>⚠️ <b>Yana bir bor urinib ko'ring!</b></div>
            <div class="font-arabic" style="font-size:18px; margin-top:4px;">Eshitildi: "${spokenText}"</div>
        `;
        if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('warning');
    }
}

function cleanArabicText(txt) {
    if (!txt) return "";
    return txt.replace(/[\u064B-\u065F\u0670]/g, '') // Remove harakat
              .replace(/[^\u0600-\u06FF\s]/g, '')     // Keep only arabic & spaces
              .trim();
}

function similarity(s1, s2) {
    let longer = s1.length > s2.length ? s1 : s2;
    let shorter = s1.length > s2.length ? s2 : s1;
    if (longer.length === 0) return 1.0;
    return (longer.length - editDistance(longer, shorter)) / parseFloat(longer.length);
}

function editDistance(s1, s2) {
    s1 = s1.toLowerCase();
    s2 = s2.toLowerCase();
    let costs = [];
    for (let i = 0; i <= s1.length; i++) {
        let lastValue = i;
        for (let j = 0; j <= s2.length; j++) {
            if (i === 0) costs[j] = j;
            else {
                if (j > 0) {
                    let newValue = costs[j - 1];
                    if (s1.charAt(i - 1) !== s2.charAt(j - 1))
                        newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
                    costs[j - 1] = lastValue;
                    lastValue = newValue;
                }
            }
        }
        if (i > 0) costs[s2.length] = lastValue;
    }
    return costs[s2.length];
}

// ─── Quizzes Flow ──────────────────────────────────────────────────
let quizList = [];
let currentQuizIndex = 0;
let quizScore = 0;

async function startQuizzes(category = null) {
    try {
        let url = '/api/webapp/quizzes';
        if (category) url += `?category=${category}`;
        const res = await fetch(url);
        const data = await res.json();

        if (data.success && data.quizzes && data.quizzes.length > 0) {
            quizList = data.quizzes;
            currentQuizIndex = 0;
            quizScore = 0;
            renderCurrentQuestion();
            switchView('quiz-runner-view');
        } else {
            showToast("Ushbu bo'lim bo'yicha hozircha testlar yo'q");
        }
    } catch (e) {
        showToast("Testlarni yuklashda xatolik");
    }
}

function renderCurrentQuestion() {
    const container = document.getElementById('quiz-question-box');
    if (!container || !quizList[currentQuizIndex]) return;

    const q = quizList[currentQuizIndex];
    document.getElementById('quiz-progress-text').textContent = `Savol ${currentQuizIndex + 1} / ${quizList.length}`;

    let optionsHtml = '';
    const opts = q.options || [];
    opts.forEach((opt, idx) => {
        optionsHtml += `
            <button class="quiz-option-btn" onclick="handleQuizAnswer(${idx}, ${q.correct_option})">
                ${idx + 1}) ${opt}
            </button>
        `;
    });

    container.innerHTML = `
        <h3 style="font-size:18px; margin-bottom:18px; line-height:1.4;">${q.question}</h3>
        ${optionsHtml}
    `;
}

function handleQuizAnswer(selectedIdx, correctIdx) {
    const btns = document.querySelectorAll('.quiz-option-btn');
    btns.forEach((btn, idx) => {
        btn.disabled = true;
        if (idx === correctIdx) btn.classList.add('correct');
        else if (idx === selectedIdx) btn.classList.add('wrong');
    });

    if (selectedIdx === correctIdx) {
        quizScore++;
        if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
    } else {
        if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
    }

    setTimeout(() => {
        currentQuizIndex++;
        if (currentQuizIndex < quizList.length) {
            renderCurrentQuestion();
        } else {
            renderQuizFinish();
        }
    }, 1200);
}

function renderQuizFinish() {
    const container = document.getElementById('quiz-question-box');
    const percent = Math.round((quizScore / quizList.length) * 100);
    container.innerHTML = `
        <div style="text-align:center; padding:20px 0;">
            <div style="font-size:54px; margin-bottom:12px;">🏆</div>
            <h2 style="font-size:22px; margin-bottom:8px;">Test yakunlandi!</h2>
            <p style="color:var(--text-secondary); margin-bottom:16px;">
                To'g'ri javoblar: <b style="color:var(--primary); font-size:18px;">${quizScore} / ${quizList.length}</b> (${percent}%)
            </p>
            <button class="btn-sm btn-primary" onclick="switchTab('home')">🏠 Bosh sahifaga qaytish</button>
        </div>
    `;
}

// ─── Click & Payme Checkout Modal ──────────────────────────────────
let pendingCheckoutCourseId = null;

function openCheckoutModal(courseId, price, title) {
    pendingCheckoutCourseId = courseId;
    document.getElementById('modal-course-title').textContent = title;
    document.getElementById('modal-course-price').textContent = formatPrice(price) + " UZS";
    document.getElementById('checkout-modal').classList.add('active');
}

function closeCheckoutModal() {
    document.getElementById('checkout-modal').classList.remove('active');
}

async function startPayment(provider) {
    if (!currentUser) {
        showToast("Foydalanuvchi aniqlanmadi");
        return;
    }

    try {
        showToast("To'lov havolasi tayyorlanmoqda...");
        const res = await fetch('/api/webapp/payments/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                userId: currentUser.id,
                courseId: pendingCheckoutCourseId,
                provider: provider
            })
        });
        const data = await res.json();
        if (data.success && data.paymentUrl) {
            closeCheckoutModal();
            if (tg && tg.openLink) {
                tg.openLink(data.paymentUrl);
            } else {
                window.open(data.paymentUrl, '_blank');
            }
        } else {
            showToast(data.error || "To'lov xatoligi");
        }
    } catch (e) {
        showToast("To'lovni boshlashda xatolik");
    }
}

// ─── Homework Submit ────────────────────────────────────────────────
async function submitHomework() {
    const text = document.getElementById('hw-text-input').value;
    const audioUrl = document.getElementById('hw-audio-input').value;

    if (!text && !audioUrl) {
        showToast("Iltimos, matn yoki audio havolani kiriting");
        return;
    }

    try {
        const res = await fetch('/api/webapp/homework/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                userId: currentUser.id,
                courseId: currentLesson.courseId,
                lessonNumber: currentLesson.lessonNumber,
                text: text,
                audioUrl: audioUrl
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast("✅ Vazifa ustozga yuborildi!");
            document.getElementById('hw-text-input').value = '';
            document.getElementById('hw-audio-input').value = '';
        }
    } catch (e) {
        showToast("Vazifani yuborishda xatolik");
    }
}

// ─── Tab & View Navigation ──────────────────────────────────────────
function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active'));
    const btn = document.getElementById(`nav-${tab}-btn`);
    if (btn) btn.classList.add('active');

    if (tab === 'home') {
        switchView('home-view');
        loadCourses(activeCategory);
    } else if (tab === 'quizzes') {
        switchView('quizzes-catalog-view');
    } else if (tab === 'profile') {
        renderProfileView();
        switchView('profile-view');
    } else if (tab === 'admin') {
        switchView('admin-view');
        adminSwitchTab('courses');
    }
}

function switchView(viewId) {
    document.querySelectorAll('.app-view').forEach(v => v.style.display = 'none');
    const target = document.getElementById(viewId);
    if (target) target.style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function renderProfileView() {
    if (!currentUser) return;
    document.getElementById('prof-name').textContent = currentUser.name;
    document.getElementById('prof-id').textContent = `ID: ${currentUser.id}`;
    document.getElementById('prof-score').textContent = currentUser.score || 0;
    document.getElementById('prof-courses-count').textContent = (currentUser.allowedCourses || []).length;
}

// ─── Helpers ────────────────────────────────────────────────────────
function formatPrice(num) {
    return (num || 0).toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

function showToast(msg) {
    const el = document.getElementById('toast-msg');
    if (!el) return;
    el.textContent = msg;
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 2600);
}

// ─── Admin Panel ─────────────────────────────────────────────────────
let adminCoursesList = [];
let adminSelectedCourseId = null;

function adminSwitchTab(tab) {
    const coursesTab = document.getElementById('admin-courses-tab');
    const lessonsTab = document.getElementById('admin-lessons-tab');
    const coursesBtn = document.getElementById('admin-tab-courses-btn');
    const lessonsBtn = document.getElementById('admin-tab-lessons-btn');

    if (tab === 'courses') {
        coursesTab.style.display = 'block';
        lessonsTab.style.display = 'none';
        coursesBtn.className = 'btn-sm btn-primary';
        lessonsBtn.style.cssText = 'flex:1;padding:10px;background:var(--bg-card);color:var(--text-secondary);';
        adminLoadCourses();
    } else {
        coursesTab.style.display = 'none';
        lessonsTab.style.display = 'block';
        lessonsBtn.className = 'btn-sm btn-primary';
        lessonsBtn.style.cssText = 'flex:1;padding:10px;';
        coursesBtn.style.cssText = 'flex:1;padding:10px;background:var(--bg-card);color:var(--text-secondary);';
        adminPopulateCourseSelect();
    }
}

async function adminLoadCourses() {
    const listEl = document.getElementById('admin-courses-list');
    listEl.innerHTML = '<div style="color:var(--text-secondary);text-align:center;padding:30px;">⏳ Yuklanmoqda...</div>';

    const res = await fetch('/api/webapp/courses');
    const data = await res.json();
    adminCoursesList = data.courses || [];

    if (!adminCoursesList.length) {
        listEl.innerHTML = '<div style="color:var(--text-secondary);text-align:center;padding:30px;">Hozircha kurslar yo\'q. ➕ Yangi Kurs tugmasini bosing.</div>';
        return;
    }

    listEl.innerHTML = adminCoursesList.map(c => `
        <div style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:14px 16px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;gap:12px;">
            <div>
                <div style="font-weight:700;font-size:15px;">${c.courseNumber}-kurs: ${c.title}</div>
                <div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">${c.category} · ${formatPrice(c.price)} UZS</div>
            </div>
            <button class="btn-sm btn-primary" onclick="adminShowCourseForm('${c.id}')">✏️ Tahrir</button>
        </div>
    `).join('');
}

function adminPopulateCourseSelect() {
    const sel = document.getElementById('admin-lesson-course-select');
    sel.innerHTML = '<option value="">— Kurs tanlang —</option>';
    (adminCoursesList || []).forEach(c => {
        sel.innerHTML += `<option value="${c.id}">${c.courseNumber}-kurs: ${c.title} (${c.category})</option>`;
    });
    if (!adminCoursesList.length) {
        // Load if not yet loaded
        fetch('/api/webapp/courses').then(r => r.json()).then(data => {
            adminCoursesList = data.courses || [];
            adminPopulateCourseSelect();
        });
    }
}

async function adminLoadLessons(courseId) {
    adminSelectedCourseId = courseId;
    const listEl = document.getElementById('admin-lessons-list');
    const addBtn = document.getElementById('admin-add-lesson-btn');

    if (!courseId) {
        listEl.innerHTML = '<div style="color:var(--text-secondary);text-align:center;padding:30px;">Yuqoridan kurs tanlang</div>';
        addBtn.style.display = 'none';
        return;
    }

    addBtn.style.display = 'inline-block';
    listEl.innerHTML = '<div style="color:var(--text-secondary);text-align:center;padding:20px;">⏳ Yuklanmoqda...</div>';

    const res = await fetch(`/api/webapp/courses/${courseId}`);
    const data = await res.json();
    const lessons = data.course?.lessons || [];

    if (!lessons.length) {
        listEl.innerHTML = '<div style="color:var(--text-secondary);text-align:center;padding:30px;">Bu kursda hozircha darslar yo\'q. ➕ Yangi Dars tugmasini bosing.</div>';
        return;
    }

    listEl.innerHTML = lessons.map(l => `
        <div style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:14px 16px;margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-weight:700;font-size:15px;">${l.lessonNumber}-dars: ${l.title}</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">
                        ${l.type === 'video' ? '🎬 Video' : l.type === 'pronunciation' ? '🎙 Talaffuz' : '📄 PDF'}
                        ${l.videoUrl ? ' · <span style="color:var(--primary);">✅ Video mavjud</span>' : ' · <span style="color:var(--danger);">⚠️ Video yo\'q</span>'}
                        ${l.isLocked ? '' : ' · 👁 Preview'}
                    </div>
                </div>
                <button class="btn-sm btn-primary" onclick="adminShowLessonForm('${l.lessonNumber}', ${JSON.stringify(l).replace(/'/g, "\\'")})">✏️</button>
            </div>
            ${l.videoUrl ? `<div style="font-size:11px;color:var(--text-muted);margin-top:6px;word-break:break-all;">🔗 ${l.videoUrl.substring(0,60)}...</div>` : ''}
        </div>
    `).join('');
}

// ── Course Form ──
function adminShowCourseForm(courseId) {
    const course = courseId ? adminCoursesList.find(c => c.id === courseId) : null;
    document.getElementById('admin-course-modal-title').textContent = course ? '✏️ Kursni Tahrirlash' : '➕ Yangi Kurs';
    document.getElementById('acf-course-id').value = courseId || '';
    document.getElementById('acf-category').value = course?.category || 'Sarf';
    document.getElementById('acf-number').value = course?.courseNumber || '';
    document.getElementById('acf-title').value = course?.title || '';
    document.getElementById('acf-desc').value = course?.description || '';
    document.getElementById('acf-price').value = course?.price || 150000;
    document.getElementById('acf-thumbnail').value = course?.thumbnail || '';
    document.getElementById('admin-course-modal').classList.add('active');
}

async function adminSaveCourse() {
    if (!currentUser?.isAdmin) { showToast("❌ Siz admin emassiz"); return; }
    const courseId = document.getElementById('acf-course-id').value || null;
    const title = document.getElementById('acf-title').value.trim();
    const courseNumber = document.getElementById('acf-number').value;
    if (!title || !courseNumber) { showToast("⚠️ Sarlavha va Raqam majburiy"); return; }

    const payload = {
        userId: currentUser.id,
        courseId: courseId || undefined,
        category: document.getElementById('acf-category').value,
        courseNumber: parseInt(courseNumber),
        title,
        description: document.getElementById('acf-desc').value,
        price: parseInt(document.getElementById('acf-price').value) || 150000,
        thumbnail: document.getElementById('acf-thumbnail').value,
        isPublished: true,
    };

    const res = await fetch('/api/webapp/admin/save_course', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.success) {
        showToast('✅ Kurs saqlandi!');
        closeAdminModal('admin-course-modal');
        await adminLoadCourses();
    } else {
        showToast('❌ ' + (data.error || 'Xatolik'));
    }
}

// ── Lesson Form ──
function adminShowLessonForm(lessonNum, lessonData) {
    const courseId = adminSelectedCourseId;
    if (!courseId) { showToast("Avval kursni tanlang"); adminSwitchTab('lessons'); return; }

    document.getElementById('admin-lesson-modal-title').textContent = lessonNum ? '✏️ Darsni Tahrirlash' : '🎬 Yangi Dars';
    document.getElementById('alf-course-id').value = courseId;
    document.getElementById('alf-lesson-num').value = lessonNum || '';
    document.getElementById('alf-number').value = lessonNum || '';
    document.getElementById('alf-title').value = lessonData?.title || '';
    document.getElementById('alf-type').value = lessonData?.type || 'video';
    document.getElementById('alf-video').value = lessonData?.videoUrl || '';
    document.getElementById('alf-phrase').value = lessonData?.phrase || '';
    document.getElementById('alf-translation').value = lessonData?.translation || '';
    document.getElementById('alf-desc').value = lessonData?.description || '';
    document.getElementById('alf-preview').checked = !lessonData?.isLocked;
    document.getElementById('admin-lesson-modal').classList.add('active');
}

async function adminSaveLesson() {
    if (!currentUser?.isAdmin) { showToast("❌ Siz admin emassiz"); return; }
    const courseId = document.getElementById('alf-course-id').value;
    const lessonNumber = document.getElementById('alf-number').value;
    const title = document.getElementById('alf-title').value.trim();
    if (!courseId || !lessonNumber || !title) { showToast("⚠️ Kurs, Dars Raqami va Sarlavha majburiy"); return; }

    const payload = {
        userId: currentUser.id,
        courseId,
        lessonNumber: parseFloat(lessonNumber),
        title,
        type: document.getElementById('alf-type').value,
        videoUrl: document.getElementById('alf-video').value.trim(),
        phrase: document.getElementById('alf-phrase').value.trim(),
        translation: document.getElementById('alf-translation').value.trim(),
        description: document.getElementById('alf-desc').value.trim(),
        isPreview: document.getElementById('alf-preview').checked,
    };

    const res = await fetch('/api/webapp/admin/save_lesson', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.success) {
        showToast('✅ Dars saqlandi!');
        closeAdminModal('admin-lesson-modal');
        await adminLoadLessons(courseId);
    } else {
        showToast('❌ ' + (data.error || 'Xatolik'));
    }
}

function closeAdminModal(id) {
    document.getElementById(id).classList.remove('active');
}
