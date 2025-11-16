import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import Message, User, Chat, Channel

# --- تنظیمات ضروری ---
API_ID = 29299283             # 🔸 حتماً جایگزین کنید
API_HASH = 'API_HASH'     # 🔸 حتماً جایگزین کنید
SESSION_NAME = 'my_banner_bot_session'

# --- تنظیمات پیشرفته ---
SEND_TO_PRIVATE_CHATS = True  # True = هم پی‌وی‌ها هم گروه/کانال | False = فقط گروه/کانال

# متغیرهای جهانی برای زمان‌بندی
scheduled_task = None
scheduled_message = None
scheduled_interval = 0
client_instance = None

# -------------------------

async def send_to_all_chats(client, replied_msg):
    dialogs = await client.get_dialogs()
    target_chats = []
    for d in dialogs:
        entity = d.entity
        if isinstance(entity, (Chat, Channel)):
            target_chats.append(d)
        elif SEND_TO_PRIVATE_CHATS and isinstance(entity, User) and not entity.bot:
            target_chats.append(d)

    if not target_chats:
        return 0, 0

    sent_count = 0
    failed_count = 0
    for dialog in target_chats:
        try:
            if replied_msg.text and not replied_msg.media:
                await client.send_message(dialog.id, replied_msg.text)
            elif replied_msg.media:
                await client.send_file(dialog.id, replied_msg.media, caption=replied_msg.text or "")
            else:
                continue
            sent_count += 1
        except Exception as e:
            print(f"❌ خطا در ارسال به {dialog.name or dialog.id}: {e}")
            failed_count += 1

    return sent_count, failed_count


async def scheduled_sender():
    global scheduled_message, scheduled_interval
    while True:
        try:
            if scheduled_message:
                sent, failed = await send_to_all_chats(client_instance, scheduled_message)
                print(f"[زمان‌بندی] ارسال موفق: {sent} | خطا: {failed}")
            else:
                break
        except Exception as e:
            print(f"[زمان‌بندی] خطا در ارسال خودکار: {e}")
        await asyncio.sleep(scheduled_interval)


def get_help_message():
    return (
        "پنل ربات SHAHZADEH MAKHLOGHAT\n\n"
        "🤖 **راهنمای ربات Banner Sender**\n\n"
        "🔹 `/banner` — پیام ریپلای‌شده را **یک‌باره** به تمام چت‌های مجاز ارسال می‌کند.\n\n"
        "🔹 `/schedule_banner <ثانیه>` — پیام ریپلای‌شده را **هر X ثانیه** ارسال می‌کند. (حداقل: 10 ثانیه)\n"
        "  مثال: `/schedule_banner 60`\n\n"
        "🔹 `/stop_banner` — ارسال خودکار (زمان‌بندی‌شده) را متوقف می‌کند.\n\n"
        "🔹 `/test_bot` — تست اتصال ربات.\n\n"
        "ℹ️ **نکات مهم**:\n"
        " • حتماً یک پیام را **ریپلای** کنید.\n"
        " • از اسپم خودداری کنید.\n"
        " • اگر در گروه هستید، دستور را مستقیم بنویسید (نیازی به @نام‌ربات نیست)."
    )


async def handler(event: Message):
    global scheduled_task, scheduled_message, scheduled_interval, client_instance

    # 🔍 دریافت اطلاعات فرستنده (برای لاگ)
    sender_info = await event.get_sender()
    sender_name = getattr(sender_info, 'first_name', 'Unknown')
    if sender_info and hasattr(sender_info, 'username') and sender_info.username:
        sender_name = f"@{sender_info.username}"
    print(f"\n[!!! پیام جدید دریافت شد !!!] از: {sender_name} (ID: {event.chat_id})")

    raw_text = event.raw_text.strip()
    if not raw_text:
        return  # پیام خالی

    # استخراج دستور اصلی (اولین کلمه)
    command = raw_text.split()[0].lower().rstrip('!@#')

    # --- دستورات ---
    if command in ('/help', 'help'):
        await event.reply(get_help_message(), parse_mode='markdown')
        print(">>> دستور help اجرا شد.")
        return

    if command == '/test_bot':
        await event.reply('✅ تست موفق: رویداد دریافت شد و پاسخ دادم!')
        print(">>> دستور /test_bot اجرا شد.")
        return

    if command == '/banner':
        if not event.message.reply_to_msg_id:
            await event.reply('❌ لطفاً یک پیام را **ریپلای** کنید و سپس `/banner` را ارسال کنید.')
            return

        replied_msg = await event.get_reply_message()
        if not replied_msg or (not replied_msg.text and not replied_msg.media):
            await event.reply('❌ پیام ریپلای شده خالی است یا قابل دسترسی نیست.')
            return

        sent_count, failed_count = await send_to_all_chats(event.client, replied_msg)
        await event.reply(
            f"✅ پیام با موفقیت در **{sent_count}** چت ارسال شد.\n"
            f"❌ **{failed_count}** مورد با خطا مواجه شد."
        )
        print(f">>> ارسال /banner کامل شد. موفق: {sent_count} | خطا: {failed_count}")
        return

    if command == '/schedule_banner':
        parts = raw_text.split()
        if len(parts) != 2 or not parts[1].isdigit():
            await event.reply('❌ استفاده صحیح: `/schedule_banner 30` (هر 30 ثانیه)')
            return

        interval = int(parts[1])
        if interval < 10:
            await event.reply('⚠️ حداقل فاصله زمانی **10 ثانیه** است.')
            return

        if not event.message.reply_to_msg_id:
            await event.reply('❌ لطفاً یک پیام را **ریپلای** کنید و سپس دستور را ارسال کنید.')
            return

        replied_msg = await event.get_reply_message()
        if not replied_msg or (not replied_msg.text and not replied_msg.media):
            await event.reply('❌ پیام ریپلای شده خالی است یا قابل دسترسی نیست.')
            return

        # لغو ارسال قبلی
        global scheduled_task
        if scheduled_task and not scheduled_task.done():
            scheduled_task.cancel()
            print(">>> ارسال قبلی لغو شد.")

        # راه‌اندازی جدید
        scheduled_message = replied_msg
        scheduled_interval = interval
        client_instance = event.client
        scheduled_task = asyncio.create_task(scheduled_sender())

        await event.reply(
            f'🔁 ارسال خودکار هر **{interval} ثانیه** فعال شد!\n'
            f'برای توقف: `/stop_banner`',
            parse_mode='markdown'
        )
        print(f">>> ارسال خودکار هر {interval} ثانیه شروع شد.")
        return

    if command == '/stop_banner':
        if scheduled_task and not scheduled_task.done():
            scheduled_task.cancel()
            scheduled_task = None
            scheduled_message = None
            await event.reply('⏹️ ارسال خودکار با موفقیت متوقف شد.')
            print(">>> ارسال خودکار متوقف شد.")
        else:
            await event.reply('ℹ️ هیچ ارسال خودکاری در حال اجرا نیست.')
        return


# --- اجرای کلاینت ---
async def main():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    print("--- ربات با موفقیت متصل شد ---")
    print("🌟 ربات آماده اجرا است.")
    print("💡 دستورات: /help")

    # 🔄 گوش دادن به همه پیام‌های جدید (چه ورودی، چه خروجی)
    client.add_event_handler(handler, events.NewMessage())

    await client.run_until_disconnected()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "cannot be run inside" in str(e):
            # برای محیط‌هایی مثل Jupyter یا برخی IDEها
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(main())
            else:
                loop.run_until_complete(main())
        else:
            raise