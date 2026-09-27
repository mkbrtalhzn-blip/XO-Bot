import sqlite3
import random

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "YOUR_BOT_TOKEN"

db = sqlite3.connect("xo_bot.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0
)
""")
db.commit()


def add_user(user):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)",
        (user.id, user.first_name or "User")
    )
    cursor.execute(
        "UPDATE users SET name = ? WHERE user_id = ?",
        (user.first_name or "User", user.id)
    )
    db.commit()


menu_keyboard = ReplyKeyboardMarkup(
    [["☰ القائمة"]],
    resize_keyboard=True
)


def inline_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 لعب XO", callback_data="play")],
        [
            InlineKeyboardButton("👤 حسابي", callback_data="profile"),
            InlineKeyboardButton("🏆 الترتيب", callback_data="ranking")
        ],
        [InlineKeyboardButton("ℹ️ المساعدة", callback_data="help")]
    ])


def xo_keyboard(board):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(board[0], callback_data="cell_0"),
            InlineKeyboardButton(board[1], callback_data="cell_1"),
            InlineKeyboardButton(board[2], callback_data="cell_2"),
        ],
        [
            InlineKeyboardButton(board[3], callback_data="cell_3"),
            InlineKeyboardButton(board[4], callback_data="cell_4"),
            InlineKeyboardButton(board[5], callback_data="cell_5"),
        ],
        [
            InlineKeyboardButton(board[6], callback_data="cell_6"),
            InlineKeyboardButton(board[7], callback_data="cell_7"),
            InlineKeyboardButton(board[8], callback_data="cell_8"),
        ],
        [InlineKeyboardButton("🔙 القائمة", callback_data="home")]
    ])


def check_winner(board):
    wins = [
        (0,1,2), (3,4,5), (6,7,8),
        (0,3,6), (1,4,7), (2,5,8),
        (0,4,8), (2,4,6)
    ]

    for a, b, c in wins:
        if board[a] != "⬜" and board[a] == board[b] == board[c]:
            return board[a]

    if "⬜" not in board:
        return "draw"

    return None


def bot_move(board):
    empty = [i for i, x in enumerate(board) if x == "⬜"]

    if not empty:
        return None

    # البوت يحاول يفوز
    for i in empty:
        test = board.copy()
        test[i] = "⭕"
        if check_winner(test) == "⭕":
            return i

    # البوت يمنع اللاعب من الفوز
    for i in empty:
        test = board.copy()
        test[i] = "❌"
        if check_winner(test) == "❌":
            return i

    # الوسط
    if board[4] == "⬜":
        return 4

    # الزوايا
    corners = [i for i in [0,2,6,8] if board[i] == "⬜"]

    if corners:
        return random.choice(corners)

    return random.choice(empty)


games = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user)

    await update.message.reply_text(
        "╔════════════════════╗\n"
        "        ♟️ XO BOT\n"
        "╚════════════════════╝\n\n"
        "هلا بيك 👋\n\n"
        "اضغط زر القائمة حتى تشوف الخيارات.",
        reply_markup=menu_keyboard
    )


async def menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "☰ القائمة":
        return

    await update.message.reply_text(
        "╔════════════════════╗\n"
        "          ☰ القائمة\n"
        "╚════════════════════╝\n\n"
        "اختار من الخيارات 👇",
        reply_markup=inline_menu()
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    add_user(user)

    if query.data == "home":
        await query.edit_message_text(
            "╔════════════════════╗\n"
            "          ☰ القائمة\n"
            "╚════════════════════╝\n\n"
            "اختار من الخيارات 👇",
            reply_markup=inline_menu()
        )
        return

    if query.data == "play":
        board = ["⬜"] * 9
        games[user.id] = {"board": board}

        await query.edit_message_text(
            "🎮 XO GAME\n\n"
            "❌ أنت\n"
            "⭕ البوت\n\n"
            "اختار مكانك 👇",
            reply_markup=xo_keyboard(board)
        )
        return

    if query.data == "profile":
        cursor.execute(
            "SELECT wins, losses, draws FROM users WHERE user_id = ?",
            (user.id,)
        )

        wins, losses, draws = cursor.fetchone()

        await query.edit_message_text(
            "╔════════════════════╗\n"
            "          👤 حسابي\n"
            "╚════════════════════╝\n\n"
            f"👤 الاسم: {user.first_name}\n\n"
            f"🏆 الفوز: {wins}\n"
            f"💀 الخسارة: {losses}\n"
            f"🤝 التعادل: {draws}\n",
            reply_markup=inline_menu()
        )
        return

    if query.data == "ranking":
        cursor.execute("""
            SELECT name, wins
            FROM users
            ORDER BY wins DESC
            LIMIT 10
        """)

        rows = cursor.fetchall()

        text = (
            "╔════════════════════╗\n"
            "          🏆 الترتيب\n"
            "╚════════════════════╝\n\n"
        )

        if not rows:
            text += "لا يوجد لاعبين بعد."

        else:
            medals = ["🥇", "🥈", "🥉"]

            for i, (name, wins) in enumerate(rows, start=1):
                medal = medals[i-1] if i <= 3 else f"{i}."
                text += f"{medal} {name} — {wins} فوز\n"

        await query.edit_message_text(
            text,
            reply_markup=inline_menu()
        )
        return

    if query.data == "help":
        await query.edit_message_text(
            "╔════════════════════╗\n"
            "          ℹ️ المساعدة\n"
            "╚════════════════════╝\n\n"
            "🎮 لعب XO\n"
            "❌ أنت تلعب X\n"
            "⭕ البوت يلعب O\n\n"
            "🏆 الفوز يضيف نقطة.\n"
            "🤝 التعادل يُحسب.\n"
            "💀 الخسارة تُحسب عليك.",
            reply_markup=inline_menu()
        )
        return

    if query.data.startswith("cell_"):

        if user.id not in games:
            await query.answer(
                "ابدأ لعبة جديدة أولاً 🎮",
                show_alert=True
            )
            return

        board = games[user.id]["board"]
        index = int(query.data.split("_")[1])

        if board[index] != "⬜":
            await query.answer(
                "هذا المكان مأخوذ ❌",
                show_alert=True
            )
            return

        board[index] = "❌"

        result = check_winner(board)

        if result:
            await finish_game(query, user.id, result)
            return

        move = bot_move(board)

        if move is not None:
            board[move] = "⭕"

        result = check_winner(board)

        if result:
            await finish_game(query, user.id, result)
            return

        await query.edit_message_text(
            "🎮 دورك\n\n"
            "❌ أنت\n"
            "⭕ البوت",
            reply_markup=xo_keyboard(board)
        )


async def finish_game(query, user_id, result):
    board = games[user_id]["board"]

    if result == "❌":
        cursor.execute(
            "UPDATE users SET wins = wins + 1 WHERE user_id = ?",
            (user_id,)
        )
        title = "🏆 فزت!"

    elif result == "⭕":
        cursor.execute(
            "UPDATE users SET losses = losses + 1 WHERE user_id = ?",
            (user_id,)
        )
        title = "💀 خسرت!"

    else:
        cursor.execute(
            "UPDATE users SET draws = draws + 1 WHERE user_id = ?",
            (user_id,)
        )
        title = "🤝 تعادل!"

    db.commit()
    del games[user_id]

    await query.edit_message_text(
        f"╔════════════════════╗\n"
        f"          {title}\n"
        f"╚════════════════════╝\n\n"
        f"{board[0]} {board[1]} {board[2]}\n"
        f"{board[3]} {board[4]} {board[5]}\n"
        f"{board[6]} {board[7]} {board[8]}\n\n"
        "تريد تلعب مرة ثانية؟",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 جولة جديدة", callback_data="play")],
            [InlineKeyboardButton("☰ القائمة", callback_data="home")]
        ])
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            menu_message
        )
    )

    app.add_handler(
        CallbackQueryHandler(buttons)
    )

    print("✅ XO BOT شغال")

    app.run_polling()


if __name__ == "__main__":
    main()
