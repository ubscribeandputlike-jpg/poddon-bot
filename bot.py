import telebot
from telebot import types
from config import BOT_TOKEN
import db
from utils import read_barcode

bot = telebot.TeleBot(BOT_TOKEN)
db.init_db()

user_state = {}

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row('📷 Сканировать', '🔍 Где лежит?')
    kb.row('🧱 Поддоны', '⚙️ Настройки')
    return kb

def settings_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row('👷 Смена', '📦 Поддон')
    kb.row('⬅️ Назад')
    return kb

def shift_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row('Смена 1', 'Смена 2')
    kb.row('⬅️ К настройкам')
    return kb

def back_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row('⬅️ Назад')
    return kb

def scan_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row('✍️ Ввести вручную')
    kb.row('⬅️ В главное меню')
    return kb

def find_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row('✍️ Ввести вручную поиск')
    kb.row('⬅️ В главное меню')
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    u = db.get_user(m.from_user.id)
    bot.send_message(m.chat.id,
        "Добро пожаловать в бота *Поддон*\n\nОдна общая база для всех, у кого есть ссылка на бота.\n\nСначала настрой смену и поддон: ⚙️ Настройки",
        reply_markup=main_menu(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '⚙️ Настройки')
def settings(m):
    u = db.get_user(m.from_user.id)
    bot.send_message(m.chat.id,
        f"Текущие настройки:\n👷 Смена: {u['shift'] or 'не выбрана'}\n📦 Поддон: {u['pallet'] or 'не выбран'}\n\nВыбери, что хочешь изменить:",
        reply_markup=settings_menu())

@bot.message_handler(func=lambda m: m.text == '⬅️ Назад')
def back(m):
    bot.send_message(m.chat.id, "Главное меню", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == '⬅️ К настройкам')
def back_s(m):
    settings(m)

@bot.message_handler(func=lambda m: m.text == '⬅️ В главное меню')
def back_m(m):
    user_state.pop(m.from_user.id, None)
    bot.send_message(m.chat.id, "Главное меню", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == '👷 Смена')
def set_shift(m):
    user_state[m.from_user.id] = {'action':'shift'}
    bot.send_message(m.chat.id, "Выбери смену:", reply_markup=shift_kb())

@bot.message_handler(func=lambda m: m.text in ['Смена 1','Смена 2'])
def shift_done(m):
    if user_state.get(m.from_user.id,{}).get('action') == 'shift':
        db.update_user(m.from_user.id, shift=m.text)
        user_state.pop(m.from_user.id,None)
        bot.send_message(m.chat.id, f"Смена сохранена: {m.text}", reply_markup=main_menu())
        return
    bot.send_message(m.chat.id, "Главное меню", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == '📦 Поддон')
def set_pallet(m):
    user_state[m.from_user.id] = {'action':'pallet'}
    bot.send_message(m.chat.id, "Напиши название поддона.\nНапример: Поддон А-12", reply_markup=back_kb())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id,{}).get('action') == 'pallet' and m.text and m.text not in ['⬅️ Назад','⬅️ К настройкам','⬅️ В главное меню'])
def pallet_done(m):
    name = m.text.strip()
    if len(name) < 2:
        bot.send_message(m.chat.id, "Слишком короткое название")
        return
    db.update_user(m.from_user.id, pallet=name)
    user_state.pop(m.from_user.id,None)
    bot.send_message(m.chat.id, f"Поддон сохранён: {name}", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == '📷 Сканировать')
def scan(m):
    u = db.get_user(m.from_user.id)
    if not u['shift'] or not u['pallet']:
        bot.send_message(m.chat.id, "Сначала выбери смену и поддон в ⚙️ Настройки", reply_markup=main_menu())
        return
    user_state.pop(m.from_user.id,None)
    bot.send_message(m.chat.id,
        f"Режим сканирования\n\nСмена: {u['shift']}\nПоддон: {u['pallet']}\n\nПришли фото штрихкода или нажми «✍️ Ввести вручную»",
        reply_markup=scan_kb())

@bot.message_handler(content_types=['photo'])
def photo(m):
    u = db.get_user(m.from_user.id)
    if not u['shift'] or not u['pallet']:
        bot.send_message(m.chat.id, "Сначала выбери смену и поддон в ⚙️ Настройки", reply_markup=main_menu())
        return
    try:
        file_info = bot.get_file(m.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        codes = read_barcode(downloaded)
        if not codes:
            bot.send_message(m.chat.id, "Не удалось распознать штрихкод.\nПопробуй чётче или ввести вручную", reply_markup=scan_kb())
            return
        for c in codes:
            db.add_scan(c, u['pallet'], u['shift'], m.from_user.id, m.from_user.username or '', m.from_user.full_name or '')
        if len(codes)==1:
            bot.send_message(m.chat.id, f"✅ Записано\n\nШтрихкод: {codes[0]}\nПоддон: {u['pallet']}\nСмена: {u['shift']}", reply_markup=scan_kb())
        else:
            txt = "✅ Записано:\n\n"
            for c in codes: txt += f"• {c}\n"
            txt += f"\nПоддон: {u['pallet']}\nСмена: {u['shift']}"
            bot.send_message(m.chat.id, txt, reply_markup=scan_kb())
    except Exception as e:
        bot.send_message(m.chat.id, "Ошибка при обработке фото", reply_markup=scan_kb())

@bot.message_handler(func=lambda m: m.text == '✍️ Ввести вручную')
def manual(m):
    u = db.get_user(m.from_user.id)
    if not u['shift'] or not u['pallet']:
        bot.send_message(m.chat.id, "Сначала выбери смену и поддон в ⚙️ Настройки", reply_markup=main_menu())
        return
    user_state[m.from_user.id] = {'action':'manual'}
    bot.send_message(m.chat.id, "Введи штрихкод цифрами:", reply_markup=back_kb())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id,{}).get('action') == 'manual' and m.text and m.text not in ['⬅️ Назад','⬅️ В главное меню'])
def manual_done(m):
    u = db.get_user(m.from_user.id)
    code = m.text.strip().replace(' ','')
    if not code.isdigit():
        bot.send_message(m.chat.id, "Только цифры", reply_markup=back_kb())
        return
    db.add_scan(code, u['pallet'], u['shift'], m.from_user.id, m.from_user.username or '', m.from_user.full_name or '')
    user_state.pop(m.from_user.id,None)
    bot.send_message(m.chat.id, f"✅ Записано\n\nШтрихкод: {code}\nПоддон: {u['pallet']}\nСмена: {u['shift']}", reply_markup=scan_kb())

@bot.message_handler(func=lambda m: m.text == '🔍 Где лежит?')
def find(m):
    user_state.pop(m.from_user.id,None)
    bot.send_message(m.chat.id, "Найти, где лежит товар.\n\nПришли фото или нажми «✍️ Ввести вручную поиск»", reply_markup=find_kb())

@bot.message_handler(content_types=['photo'])
def find_photo(m):
    # if in find context - handle
    try:
        file_info = bot.get_file(m.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        codes = read_barcode(downloaded)
        if not codes:
            bot.send_message(m.chat.id, "Не удалось распознать. Введи вручную", reply_markup=find_kb())
            return
        show_find(m, codes[0])
    except:
        bot.send_message(m.chat.id, "Ошибка", reply_markup=find_kb())

def show_find(m, code):
    rows = db.find_by_barcode(code)
    if not rows:
        bot.send_message(m.chat.id, f"NНичего не найдено: {code}", reply_markup=find_kb())
        return
    top = rows[0]
    txt = f"🔍 Штрихкод: {code}\n\n📦 Поддон: {top['pallet']}\n👷 Смена: {top['shift'] or '—'}\n🕒 Добавлен: {top['added_at']}\n👤 Кем: {top['full_name'] or top['username'] or '—'}\n"
    if len(rows)>1:
        txt += f"\nЕщё записей: {len(rows)-1}"
    bot.send_message(m.chat.id, txt, reply_markup=find_kb())

@bot.message_handler(func=lambda m: m.text == '✍️ Ввести вручную поиск')
def find_manual(m):
    user_state[m.from_user.id] = {'action':'findm'}
    bot.send_message(m.chat.id, "Введи штрихкод для поиска:", reply_markup=back_kb())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id,{}).get('action') == 'findm' and m.text and m.text not in ['⬅️ Назад','⬅️ В главное меню'])
def find_manual_done(m):
    code = m.text.strip().replace(' ','')
    if not code.isdigit():
        bot.send_message(m.chat.id, "Только цифры", reply_markup=back_kb())
        return
    user_state.pop(m.from_user.id,None)
    show_find(m, code)

@bot.message_handler(func=lambda m: m.text == '🧱 Поддоны')
def pallets(m):
    ps = db.get_pallets()
    if not ps:
        bot.send_message(m.chat.id, "Пока нет ни одного поддона.\nСначала отсканируй что-нибудь.", reply_markup=main_menu())
        return
    txt = "🧱 Поддоны:\n\n"
    for p in ps:
        txt += f"• {p['pallet']} — {p['count']} шт. (посл.: {p['last_added']})\n"
    txt += "\nНапиши название поддона из списка, чтобы посмотреть содержимое."
    bot.send_message(m.chat.id, txt, reply_markup=back_kb())

@bot.message_handler(func=lambda m: m.text and m.text not in ['📷 Сканировать','🔍 Где лежит?','🧱 Поддоны','⚙️ Настройки','⬅️ Назад','⬅️ К настройкам','⬅️ В главное меню','👷 Смена','📦 Поддон','Смена 1','Смена 2','✍️ V Ввести вручную','✍️ Ввести вручную','✍️ V Ввести вручную поиск','✍️ Ввести вручную поиск'])
def pallet_view(m):
    ps = db.get_pallets()
    names = [p['pallet'] for p in ps]
    if m.text in names:
        items = db.get_pallet_items(m.text)
        txt = f"📦 {m.text}\nВсего: {len(items)} шт.\n\n"
        for i,it in enumerate(items[:40],1):
            txt += f"{i}. {it['barcode']} | {it['added_at']} | {it['full_name'] or it['username'] or ''}\n"
        if len(items)>40: txt += f"\n...и ещё {len(items)-40}"
        bot.send_message(m.chat.id, txt, reply_markup=main_menu())
        return

if __name__ == '__main__':
    print("Бот запущен. Нажми Ctrl+C для остановки")
    bot.polling(none_stop=True)
