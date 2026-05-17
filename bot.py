import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8973926686:AAFf-JgBO0NQmkE71pUnSVnqi_PAk7bAnFc"
JB_BIN    = "6a08832bc0954111d831c10a"
JB_KEY    = "$2a$10$tZK9IkDR4j2IHu8/R7qAPe5u8OII.xJJ7hSirNt0IMIaDN30qyVt2"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def log_message(self, format, *args):
        pass

def run_server():
    HTTPServer(('0.0.0.0', 8080), Handler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

print(f"Starting bot with token: {BOT_TOKEN[:15]}...", flush=True)

def fetch_orders():
    url = f"https://api.jsonbin.io/v3/b/{JB_BIN}/latest"
    headers = {"X-Master-Key": JB_KEY, "X-Bin-Meta": "false"}
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()
    return data.get("orders", [])

def sum_type(order, entry_type):
    result = {s: 0 for s in order.get("sizes", [])}
    for e in order.get("entries", []):
        if e.get("type") == entry_type:
            for s in order.get("sizes", []):
                result[s] += e.get("data", {}).get(s, 0)
    return result

def tot(d):
    return sum(d.values())

def format_order(o):
    sizes = o.get("sizes", [])
    order_qty  = o.get("orderQty", {})
    cutting    = sum_type(o, "cutting")
    line_issue = sum_type(o, "lineissue")
    fg         = sum_type(o, "fg")
    rejection  = sum_type(o, "rejection")
    shipped    = sum_type(o, "shipped")
    wip = {s: line_issue[s] - fg[s] - rejection[s] for s in sizes}

    msg = f"""📋 *Order: {o.get('id','-')}*

🏷 Buyer: {o.get('buyer','-')}
👕 Style: {o.get('style','-')}
🎨 Color: {o.get('color','-')}
📅 Delivery: {o.get('deliveryDate','-')}
📌 Status: {o.get('status','active').upper()}

━━━━━━━━━━━━━━
📦 Order Qty: {tot(order_qty):,}
✂️ Cutting: {tot(cutting):,}
📤 Line Issue: {tot(line_issue):,}
📦 FG Output: {tot(fg):,}
❌ Rejection: {tot(rejection):,}
🚢 Shipped: {tot(shipped):,}
⚙️ WIP: {tot(wip):,}"""

    if o.get("hasPrinting"):
        msg += f"\n🖨️ Printing: {o.get('printingVendor','-')}"
    if o.get("hasEmbroidery"):
        msg += f"\n🧵 Embroidery: {o.get('embroideryVendor','-')}"
    return msg

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *STR Garments Bot*\n\n"
        "Order number type pannunga!\n"
        "Example: `H24/000086`\n\n"
        "📋 All orders: /orders\n"
        "📊 Summary: /summary",
        parse_mode="Markdown"
    )

async def orders_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        orders = fetch_orders()
        if not orders:
            await update.message.reply_text("No orders found!")
            return
        msg = "📋 *All Orders:*\n\n"
        for o in orders:
            status = "🟢" if o.get("status") == "active" else "🔴"
            msg += f"{status} `{o.get('id','-')}` — {o.get('buyer','-')}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        orders = fetch_orders()
        total_cutting = total_fg = total_reject = total_shipped = 0
        for o in orders:
            total_cutting += tot(sum_type(o, "cutting"))
            total_fg      += tot(sum_type(o, "fg"))
            total_reject  += tot(sum_type(o, "rejection"))
            total_shipped += tot(sum_type(o, "shipped"))
        msg = f"""📊 *STR Garments Summary*

📋 Total Orders: {len(orders)}
✂️ Cutting: {total_cutting:,}
📦 FG Output: {total_fg:,}
❌ Rejection: {total_reject:,}
🚢 Shipped: {total_shipped:,}"""
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    try:
        orders = fetch_orders()
        found = None
        for o in orders:
            if o.get("id", "").upper() == text:
                found = o
                break
        if found:
            await update.message.reply_text(format_order(found), parse_mode="Markdown")
        else:
            await update.message.reply_text(
                f"❌ Order `{text}` not found!\n\nAll orders: /orders",
                parse_mode="Markdown"
            )
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

if __name__ == "__main__":
    print("✅ STR Garments Bot running...", flush=True)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("orders", orders_list))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
