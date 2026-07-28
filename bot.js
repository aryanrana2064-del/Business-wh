// ============================================
// ARYAN VX7 — WhatsApp Auto-Reply Bot
// Premium Digital Agency
// ============================================

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

// ============================================
// BRAND CONFIGURATION
// ============================================
const CONFIG = {
    brandName: 'ARYAN VX7',
    tagline: 'Premium Digital Agency',
    phone: '+91 9105315121',
    whatsapp: '+91 9286928539',
    instagram: '@aryan.vx7',
    telegram: '@BYTEFURY_02',
    website: 'https://aryan-vx7.vercel.app',
    email: 'aryanvx7@gmail.com',
    ownerName: 'Aryan',
    replyDelay: 1500
};

// ============================================
// AUTO-REPLY MESSAGES
// ============================================
const REPLIES = {
    // Main auto-reply (offline/general)
    main: `🚀 *${CONFIG.brandName} — ${CONFIG.tagline}*

Thank you for reaching out! 🙏

We help businesses, startups & creators build a powerful digital presence with premium creative solutions.

━━━━━━━━━━━━━━━━━━

🌐 *Our Services:*
• Website Development
• Cinematic Video Shooting
• Professional Video Editing
• Branding & Creative Design
• Social Media Content

━━━━━━━━━━━━━━━━━━

✨ *Why Choose Us?*
✔ Premium Quality
✔ Modern & Creative Designs
✔ Fast Delivery
✔ Affordable Pricing
✔ Professional Support

━━━━━━━━━━━━━━━━━━

💬 *Quick Commands:*
Reply with a number:
*1* - Website Development
*2* - Video Shooting
*3* - Video Editing
*4* - Branding & Design
*5* - Social Media
*6* - Get Quote
*7* - View Portfolio
*8* - Contact Info

━━━━━━━━━━━━━━━━━━

📩 Or visit: ${CONFIG.website}
📞 Urgent? Call: ${CONFIG.phone}

_I'll reply personally within 1-2 hours!_ 🙏`,

    // Service details
    service1: `🌐 *Website Development*

We build modern, fast & responsive websites:
• Business Websites
• E-commerce Stores
• Landing Pages
• Portfolio Sites
• Web Applications

⚡ *Tech Stack:* HTML/CSS, React, Node.js, Firebase
💰 *Starting from:* ₹4,999
⏱ *Delivery:* 3-7 days

📩 Reply *QUOTE* for custom pricing!
Or visit: ${CONFIG.website}`,

    service2: `🎬 *Cinematic Video Shooting*

Professional video production:
• Product Videos
• Brand Films
• Event Coverage
• Music Videos
• Commercial Ads

🎥 *Equipment:* Cinema cameras, Drone, Studio lighting
💰 *Starting from:* ₹9,999
⏱ *Delivery:* 5-14 days

📩 Reply *QUOTE* for custom pricing!`,

    service3: `🎞 *Professional Video Editing*

Premium post-production services:
• Color Grading
• VFX & Motion Graphics
• Sound Design
• Transitions & Effects
• Social Media Cuts

🛠 *Tools:* Premiere Pro, After Effects, DaVinci Resolve
💰 *Starting from:* ₹2,999
⏱ *Delivery:* 1-5 days

📩 Reply *QUOTE* for custom pricing!`,

    service4: `🎨 *Branding & Creative Design*

Complete brand identity solutions:
• Logo Design
• Brand Guidelines
• Packaging Design
• Business Cards
• Social Media Kit

🎯 *Includes:* Source files, Multiple revisions
💰 *Starting from:* ₹3,999
⏱ *Delivery:* 3-7 days

📩 Reply *QUOTE* for custom pricing!`,

    service5: `📱 *Social Media Content*

Engaging content for your platforms:
• Instagram Reels & Posts
• YouTube Shorts & Thumbnails
• TikTok Videos
• Carousel Designs
• Story Templates

📈 *Platforms:* Instagram, YouTube, Facebook, TikTok
💰 *Starting from:* ₹1,999/month
⏱ *Delivery:* Weekly content calendar

📩 Reply *QUOTE* for custom pricing!`,

    // Quote request
    quote: `📋 *Get a Custom Quote*

Please share these details:
• Service needed:
• Project description:
• Budget range:
• Deadline:
• Reference links (if any):

📩 Just type your requirements and I'll get back with a custom quote within 24 hours!

Or fill the form: ${CONFIG.website}

Thank you! 🙏`,

    // Portfolio
    portfolio: `🎯 *Our Portfolio*

Check out our recent work:
🌐 ${CONFIG.website}

📱 Instagram: ${CONFIG.instagram}
💬 Telegram: ${CONFIG.telegram}

Highlights:
✅ 50+ Projects Completed
✅ 100+ Happy Clients
✅ 4.9/5 Average Rating

Reply a number to see specific work:
*1* - Websites
*2* - Videos
*3* - Designs`,

    // Contact info
    contact: `📞 *Contact ARYAN VX7*

💬 WhatsApp: ${CONFIG.whatsapp}
📞 Phone: ${CONFIG.phone}
📷 Instagram: ${CONFIG.instagram}
✈️ Telegram: ${CONFIG.telegram}
📧 Email: ${CONFIG.email}
🌐 Website: ${CONFIG.website}

⏰ *Working Hours:*
Mon-Sat: 9 AM - 9 PM
Sunday: Limited availability

📩 Feel free to message anytime!`,

    // Thank you
    thanks: `🙏 *Thank You!*

Your message has been received. I'll personally get back to you within 1-2 hours.

⚡ *In the meantime:*
• Browse our work: ${CONFIG.website}
• Instagram: ${CONFIG.instagram}
• Urgent: Call ${CONFIG.phone}

Have a great day! ✨`
};

// ============================================
// INITIALIZE WHATSAPP CLIENT
// ============================================
const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './aryan-auth' }),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

// ============================================
// QR CODE
// ============================================
client.on('qr', (qr) => {
    console.clear();
    console.log('╔══════════════════════════════════════╗');
    console.log('║     ARYAN VX7 - WhatsApp Bot        ║');
    console.log('║     Scan QR Code to Connect         ║');
    console.log('╚══════════════════════════════════════╝\n');
    qrcode.generate(qr, { small: true });
});

// ============================================
// BOT READY
// ============================================
client.on('ready', () => {
    console.clear();
    console.log('╔══════════════════════════════════════╗');
    console.log('║                                      ║');
    console.log('║   ✅ ARYAN VX7 BOT IS LIVE!         ║');
    console.log('║   🚀 Auto-reply Active              ║');
    console.log('║   📱 Premium Digital Agency         ║');
    console.log('║                                      ║');
    console.log('╚══════════════════════════════════════╝');
});

// ============================================
// MESSAGE HANDLER — AUTO REPLY
// ============================================
client.on('message', async (message) => {
    if (message.fromMe || message.isStatus) return;

    const chat = await message.getChat();
    const contact = await message.getContact();
    const name = contact.pushname || contact.name || 'Friend';
    const firstName = name.split(' ')[0];
    const text = message.body?.trim() || '';
    const textLower = text.toLowerCase();

    console.log(`📩 [${name}]: ${text}`);

    // Mark as read
    await chat.sendSeen();

    let reply = '';

    // ============================================
    // KEYWORD DETECTION
    // ============================================
    if (text === '1' || textLower.includes('website') || textLower.includes('web dev')) {
        reply = REPLIES.service1;
    } 
    else if (text === '2' || textLower.includes('video shoot') || textLower.includes('shooting')) {
        reply = REPLIES.service2;
    } 
    else if (text === '3' || textLower.includes('video edit') || textLower.includes('editing')) {
        reply = REPLIES.service3;
    } 
    else if (text === '4' || textLower.includes('brand') || textLower.includes('design') || textLower.includes('logo')) {
        reply = REPLIES.service4;
    } 
    else if (text === '5' || textLower.includes('social') || textLower.includes('content') || textLower.includes('instagram')) {
        reply = REPLIES.service5;
    } 
    else if (text === '6' || textLower.includes('quote') || textLower.includes('price') || textLower.includes('cost')) {
        reply = REPLIES.quote;
    } 
    else if (text === '7' || textLower.includes('portfolio') || textLower.includes('work') || textLower.includes('project')) {
        reply = REPLIES.portfolio;
    } 
    else if (text === '8' || textLower.includes('contact') || textLower.includes('call') || textLower.includes('number')) {
        reply = REPLIES.contact;
    } 
    else if (textLower.match(/^(hi|hello|hey|hlo|hy|yo|sup)/i)) {
        reply = `👋 *Hey ${firstName}!*\n\n` + REPLIES.main;
    } 
    else if (textLower.includes('thank') || textLower.includes('thanks')) {
        reply = REPLIES.thanks;
    } 
    else {
        reply = `👋 *Hi ${firstName}!*\n\n` + REPLIES.main;
    }

    // Add footer
    reply += `\n\n━━━━━━━━━━━━━━━\n🤖 Auto-reply | ${CONFIG.brandName}\n🌐 ${CONFIG.website}`;

    // Send reply
    setTimeout(async () => {
        try {
            await message.reply(reply);
            console.log(`✅ Replied to ${name}`);
        } catch (error) {
            console.error('❌ Error:', error.message);
        }
    }, CONFIG.replyDelay);
});

// ============================================
// START BOT
// ============================================
client.initialize();
console.log('🔄 Starting ARYAN VX7 Bot...\n');