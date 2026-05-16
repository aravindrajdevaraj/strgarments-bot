import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
JB_BIN    = os.environ.get("JB_BIN")
JB_KEY    = os.environ.get("JB_KEY")

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
    order_qty   = o.get("orderQty", {})
    cutting     = sum_type(o, "cutting")
    recut       = sum_type(o, "recut")
    line_issue  = sum_type(o, "lineissue")
    fg          = sum_type(o, "fg")
    rejection   = sum_type(o, "rejection")
    shipped     = sum_type(o, "shipped")

    wip = {s: line_issue[s] - fg[s] - rejection[s] for s in sizes}

    msg = f"""📋 *Order: {o.get('id','-')}*

🏷 Buyer: {o.get('buyer','-')}
👕 Style: {o.get('style','-')}
🎨 Color: {o.get('color','-')}
📅 Delivery: {o.get('deliveryDate','-')}
📌 Status: {o.get('status','active').upper()}

━━━━━━━━━━━━━━━━━━
📦 *ORDER QTY:* {tot(order_qty):,}
✂️ *CUTTING:* {tot(cutting):,}
📤 *LINE ISSUE:* {tot(line_issue):,}
📦 *FG OUTPUT:* {tot(fg):,}
❌ *REJECTION:* {tot(rejection):,}
🚢 *SHIPPED:* {tot(shipped):,}
⚙️ *WIP:* {tot(wip):,}"""

    if o.get("hasPrinting"):
        msg += f"\n🖨️ *PRINTING:* {o.get('printingVendor','-')}"
    if o.get("hasEmbroidery"):
        msg += f"\n🧵 *EMBROIDERY:* {o.get('embroideryVendor','-')}"

    return msg

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *STR Garments Bot*\n\n"
        "Order number type pannunga!\n"
        "Example: `H24/000086`\n\n"
        "📋 All orders list: /orders\n"
        "📊 Summary: /summary",
        parse_mode="Markdown"
    )

async def orders_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        orders = fetch_orders()
        if not orders:
            await update.message.reply_text("⚠️ No orders found!")
            return
        msg = "📋 *All Orders:*\n\n"
        for o in orders:
            status = "🟢" if o.get("status") == "active" else "🔴"
            msg += f"{status} `{o.get('id','-')}` — {o.get('buyer','-')} — {o.get('style','-')}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        orders = fetch_orders()
        if not orders:
            await update.message.reply_text("⚠️ No orders found!")
            return
        total_orders = len(orders)
        total_cutting = total_fg = total_reject = total_shipped = 0
        for o in orders:
            total_cutting  += tot(sum_type(o, "cutting"))
            total_fg       += tot(sum_type(o, "fg"))
            total_reject   += tot(sum_type(o, "rejection"))
            total_shipped  += tot(sum_type(o, "shipped"))
        msg = f"""📊 *STR Garments Summary*

📋 Total Orders: {total_orders}
✂️ Total Cutting: {total_cutting:,}
📦 Total FG Output: {total_fg:,}
❌ Total Rejection: {total_reject:,}
🚢 Total Shipped: {total_shipped:,}"""
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

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
            msg = format_order(found)
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text(
                f"❌ Order `{text}` not found!\n\n"
                "📋 All orders list: /orders",
                parse_mode="Markdown"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("orders", orders_list))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ STR Garments Bot running...")
    app.run_polling()
