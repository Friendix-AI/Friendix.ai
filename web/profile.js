// --- Backend URL ---
const BACKEND_URL = ''; // Relative path
const PUBLIC_URL_BASE = window.location.origin; 

// --- Default Avatar Path (Served by Frontend/Vercel) ---
const DEFAULT_AVATAR_STATIC_PATH = "/avatars/default_avatar.png";

// --- Elements ---
const avatarPreview = document.getElementById('avatarPreview');
const avatarUpload = document.getElementById('avatarUpload');
const avatarWrapper = document.getElementById('avatarWrapper');
const displayNameInput = document.getElementById('displayNameInput');
const statusMessageInput = document.getElementById('statusMessageInput');
const saveProfileBtn = document.getElementById('saveProfileBtn');
const cancelBtn = document.getElementById('cancelBtn');
const saveMessage = document.getElementById('saveMessage');
const shareBtn = document.getElementById('shareBtn');
const qrCodeContainer = document.getElementById('qrCodeContainer');
const qrWrapper = document.getElementById('qrWrapper');
const cardTop = document.getElementById('cardTop'); 

// --- Context Menu Elements ---
const avatarContextMenu = document.getElementById('avatarContextMenu');
const menuChangeImage = document.getElementById('menuChangeImage');
const menuViewImage = document.getElementById('menuViewImage');
const menuRemoveImage = document.getElementById('menuRemoveImage');

// --- Card Elements ---
const idCardShareBtn = document.getElementById('idCardShareBtn');
const nameEditIcon = document.getElementById('nameEditIcon');
const statusEditIcon = document.getElementById('statusEditIcon');
const qrCloseBtn = document.getElementById('qrCloseBtn');

// --- XP Elements ---
const idCardLevel = document.getElementById('idCardLevel');
const idCardProgressFill = document.getElementById('idCardProgressFill');
const idCardXpText = document.getElementById('idCardXpText');

let currentAvatarFile = null; 
const MAX_AVATAR_SIZE_KB = 100;

// ---------- Textarea Auto-Resize Function ----------
function autoResizeTextarea(textarea) {
    if (textarea) {
        textarea.style.height = 'auto'; 
        textarea.style.height = (textarea.scrollHeight) + 'px'; 
    }
}

// ---------- Initialization ----------
window.addEventListener('DOMContentLoaded', async () => {
    initializeProfilePage();

    document.addEventListener('click', (e) => {
        if (avatarContextMenu && avatarContextMenu.classList.contains('show')) {
            if (!avatarContextMenu.contains(e.target) && !avatarWrapper.contains(e.target)) {
                avatarContextMenu.classList.remove('show');
            }
        }
        
        if (qrWrapper && qrWrapper.classList.contains('show')) {
            if (!qrWrapper.contains(e.target) && !idCardShareBtn.contains(e.target)) {
                qrWrapper.classList.remove('show');
            }
        }
    });
});

/**
 * Initializes the profile page
 */
async function initializeProfilePage() {
    const params = new URLSearchParams(window.location.search);
    const urlId = params.get('id');
    const source = params.get('source');

    if (source === 'qr') {
        document.body.classList.add('qr-view');
    }

    if (urlId) {
        // --- PUBLIC VIEW ---
        document.body.classList.add('public-view');
        if (saveProfileBtn) saveProfileBtn.style.display = 'none';
        if (shareBtn) shareBtn.style.display = 'inline-block';
        if (avatarWrapper) avatarWrapper.style.pointerEvents = 'none';
        if (displayNameInput) displayNameInput.readOnly = true;
        if (statusMessageInput) statusMessageInput.readOnly = true;
        if (cancelBtn) cancelBtn.textContent = 'Go to Chat';
        
        if (cancelBtn) cancelBtn.addEventListener('click', () => window.location.href = 'chat');
        
        await loadPublicProfile(urlId);

    } else {
        // --- OWNER VIEW ---
        document.body.classList.add('owner-view');
        const username = localStorage.getItem('luvisa_user');
        if (!username) {
            window.location.href = 'login.html';
            return;
        }

        if (saveProfileBtn) saveProfileBtn.style.display = 'inline-block';
        
        if (avatarWrapper) {
            avatarWrapper.addEventListener('click', (e) => {
                e.stopPropagation(); 
                if (avatarContextMenu) {
                    avatarContextMenu.classList.toggle('show');
                }
            });
        }
        
        // --- Avatar Menu Listeners ---
        if (menuChangeImage) {
            menuChangeImage.addEventListener('click', () => {
                avatarUpload.click();
                if (avatarContextMenu) avatarContextMenu.classList.remove('show');
            });
        }
        if (menuViewImage) {
            menuViewImage.addEventListener('click', () => {
                window.open(avatarPreview.src, '_blank');
                if (avatarContextMenu) avatarContextMenu.classList.remove('show');
            });
        }
        if (menuRemoveImage) {
            menuRemoveImage.addEventListener('click', () => {
                if (confirm('Are you sure you want to remove your profile image?')) {
                    avatarPreview.src = DEFAULT_AVATAR_STATIC_PATH;
                    currentAvatarFile = 'remove'; 
                    if (avatarContextMenu) avatarContextMenu.classList.remove('show');
                }
            });
        }

        if (statusMessageInput) {
            statusMessageInput.addEventListener('input', () => autoResizeTextarea(statusMessageInput));
        }

        // --- Click listeners for new buttons ---
        if (idCardShareBtn) {
            idCardShareBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (qrWrapper) qrWrapper.classList.toggle('show');
            });
        }
        if (qrCloseBtn) {
            qrCloseBtn.addEventListener('click', () => {
                if (qrWrapper) qrWrapper.classList.remove('show');
            });
        }
        
        if (nameEditIcon) {
            nameEditIcon.addEventListener('click', () => {
                displayNameInput.readOnly = false;
                displayNameInput.focus();
            });
        }
        if (statusEditIcon) {
            statusEditIcon.addEventListener('click', () => {
                statusMessageInput.readOnly = false;
                statusMessageInput.focus();
            });
        }

        if (avatarUpload) avatarUpload.addEventListener('change', handleAvatarChange);
        if (saveProfileBtn) saveProfileBtn.addEventListener('click', () => saveProfileChanges(username));
        if (cancelBtn) cancelBtn.addEventListener('click', () => window.location.href = 'chat');
        
        await loadCurrentProfile(username);
    }
}

/**
 * Loads a public profile using a Friend ID
 */
async function loadPublicProfile(friendId) {
    saveMessage.textContent = 'Loading profile...';
    try {
        const response = await fetch(`/api/profile_by_id?id=${encodeURIComponent(friendId)}`);
        const data = await response.json();

        if (response.ok && data.success && data.profile) {
            populateProfileData(data.profile);
            
            const publicUrl = `${PUBLIC_URL_BASE}/profile.html?id=${data.profile.friend_id}`;
            const qrUrl = `${PUBLIC_URL_BASE}/profile.html?id=${data.profile.friend_id}&source=qr`;
            
            generateQRCode(qrUrl);
            setupShareButton(publicUrl, data.profile.friend_id);
            saveMessage.textContent = '';
        } else {
             handleProfileError(data.message || 'Could not load profile.');
        }
    } catch (error) {
        handleProfileError('Network error loading profile.');
    }
}


/**
 * Loads the logged-in user's profile using their email
 */
async function loadCurrentProfile(email) {
    saveMessage.textContent = 'Loading profile...';
    try {
        const response = await fetch(`/api/profile?email=${encodeURIComponent(email)}`);
        const data = await response.json();

        if (response.ok && data.success && data.profile) {
            populateProfileData(data.profile);
            
            const publicUrl = `${PUBLIC_URL_BASE}/profile.html?id=${data.profile.friend_id}`;
            const qrUrl = `${PUBLIC_URL_BASE}/profile.html?id=${data.profile.friend_id}&source=qr`;
            
            generateQRCode(qrUrl);
            setupShareButton(publicUrl, data.profile.friend_id);
            saveMessage.textContent = '';
        } else {
             handleProfileError(data.message || 'Could not load profile.');
        }
    } catch (error) {
        handleProfileError('Network error loading profile.');
    }
}

/**
 * Fills all the HTML elements with data from a profile object
 */
function populateProfileData(profile) {
    if (displayNameInput) displayNameInput.value = profile.display_name;
    if (statusMessageInput) statusMessageInput.value = profile.status || 'Hey there! I’m using Luvisa 💗';

    if (profile.avatar) {
        avatarPreview.src = profile.avatar;
    } else {
        avatarPreview.src = DEFAULT_AVATAR_STATIC_PATH;
    }

    cardTop.style.backgroundImage = ''; 

    if (document.getElementById('friendshipYear')) {
        document.getElementById('friendshipYear').textContent = profile.creation_year;
    }
    if (document.getElementById('idCode')) {
        document.getElementById('idCode').textContent = profile.friend_id;
    }
    
    const badge = document.getElementById('earlyUserBadge');
    if (badge && profile.is_early_user) {
        badge.style.display = 'inline-block';
    } else if (badge) {
        badge.style.display = 'none';
    }

    // --- UPDATED: XP Logic ---
    const xp = profile.xp || 0;
    const level = profile.level || 1;
    const nextXp = profile.next_level_xp || 50;

    if (idCardLevel) idCardLevel.textContent = `Lvl ${level}`;
    if (idCardXpText) idCardXpText.textContent = `${xp}/${nextXp} XP`;
    
    if (idCardProgressFill) {
        let percentage = 0;
        if (nextXp > 0) {
            percentage = Math.min((xp / nextXp) * 100, 100);
        }
        idCardProgressFill.style.width = `${percentage}%`;
    }

    autoResizeTextarea(statusMessageInput);
}

/**
 * Handles errors during profile loading
 */
function handleProfileError(message) {
    console.error('Failed load profile:', message);
    if (saveMessage) {
        saveMessage.textContent = `Error: ${message}`;
        saveMessage.className = 'save-message error';
    }
    if (displayNameInput) displayNameInput.value = 'User Not Found';
    if (statusMessageInput) statusMessageInput.value = '---';
    if (avatarPreview) avatarPreview.src = DEFAULT_AVATAR_STATIC_PATH;
    if (qrWrapper) qrWrapper.style.display = 'none';
}


/**
 * Generates the QR Code
 */
function generateQRCode(qrUrl) {
    if (qrCodeContainer) {
        qrCodeContainer.innerHTML = '';
        try {
            new QRCode(qrCodeContainer, {
                text: qrUrl,
                width: 180,
                height: 180,
                colorDark : "#000000",
                colorLight : "#ffffff",
                correctLevel : QRCode.CorrectLevel.H
            });
        } catch (e) {
            console.error('QR Code generation failed:', e);
            qrCodeContainer.textContent = 'Could not load QR Code.';
        }
    }
}

/**
 * Sets up the Share button functionality
 */
function setupShareButton(publicUrl, friendId) {
    if (!shareBtn) return;
    
    shareBtn.addEventListener('click', async () => {
        try {
            if (navigator.share) {
                await navigator.share({
                    title: 'My Friendix ID',
                    text: `Add me on Friendix! My ID is ${friendId}`,
                    url: publicUrl
                });
            } else {
                await navigator.clipboard.writeText(publicUrl);
                saveMessage.textContent = 'Profile URL copied to clipboard!';
                saveMessage.className = 'save-message success';
                setTimeout(() => saveMessage.textContent = '', 2000);
            }
        } catch (err) {
            console.error('Share failed:', err);
            saveMessage.textContent = 'Could not share or copy URL.';
            saveMessage.className = 'save-message error';
            setTimeout(() => saveMessage.textContent = '', 2000);
        }
    });
}


// ---------- Handle Avatar Selection ----------
function handleAvatarChange(event) {
    const file = event.target.files[0];
    saveMessage.textContent = '';
    saveMessage.className = 'save-message';

    if (file && file.type.startsWith("image/")) {
        if (file.size > MAX_AVATAR_SIZE_KB * 1024) {
             saveMessage.textContent = `Image too large! Please choose one under ${MAX_AVATAR_SIZE_KB} KB.`;
             saveMessage.className = 'save-message error';
             avatarUpload.value = '';
             currentAvatarFile = null;
             return;
        }

        currentAvatarFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            avatarPreview.src = e.target.result;
        };
        reader.readAsDataURL(file);
    } else {
        currentAvatarFile = null;
        if (file) {
            saveMessage.textContent = 'Please select a valid image file.';
            saveMessage.className = 'save-message error';
        }
    }
    
    if (avatarContextMenu) avatarContextMenu.classList.remove('show');
}


// ---------- Save Profile Changes ----------
async function saveProfileChanges(username) {
    const displayName = displayNameInput.value.trim();
    const statusMessage = statusMessageInput.value.trim();

    if (!displayName) { 
        saveMessage.textContent = 'Display name cannot be empty.';
        saveMessage.className = 'save-message error';
        return; 
    }

    saveProfileBtn.classList.add("loading");
    saveProfileBtn.disabled = true;
    saveMessage.textContent = 'Saving...';
    saveMessage.className = 'save-message';

    const formData = new FormData();
    formData.append('email', username);
    formData.append('display_name', displayName);
    formData.append('status_message', statusMessage);
    
    if (currentAvatarFile === 'remove') {
        formData.append('remove_avatar', 'true');
    } else if (currentAvatarFile) {
        formData.append('avatar_file', currentAvatarFile);
    }

    try {
        const response = await fetch(`/api/profile`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (response.ok && data.success) {
            saveMessage.textContent = data.message;
            saveMessage.className = 'save-message success';

            populateProfileData(data.profile);
            
            currentAvatarFile = null;
            avatarUpload.value = '';
            displayNameInput.readOnly = true;
            statusMessageInput.readOnly = true;

             setTimeout(() => window.location.href = 'chat', 1500);
        } else {
            if (response.status === 413) {
                 saveMessage.textContent = data.message || `Image file is too large.`;
            } else {
                 saveMessage.textContent = `Error: ${data.message || 'Failed to save profile.'}`;
            }
            saveMessage.className = 'save-message error';
        }
    } catch (error) {
        console.error('Save profile network error:', error);
        saveMessage.textContent = 'Network error saving profile.';
        saveMessage.className = 'save-message error';
    } finally {
        saveProfileBtn.classList.remove("loading");
        saveProfileBtn.disabled = false;
    }
}