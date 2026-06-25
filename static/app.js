/* ═══════════════════════════════════════════════════════════════
   Museum Ticketing Bot - Frontend Application Logic
   Full Integration: Chat ↔ Payment ↔ QR ↔ Admin ↔ Exhibitions
   ═══════════════════════════════════════════════════════════════ */

const API_BASE = window.location.origin;
let currentSessionId = localStorage.getItem('museum_session_id') || null;
let chatOpen = false;
let selectedLanguage = localStorage.getItem('museum_lang') || 'en';
let isTyping = false;
let pendingBookingId = localStorage.getItem('museum_pending_booking') || null;
let paymentWindow = null;

// ═══════════════════ INITIALIZATION ═══════════════════

document.addEventListener('DOMContentLoaded', () => {
    initParticles();
    loadExhibitions();
    initScrollAnimations();

    // Restore session
    if (currentSessionId) {
        loadSessionHistory();
    }

    // Check if we returned from a payment
    checkPendingPayment();

    // Listen for payment completion from payment window
    window.addEventListener('message', (event) => {
        if (event.data && event.data.type === 'payment_complete') {
            handlePaymentComplete(event.data.bookingId);
        }
    });
});

// ═══════════════════ CHAT WIDGET ═══════════════════

function toggleChat() {
    const widget = document.getElementById('chatWidget');
    const badge = document.getElementById('chatBadge');

    chatOpen = !chatOpen;
    widget.classList.toggle('active', chatOpen);

    if (chatOpen) {
        badge.style.display = 'none';

        // Send initial greeting if new session
        if (!currentSessionId && document.getElementById('chatMessages').children.length === 0) {
            setTimeout(() => sendInitialGreeting(), 500);
        }

        // Focus input
        setTimeout(() => document.getElementById('chatInput').focus(), 400);
    }
}

function closeChat() {
    const widget = document.getElementById('chatWidget');
    chatOpen = false;
    widget.classList.remove('active');
}

async function sendInitialGreeting() {
    addMessage('bot', '🏛️ **Welcome to the National Heritage Museum!**\n\nI\'m Heritage Guide, your AI assistant. I can help you with:\n\n1. 🎫 **Book Tickets** - Gate entry, exhibitions, shows & tours\n2. 📋 **View Exhibitions** - Current & upcoming exhibitions\n3. 💰 **Check Pricing** - Ticket prices & discounts\n4. 📊 **Check Availability** - Date-wise availability\n5. 🔍 **Look up Booking** - Check booking status\n\nHow can I help you today?');
}

// ═══════════════════ MESSAGE HANDLING ═══════════════════

function handleKeyPress(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();

    if (!message || isTyping) return;

    // Add user message
    addMessage('user', message);
    input.value = '';

    // Show typing indicator
    showTypingIndicator();

    try {
        const response = await fetch(`${API_BASE}/api/chat/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                session_id: currentSessionId,
                language: selectedLanguage,
            }),
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();

        // Store session ID
        if (data.session_id) {
            currentSessionId = data.session_id;
            localStorage.setItem('museum_session_id', currentSessionId);
        }

        // Remove typing indicator
        hideTypingIndicator();

        // Add bot response
        addMessage('bot', data.reply);

        // Handle special actions
        if (data.action) {
            handleAction(data.action, data.data);
        }
    } catch (error) {
        hideTypingIndicator();
        addMessage('bot', '⚠️ Sorry, I\'m having trouble connecting. Please try again in a moment.');
        console.error('Chat error:', error);
    }
}

function sendQuickMessage(msg) {
    document.getElementById('chatInput').value = msg;
    sendMessage();
}

function addMessage(role, content) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `message message-${role === 'user' ? 'user' : 'bot'}`;

    // Parse markdown-like formatting
    let html = formatMessage(content);

    // Add timestamp
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    html += `<span class="message-time">${time}</span>`;

    div.innerHTML = html;

    // Add entrance animation
    div.style.opacity = '0';
    div.style.transform = role === 'user' ? 'translateX(20px)' : 'translateX(-20px)';
    container.appendChild(div);

    requestAnimationFrame(() => {
        div.style.transition = 'opacity 0.3s, transform 0.3s';
        div.style.opacity = '1';
        div.style.transform = 'translateX(0)';
        container.scrollTop = container.scrollHeight;
    });
}

function formatMessage(text) {
    if (!text) return '';

    // Escape HTML
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Bold: **text**
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic: *text*
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Code: `text`
    html = html.replace(/`(.+?)`/g, '<code style="background:rgba(124,92,252,0.15);padding:2px 6px;border-radius:4px;font-size:0.85em;">$1</code>');

    // Links: [text](url)
    html = html.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" style="color:#5ce0d8;text-decoration:underline;" onclick="handlePaymentLink(event, \'$2\')">$1</a>');

    // Line breaks
    html = html.replace(/\n/g, '<br>');

    return html;
}

function showTypingIndicator() {
    isTyping = true;
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = 'typing-indicator';
    div.id = 'typingIndicator';
    div.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function hideTypingIndicator() {
    isTyping = false;
    const indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
}

// ═══════════════════ ACTIONS HANDLER ═══════════════════

function handleAction(action, data) {
    switch (action) {
        case 'ticket_confirmed':
            if (data && data.qr_code) {
                showQRCode(data.booking_id, data.qr_code);
                // Also show QR inline in chat
                addQRToChat(data.booking_id, data.qr_code);
            }
            // Clear pending booking
            localStorage.removeItem('museum_pending_booking');
            pendingBookingId = null;
            break;

        case 'payment_pending':
            if (data) {
                // Store booking ID for tracking
                pendingBookingId = data.booking_id;
                localStorage.setItem('museum_pending_booking', pendingBookingId);

                // Auto-open payment page
                if (data.payment_url) {
                    setTimeout(() => {
                        openPaymentPage(data.payment_url, data.booking_id);
                    }, 1000);
                }
            }
            break;

        case 'reset':
        case 'cancelled':
            localStorage.removeItem('museum_pending_booking');
            pendingBookingId = null;
            break;

        case 'show_exhibitions':
            // Refresh the exhibitions section on the page
            loadExhibitions();
            break;
    }
}

// ═══════════════════ PAYMENT FLOW ═══════════════════

function handlePaymentLink(event, url) {
    // Intercept payment link clicks to manage the flow
    if (url && url.includes('payment-demo')) {
        event.preventDefault();
        const urlObj = new URL(url, window.location.origin);
        const bookingId = urlObj.searchParams.get('booking_id');
        openPaymentPage(url, bookingId);
    }
}

function openPaymentPage(url, bookingId) {
    // Open payment in a popup window
    const width = 500;
    const height = 650;
    const left = (screen.width - width) / 2;
    const top = (screen.height - height) / 2;

    paymentWindow = window.open(
        url,
        'museum_payment',
        `width=${width},height=${height},left=${left},top=${top},scrollbars=yes`
    );

    // If popup was blocked, add a message
    if (!paymentWindow) {
        addMessage('bot', `💡 Your browser blocked the payment popup. Please click the payment link directly or type **'paid'** after completing payment.`);
    } else {
        addMessage('bot', `💳 Payment window opened! Complete your payment there, then come back here.\n\n_If the window doesn't appear, click the payment link above._`);

        // Monitor the payment window
        const checkPayment = setInterval(() => {
            if (paymentWindow && paymentWindow.closed) {
                clearInterval(checkPayment);
                // Payment window was closed - ask if paid
                setTimeout(() => {
                    if (pendingBookingId) {
                        addMessage('bot', `Payment window closed. Did you complete the payment?\n\n• Type **'paid'** if you completed payment\n• Type **'cancel'** to cancel the booking`);
                    }
                }, 500);
            }
        }, 1000);
    }
}

function checkPendingPayment() {
    // Check URL params for returning from a payment redirect
    const params = new URLSearchParams(window.location.search);
    const bookingId = params.get('booking_id');
    const paymentStatus = params.get('payment_status');

    if (bookingId && paymentStatus === 'success') {
        // Auto-confirm payment
        handlePaymentComplete(bookingId);
        // Clean URL
        window.history.replaceState({}, '', '/');
    }
}

async function handlePaymentComplete(bookingId) {
    if (!chatOpen) toggleChat();

    setTimeout(async () => {
        addMessage('bot', '⏳ Verifying your payment...');

        try {
            const res = await fetch(`${API_BASE}/api/payment/confirm/${bookingId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });

            const data = await res.json();

            if (data.success) {
                addMessage('bot', `🎉 **Payment Confirmed!**\n\n✅ Your ticket is ready!\n📋 **Booking ID**: \`${bookingId}\`\n\n🎫 Your QR code ticket has been generated below.\n\n🏛️ **Enjoy your visit to the National Heritage Museum!**`);

                if (data.qr_code) {
                    addQRToChat(bookingId, data.qr_code);
                    showQRCode(bookingId, data.qr_code);
                }

                localStorage.removeItem('museum_pending_booking');
                pendingBookingId = null;

                // Reset chat state by sending a message to the agent
                await fetch(`${API_BASE}/api/chat/message`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: 'paid',
                        session_id: currentSessionId,
                        language: selectedLanguage,
                    }),
                });
            } else {
                addMessage('bot', `⚠️ Payment verification issue. Please type **'paid'** to retry or contact support.`);
            }
        } catch (error) {
            addMessage('bot', '⚠️ Could not verify payment. Please type **\'paid\'** to retry.');
            console.error('Payment confirm error:', error);
        }
    }, 500);
}

// ═══════════════════ QR CODE DISPLAY ═══════════════════

function addQRToChat(bookingId, qrBase64) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = 'message message-bot';
    div.innerHTML = `
        <div style="text-align:center;padding:12px;">
            <div style="font-size:1.1em;font-weight:600;margin-bottom:8px;">🎫 Your QR Ticket</div>
            <img src="data:image/png;base64,${qrBase64}" 
                 alt="QR Code Ticket" 
                 style="width:180px;height:180px;border-radius:12px;border:2px solid rgba(124,92,252,0.3);background:white;padding:8px;margin:8px 0;">
            <div style="font-size:0.85em;color:var(--text-muted);margin-top:4px;">
                Booking: <code style="background:rgba(124,92,252,0.15);padding:2px 6px;border-radius:4px;">${bookingId}</code>
            </div>
            <div style="font-size:0.8em;color:var(--text-muted);margin-top:8px;">
                📱 Screenshot this or show at museum entrance
            </div>
        </div>
    `;
    div.style.opacity = '0';
    div.style.transform = 'scale(0.8)';
    container.appendChild(div);

    requestAnimationFrame(() => {
        div.style.transition = 'opacity 0.4s, transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
        div.style.opacity = '1';
        div.style.transform = 'scale(1)';
        container.scrollTop = container.scrollHeight;
    });
}

function showQRCode(bookingId, qrBase64) {
    const qrDisplay = document.getElementById('qrDisplay');
    const qrImage = document.getElementById('qrImage');
    const qrBookingId = document.getElementById('qrBookingId');

    qrImage.src = `data:image/png;base64,${qrBase64}`;
    qrBookingId.textContent = `Booking ID: ${bookingId}`;
    qrDisplay.style.display = 'flex';
}

function hideQR() {
    document.getElementById('qrDisplay').style.display = 'none';
}

// ═══════════════════ LANGUAGE SELECTOR ═══════════════════

function showLanguageSelector() {
    const selector = document.getElementById('languageSelector');
    selector.classList.toggle('active');
}

function selectLanguage(lang) {
    selectedLanguage = lang;
    localStorage.setItem('museum_lang', lang);

    // Update UI
    document.querySelectorAll('.lang-option').forEach(btn => {
        btn.classList.toggle('selected', btn.dataset.lang === lang);
    });

    document.getElementById('languageSelector').classList.remove('active');

    // Inform the bot
    const langNames = {
        en: 'English', hi: 'Hindi', es: 'Spanish', fr: 'French',
        de: 'German', ja: 'Japanese', zh: 'Chinese', ar: 'Arabic'
    };

    addMessage('bot', `🌐 Language set to **${langNames[lang]}**. I'll try to respond in your preferred language.`);
}

// ═══════════════════ SESSION HISTORY ═══════════════════

async function loadSessionHistory() {
    if (!currentSessionId) return;

    try {
        const response = await fetch(`${API_BASE}/api/chat/session/${currentSessionId}`);
        if (response.ok) {
            const session = await response.json();
            const container = document.getElementById('chatMessages');
            container.innerHTML = '';

            if (session.messages && session.messages.length > 0) {
                // Show last 20 messages
                const recentMessages = session.messages.slice(-20);
                recentMessages.forEach(msg => {
                    const role = msg.role === 'user' ? 'user' : 'bot';
                    addMessage(role, msg.content);
                });
            }

            // Restore language
            if (session.language) {
                selectedLanguage = session.language;
                localStorage.setItem('museum_lang', selectedLanguage);
            }
        } else if (response.status === 404) {
            // Session not found - clear stale data
            localStorage.removeItem('museum_session_id');
            currentSessionId = null;
        }
    } catch (e) {
        console.log('Could not load session history:', e);
    }
}

// ═══════════════════ EXHIBITIONS LOADER ═══════════════════

async function loadExhibitions() {
    const grid = document.getElementById('exhibitionsGrid');

    try {
        const response = await fetch(`${API_BASE}/api/tickets/exhibitions`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        if (data.exhibitions && data.exhibitions.length > 0) {
            grid.innerHTML = '';
            const icons = ['🏺', '🎨', '📸', '🪐', '🕌', '🦕', '🎭', '🏛️'];

            data.exhibitions.forEach((ex, i) => {
                const icon = icons[i % icons.length];
                const card = document.createElement('div');
                card.className = 'exhibition-card';
                card.setAttribute('data-aos', 'fade-up');
                card.style.opacity = '0';
                card.style.transform = 'translateY(30px)';
                card.style.transition = `all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) ${i * 0.1}s`;

                card.innerHTML = `
                    <div class="exhibition-card-image">
                        ${ex.is_special ? '<div class="exhibition-special-badge">✨ Special</div>' : ''}
                        <span>${icon}</span>
                    </div>
                    <div class="exhibition-card-body">
                        <h3>${escapeHtml(ex.name)}</h3>
                        <p>${escapeHtml(ex.description)}</p>
                        <div class="exhibition-meta">
                            <span class="exhibition-price">₹${ex.ticket_price}</span>
                            <span class="exhibition-date">📅 Till ${ex.end_date}</span>
                        </div>
                        ${ex.show_times ? `<div style="margin-top:10px;color:var(--text-muted);font-size:0.85rem;">⏰ Shows: ${ex.show_times.join(', ')}</div>` : ''}
                        <button class="exhibition-book-btn" onclick="bookExhibition('${escapeHtml(ex.name)}')">Book Tickets →</button>
                    </div>
                `;
                grid.appendChild(card);

                // Trigger animation
                setTimeout(() => {
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, 100 + i * 100);
            });
        } else {
            grid.innerHTML = '<p style="text-align:center;color:var(--text-muted);grid-column:1/-1;">No exhibitions currently available.</p>';
        }
    } catch (error) {
        grid.innerHTML = '<p style="text-align:center;color:var(--text-muted);grid-column:1/-1;">Loading exhibitions...</p>';
        console.log('Could not load exhibitions:', error);
        // Retry after 3 seconds
        setTimeout(loadExhibitions, 3000);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function bookExhibition(name) {
    if (!chatOpen) toggleChat();
    setTimeout(() => {
        document.getElementById('chatInput').value = `Book tickets for ${name}`;
        sendMessage();
    }, 500);
}

// ═══════════════════ PARTICLE EFFECTS ═══════════════════

function initParticles() {
    const container = document.getElementById('heroParticles');
    if (!container) return;

    const particleCount = 50;

    // Add a unique style block for particle animations
    const style = document.createElement('style');
    let keyframes = '';

    for (let i = 0; i < particleCount; i++) {
        const size = Math.random() * 3 + 1;
        const x = Math.random() * 100;
        const y = Math.random() * 100;
        const duration = Math.random() * 20 + 10;
        const delay = Math.random() * 10;
        const opacity = Math.random() * 0.5 + 0.1;

        // Unique keyframes per particle for varied motion
        const dx1 = Math.random() * 60 - 30;
        const dy1 = Math.random() * -60;
        const dx2 = Math.random() * 40 - 20;
        const dy2 = Math.random() * -40;
        const dx3 = Math.random() * -40;
        const dy3 = Math.random() * 30;

        keyframes += `
            @keyframes floatParticle${i} {
                0%, 100% { transform: translate(0, 0) scale(1); }
                25% { transform: translate(${dx1}px, ${dy1}px) scale(1.2); }
                50% { transform: translate(${dx2}px, ${dy2}px) scale(0.8); }
                75% { transform: translate(${dx3}px, ${dy3}px) scale(1.1); }
            }
        `;

        const particle = document.createElement('div');
        particle.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            background: ${Math.random() > 0.5 ? 'var(--accent-primary)' : 'var(--accent-secondary)'};
            border-radius: 50%;
            left: ${x}%;
            top: ${y}%;
            opacity: ${opacity};
            animation: floatParticle${i} ${duration}s ease-in-out ${delay}s infinite;
            will-change: transform;
        `;
        container.appendChild(particle);
    }

    style.textContent = keyframes;
    document.head.appendChild(style);
}

// ═══════════════════ SCROLL ANIMATIONS ═══════════════════

function initScrollAnimations() {
    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        },
        { threshold: 0.1 }
    );

    // Animate feature cards
    document.querySelectorAll('.feature-card').forEach((card, i) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        card.style.transition = `all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) ${i * 0.1}s`;
        observer.observe(card);
    });

    // Animate pricing cards
    document.querySelectorAll('.pricing-card').forEach((card, i) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        card.style.transition = `all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) ${i * 0.15}s`;
        observer.observe(card);
    });
}

// ═══════════════════ NAVBAR SCROLL EFFECT ═══════════════════

let lastScroll = 0;
window.addEventListener('scroll', () => {
    const nav = document.querySelector('.hero-nav');
    const scrollTop = window.scrollY;

    if (scrollTop > 100) {
        nav.style.background = 'rgba(10, 10, 26, 0.95)';
        nav.style.backdropFilter = 'blur(20px)';
        nav.style.borderBottomColor = 'rgba(124, 92, 252, 0.2)';
    } else {
        nav.style.background = 'rgba(10, 10, 26, 0.6)';
        nav.style.backdropFilter = 'blur(10px)';
        nav.style.borderBottomColor = 'rgba(124, 92, 252, 0.15)';
    }

    lastScroll = scrollTop;
});
