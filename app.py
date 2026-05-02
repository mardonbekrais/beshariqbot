import logging

import sqlite3

from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

import os

from dotenv import load_dotenv
from firebase_db import firebase_db

load_dotenv()

# Firebase ni ishga tushirish (ixtiyoriy, .env da FIREBASE_URL bo'lsa)
if os.getenv('FIREBASE_DATABASE_URL'):
    firebase_db.initialize(
        database_url=os.getenv('FIREBASE_DATABASE_URL'),
        credential_path=os.getenv('FIREBASE_CREDENTIAL_PATH')
    )



# Enable logging

logging.basicConfig(

    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',

    level=logging.INFO

)

logger = logging.getLogger(__name__)



# Database setup

def init_db():

    conn = sqlite3.connect('taxibot.db')

    cursor = conn.cursor()

    

    # Users table

    cursor.execute('''

        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            telegram_id INTEGER UNIQUE,

            name TEXT,

            phone TEXT,

            user_type TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

    ''')

    

    # Driver applications table

    cursor.execute('''

        CREATE TABLE IF NOT EXISTS driver_applications (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            telegram_id INTEGER,

            name TEXT,

            phone TEXT,

            status TEXT DEFAULT 'pending',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

    ''')

    

    # Orders table

    cursor.execute('''

        CREATE TABLE IF NOT EXISTS orders (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            order_type TEXT,

            destination TEXT,

            passenger_count INTEGER,

            driver_id INTEGER DEFAULT NULL,

            status TEXT DEFAULT 'pending',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id) REFERENCES users (telegram_id)

        )

    ''')

    

    # Drivers table

    cursor.execute('''

        CREATE TABLE IF NOT EXISTS drivers (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            telegram_id INTEGER UNIQUE,

            name TEXT,

            phone TEXT,

            status TEXT DEFAULT 'active',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

    ''')

    

    # Driver approvals table

    cursor.execute('''

        CREATE TABLE IF NOT EXISTS driver_approvals (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            application_id INTEGER,

            telegram_id INTEGER,

            approved_by INTEGER,

            approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (application_id) REFERENCES driver_applications (id)

        )

    ''')

    

    conn.commit()

    conn.close()



# Main menu keyboard

def get_main_menu():

    keyboard = [

        [KeyboardButton("🚖 Yo'lovchi"), KeyboardButton("🚗 Taksi bo'lish")],

        [KeyboardButton("📦 Pochta yuborish")]

    ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)



# Passenger menu

def get_passenger_menu():

    keyboard = [

        [KeyboardButton("📍 Joylashuvni yuborish"), KeyboardButton("✏️ Manzilni kiriting")],

        [KeyboardButton("🔙 Orqaga")]

    ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)



# Driver menu keyboard

def get_driver_menu():

    keyboard = [

        [KeyboardButton("📋 Mening buyurtmalarim")],

        [KeyboardButton("📝 Ariza yuborish"), KeyboardButton("📊 Mening arizam")],

        [KeyboardButton("🔙 Orqaga")]

    ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)



# Admin panel keyboard

def get_admin_menu():

    keyboard = [

        [KeyboardButton("📊 Statistika"), KeyboardButton("� Buyurtmalar")],

        [KeyboardButton("🚗 Haydovchilar"), KeyboardButton("📋 Arizalar")],

        [KeyboardButton("➕ Haydovchi qo'shish"), KeyboardButton("🔙 Orqaga")]

    ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)



# Driver management keyboard with approval options

def get_driver_management_menu():

    keyboard = [

        [KeyboardButton("📋 Faol haydovchilar"), KeyboardButton("⏸ Band haydovchilar")],

        [KeyboardButton("➕ Yangi haydovchi"), KeyboardButton("📞 Telefon bilan qo'shish")],

        [KeyboardButton("✅ Arizalarni tasdiqlash"), KeyboardButton("🗑 Haydovchi o'chirish")],

        [KeyboardButton("🔙 Orqaga")]

    ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)



# Start command

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    user = update.effective_user

    telegram_id = user.id

    

    # Check if user exists

    conn = sqlite3.connect('taxibot.db')

    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))

    existing_user = cursor.fetchone()

    

    if not existing_user:

        # Auto-register user with Telegram info

        username = f"@{user.username}" if user.username else user.first_name

        cursor.execute('INSERT OR REPLACE INTO users (telegram_id, name) VALUES (?, ?)', 

                      (telegram_id, username))

        conn.commit()

        # Firebase ga ham saqlash

        firebase_db.save_user(telegram_id, username)

        await update.message.reply_text(

            f"Assalomu alaykum, {user.first_name}! 🚖\n\n"

            "Taksi botimizga xush kelibsiz!\n\n"

            "Iltimos, telefon raqamingizni kiriting yoki pastdagi tugmani bosing:",

            reply_markup=ReplyKeyboardMarkup([

                [KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)]

            ], resize_keyboard=True)

        )

        context.user_data['awaiting_phone'] = True

    else:

        await update.message.reply_text(

            f"Xush kelibsiz, {user.first_name}! 🚖\n\n"

            "Asosiy menyuga qaytdingiz.",

            reply_markup=get_main_menu()

        )

    

    conn.close()



# Handle text messages

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    user = update.effective_user

    telegram_id = user.id

    text = update.message.text

    

    conn = sqlite3.connect('taxibot.db')

    cursor = conn.cursor()

    

    # Handle phone registration

    if context.user_data.get('awaiting_phone'):

        if update.message.contact:

            phone = update.message.contact.phone_number

        else:

            phone = text.strip()

        

        cursor.execute('UPDATE users SET phone = ? WHERE telegram_id = ?', (phone, telegram_id))

        conn.commit()

        

        # Firebase da ham yangilash

        user = firebase_db.get_user(telegram_id)

        if user:

            firebase_db.save_user(telegram_id, user.get('name'), phone, user.get('user_type'))

        

        await update.message.reply_text(

            "Ro'yxatdan o'tdingiz! 🎉\n\n"

            "Endi asosiy menyudan foydalanishingiz mumkin:",

            reply_markup=get_main_menu()

        )

        context.user_data['awaiting_phone'] = False

        conn.close()

        return

    

    elif text == "🚖 Yo'lovchi":

        await update.message.reply_text(

            "Yo'lovchi rejimiga o'tdingiz! 🚖\n\n"

            "Iltimos, yo'lovchilar sonini kiriting:",

            reply_markup=ReplyKeyboardMarkup([

                [KeyboardButton("1 kishi"), KeyboardButton("2 kishi")],

                [KeyboardButton("3 kishi"), KeyboardButton("4+ kishi")],

                [KeyboardButton("🔙 Orqaga")]

            ], resize_keyboard=True)

        )

        context.user_data['mode'] = 'passenger'

        context.user_data['awaiting_passengers'] = True

    

    elif text == "🚗 Taksi bo'lish":

        # Check if user is already a driver

        cursor.execute('SELECT * FROM drivers WHERE telegram_id = ?', (telegram_id,))

        driver = cursor.fetchone()

        

        if driver:

            # User is already a driver, show driver menu

            await update.message.reply_text(

                "🚗 Haydovchi menyusi!\n\n"

                "Quyidagi funktsiyalardan foydalanishingiz mumkin:",

                reply_markup=get_driver_menu()

            )

            context.user_data['mode'] = 'driver'

        else:

            # User is not a driver yet, show application menu

            await update.message.reply_text(

                "Haydovchi bo'lish rejimi! 🚗\n\n"

                "Taksi haydovchisi bo'lish uchun ariza topshiring:",

                reply_markup=get_driver_menu()

            )

            context.user_data['mode'] = 'driver'

    

    elif text == "📦 Pochta yuborish":

        await update.message.reply_text(

            "Pochta yuborish xizmati! 📦\n\n"

            "Pochtangizni qayerga yetkazish kerak?",

            reply_markup=ReplyKeyboardMarkup([

                [KeyboardButton("Beshariqdan Farg'onaga"), KeyboardButton("Farg'onadan Beshariqqa")],

                [KeyboardButton("🔙 Orqaga")]

            ], resize_keyboard=True)

        )

        context.user_data['mode'] = 'delivery'

        context.user_data['awaiting_delivery_destination'] = True

    

    elif text == "👤 Profil":

        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))

        user_data = cursor.fetchone()

        if user_data:

            await update.message.reply_text(

                f"👤 Sizning profilingiz:\n\n"

                f"📝 Ism: {user_data[2]}\n"

                f"📱 Telefon: {user_data[3]}\n"

                f"👥 Foydalanuvchi turi: {user_data[4] or 'Belgilanmagan'}\n"

                f"📅 Ro'yxatdan o'tgan: {user_data[5]}",

                reply_markup=get_main_menu()

            )

    

    elif text == "🔙 Orqaga":

        await update.message.reply_text(

            "Asosiy menyuga qaytdingiz:",

            reply_markup=get_main_menu()

        )

        context.user_data.clear()

    

    # Handle passenger count selection

    elif context.user_data.get('awaiting_passengers') and text in ["1 kishi", "2 kishi", "3 kishi", "4+ kishi"]:

        passenger_count = text.split()[0]

        context.user_data['passenger_count'] = passenger_count

        context.user_data['awaiting_passengers'] = False

        context.user_data['awaiting_destination'] = True

        

        await update.message.reply_text(

            f"Yo'lovchilar soni: {passenger_count}\n\n"

            "Qayerga bormoqchisiz? Marshrutni tanlang:",

            reply_markup=ReplyKeyboardMarkup([

                [KeyboardButton("Beshariqdan Farg'onaga"), KeyboardButton("Farg'onadan Beshariqqa")],

                [KeyboardButton("🔙 Orqaga")]

            ], resize_keyboard=True)

        )

    

    # Handle destination input

    elif context.user_data.get('awaiting_destination'):

        destination = text.strip()

        passenger_count = context.user_data.get('passenger_count', '1')

        

        # Save order

        cursor.execute('''

            INSERT INTO orders (user_id, order_type, destination, passenger_count)

            VALUES (?, ?, ?, ?)

        ''', (telegram_id, 'taxi', destination, int(passenger_count)))

        conn.commit()

        

        # Get user info for admin notification

        username = f"@{user.username}" if user.username else user.first_name

        

        # Send notification to admin and group

        admin_message = (

            f"🚖 YANGI TAKSI BUYURTMA!\n\n"

            f"👤 Mijoz: {username}\n"

            f"🆔 Telegram ID: {telegram_id}\n"

            f"👥 Yo'lovchilar soni: {passenger_count}\n"

            f"📍 Manzil: {destination}\n"

            f"📅 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        )

        

        # Create inline keyboard for order taking

        order_id = cursor.lastrowid

        

        # Firebase ga buyurtma saqlash

        firebase_db.create_order(order_id, telegram_id, 'taxi', destination, int(passenger_count))

        

        order_keyboard = InlineKeyboardMarkup([

            [InlineKeyboardButton("🚖 Buyurtmani olish", callback_data=f"take_order_{order_id}")],

            [InlineKeyboardButton("📋 Batafsil", callback_data=f"order_details_{order_id}")]

        ])

        

        # Send to admin

        try:

            await context.bot.send_message(

                chat_id=os.getenv('ADMIN_CHAT_ID', ''), 

                text=admin_message,

                reply_markup=order_keyboard

            )

        except:

            pass

        

        # Send to group

        try:

            group_username = os.getenv('GROUP_USERNAME', '')

            if group_username:

                # Remove @ if present

                if group_username.startswith('@'):

                    group_username = group_username[1:]

                

                # Try to send to group

                await context.bot.send_message(

                    chat_id=f"@{group_username}", 

                    text=admin_message,

                    reply_markup=order_keyboard

                )

                

                # Log success

                print(f"✅ Group message sent to @{group_username}")

        except Exception as e:

            # Log error for debugging

            print(f" Failed to send group message: {e}")

            # If group message fails, continue without notification

            pass

        

        # Get order details for passenger confirmation

        cursor.execute('''

            SELECT o.*, u.name, u.phone FROM orders o 

            LEFT JOIN users u ON o.user_id = u.telegram_id 

            WHERE o.id = ?

        ''', (order_id,))

        order_details = cursor.fetchone()

        

        await update.message.reply_text(

            f"✅ Buyurtmangiz qabul qilindi!\n\n"

            f"🆔 Buyurtma raqami: #{order_id}\n"

            f"👥 Yo'lovchilar soni: {passenger_count}\n"

            f"📍 Manzil: {destination}\n"

            f"📅 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

            "Tez orada siz bilan bog'lanamiz. Haydovchi topilganda sizga xabar beramiz.",

            reply_markup=get_main_menu()

        )

        context.user_data.clear()

    

    # Handle delivery destination

    elif context.user_data.get('awaiting_delivery_destination'):

        destination = text.strip()

        

        # Save delivery order

        cursor.execute('''

            INSERT INTO orders (user_id, order_type, destination)

            VALUES (?, ?, ?)

        ''', (telegram_id, 'delivery', destination))

        conn.commit()

        

        # Get user info for admin notification

        username = f"@{user.username}" if user.username else user.first_name

        

        # Send notification to admin and group

        delivery_message = (

            f"📦 YANGI POCHTA BUYURTMA!\n\n"

            f"👤 Mijoz: {username}\n"

            f"🆔 Telegram ID: {telegram_id}\n"

            f"📍 Yetkazish manzili: {destination}\n"

            f"📅 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        )

        

        # Create inline keyboard for delivery order taking

        delivery_order_id = cursor.lastrowid

        

        # Firebase ga pochta buyurtmasi saqlash

        firebase_db.create_order(delivery_order_id, telegram_id, 'delivery', destination, 1)

        

        delivery_keyboard = InlineKeyboardMarkup([

            [InlineKeyboardButton("📦 Buyurtmani olish", callback_data=f"take_order_{delivery_order_id}")],

            [InlineKeyboardButton("📋 Batafsil", callback_data=f"order_details_{delivery_order_id}")]

        ])

        

        # Send to admin

        try:

            await context.bot.send_message(

                chat_id=os.getenv('ADMIN_CHAT_ID', ''), 

                text=delivery_message,

                reply_markup=delivery_keyboard

            )

        except:

            pass

        

        # Send to group

        try:

            group_username = os.getenv('GROUP_USERNAME', '')

            if group_username:

                # Remove @ if present

                if group_username.startswith('@'):

                    group_username = group_username[1:]

                

                # Try to send to group

                await context.bot.send_message(

                    chat_id=f"@{group_username}", 

                    text=delivery_message,

                    reply_markup=delivery_keyboard

                )

                

                # Log success

                print(f"✅ Delivery message sent to @{group_username}")

        except Exception as e:

            print(f"❌ Failed to send delivery message: {e}")

            # If group message fails, continue without notification

            pass

        

        await update.message.reply_text(

            f"📦 Pochta buyurtmangiz qabul qilindi!\n\n"

            f"📍 Yetkazish manzili: {destination}\n\n"

            "Tez orada siz bilan bog'lanamiz. Kurerni topilganda sizga xabar beramiz.",

            reply_markup=get_main_menu()

        )

        context.user_data.clear()

    

    # Handle delivery destination (second handler - should not be here, first one already handles it)

    elif context.user_data.get('awaiting_delivery_destination') and False:

        # This block is intentionally disabled - handled above already

        pass

    

    elif text == "📋 Mening buyurtmalarim":

        # Check if user is a driver

        cursor.execute('SELECT * FROM drivers WHERE telegram_id = ?', (telegram_id,))

        driver = cursor.fetchone()

        

        if driver:

            cursor.execute('''

                SELECT o.*, u.name, u.phone FROM orders o 

                LEFT JOIN users u ON o.user_id = u.telegram_id 

                WHERE o.driver_id = ?

                ORDER BY o.created_at DESC

                LIMIT 20

            ''', (telegram_id,))

            orders = cursor.fetchall()

            

            if not orders:

                await update.message.reply_text(

                    "📋 Siz hali buyurtma olmadingiz.",

                    reply_markup=get_driver_menu()

                )

            else:

                message = "📋 Mening buyurtmalarim:\n\n"

                for order in orders:

                    order_type = "🚖 Taksi" if order[2] == 'taxi' else "📦 Pochta"

                    passenger_info = f"👥 {order[4] or 0} kishi" if order[2] == 'taxi' else ""

                    status_map = {'pending': '⏳', 'assigned': '🚗', 'completed': '✅'}

                    status = status_map.get(order[6], order[6])

                    message += f"🆔 #{order[0]} {order_type} {status}\n"

                    message += f"👤 {order[8] or 'Noma`lum'}\n📱 {order[9] or '-'}\n"

                    message += f"📍 {order[3]} {passenger_info}\n"

                    message += f"📅 {order[7]}\n\n"

                

                await update.message.reply_text(message, reply_markup=get_driver_menu())

        else:

            await update.message.reply_text(

                "❌ Siz haydovchi emassiz. Avval ariza topshiring.",

                reply_markup=get_main_menu()

            )

    

    elif text == "📝 Ariza yuborish":

        cursor.execute('SELECT * FROM driver_applications WHERE telegram_id = ?', (telegram_id,))

        existing_application = cursor.fetchone()

        

        if existing_application:

            await update.message.reply_text(

                "Sizning arizangiz allaqachon yuborilgan.\n\n"

                f"Holati: {existing_application[4]}",

                reply_markup=get_driver_menu()

            )

        else:

            cursor.execute('SELECT name, phone FROM users WHERE telegram_id = ?', (telegram_id,))

            user_info = cursor.fetchone()

            

            if user_info:

                cursor.execute('''

                    INSERT INTO driver_applications (telegram_id, name, phone)

                    VALUES (?, ?, ?)

                ''', (telegram_id, user_info[0], user_info[1]))

                conn.commit()

                # Firebase ga ariza saqlash

                app_id = cursor.lastrowid

                firebase_db.save_application(app_id, telegram_id, user_info[0], user_info[1], 'pending')

                

                await update.message.reply_text(

                    "🎉 Sizning arizangiz adminga yuborildi!\n\n"

                    "Tez orada siz bilan bog'lanishadi.",

                    reply_markup=get_driver_menu()

                )

            else:

                await update.message.reply_text(

                    "Avval ro'yxatdan o'tishingiz kerak!",

                    reply_markup=get_main_menu()

                )

    

    elif text == "📊 Mening arizam":

        cursor.execute('SELECT * FROM driver_applications WHERE telegram_id = ?', (telegram_id,))

        application = cursor.fetchone()

        

        if application:

            status_emoji = {

                'pending': '⏳',

                'approved': '✅',

                'rejected': '❌'

            }

            emoji = status_emoji.get(application[4], '❓')

            

            await update.message.reply_text(

                f"📊 Sizning arizangiz:\n\n"

                f"📝 Ariza raqami: #{application[0]}\n"

                f"👤 Ism: {application[2]}\n"

                f"📱 Telefon: {application[3]}\n"

                f"{emoji} Holati: {application[4]}\n"

                f"📅 Yuborilgan: {application[5]}",

                reply_markup=get_driver_menu()

            )

        else:

            await update.message.reply_text(

                "Siz hali ariza yubormagansiz.",

                reply_markup=get_driver_menu()

            )

    

    # Handle admin panel

    elif text == "📊 Statistika":

        if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

            # Statistikani olish

            cursor.execute('SELECT COUNT(*) FROM users')

            total_users = cursor.fetchone()[0]

            

            cursor.execute('SELECT COUNT(*) FROM drivers')

            total_drivers = cursor.fetchone()[0]

            

            cursor.execute('SELECT COUNT(*) FROM orders')

            total_orders = cursor.fetchone()[0]

            

            cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "completed"')

            completed_orders = cursor.fetchone()[0]

            

            cursor.execute('SELECT COUNT(*) FROM driver_applications WHERE status = "pending"')

            pending_applications = cursor.fetchone()[0]

            

            cursor.execute('SELECT COUNT(*) FROM driver_applications WHERE status = "approved"')

            approved_applications = cursor.fetchone()[0]

            

            cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "pending"')

            pending_orders = cursor.fetchone()[0]

            

            cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "assigned"')

            assigned_orders = cursor.fetchone()[0]

            

            stats_message = (

                "📊 TAKSI BOT STATISTIKA\n\n"

                "👥 Foydalanuvchilar:\n"

                f"   • Jami foydalanuvchilar: {total_users}\n"

                f"   • Jami haydovchilar: {total_drivers}\n\n"

                "📦 Buyurtmalar:\n"

                f"   • Jami buyurtmalar: {total_orders}\n"

                f"   • Kutilayotgan: {pending_orders}\n"

                f"   • Biriktirilgan: {assigned_orders}\n"

                f"   • Tugatilgan: {completed_orders}\n\n"

                "📝 Arizalar:\n"

                f"   • Kutilayotgan arizalar: {pending_applications}\n"

                f"   • Tasdiqlangan arizalar: {approved_applications}\n\n"

                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            )

            

            await update.message.reply_text(stats_message, reply_markup=get_admin_menu())

    elif text == "📊 Buyurtmalar":

        if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

            cursor.execute('''

                SELECT o.*, u.name, u.phone FROM orders o 

                LEFT JOIN users u ON o.user_id = u.telegram_id 

                WHERE o.status = 'pending' 

                ORDER BY o.created_at DESC

            ''')

            orders = cursor.fetchall()

            

            if not orders:

                await update.message.reply_text("📊 Kutilayotgan buyurtmalar yo'q.", reply_markup=get_admin_menu())

            else:

                message = "📊 Kutilayotgan buyurtmalar:\n\n"

                for order in orders:

                    message += f"🆔 #{order[0]}\n👤 {order[8]}\n📱 {order[9]}\n📍 {order[3]}\n👥 {order[4] or 0} kishi\n📅 {order[7]}\n\n"

                

                await update.message.reply_text(message, reply_markup=get_admin_menu())

        else:

            await update.message.reply_text("❌ Sizda admin huquqi yo'q.", reply_markup=get_main_menu())

    

    elif text == "🚗 Haydovchilar":

        if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

            await update.message.reply_text(

                "🚗 Haydovchilar boshqaruvi:\n\n",

                reply_markup=get_driver_management_menu()

            )

        else:

            await update.message.reply_text("❌ Sizda admin huquqi yo'q.", reply_markup=get_main_menu())

    

    elif text == "📋 Faol haydovchilar":

        if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

            cursor.execute('SELECT * FROM drivers WHERE status = "active"')

            drivers = cursor.fetchall()

            

            if not drivers:

                await update.message.reply_text("📋 Faol haydovchilar yo'q.", reply_markup=get_driver_management_menu())

            else:

                message = "📋 Faol haydovchilar:\n\n"

                for driver in drivers:

                    message += f"👤 {driver[2]}\n📱 {driver[3]}\n🆔 {driver[1]}\n\n"

                

                await update.message.reply_text(message, reply_markup=get_driver_management_menu())

    

    elif text == "⏸ Band haydovchilar":

        if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

            cursor.execute('SELECT * FROM drivers WHERE status = "busy"')

            drivers = cursor.fetchall()

            

            if not drivers:

                await update.message.reply_text("⏸ Band haydovchilar yo'q.", reply_markup=get_driver_management_menu())

            else:

                message = "⏸ Band haydovchilar:\n\n"

                for driver in drivers:

                    message += f"👤 {driver[2]}\n📱 {driver[3]}\n🆔 {driver[1]}\n\n"

                

                await update.message.reply_text(message, reply_markup=get_driver_management_menu())

    

    elif text == "➕ Yangi haydovchi":

        if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

            await update.message.reply_text(

                "➕ Yangi haydovchi qo'shish:\n\n"

                "Haydovchining Telegram ID raqamini kiriting:",

                reply_markup=get_driver_management_menu()

            )

            context.user_data['awaiting_driver_id'] = True

    

    elif text == "🗑 Haydovchi o'chirish":

        if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

            await update.message.reply_text(

                "🗑 Haydovchi o'chirish:\n\n"

                "Haydovchining Telegram ID raqamini kiriting:",

                reply_markup=get_driver_management_menu()

            )

            context.user_data['awaiting_driver_remove'] = True

        

    elif text == "📋 Arizalar":

        if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

            cursor.execute('SELECT * FROM driver_applications ORDER BY created_at DESC')

            applications = cursor.fetchall()

            

            if not applications:

                await update.message.reply_text("📋 Haydovchi arizalari yo'q.", reply_markup=get_admin_menu())

            else:

                message = "📋 Haydovchi arizalari:\n\n"

                keyboard_buttons = []

                

                for app in applications:

                    status_emoji = {

                        'pending': '⏳',

                        'approved': '✅',

                        'rejected': '❌'

                    }

                    emoji = status_emoji.get(app[4], '❓')

                    message += f"#{app[0]} - {app[2]} ({app[3]}) {emoji} {app[4]}\n"

                    

                    # Add inline buttons for pending applications

                    if app[4] == 'pending':

                        keyboard_buttons.append([

                            InlineKeyboardButton(f"✅ Tasdiqlash #{app[0]}", callback_data=f"approve_app_{app[0]}"),

                            InlineKeyboardButton(f"❌ Rad etish #{app[0]}", callback_data=f"reject_app_{app[0]}")

                        ])

                

                if keyboard_buttons:

                    await update.message.reply_text(

                        message, 

                        reply_markup=InlineKeyboardMarkup(keyboard_buttons)

                    )

                else:

                    await update.message.reply_text(message, reply_markup=get_admin_menu())

    

    elif text == "✅ Arizalarni tasdiqlash":

        if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

            cursor.execute('SELECT * FROM driver_applications WHERE status = "pending"')

            applications = cursor.fetchall()

            

            if not applications:

                await update.message.reply_text("✅ Tasdiqlash uchun arizalar yo'q.", reply_markup=get_driver_management_menu())

            else:

                message = "✅ Tasdiqlash uchun arizalar:\n\n"

                for app in applications:

                    message += f"#{app[0]} - {app[2]} ({app[3]})\n"

                    message += f"📅 {app[5]}\n\n"

                

                message += "Tasdiqlash uchun ariza raqamini kiriting:"

                await update.message.reply_text(message, reply_markup=get_driver_management_menu())

                context.user_data['awaiting_approval'] = True

    

    elif text == "📞 Telefon bilan qo'shish":

        if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

            await update.message.reply_text(

                "📞 Telefon raqami bilan haydovchi qo'shish:\n\n"

                "Haydovchining telefon raqamini kiriting (+998...):",

                reply_markup=get_driver_management_menu()

            )

            context.user_data['awaiting_driver_phone'] = True

    

    # Handle adding new driver

    elif context.user_data.get('awaiting_driver_id'):

        if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

            try:

                driver_telegram_id = int(text.strip())

                

                # Get driver info from users table

                cursor.execute('SELECT name, phone FROM users WHERE telegram_id = ?', (driver_telegram_id,))

                driver_info = cursor.fetchone()

                

                if driver_info:

                    # Add to drivers table

                    cursor.execute('''

                        INSERT OR REPLACE INTO drivers (telegram_id, name, phone)

                        VALUES (?, ?, ?)

                    ''', (driver_telegram_id, driver_info[0], driver_info[1]))

                    conn.commit()

                    

                    # Update application status if exists

                    cursor.execute('''

                        UPDATE driver_applications SET status = 'approved' 

                        WHERE telegram_id = ?

                    ''', (driver_telegram_id,))

                    conn.commit()

                    

                    await update.message.reply_text(

                        f"✅ Haydovchi muvaffaqiyatli qo'shildi!\n\n"

                        f"👤 Ism: {driver_info[0]}\n"

                        f"📱 Telefon: {driver_info[1]}\n"

                        f"🆔 Telegram ID: {driver_telegram_id}",

                        reply_markup=get_driver_management_menu()

                    )

                    context.user_data.clear()

                else:

                    await update.message.reply_text(

                        "❌ Bu Telegram ID foydalanuvchi topilmadi. Iltimos, tekshirib ko'ring.",

                        reply_markup=get_driver_management_menu()

                    )

                    context.user_data.clear()

            except ValueError:

                await update.message.reply_text(

                    "❌ Noto'g'ri ID formati. Iltimos, raqam kiriting.",

                    reply_markup=get_driver_management_menu()

                )

    

    # Handle removing driver

    elif context.user_data.get('awaiting_driver_remove'):

        if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

            try:

                driver_telegram_id = int(text.strip())

                

                # Remove from drivers table

                cursor.execute('DELETE FROM drivers WHERE telegram_id = ?', (driver_telegram_id,))

                conn.commit()

                

                if cursor.rowcount > 0:

                    await update.message.reply_text(

                        f"✅ Haydovchi muvaffaqiyatli o'chirildi!\n\n"

                        f"🆔 Telegram ID: {driver_telegram_id}",

                        reply_markup=get_driver_management_menu()

                    )

                else:

                    await update.message.reply_text(

                        "❌ Haydovchi topilmadi.",

                        reply_markup=get_driver_management_menu()

                    )

                context.user_data.clear()

            except ValueError:

                await update.message.reply_text(

                    "❌ Noto'g'ri ID formati. Iltimos, raqam kiriting.",

                    reply_markup=get_driver_management_menu()

                )

    

    # Handle application approval

    elif context.user_data.get('awaiting_approval'):

        if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

            try:

                application_id = int(text.strip())

                

                # Get application details

                cursor.execute('SELECT * FROM driver_applications WHERE id = ? AND status = "pending"', (application_id,))

                application = cursor.fetchone()

                

                if application:

                    # Update application status

                    cursor.execute('UPDATE driver_applications SET status = "approved" WHERE id = ?', (application_id,))

                    

                    # Add to drivers table

                    cursor.execute('''

                        INSERT OR REPLACE INTO drivers (telegram_id, name, phone, status)

                        VALUES (?, ?, ?, 'active')

                    ''', (application[1], application[2], application[3]))

                    

                    # Update user type

                    cursor.execute('UPDATE users SET user_type = "driver" WHERE telegram_id = ?', (application[1],))

                    

                    # Add to approvals table

                    cursor.execute('''

                        INSERT INTO driver_approvals (application_id, telegram_id, approved_by)

                        VALUES (?, ?, ?)

                    ''', (application_id, application[1], telegram_id))

                    

                    conn.commit()

                    

                    # Notify driver

                    try:

                        await context.bot.send_message(

                            chat_id=application[1],

                            text=f"🎉 Tabriklaymiz! Sizning arizangiz tasdiqlandi!\n\n"

                                  f"Endi siz haydovchi rejimidan foydalanishingiz mumkin.\n"

                                  f"Botdan to'liq foydalaning."

                        )

                    except:

                        pass  # If driver doesn't receive message

                    

                    await update.message.reply_text(

                        f"✅ Ariza #{application_id} muvaffaqiyatli tasdiqlandi!\n\n"

                        f"👤 Haydovchi: {application[2]}\n"

                        f"📱 Telefon: {application[3]}\n"

                        f"🆔 Telegram ID: {application[1]}",

                        reply_markup=get_driver_management_menu()

                    )

                    context.user_data.clear()

                else:

                    await update.message.reply_text(

                        "❌ Ariza topilmadi yoki allaqachon tasdiqlangan.",

                        reply_markup=get_driver_management_menu()

                    )

                    context.user_data.clear()

            except ValueError:

                await update.message.reply_text(

                    "❌ Noto'g'ri raqam formati. Iltimos, ariza raqamini kiriting.",

                    reply_markup=get_driver_management_menu()

                )

    

    # Handle adding driver by phone

    elif context.user_data.get('awaiting_driver_phone'):

        if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

            phone = text.strip()

            

            # Find user by phone

            cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))

            user = cursor.fetchone()

            

            if user:

                # Add to drivers table

                cursor.execute('''

                    INSERT OR REPLACE INTO drivers (telegram_id, name, phone, status)

                    VALUES (?, ?, ?, 'active')

                ''', (user[1], user[2], user[3]))

                

                # Update user type

                cursor.execute('UPDATE users SET user_type = "driver" WHERE telegram_id = ?', (user[1],))

                

                conn.commit()

                

                # Notify driver

                try:

                    await context.bot.send_message(

                        chat_id=user[1],

                        text=f"🎉 Siz haydovchi sifatida qo'shildingiz!\n\n"

                              f"Endi siz haydovchi rejimidan foydalanishingiz mumkin."

                    )

                except:

                    pass

                

                await update.message.reply_text(

                    f"✅ Haydovchi muvaffaqiyatli qo'shildi!\n\n"

                    f"👤 Ism: {user[2]}\n"

                    f"📱 Telefon: {user[3]}\n"

                    f"🆔 Telegram ID: {user[1]}",

                    reply_markup=get_driver_management_menu()

                )

                context.user_data.clear()

            else:

                await update.message.reply_text(

                    "❌ Bu telefon raqami bilan foydalanuvchi topilmadi.",

                    reply_markup=get_driver_management_menu()

                )

                context.user_data.clear()

    

    conn.close()



# Handle location (removed - location sending disabled)

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    # Location sending is disabled as requested

    pass



# Admin command to show admin panel

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    user = update.effective_user

    telegram_id = user.id

    

    if str(telegram_id) == os.getenv('ADMIN_CHAT_ID'):

        conn = sqlite3.connect('taxibot.db')

        cursor = conn.cursor()

        

        # Statistikani olish

        cursor.execute('SELECT COUNT(*) FROM users')

        total_users = cursor.fetchone()[0]

        

        cursor.execute('SELECT COUNT(*) FROM drivers')

        total_drivers = cursor.fetchone()[0]

        

        cursor.execute('SELECT COUNT(*) FROM orders')

        total_orders = cursor.fetchone()[0]

        

        cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "completed"')

        completed_orders = cursor.fetchone()[0]

        

        cursor.execute('SELECT COUNT(*) FROM driver_applications WHERE status = "pending"')

        pending_applications = cursor.fetchone()[0]

        

        cursor.execute('SELECT COUNT(*) FROM driver_applications WHERE status = "approved"')

        approved_applications = cursor.fetchone()[0]

        

        conn.close()

        

        stats_message = (

            "📊 ADMIN PANEL STATISTIKA\n\n"

            f"👥 Jami foydalanuvchilar: {total_users}\n"

            f"🚗 Jami haydovchilar: {total_drivers}\n"

            f"📦 Jami buyurtmalar: {total_orders}\n"

            f"✅ Tugatilgan buyurtmalar: {completed_orders}\n"

            f"⏳ Kutilayotgan arizalar: {pending_applications}\n"

            f"✅ Tasdiqlangan arizalar: {approved_applications}\n\n"

            "👨‍💼 Quyidagi funktsiyalardan foydalanishingiz mumkin:"

        )

        

        await update.message.reply_text(stats_message, reply_markup=get_admin_menu())



# Admin command to view applications (old function kept for compatibility)

async def admin_applications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    conn = sqlite3.connect('taxibot.db')

    cursor = conn.cursor()

    

    cursor.execute('SELECT * FROM driver_applications ORDER BY created_at DESC')

    applications = cursor.fetchall()

    

    if not applications:

        await update.message.reply_text("Hozircha arizalar yo'q.")

    else:

        message = "📊 Haydovchi arizalari:\n\n"

        for app in applications:

            status_emoji = {

                'pending': '⏳',

                'approved': '✅',

                'rejected': '❌'

            }

            emoji = status_emoji.get(app[4], '❓')

            message += f"#{app[0]} - {app[2]} ({app[3]}) {emoji} {app[4]}\n"

        

        await update.message.reply_text(message)

    

    conn.close()



# Handle callback queries for inline buttons

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    query = update.callback_query

    await query.answer()

    

    user = update.effective_user

    telegram_id = user.id

    callback_data = query.data

    

    conn = sqlite3.connect('taxibot.db')

    cursor = conn.cursor()

    

    if callback_data.startswith("take_order_"):

        order_id = callback_data.split("_")[2]

        

        # Check if user is a driver

        cursor.execute('SELECT * FROM drivers WHERE telegram_id = ?', (telegram_id,))

        driver = cursor.fetchone()

        

        if not driver:

            await query.edit_message_text("❌ Siz haydovchi emassiz! Buyurtma olish uchun haydovchi bo'lishingiz kerak.")

            conn.close()

            return

        

        # Check if order is still available

        cursor.execute('SELECT * FROM orders WHERE id = ? AND status = "pending" AND driver_id IS NULL', (order_id,))

        order = cursor.fetchone()

        

        if not order:

            await query.edit_message_text("❌ Bu buyurtma allaqachon olingan!")

            conn.close()

            return

        

        # Assign order to driver

        cursor.execute('UPDATE orders SET driver_id = ?, status = "assigned" WHERE id = ?', (telegram_id, order_id))

        conn.commit()

        

        # Firebase da ham yangilash

        firebase_db.assign_order(order_id, telegram_id)

        

        # Get order details

        cursor.execute('''

            SELECT o.*, u.name, u.phone FROM orders o 

            LEFT JOIN users u ON o.user_id = u.telegram_id 

            WHERE o.id = ?

        ''', (order_id,))

        order_details = cursor.fetchone()

        

        # Get driver username

        driver_username = f"@{user.username}" if user.username else user.first_name

        

        # Send notifications

        notification_message = (

            f"✅ BUYURTMA OLINDI!\n\n"

            f"🆔 Buyurtma raqami: #{order_id}\n"

            f"🚗 Haydovchi: {driver_username}\n"

            f"👤 Mijoz: {order_details[8]}\n"

            f"📱 Telefon: {order_details[9]}\n"

            f"📍 Manzil: {order_details[3]}\n"

            f"📅 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        )

        

        # Send to group

        try:

            group_username = os.getenv('GROUP_USERNAME', '')

            if group_username:

                if group_username.startswith('@'):

                    group_username = group_username[1:]

                

                await context.bot.send_message(

                    chat_id=f"@{group_username}", 

                    text=notification_message

                )

        except:

            pass

        

        # Send to admin

        try:

            await context.bot.send_message(

                chat_id=os.getenv('ADMIN_CHAT_ID', ''), 

                text=notification_message

            )

        except:

            pass

        

        # Send to customer

        try:

            await context.bot.send_message(

                chat_id=order_details[1], 

                text=f"🎉 Sizning buyurtmangiz olindi!\n\n"

                     f"🚗 Haydovchi: {driver_username}\n"

                     f"Tez orada siz bilan bog'lanishadi."

            )

        except:

            pass

        

        # Update the original message

        await query.edit_message_text(

            f"✅ Buyurtma #{order_id} muvaffaqiyatli olindi!\n\n"

            f"🚗 Haydovchi: {driver_username}\n"

            f"👤 Mijoz: {order_details[8]}\n"

            f"📍 Manzil: {order_details[3]}"

        )

        

        # Send completion notification to driver with inline keyboard

        completion_keyboard = InlineKeyboardMarkup([

            [InlineKeyboardButton("✅ Buyurtma tugatildi", callback_data=f"complete_order_{order_id}")]

        ])

        

        try:

            await context.bot.send_message(

                chat_id=telegram_id,

                text=f"🎉 Buyurtma #{order_id} muvaffaqiyatli olindi!\n\n"

                     f"👤 Mijoz: {order_details[8]}\n"

                     f"📱 Telefon: {order_details[9]}\n"

                     f"📍 Manzil: {order_details[3]}\n"

                     f"📅 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

                     "Buyurtma tugatilganda quyidagi tugmani bosing:",

                reply_markup=completion_keyboard

            )

        except:

            pass

    

    elif callback_data.startswith("order_details_"):

        order_id = callback_data.split("_")[2]

        

        # Get order details

        cursor.execute('''

            SELECT o.*, u.name, u.phone FROM orders o 

            LEFT JOIN users u ON o.user_id = u.telegram_id 

            WHERE o.id = ?

        ''', (order_id,))

        order = cursor.fetchone()

        

        if order:

            order_type = "🚖 Taksi" if order[2] == 'taxi' else "📦 Pochta"

            passenger_info = f"👥 {order[4] or 0} kishi" if order[2] == 'taxi' else ""

            

            details_message = (

                f"📋 BUYURTMA DETALLARI\n\n"

                f"🆔 Buyurtma raqami: #{order[0]}\n"

                f"{order_type}\n"

                f"👤 Mijoz: {order[8]}\n"

                f"📱 Telefon: {order[9]}\n"

                f"📍 Manzil: {order[3]}\n"

                f"{passenger_info}\n"

                f"📅 Vaqt: {order[7]}\n"

                f"🔄 Holati: {order[6] or 'pending'}"

            )

            

            await query.edit_message_text(details_message)

        else:

            await query.edit_message_text("❌ Buyurtma topilmadi!")

    

    elif callback_data.startswith("approve_app_"):

        application_id = callback_data.split("_")[2]

        

        # Check if user is admin

        if str(telegram_id) != os.getenv('ADMIN_CHAT_ID'):

            await query.edit_message_text("❌ Sizda admin huquqi yo'q!")

            conn.close()

            return

        

        # Get application details

        cursor.execute('SELECT * FROM driver_applications WHERE id = ? AND status = "pending"', (application_id,))

        application = cursor.fetchone()

        

        if application:

            # Update application status

            cursor.execute('UPDATE driver_applications SET status = "approved" WHERE id = ?', (application_id,))

            

            # Add to drivers table

            cursor.execute('''

                INSERT OR REPLACE INTO drivers (telegram_id, name, phone, status)

                VALUES (?, ?, ?, 'active')

            ''', (application[1], application[2], application[3]))

            

            # Update user type

            cursor.execute('UPDATE users SET user_type = "driver" WHERE telegram_id = ?', (application[1],))

            

            # Add to approvals table

            cursor.execute('''

                INSERT INTO driver_approvals (application_id, telegram_id, approved_by)

                VALUES (?, ?, ?)

            ''', (application_id, application[1], telegram_id))

            

            conn.commit()

            

            # Firebase da ham yangilash

            firebase_db.update_application_status(application_id, 'approved')

            firebase_db.save_driver(application[1], application[2], application[3], 'active')

            firebase_db.save_user(application[1], application[2], application[3], 'driver')

            

            # Notify driver

            try:

                await context.bot.send_message(

                    chat_id=application[1],

                    text=f"🎉 Tabriklaymiz! Sizning arizangiz tasdiqlandi!\n\n"

                          f"Endi siz haydovchi rejimidan foydalanishingiz mumkin.\n"

                          f"Botdan to'liq foydalaning.\n\n"

                          f"Agar sizda savol yoki muammo bo'lsa, iltimos, biz bilan bog'laning."

                )

            except:

                pass

            

            # Update the message

            await query.edit_message_text(

                f"✅ Ariza #{application_id} muvaffaqiyatli tasdiqlandi!\n\n"

                f"👤 Haydovchi: {application[2]}\n"

                f"📱 Telefon: {application[3]}\n"

                f"🆔 Telegram ID: {application[1]}\n"

                f"📝 Izoh: {application[4]}"

            )

        else:

            await query.edit_message_text("❌ Ariza topilmadi yoki allaqachon tasdiqlangan!")

    

    elif callback_data.startswith("reject_app_"):

        application_id = callback_data.split("_")[2]

        

        # Check if user is admin

        if str(telegram_id) != os.getenv('ADMIN_CHAT_ID'):

            await query.edit_message_text("❌ Sizda admin huquqi yo'q!")

            conn.close()

            return

        

        # Get application details

        cursor.execute('SELECT * FROM driver_applications WHERE id = ? AND status = "pending"', (application_id,))

        application = cursor.fetchone()

        

        if application:

            # Update application status

            cursor.execute('UPDATE driver_applications SET status = "rejected" WHERE id = ?', (application_id,))

            conn.commit()

            

            # Firebase da ham rad etilgan deb belgilash

            firebase_db.update_application_status(application_id, 'rejected')

            

            # Notify driver

            try:

                await context.bot.send_message(

                    chat_id=application[1],

                    text=f"❌ Sizning arizangiz rad etildi.\n\n"

                          f"Qayta ariza topshirishingiz mumkin."

                )

            except:

                pass

            # Update the message

            await query.edit_message_text(

                f"❌ Ariza #{application_id} rad etildi!\n\n"

                f"👤 Arizachi: {application[2]}\n"

                f"📱 Telefon: {application[3]}"

            )

        else:

            await query.edit_message_text("❌ Ariza topilmadi yoki allaqachon ko'rib chiqilgan!")

    

    elif callback_data.startswith("complete_order_"):

        order_id = callback_data.split("_")[2]

        

        # Check if user is driver

        cursor.execute('SELECT * FROM drivers WHERE telegram_id = ?', (telegram_id,))

        driver = cursor.fetchone()

        

        if not driver:

            await query.edit_message_text("❌ Siz haydovchi emassiz!")

            conn.close()

            return

            

        # Check if order belongs to this driver

        cursor.execute('SELECT * FROM orders WHERE id = ? AND driver_id = ?', (order_id, telegram_id))

        order = cursor.fetchone()

        

        if not order:

            await query.edit_message_text("❌ Bu buyurtma sizga tegishli emas!")

            conn.close()

            return

            

        # Update order status to completed

        cursor.execute('UPDATE orders SET status = "completed" WHERE id = ?', (order_id,))

        conn.commit()

        # Firebase da ham tugatilgan deb belgilash

        firebase_db.complete_order(order_id)

        

        # Get order details for notification

        cursor.execute('''

            SELECT o.*, u.name, u.phone FROM orders o 

            LEFT JOIN users u ON o.user_id = u.telegram_id 

            WHERE o.id = ?

        ''', (order_id,))

        order_details = cursor.fetchone()

        

        # Get driver username

        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))

        driver_user = cursor.fetchone()

        driver_username = f"@{driver_user[1]}" if driver_user and driver_user[1] else (driver_user[2] if driver_user else "Haydovchi")



        # Send completion notification

        completion_message = (

            f"✅ BUYURTMA TUGATILDI!\n\n"

            f"🆔 Buyurtma raqami: #{order_id}\n"

            f"🚗 Haydovchi: {driver_username}\n"

            f"👤 Mijoz: {order_details[8]}\n"

            f"📱 Telefon: {order_details[9]}\n"

            f"📍 Manzil: {order_details[3]}\n"

            f"📅 Tugatilgan vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        )

        

        # Send to group

        try:

            group_username = os.getenv('GROUP_USERNAME', '')

            if group_username:

                if group_username.startswith('@'):

                    group_username = group_username[1:]

                

                await context.bot.send_message(

                    chat_id=f"@{group_username}", 

                    text=completion_message

                )

        except:

            pass

        

        # Send to admin

        try:

            await context.bot.send_message(

                chat_id=os.getenv('ADMIN_CHAT_ID', ''), 

                text=completion_message

            )

        except:

            pass

        

        # Send to customer

        try:

            await context.bot.send_message(

                chat_id=order_details[1], 

                text=f"🎉 Sizning buyurtmangiz tugatildi!\n\n"

                     f"🚗 Haydovchi: {driver_username}\n"

                     f"Rahmat bizni tanlaganingiz uchun!"

            )

        except:

            pass

            

        # Update the message

        await query.edit_message_text(

            f"✅ Buyurtma #{order_id} tugatildi!\n\n"

            f"🚗 Haydovchi: {driver_username}\n"

            f"👤 Mijoz: {order_details[8]}\n"

            f"📍 Manzil: {order_details[3]}"

        )

    

    conn.close()



def main() -> None:

    # Initialize database

    init_db()

    

    # Create the Application

    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()

    

    # Add handlers

    application.add_handler(CommandHandler("start", start))

    application.add_handler(CommandHandler("admin", admin_applications))

    application.add_handler(CommandHandler("panel", admin_panel))

    application.add_handler(MessageHandler(filters.CONTACT, handle_message))

    application.add_handler(MessageHandler(filters.LOCATION, handle_location))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.add_handler(CallbackQueryHandler(handle_callback_query))

    

    # Run the bot

    application.run_polling()



if __name__ == "__main__":

    main()