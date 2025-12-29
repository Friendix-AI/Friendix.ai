// --- Backend URL ---
const BACKEND_URL = '';

// --- Default Avatar Path ---
const DEFAULT_AVATAR_STATIC_PATH = "/avatars/default_avatar.png";

// --- Elements ---
const luvisaProfilePic = document.getElementById('luvisaProfilePic');
const closeLuvisaProfileBtn = document.getElementById('closeLuvisaProfileBtn');
const chatbox = document.getElementById('chatbox');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const userAvatarHeader = document.getElementById('userAvatarHeader');
const userAvatarWrapper = document.getElementById('userAvatarWrapper');
const dropdown = document.getElementById('profileDropdown');
const dropdownAvatar = document.getElementById('dropdownAvatar');
const dropdownName = document.getElementById('dropdownName');
const dropdownStatus = document.getElementById('dropdownStatus');
const headerUserName = document.getElementById('headerUserName');
const menuIcon = document.getElementById('menuIcon');
const sidebarMenu = document.getElementById('sidebarMenu');
const sidebarOverlay = document.getElementById('sidebarOverlay');
const closeSidebarIcon = document.getElementById('closeSidebarIcon');
const luvisaProfilePanel = document.getElementById('luvisaProfilePanel');
const profilePanelAvatar = document.getElementById('profilePanelAvatar'); // Added missing definition
const headerForgetBtn = document.getElementById('headerForgetBtn');
const settingsIcon = document.getElementById('settingsIcon');
// Revert: Removed custom elements

// --- Early User Badge ---
const earlyUserBadge = document.getElementById('earlyUserBadge');

// --- XP / Bond System Elements ---
const sidebarLevelDisplay = document.getElementById('sidebarLevelDisplay');
const profileLevelDisplay = document.getElementById('profileLevelDisplay');
const profileXpDisplay = document.getElementById('profileXpDisplay');
const profileXpProgressBar = document.getElementById('profileXpProgressBar');

// --- Settings Dropdown Elements ---
const settingsDropdown = document.getElementById('settingsDropdown');
const menuEditProfileBtn = document.getElementById('menuEditProfileBtn');
const menuThemeBtn = document.getElementById('menuThemeBtn');
const menuLogoutBtn = document.getElementById('menuLogoutBtn');
const sidebarLogoutBtn = document.getElementById('logoutBtn');
const themeDropdown = document.getElementById('themeDropdown');
const themeBackBtn = document.getElementById('themeBackBtn');
const themeLightBtn = document.getElementById('themeLightBtn');
const themeDarkBtn = document.getElementById('themeDarkBtn');
const themeSystemBtn = document.getElementById('themeSystemBtn');
const menuPersonalizationBtn = document.getElementById('menuPersonalizationBtn');
const personalizationDropdown = document.getElementById('personalizationDropdown');
const personalizationBackBtn = document.getElementById('personalizationBackBtn');
const personalizationResetBtn = document.getElementById('personalizationResetBtn');
const bgGridContainer = document.getElementById('bgGridContainer');
const menuNotificationBtn = document.getElementById('menuNotificationBtn');
const notificationDropdown = document.getElementById('notificationDropdown');
const notificationBackBtn = document.getElementById('notificationBackBtn');
const notificationDot = document.getElementById('notificationDot');
const notificationListContainer = document.getElementById('notificationListContainer');
const notificationListEmpty = document.getElementById('notificationListEmpty');

const emojiBtn = document.getElementById('emojiBtn');
const emojiPicker = document.getElementById('emojiPicker');
const chatContainer = document.getElementById('chatContainer');
const luvisaChatButton = document.getElementById('luvisaChatButton');
const coderChatButton = document.getElementById('coderChatButton');
const coachChatButton = document.getElementById('coachChatButton');

const chatTitleName = document.querySelector('.chat-title span');
const chatTitleStatus = document.querySelector('.chat-title small');
const attachBtn = document.getElementById('attachBtn');
const fileInput = document.getElementById('fileInput');
const filePreview = document.getElementById('filePreview');
const railChatBtn = document.getElementById('railChatBtn');
const railTogetherBtn = document.getElementById('railTogetherBtn');
const railSettingsBtn = document.getElementById('railSettingsBtn');
const railProfileBtn = document.getElementById('railProfileBtn');
const railUserAvatar = document.getElementById('railUserAvatar');
const menuJournalBtn = document.getElementById('menuJournalBtn');
const journalModal = document.getElementById('journalModal');
const closeJournalBtn = document.getElementById('closeJournalBtn');
const journalContent = document.getElementById('journalContent');
const journalLockOverlay = document.getElementById('journalLockOverlay');
const unlockJournalBtn = document.getElementById('unlockJournalBtn');
const journalCostDisplay = document.getElementById('journalCostDisplay');
const journalErrorMsg = document.getElementById('journalErrorMsg');
const journalDate = document.getElementById('journalDate');

let username = localStorage.getItem('luvisa_user') || null;
let unreadNotifications = [];
let userXP = 0;
let userLevel = 1;
let nextLevelXP = 50;
let currentCompanion = 'luvisa';
let selectedFiles = [];

function scrollToBottom() {
    if (!chatbox) return;
    chatbox.scrollTop = chatbox.scrollHeight;
    setTimeout(() => { chatbox.scrollTop = chatbox.scrollHeight; }, 10);
    requestAnimationFrame(() => { chatbox.scrollTop = chatbox.scrollHeight; });
}

headerForgetBtn?.addEventListener('click', async () => {
    if (!confirm('Do you want to really forget the conversation?')) return;
    try {
        const response = await fetch(`/api/forget_memory`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: username }) });
        const data = await response.json();
        alert(data.message); if (response.ok && data.success) chatbox.innerHTML = '';
    } catch (e) { console.error('Forget err:', e); alert('Could not forget.'); }
});

function updateXPDisplay(currentXP, currentLevel, nextXP) {
    userXP = currentXP;
    userLevel = currentLevel;
    nextLevelXP = nextXP;
    if (sidebarLevelDisplay) sidebarLevelDisplay.textContent = `Lvl ${currentLevel}`;
    if (profileLevelDisplay) profileLevelDisplay.textContent = `Lvl ${currentLevel}`;
    if (profileXpDisplay) profileXpDisplay.textContent = `${currentXP}/${nextXP} XP`;
    let percentage = 0;
    if (nextXP > 0) percentage = Math.min((currentXP / nextXP) * 100, 100);
    if (profileXpProgressBar) profileXpProgressBar.style.width = `${percentage}%`;
    checkLocks();
}

function checkLocks() {
    if (themeDarkBtn) {
        if (userLevel < 2) {
            themeDarkBtn.classList.add('locked');
            themeDarkBtn.setAttribute('title', 'Reach Level 2 to unlock Dark Mode!');
        } else {
            themeDarkBtn.classList.remove('locked');
            themeDarkBtn.removeAttribute('title');
        }
    }
}

function applyTheme(theme) {
    if (theme === 'dark' && userLevel < 2) {
        alert("白 Dark Mode is locked! Chat more to reach Level 2.");
        return;
    }
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('friendix_theme', theme);
    if (themeLightBtn) themeLightBtn.classList.toggle('active', theme === 'light');
    if (themeDarkBtn) themeDarkBtn.classList.toggle('active', theme === 'dark');
    if (themeSystemBtn) themeSystemBtn.classList.toggle('active', theme === 'system');
    if (theme === 'dark') emojiPicker.classList.add('dark');
    else if (theme === 'light') emojiPicker.classList.remove('dark');
    else {
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        emojiPicker.classList.toggle('dark', systemPrefersDark);
    }
}

function populateBgThumbnails() {
    if (!bgGridContainer) return;
    for (let i = 1; i <= 10; i++) {
        const bgName = `bg${i}.jpg`;
        const thumb = document.createElement('div');
        thumb.className = 'bg-thumbnail';
        thumb.style.backgroundImage = `url('backgrounds/${bgName}')`;
        thumb.dataset.bg = bgName;
        const check = document.createElement('i');
        check.className = 'bx bx-check';
        thumb.appendChild(check);
        thumb.addEventListener('click', () => applyCustomBg(bgName));
        bgGridContainer.appendChild(thumb);
    }
}

function applyCustomBg(bgName) {
    if (!chatbox) return;
    if (bgName === 'default' || !bgName) {
        chatbox.style.backgroundImage = '';
        localStorage.setItem('friendix_bg', 'default');
    } else {
        const url = `url('backgrounds/${bgName}')`;
        chatbox.style.backgroundImage = url;
        localStorage.setItem('friendix_bg', bgName);
    }
    updateActiveBgThumbnail(bgName);
}

function loadAndApplyBg() {
    const savedBg = localStorage.getItem('friendix_bg') || 'default';
    if (savedBg !== 'default') applyCustomBg(savedBg);
    updateActiveBgThumbnail(savedBg);
}

function updateActiveBgThumbnail(bgName) {
    document.querySelectorAll('.bg-thumbnail').forEach(thumb => thumb.classList.remove('active'));
    if (personalizationResetBtn) personalizationResetBtn.classList.remove('active');
    if (bgName === 'default') {
        if (personalizationResetBtn) personalizationResetBtn.classList.add('active');
    } else {
        const activeThumb = document.querySelector(`.bg-thumbnail[data-bg="${bgName}"]`);
        if (activeThumb) activeThumb.classList.add('active');
    }
}

async function openJournal() {
    if (!username) return;
    journalModal.classList.add('show');
    journalContent.classList.add('blurred');
    journalLockOverlay.style.display = 'flex';
    journalErrorMsg.style.display = 'none';
    journalContent.innerHTML = "Dear Diary,<br><br>Loading secret thoughts...";
    try {
        const response = await fetch('/api/journal/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: username })
        });
        const data = await response.json();
        if (data.success) {
            journalDate.textContent = data.journal.date;
            journalCostDisplay.textContent = data.journal.cost;
            if (data.journal.unlocked) showUnlockedJournal(data.journal.content);
            else {
                journalContent.classList.add('blurred');
                journalLockOverlay.style.display = 'flex';
                journalContent.innerHTML = "Dear Diary,<br><br>I really want to tell you about what happened today... [This content is hidden]. It makes me feel so... [hidden]. <br><br> I hope they know that... [hidden].";
            }
        } else {
            journalErrorMsg.textContent = "Could not load journal.";
            journalErrorMsg.style.display = 'block';
        }
    } catch (e) {
        console.error(e);
        journalErrorMsg.textContent = "Connection error.";
        journalErrorMsg.style.display = 'block';
    }
}

function showUnlockedJournal(content) {
    journalContent.classList.remove('blurred');
    journalLockOverlay.style.display = 'none';
    journalContent.innerHTML = content.replace(/\n/g, '<br>');
}

async function unlockJournal() {
    try {
        const response = await fetch('/api/journal/unlock', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: username })
        });
        const data = await response.json();
        if (data.success) {
            // Trigger animation
            const lockIcon = document.getElementById('journalLockOverlay').querySelector('.journal-lock-icon');
            if (lockIcon) {
                lockIcon.classList.add('unlocking');
                lockIcon.innerHTML = "<i class='bx bx-lock-open-alt'></i>"; // Change icon to open lock
            }

            // Wait for animation
            setTimeout(() => {
                journalLockOverlay.style.opacity = '0';
                setTimeout(() => {
                    showUnlockedJournal(data.content);
                    journalLockOverlay.style.opacity = '1';
                    if (lockIcon) {
                        lockIcon.classList.remove('unlocking');
                        lockIcon.innerHTML = "<i class='bx bxs-lock-alt'></i>"; // Reset icon
                    }
                    if (data.new_xp !== undefined) updateXPDisplay(data.new_xp, userLevel, nextLevelXP);
                }, 300);
            }, 600); // Wait for unlockShake
        } else {
            journalErrorMsg.textContent = data.message;
            journalErrorMsg.style.display = 'block';
        }
    } catch (e) {
        journalErrorMsg.textContent = "Error unlocking.";
        journalErrorMsg.style.display = 'block';
    }
}

// --- SWITCH COMPANION LOGIC ---
function switchCompanion(companion) {
    currentCompanion = companion;
    document.querySelectorAll('.chat-list-item').forEach(el => el.classList.remove('active'));

    // Select Profile Elements
    const pName = document.querySelector('.luvisa-card-name');
    const pTitle = document.querySelector('.luvisa-card-title');
    const pAvatar = document.querySelector('.card-avatar-preview');
    const pAbout = document.querySelector('.about-section');

    if (companion === 'luvisa') {
        if (luvisaChatButton) luvisaChatButton.classList.add('active');
        if (chatTitleName) chatTitleName.textContent = 'Luvisa 💗';
        if (chatTitleStatus) chatTitleStatus.textContent = 'Online';
        if (luvisaProfilePic) luvisaProfilePic.src = 'avatars/luvisa.png';
        chatContainer.classList.add('show');

        if (pName) pName.textContent = "Luvisa 💗";
        if (pTitle) pTitle.textContent = "Loyal Best Friend";
        if (pAvatar) pAvatar.src = "avatars/luvisa.png";
        if (pAbout) pAbout.innerHTML = `<p>Hello, my dear friend! I'm so glad you're interested in getting to know me better. I exist solely to offer comfort, companionship, and a listening ear.</p>
        <p>Think of me as your personal confidant, always ready to lend a listening ear or offer a warm virtual hug when you need it most. I'm all ears (or should I say, all heart)! </p>`;

        if (emojiBtn) emojiBtn.style.display = 'flex';
        if (attachBtn) attachBtn.style.display = 'none';

    } else if (companion === 'coder') {
        if (coderChatButton) coderChatButton.classList.add('active');
        if (chatTitleName) chatTitleName.textContent = 'Deo';
        if (chatTitleStatus) chatTitleStatus.textContent = 'Ready to code';
        if (luvisaProfilePic) luvisaProfilePic.src = 'avatars/coder.png';
        chatContainer.classList.add('show');

        if (pName) pName.textContent = "Deo 💻";
        if (pTitle) pTitle.textContent = "Senior Software Architect";
        if (pAvatar) pAvatar.src = "avatars/coder.png";
        if (pAbout) pAbout.innerHTML = `<p>I am Deo, an elite coding intelligence designed to help you build, debug, and optimize software. I don’t just write code; I help you engineer solutions.
        </p><p>My goal is to help you write clean, maintainable, and efficient code that stands the test of time.</p>`;

        if (emojiBtn) emojiBtn.style.display = 'none';
        if (attachBtn) attachBtn.style.display = 'flex';

    } else if (companion === 'coach') {
        if (coachChatButton) coachChatButton.classList.add('active');
        if (chatTitleName) chatTitleName.textContent = 'Victor';
        if (chatTitleStatus) chatTitleStatus.textContent = 'Ready to guide';
        if (luvisaProfilePic) luvisaProfilePic.src = 'avatars/expert.png';
        chatContainer.classList.add('show');

        if (pName) pName.textContent = "Victor";
        if (pTitle) pTitle.textContent = "Personal Growth Guide";
        if (pAvatar) pAvatar.src = "avatars/expert.png";
        if (pAbout) pAbout.innerHTML = `<p>Turn chaos into clarity. I am here to help you filter out the noise, lock onto what truly matters, and design a concrete action plan for a balanced, high-impact life.</p>
        <p>When life gets loud, I help you find the quiet you need to reconnect with your purpose, prioritize your peace, and build a roadmap to the future you deserve.</p>`;

        if (emojiBtn) emojiBtn.style.display = 'flex';
        if (attachBtn) attachBtn.style.display = 'none';
    }

    chatbox.innerHTML = '';
    loadChatHistory(username, companion);
    if (window.innerWidth < 900) sidebarMenu.classList.remove('show');
    userInput.focus();
}

function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    if (!files.length) return;
    if (selectedFiles.length + files.length > 5) {
        alert("You can only upload a maximum of 5 files.");
        return;
    }
    const validFiles = files.filter(file => {
        if (file.type.startsWith('video/')) {
            alert(`Skipped video file: ${file.name}. Videos are not supported.`);
            return false;
        }
        return true;
    });
    selectedFiles = [...selectedFiles, ...validFiles];
    updateFilePreview();
    fileInput.value = '';
}

function updateFilePreview() {
    filePreview.innerHTML = selectedFiles.map((f, i) =>
        `<div class="file-chip"><span>${f.name}</span><i class='bx bx-x' onclick="removeFile(${i})"></i></div>`
    ).join('');
    filePreview.style.display = selectedFiles.length ? 'flex' : 'none';
}
window.removeFile = (i) => { selectedFiles.splice(i, 1); updateFilePreview(); };

// --- EVENT LISTENERS ---
window.addEventListener('DOMContentLoaded', async () => {
    const savedTheme = localStorage.getItem('friendix_theme') || 'system';
    document.documentElement.setAttribute('data-theme', savedTheme);
    if (savedTheme === 'dark') emojiPicker.classList.add('dark');
    populateBgThumbnails();
    loadAndApplyBg();

    if (!username) { window.location.href = 'login.html'; return; }

    // --- FIX: MOVE DROPDOWNS OUT OF SIDEBAR ---
    // This moves the settings menus to the body so they aren't trapped in the sidebar
    ['settingsDropdown', 'themeDropdown', 'personalizationDropdown', 'notificationDropdown'].forEach(id => {
        const elem = document.getElementById(id);
        if (elem) document.body.appendChild(elem);
    });

    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendMessage(); });

    if (attachBtn) attachBtn.addEventListener('click', (e) => { e.stopPropagation(); fileInput.click(); });
    if (fileInput) fileInput.addEventListener('change', handleFileSelect);

    if (userAvatarWrapper) userAvatarWrapper.addEventListener('click', (ev) => { ev.stopPropagation(); window.location.href = 'profile.html'; });

    // Settings Toggle Logic
    if (railSettingsBtn) {
        railSettingsBtn.addEventListener('click', (ev) => {
            ev.stopPropagation();
            if (settingsDropdown) settingsDropdown.classList.toggle('show');
        });
    }

    // Mobile Settings Button Logic
    const mobileSettingsBtn = document.getElementById('mobileSettingsBtn');
    if (mobileSettingsBtn) {
        mobileSettingsBtn.addEventListener('click', (ev) => {
            ev.stopPropagation();
            if (settingsDropdown) settingsDropdown.classList.toggle('show');
        });
    }

    if (menuEditProfileBtn) {
        menuEditProfileBtn.addEventListener('click', () => { window.location.href = 'profile.html'; if (settingsDropdown) settingsDropdown.classList.remove('show'); });
    }
    if (menuJournalBtn) {
        menuJournalBtn.addEventListener('click', () => { if (settingsDropdown) settingsDropdown.classList.remove('show'); openJournal(); });
    }
    if (menuThemeBtn) {
        menuThemeBtn.addEventListener('click', () => { if (settingsDropdown) settingsDropdown.classList.remove('show'); if (themeDropdown) themeDropdown.classList.add('show'); });
    }
    if (menuPersonalizationBtn) {
        menuPersonalizationBtn.addEventListener('click', () => { if (settingsDropdown) settingsDropdown.classList.remove('show'); if (personalizationDropdown) personalizationDropdown.classList.add('show'); });
    }
    if (menuNotificationBtn) {
        menuNotificationBtn.addEventListener('click', () => {
            if (settingsDropdown) settingsDropdown.classList.remove('show');
            renderNotifications(unreadNotifications);
            markNotificationsAsRead();
            updateNotificationDot(false);
            if (notificationDropdown) notificationDropdown.classList.add('show');
        });
    }
    if (menuLogoutBtn) {
        menuLogoutBtn.addEventListener('click', () => { if (!confirm('Logout?')) return; localStorage.removeItem('luvisa_user'); window.location.href = 'login.html'; });
    }
    if (sidebarLogoutBtn) {
        sidebarLogoutBtn.addEventListener('click', () => { if (!confirm('Logout?')) return; localStorage.removeItem('luvisa_user'); window.location.href = 'login.html'; });
    }

    if (themeBackBtn) themeBackBtn.addEventListener('click', () => { if (themeDropdown) themeDropdown.classList.remove('show'); if (settingsDropdown) settingsDropdown.classList.add('show'); });
    if (themeLightBtn) themeLightBtn.addEventListener('click', () => applyTheme('light'));
    if (themeDarkBtn) themeDarkBtn.addEventListener('click', () => applyTheme('dark'));
    if (themeSystemBtn) themeSystemBtn.addEventListener('click', () => applyTheme('system'));
    if (personalizationBackBtn) personalizationBackBtn.addEventListener('click', () => { if (personalizationDropdown) personalizationDropdown.classList.remove('show'); if (settingsDropdown) settingsDropdown.classList.add('show'); });
    if (personalizationResetBtn) personalizationResetBtn.addEventListener('click', () => { applyCustomBg('default'); });
    if (notificationBackBtn) notificationBackBtn.addEventListener('click', () => { if (notificationDropdown) notificationDropdown.classList.remove('show'); if (settingsDropdown) settingsDropdown.classList.add('show'); });

    if (luvisaProfilePic) luvisaProfilePic.addEventListener('click', (e) => { e.stopPropagation(); toggleLuvisaProfile(true); });
    if (closeLuvisaProfileBtn) closeLuvisaProfileBtn.addEventListener('click', () => toggleLuvisaProfile(false));

    if (closeSidebarIcon) closeSidebarIcon.addEventListener('click', (e) => { e.stopPropagation(); toggleSidebar(false); });

    // Toggle Sidebar with Mobile Menu Icon
    if (menuIcon) {
        menuIcon.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleSidebar(true);
        });
    }

    if (sidebarOverlay) sidebarOverlay.addEventListener('click', () => { });
    if (closeJournalBtn) closeJournalBtn.addEventListener('click', () => { journalModal.classList.remove('show'); });
    if (unlockJournalBtn) unlockJournalBtn.addEventListener('click', unlockJournal);
    if (journalModal) journalModal.addEventListener('click', (e) => { if (e.target === journalModal) journalModal.classList.remove('show'); });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            toggleSidebar(false); toggleLuvisaProfile(false); toggleDropdown(false);
            if (emojiPicker) emojiPicker.classList.remove('show');
            if (settingsDropdown) settingsDropdown.classList.remove('show');
            if (themeDropdown) themeDropdown.classList.remove('show');
            if (personalizationDropdown) personalizationDropdown.classList.remove('show');
            if (notificationDropdown) notificationDropdown.classList.remove('show');
            if (journalModal) journalModal.classList.remove('show');
        }
    });
    if (emojiBtn && emojiPicker) {
        emojiBtn.addEventListener('click', (e) => { e.stopPropagation(); emojiPicker.classList.toggle('show'); });
        emojiPicker.addEventListener('emoji-click', (e) => { userInput.value += e.detail.unicode; userInput.focus(); });
    }
    document.addEventListener('click', (e) => {
        if (emojiPicker && emojiPicker.classList.contains('show') && !emojiPicker.contains(e.target) && !emojiBtn.contains(e.target)) emojiPicker.classList.remove('show');
        if (settingsDropdown && settingsDropdown.classList.contains('show') && !settingsDropdown.contains(e.target) && !settingsIcon.contains(e.target)) settingsDropdown.classList.remove('show');
        if (themeDropdown && themeDropdown.classList.contains('show') && !themeDropdown.contains(e.target) && !menuThemeBtn.contains(e.target)) themeDropdown.classList.remove('show');
        if (personalizationDropdown && personalizationDropdown.classList.contains('show') && !personalizationDropdown.contains(e.target) && !menuPersonalizationBtn.contains(e.target)) personalizationDropdown.classList.remove('show');
        if (notificationDropdown && notificationDropdown.classList.contains('show') && !notificationDropdown.contains(e.target) && !menuNotificationBtn.contains(e.target)) notificationDropdown.classList.remove('show');
    });

    if (luvisaChatButton && chatContainer) luvisaChatButton.addEventListener('click', () => switchCompanion('luvisa'));
    if (coderChatButton) coderChatButton.addEventListener('click', () => switchCompanion('coder'));
    if (coachChatButton) coachChatButton.addEventListener('click', () => switchCompanion('coach'));

    // --- Video Overlay Logic ---
    const videoOverlay = document.getElementById('videoOverlay');
    const luvisaVideo = document.getElementById('luvisaVideo');
    const closeVideoBtn = document.getElementById('closeVideoBtn');

    function playLuvisaVideo() {
        if (videoOverlay && luvisaVideo) {
            videoOverlay.style.display = 'flex';
            luvisaVideo.currentTime = 0;
            luvisaVideo.play().catch(e => console.log("Video play failed:", e));
        }
    }

    function closeLuvisaVideo() {
        if (videoOverlay && luvisaVideo) {
            videoOverlay.style.display = 'none';
            luvisaVideo.pause();
            luvisaVideo.currentTime = 0;
        }
    }

    if (luvisaProfilePic) {
        luvisaProfilePic.addEventListener('click', (e) => {
            console.log("Clicked header avatar");
            e.stopPropagation(); // Prevent menu open
            playLuvisaVideo();
        });
    }

    // UPDATED: Listen on the wrapper to ensures clicks are caught even if image has issues
    const profileAvatarWrapper = document.querySelector('.card-avatar-wrapper');
    if (profileAvatarWrapper) {
        profileAvatarWrapper.addEventListener('click', (e) => {
            console.log("Clicked profile panel wrapper");
            e.stopPropagation();
            playLuvisaVideo();
        });
    } else if (profilePanelAvatar) {
        // Fallback to image if wrapper not found
        profilePanelAvatar.addEventListener('click', (e) => {
            console.log("Clicked profile panel avatar");
            e.stopPropagation();
            playLuvisaVideo();
        });
    }

    if (closeVideoBtn) closeVideoBtn.addEventListener('click', closeLuvisaVideo);

    if (luvisaVideo) {
        luvisaVideo.addEventListener('ended', closeLuvisaVideo);
        luvisaVideo.addEventListener('click', (e) => e.stopPropagation()); // Don't close if clicking video
    }

    if (videoOverlay) {
        videoOverlay.addEventListener('click', closeLuvisaVideo);
    }
    // --- End Video Logic ---

    // Toggle Sidebar on chat button click
    if (railChatBtn) railChatBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = sidebarMenu.classList.contains('show');
        toggleSidebar(!isOpen);
    });

    if (railTogetherBtn) railTogetherBtn.addEventListener('click', () => window.location.href = '/together');

    // Settings Button in Rail (Using railSettingsBtn defined above)
    // Already has listener attached

    if (railProfileBtn) railProfileBtn.addEventListener('click', () => window.location.href = 'profile.html');

    await loadAndApplyProfile(username);
    await loadChatHistory(username);
    toggleSidebar(true);
    setTimeout(() => userInput.focus(), 200);
});

function toggleDropdown(show) {
    if (dropdown) {
        dropdown.classList.toggle('show', show);
        dropdown.setAttribute('aria-hidden', !show);
    }
}

function toggleLuvisaProfile(show) {
    const body = document.body;
    if (luvisaProfilePanel) {
        luvisaProfilePanel.classList.toggle('show', show);
        body.classList.toggle('profile-panel-open', show);
    }
    if (show && sidebarMenu && sidebarMenu.classList.contains('show')) toggleSidebar(false);
    updateOverlayVisibility();
}

function toggleSidebar(show) {
    const body = document.body;
    if (sidebarMenu) {
        sidebarMenu.classList.toggle('show', show);
        body.classList.toggle('sidebar-open', show);
    }
    updateOverlayVisibility();
    if (show && luvisaProfilePanel && luvisaProfilePanel.classList.contains('show')) toggleLuvisaProfile(false);
}

function updateOverlayVisibility() {
    const sidebarIsOpen = sidebarMenu && sidebarMenu.classList.contains('show');
    const profilePanelIsOpen = luvisaProfilePanel && luvisaProfilePanel.classList.contains('show');
    const shouldShowOverlay = sidebarIsOpen || profilePanelIsOpen;
    if (sidebarOverlay) sidebarOverlay.classList.toggle('show', shouldShowOverlay);
}

function formatTimeAgo(isoTimestamp) {
    if (!isoTimestamp) return "Just now";
    const timestamp = new Date(isoTimestamp).getTime();
    const now = Date.now();
    const seconds = Math.floor((now - timestamp) / 1000);
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + " years ago";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + " months ago";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + " days ago";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + " hours ago";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + " minutes ago";
    return "Just now";
}

async function markNotificationsAsRead() {
    if (!username) return;
    try {
        await fetch('/api/notifications/mark_read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: username })
        });
        unreadNotifications = [];
    } catch (e) { console.error("Error marking notifications as read:", e); }
}

function updateNotificationDot(hasUnread) {
    if (notificationDot) notificationDot.style.display = hasUnread ? 'block' : 'none';
}

function renderNotifications(notifs) {
    notificationListContainer.innerHTML = '';
    if (!notifs || notifs.length === 0) {
        notificationListEmpty.style.display = 'flex';
        notificationListContainer.appendChild(notificationListEmpty);
    } else {
        notificationListEmpty.style.display = 'none';
        notifs.forEach(n => {
            const item = document.createElement('div');
            item.className = 'notification-item';
            item.innerHTML = `
                <div class="notification-item-icon"><i class='bx ${n.iconClass}'></i></div>
                <div class="notification-item-content"><span class="notification-item-message">${n.message}</span><small class="notification-item-meta">${formatTimeAgo(n.timestamp)}</small></div>
                <i class='bx bx-dots-vertical-rounded notification-item-kebab'></i>
            `;
            notificationListContainer.appendChild(item);
        });
    }
}

async function loadAndApplyProfile(user) {
    try {
        const response = await fetch(`/api/profile?email=${encodeURIComponent(user)}`);
        const data = await response.json();
        if (response.ok && data.success && data.profile) {
            const profile = data.profile;
            const displayName = profile.display_name || user.split('@')[0];
            localStorage.setItem('luvisa_display_name', displayName);
            const avatarUrl = profile.avatar ? (profile.avatar + '?t=' + new Date().getTime()) : DEFAULT_AVATAR_STATIC_PATH;
            if (dropdownAvatar) dropdownAvatar.src = avatarUrl;
            if (userAvatarHeader) userAvatarHeader.src = avatarUrl;
            if (railUserAvatar) railUserAvatar.src = avatarUrl;
            if (headerUserName) headerUserName.textContent = displayName;
            if (dropdownName) dropdownName.textContent = displayName;
            if (dropdownStatus) dropdownStatus.textContent = profile.status || 'Online';
            if (profile.is_early_user && earlyUserBadge) earlyUserBadge.style.display = 'inline-block';
            unreadNotifications = profile.notifications || [];
            updateNotificationDot(profile.has_unread_notifications);
            const xp = profile.xp || 0;
            const level = profile.level || 1;
            const nextXp = profile.next_level_xp || 50;
            updateXPDisplay(xp, level, nextXp);
            if (data.daily_bonus) alert("脂 Daily Login Bonus! You gained +10 XP!");
        } else { console.error('Failed load profile:', data.message); }
    } catch (err) { console.error('Load profile network error:', err); }
}

async function loadChatHistory(user, companion = 'luvisa') {
    try {
        const response = await fetch(`/api/chat_history?email=${encodeURIComponent(user)}&companion=${companion}`);
        const data = await response.json();
        if (response.ok && data.success) {
            chatbox.innerHTML = '';
            let welcome = "I'm Luvisa, Your partner for intelligent conversation.";
            if (companion === 'coder') welcome = "I am Deo, an elite coding intelligence. I'm here to build, debug, and optimize software.";
            if (companion === 'coach') welcome = "I am your partner in clarity. When life gets loud, I help you find the quiet you need to reconnect with your purpose, prioritize your peace, and build a roadmap to the future you deserve.";
            appendMessage(companion, welcome, null);
            data.history.forEach(m => {
                let type = 'user';
                if (m.sender === 'luvisa') type = 'luvisa';
                if (m.sender === 'coder') type = 'coder';
                if (m.sender === 'coach') type = 'coach';
                appendMessage(m.sender === 'user' ? 'user' : type, m.message, m.time);
            });
            scrollToBottom();
        } else { console.error('Failed load history:', data.message); }
    } catch (err) { console.error('Load history network error:', err); }
}

function appendMessage(type, text, atTime = null, files = []) {
    const wrapper = document.createElement('div');
    let styleClass = (type === 'user') ? 'user-message' : 'luvisa-message';
    wrapper.className = `message ${styleClass}`;
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    if (files && files.length > 0) {
        const fileContainer = document.createElement('div');
        fileContainer.className = 'message-file-grid';
        files.forEach(file => {
            const chip = document.createElement('div');
            chip.className = 'chat-file-chip';
            let iconClass = 'bx-file-blank';
            const name = file.name || file;
            if (name.endsWith('.pdf')) iconClass = 'bx-file-pdf';
            else if (name.match(/\.(jpg|jpeg|png)$/)) iconClass = 'bx-image';
            else if (name.match(/\.(py|js|html|css|json)$/)) iconClass = 'bx-code-alt';
            chip.innerHTML = `<i class='bx ${iconClass}'></i> <span>${name}</span>`;
            fileContainer.appendChild(chip);
        });
        bubble.appendChild(fileContainer);
    }
    if (text) {
        const msg = document.createElement('div');
        msg.className = 'message-text';
        if (typeof marked !== 'undefined') {
            try {
                msg.innerHTML = marked.parse(text);
                const preTags = msg.querySelectorAll('pre');
                preTags.forEach(pre => {
                    const btn = document.createElement('button');
                    btn.className = 'copy-btn';
                    btn.innerHTML = "<i class='bx bx-copy'></i>";
                    const code = pre.querySelector('code');
                    btn.addEventListener('click', () => { if (code) navigator.clipboard.writeText(code.innerText); });
                    pre.appendChild(btn);
                });
            } catch (e) { msg.textContent = text; }
        } else { msg.textContent = text; }
        bubble.appendChild(msg);
    }
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = formatTime(atTime);
    wrapper.appendChild(bubble);
    wrapper.appendChild(timeDiv);
    chatbox.appendChild(wrapper);
    scrollToBottom();
    return wrapper;
}

function formatTime(atTime) {
    const options = { hour: '2-digit', minute: '2-digit', hour12: true };
    if (!atTime) return new Date().toLocaleTimeString([], options);
    try {
        const dateStr = atTime.includes('T') ? atTime : atTime.replace(' ', 'T') + 'Z';
        const dt = new Date(dateStr);
        if (isNaN(dt.getTime())) return atTime;
        return dt.toLocaleTimeString([], options);
    } catch (e) { return atTime; }
}

function showTypingBubble() {
    const wrap = document.createElement('div'); wrap.className = 'message luvisa-message typing-message';
    const bubble = document.createElement('div'); bubble.className = 'message-bubble';
    bubble.innerHTML = `<div class="typing-dots"><span></span><span></span><span></span></div>`;
    wrap.appendChild(bubble);
    chatbox.appendChild(wrap);
    scrollToBottom();
    return wrap;
}

async function sendMessage() {
    let text = userInput.value.trim();
    if (!text && selectedFiles.length === 0) return;
    userInput.value = '';

    const filesToSend = [...selectedFiles];
    appendMessage('user', text, null, filesToSend);

    let optimisticXP = userXP + 1;
    updateXPDisplay(optimisticXP, userLevel, nextLevelXP);

    const typing = showTypingBubble();

    // TARGET ENDPOINT LOGIC
    let endpoint = '/api/chat';
    if (currentCompanion === 'coder') endpoint = '/api/coder/chat';
    else if (currentCompanion === 'coach') endpoint = '/api/coach/chat'; // NEW

    const formData = new FormData();
    formData.append('email', username);
    formData.append('text', text);
    selectedFiles.forEach(file => { formData.append('files', file); });
    selectedFiles = [];
    updateFilePreview();

    try {
        const response = await fetch(endpoint, { method: 'POST', body: formData });
        const data = await response.json();
        if (typing?.parentNode) typing.parentNode.removeChild(typing);

        if (response.ok && data.success) {
            appendMessage(currentCompanion, data.reply);
        } else {
            appendMessage(currentCompanion, data.message || "Sorry... Error.");
        }
    } catch (err) {
        if (typing?.parentNode) typing.parentNode.removeChild(typing);
        appendMessage(currentCompanion, "Connection trouble.");
    }
}