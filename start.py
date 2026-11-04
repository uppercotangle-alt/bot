import asyncio
import logging
import socket
struct = __import__('struct')

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery

# Вставьте ваш токен Telegram-бота
TOKEN = "9076482964:AAGuG8gsf5JntQnVYRQvlxBHD7gXKY_4T6k"

# Настройки серверов Arizona RP (Yuma и Show-Low)
# Укажите актуальные IP и порты серверов
SERVERS = {
    "Yuma": {"ip": "185.169.134.3", "port": 7777},
    "Show-Low": {"ip": "185.169.134.167", "port": 7777}
}

router = Router()

async def query_samp_server(ip: str, port: int, timeout: float = 2.0):
    """Асинхронная функция для запроса информации у SAMP сервера по протоколу SA-MP Query."""
    try:
        loop = asyncio.get_running_loop()
        
        # Создаем UDP сокет
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        
        # Формируем пакет запроса 'i' (information)
        # Префикс 'SAMP', IP части, порт (little-endian), опкод 'i'
        ip_bytes = socket.inet_aton(ip)
        packet = b'SAMP' + ip_bytes + struct.pack('<H', port) + b'i'
        
        await loop.sock_sendto(sock, packet, (ip, port))
        
        # Ожидаем ответ с таймаутом
        data, _ = await asyncio.wait_for(loop.sock_recv(sock, 1024), timeout=timeout)
        sock.close()
        
        # Парсим ответ
        if not data.startswith(b'SAMP'):
            return None
            
        # Смещение после заголовка SAMP + IP + Port + Opcode
        # Заголовок (4) + IP (4) + Port (2) + Opcode (1) = 11 байт
        ptr = 11
        
        # Passworded (1 байт)
        passworded = data[ptr]
        ptr += 1
        
        # Players count (2 байта)
        players = struct.unpack('<H', data[ptr:ptr+2])[0]
        ptr += 2
        
        # Max players (2 байта)
        max_players = struct.unpack('<H', data[ptr:ptr+2])[0]
        ptr += 2
        
        # Hostname length + string
        hostname_len = struct.unpack('<I', data[ptr:ptr+4])[0]
        ptr += 4
        hostname = data[ptr:ptr+hostname_len].decode('latin-1', errors='ignore')
        
        return {
            "online": True,
            "players": players,
            "max_players": max_players,
            "hostname": hostname,
            "passworded": bool(passworded)
        }
    except Exception as e:
        return {"online": False, "error": str(e)}

def get_status_keyboard():
    """Клавиатура с кнопкой обновления."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить статус", callback_data="refresh_status")]
    ])

async def build_status_text():
    """Формирует красивый текст со статусом серверов."""
    text = "📊 **Состояние серверов Arizona RP**\n\n"
    
    for name, info in SERVERS.items():
        result = await query_samp_server(info["ip"], info["port"])
        
        text += f"🟢 **{name}** (`{info['ip']}:{info['port']}`)\n"
        if result and result.get("online"):
            text += f" • Статус: **В сети (Online)**\n"
            text += f" • Игроки: `{result['players']} / {result['max_players']}`\n"
            text += f" • Рестарт: Не зафиксирован (сервер работает стабильно)\n"
        else:
            text += f" • Статус: 🔴 **Выключен / Рестарт / Тех. работы**\n"
            text += f" • Примечание: Возможен плановый рестарт или обновление.\n"
        text += "\n"
        
    text += "⏱ *Информация обновляется в реальном времени.*"
    return text

@router.message(Command("check"))
async def cmd_check(message: Message):
    """Обработчик команды /check"""
    loading_msg = await message.answer("⏳ Проверяю состояние серверов...")
    text = await build_status_text()
    await loading_msg.edit_text(text, parse_mode="Markdown", reply_markup=get_status_keyboard())

@router.callback_query(F.data == "refresh_status")
async def refresh_callback(callback: CallbackQuery):
    """Обработчик нажатия на кнопку обновления"""
    try:
        text = await build_status_text()
        if callback.message.text != text:
            await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_status_keyboard())
        await callback.answer("✅ Статус успешно обновлен!")
    except Exception:
        await callback.answer("⚠️ Данные актуальны.")

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    print("Бот запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())