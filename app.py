import asyncio
import html
import os
import random
import threading
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import requests
 
try:
  from dotenv import load_dotenv
 
  load_dotenv()
except ImportError:
  pass
 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
 

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEB_APP_URL = os.getenv("WEB_APP_URL", "")
TRAVELPAYOUTS_TOKEN = os.getenv("TRAVELPAYOUTS_TOKEN", "")
 
app = Flask(__name__)
CORS(app)
 
CITY_IATA = {
    "алматы": "ALA",
    "almaty": "ALA",
    "астана": "NQZ",
    "astana": "NQZ",
    "шымкент": "CIT",
    "shymkent": "CIT",
    "москва": "MOW",
    "moscow": "MOW",
    "дубай": "DXB",
    "dubai": "DXB",
    "стамбул": "IST",
    "istanbul": "IST",
    "пекин": "BJS",
    "ташкент": "TAS",
    "париж": "PAR",
}
 
AIRLINES_MAP = {
    "KC": "Air Astana",
    "IQ": "Qazaq Air",
    "DV": "SCAT Airlines",
    "SU": "Aeroflot",
    "TK": "Turkish Airlines",
    "EK": "Emirates",
    "FZ": "flydubai",
    "FS": "FlyArystan",
}
 
 
def get_iata(city_name):
  return CITY_IATA.get(city_name.strip().lower(), "ALA")
 
 
@app.route("/")
def index():
  return send_file(os.path.join(BASE_DIR, "index.html"))
 
 
@app.route("/api/search", methods=["POST"])
def search_flights():
  data = request.json or {}
  origin = data.get("origin", "Алматы").strip().capitalize()
  destination = data.get("destination", "Москва").strip().capitalize()
  depart_date = data.get("depart_date", "")  # YYYY-MM-DD
  return_date = data.get("return_date", "")  # YYYY-MM-DD
 
  origin_iata = get_iata(origin)
  dest_iata = get_iata(destination)
 
  flights = []
 
  if TRAVELPAYOUTS_TOKEN:
    try:
      headers = {"X-Access-Token": TRAVELPAYOUTS_TOKEN}
      one_way = "false" if return_date else "true"
      url = f"https://api.travelpayouts.com/v2/prices/latest?currency=kzt&origin={origin_iata}&destination={dest_iata}&one_way={one_way}&limit=10"
 
      res = requests.get(url, headers=headers, timeout=5).json()
      print("ответ от api:", res)
 
      if res.get("success") and res.get("data"):
        for item in res["data"]:
          raw_price = int(item.get("value", 45000))
          if return_date:
            raw_price = int(raw_price * 1.8)
 
          airline_code = (item.get("gate") or "KC")[:2].upper()
          airline_name = AIRLINES_MAP.get(airline_code, "Air Astana")
          number_transfers = item.get("number_of_changes", 0)
 
          stops_str = (
              "Без пересадок"
              if number_transfers == 0
              else f"{number_transfers} пересадка"
          )
 
          duration_val = 195 if number_transfers == 0 else 340
          duration_str = f"{duration_val // 60}ч {duration_val % 60}мин"
 
          dep_hour = random.choice(["07:15", "11:40", "15:35", "19:20", "22:05"])
 
          
          actual_depart = (
              depart_date if depart_date else item.get("depart_date", "2026-10-20")
          )
          actual_return = return_date if return_date else None
 
          flights.append({
              "airline": airline_name,
              "logo": "✈️",
              "code": f"{airline_code} {random.randint(100, 999)}",
              "origin": origin,
              "destination": destination,
              "origin_code": origin_iata,
              "dest_code": dest_iata,
              "departure": dep_hour,
              "arrival": "20:10",
              "duration": duration_str,
              "duration_minutes": duration_val,
              "stops": stops_str,
              "price": f"{raw_price:,}".replace(",", " "),
              "currency": "₸",
              "raw_price": raw_price,
              "is_live": True,
              "depart_date": actual_depart,
              "return_date": actual_return,
          })
    except Exception as e:
      print("Ошибка при обращении к Travelpayouts API:", e)
 
  
  if not flights:
    times_pairs = [
        ("07:15", "10:30", "3ч 15мин", 195, "Без пересадок"),
        ("11:40", "16:25", "4ч 45мин", 285, "Без пересадок"),
        ("16:20", "22:10", "5ч 50мин", 350, "1 пересадка"),
        ("21:05", "02:20", "5ч 15мин", 315, "Без пересадок"),
    ]
 
    fallback_airlines = [
        {"name": "Air Astana", "logo": "✈️", "code": "KC 853", "base": 45000},
        {"name": "FlyArystan", "logo": "⚡", "code": "FS 705", "base": 28000},
        {"name": "SCAT Airlines", "logo": "🦅", "code": "DV 473", "base": 32000},
        {"name": "Aeroflot", "logo": "🇷🇺", "code": "SU 1947", "base": 120000},
    ]
 
    for idx, air in enumerate(fallback_airlines):
      price = int(air["base"] + random.randint(2000, 15000))
      if return_date:
        price = int(price * 1.8)
 
      dep, arr, duration, duration_min, stops = times_pairs[
          idx % len(times_pairs)
      ]
 
      flights.append({
          "airline": air["name"],
          "logo": air["logo"],
          "code": air["code"],
          "origin": origin,
          "destination": destination,
          "origin_code": origin_iata,
          "dest_code": dest_iata,
          "departure": dep,
          "arrival": arr,
          "duration": duration,
          "duration_minutes": duration_min,
          "stops": stops,
          "price": f"{price:,}".replace(",", " "),
          "currency": "₸",
          "raw_price": price,
          "is_live": False,
          "depart_date": depart_date or "2026-10-18",
          "return_date": return_date,
      })
 
  return jsonify({"success": True, "flights": flights})
 
 
@app.route("/api/board", methods=["GET"])
def get_flight_board():
  board = [
      {
          "flight": "KC 853",
          "airline": "Air Astana",
          "route": "Алматы ➔ Астана",
          "time": "14:20",
          "status": "Посадка",
          "gate": "A02",
      },
      {
          "flight": "FS 705",
          "airline": "FlyArystan",
          "route": "Алматы ➔ Шымкент",
          "time": "15:00",
          "status": "По расписанию",
          "gate": "B04",
      },
      {
          "flight": "SU 1947",
          "airline": "Aeroflot",
          "route": "Алматы ➔ Москва",
          "time": "15:35",
          "status": "По расписанию",
          "gate": "A08",
      },
      {
          "flight": "DV 473",
          "airline": "SCAT",
          "route": "Алматы ➔ Актау",
          "time": "16:10",
          "status": "Задерживается",
          "gate": "A05",
      },
      {
          "flight": "EK 398",
          "airline": "Emirates",
          "route": "Алматы ➔ Дубай",
          "time": "17:40",
          "status": "По расписанию",
          "gate": "A01",
      },
  ]
  return jsonify({"success": True, "board": board})
 
 
TOURS = [
    {"id": 1, "title": "Анталья: всё включено", "country": "Турция", "category": "beach",
     "emoji": "🏖", "nights": 7, "hotel": "Rixos Premium", "stars": 5, "price": 389000,
     "includes": ["Перелёт", "Всё включено", "Трансфер"]},
    {"id": 2, "title": "Шарм-эль-Шейх", "country": "Египет", "category": "beach",
     "emoji": "🐠", "nights": 7, "hotel": "Sunrise Diamond", "stars": 4, "price": 345000,
     "includes": ["Перелёт", "Всё включено", "Трансфер"]},
    {"id": 3, "title": "Мальдивы: остров мечты", "country": "Мальдивы", "category": "beach",
     "emoji": "🏝", "nights": 7, "hotel": "Sun Island", "stars": 4, "price": 890000,
     "includes": ["Перелёт", "Полупансион", "Трансфер"]},
    {"id": 4, "title": "Дубай: город будущего", "country": "ОАЭ", "category": "city",
     "emoji": "🏙", "nights": 5, "hotel": "Rove Downtown", "stars": 4, "price": 420000,
     "includes": ["Перелёт", "Завтраки", "Экскурсия"]},
    {"id": 5, "title": "Стамбул на выходные", "country": "Турция", "category": "city",
     "emoji": "🕌", "nights": 4, "hotel": "Pera Palace", "stars": 3, "price": 210000,
     "includes": ["Перелёт", "Завтраки"]},
    {"id": 6, "title": "Тбилиси и Кахетия", "country": "Грузия", "category": "city",
     "emoji": "🍷", "nights": 4, "hotel": "Rooms Tbilisi", "stars": 4, "price": 180000,
     "includes": ["Перелёт", "Завтраки", "Винный тур"]},
    {"id": 7, "title": "Иссык-Куль", "country": "Кыргызстан", "category": "mountains",
     "emoji": "⛰", "nights": 5, "hotel": "Aurora Resort", "stars": 4, "price": 150000,
     "includes": ["Трансфер", "Полупансион", "Экскурсии"]},
    {"id": 8, "title": "Кольсай и Каинды", "country": "Казахстан", "category": "mountains",
     "emoji": "🏞", "nights": 3, "hotel": "Guest House Kolsai", "stars": 3, "price": 95000,
     "includes": ["Трансфер", "Питание", "Гид"]},
]
 
 
@app.route("/api/tours", methods=["GET"])
def get_tours():
  category = request.args.get("category", "").strip().lower()
  tours = [t for t in TOURS if not category or t["category"] == category]
  return jsonify({"success": True, "tours": tours})
 
 
def run_flask():
  app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)
 
 

if not BOT_TOKEN:
  raise SystemExit("Не задан BOT_TOKEN. Создай файл .env (см. .env.example).")
if not WEB_APP_URL:
  raise SystemExit("Не задан WEB_APP_URL. Укажи https-адрес Mini App в .env.")
 
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
 
 
def get_main_keyboard():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="👤 Аккаунт и Баланс", callback_data="btn_account"
              ),
              InlineKeyboardButton(
                  text="ℹ️ Помощь", callback_data="btn_help"
              ),
          ],
          [
              InlineKeyboardButton(
                  text="✈️ Открыть AviaJary App",
                  web_app=WebAppInfo(url=WEB_APP_URL),
              )
          ],
      ]
  )
 
 
def get_back_keyboard():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="✈️ Открыть AviaJary App",
                  web_app=WebAppInfo(url=WEB_APP_URL),
              )
          ],
          [InlineKeyboardButton(text="⬅️ Назад", callback_data="btn_back")],
      ]
  )
 
 
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
  text = "Привет! Добро пожаловать в мир авиалиний AviaJary"
  await message.answer(text, reply_markup=get_main_keyboard())
 
 
@dp.callback_query(lambda c: c.data == "btn_account")
async def process_account(callback: types.CallbackQuery):
  user_name = html.escape(callback.from_user.first_name or "")
  text = (
      f"👤 <b>Профиль пользователя:</b> {user_name}\n"
      f"💳 <b>Баланс Kaspi Gold:</b> 1 000 000 ₸\n\n"
      f"🎫 <b>Ваши билеты:</b>\nПерейдите в Mini App, чтобы просмотреть сохраненные"
      " посадочные талоны."
  )
  await callback.message.edit_text(
      text, reply_markup=get_back_keyboard(), parse_mode="HTML"
  )
  await callback.answer()
 
 
@dp.callback_query(lambda c: c.data == "btn_help")
async def process_help(callback: types.CallbackQuery):
  text = (
      "Это умный бот-помощник, который поможет тебе забронировать и купить"
      " авиабилеты в любую точку мира..(ну, почти в любую 😉)."
  )
  await callback.message.edit_text(
      text, reply_markup=get_back_keyboard(), parse_mode="Markdown"
  )
  await callback.answer()
 
 
@dp.callback_query(lambda c: c.data == "btn_back")
async def process_back(callback: types.CallbackQuery):
  text = "Привет! Добро пожаловать в мир авиалиний AviaJary"
  await callback.message.edit_text(text, reply_markup=get_main_keyboard())
  await callback.answer()
 
 
async def main():
  threading.Thread(target=run_flask, daemon=True).start()
  print("порт запущен 8000.")
  print("твой бро запущен.")
  await dp.start_polling(bot)
 
 
if __name__ == "__main__":
  asyncio.run(main())