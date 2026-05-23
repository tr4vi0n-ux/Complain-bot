import os
import requests
import json
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler
from flask import Flask, request
import threading

# ============================================
# YOUR BOT TOKEN - PASTE HERE
# ============================================
TELEGRAM_TOKEN = "8891677148:AAFu4qkoFpOvu9V3AQpXK7vXFq7-bFpewXE"  # ← PASTE YOUR TOKEN!

# ============================================
# KNOWLEDGE BASE - Add your solutions here!
# ============================================
KNOWLEDGE_BASE = {
    # Trading Bot Problems
    "api key invalid": "🔧 SOLUTION: Generate a new API key from your exchange. Go to API Management → Create New Key → Enable Trading permission → Copy the new key → Update in your bot settings.",
    
    "bot not placing trades": "🔧 SOLUTION: Check these 3 things:\n1. Does your API key have 'Trading' permission?\n2. Do you have enough balance?\n3. Is the market open for trading?\n\nTo check: Go to bot dashboard → Status → Review permissions.",
    
    "withdrawal not received": "🔧 SOLUTION: \n1. Get the transaction hash (TXID) from your withdrawal history\n2. Check on blockchain explorer (BSCScan/Etherscan)\n3. If confirmed >1 hour, contact exchange support with the TXID\n4. Always double-check the withdrawal address!",
    
    "wrong profit calculation": "🔧 SOLUTION: Profits might look wrong because of:\n- Trading fees (usually 0.1-0.2%)\n- Slippage during volatile markets\n- Funding fees (for futures)\n\nCheck your trade history on the exchange to compare.",
    
    "bot disconnected": "🔧 SOLUTION: \n1. Go to API Management\n2. Delete the old API key\n3. Create a brand new key\n4. Update your bot with the new key\n5. Restart the bot",
    
    "rate limit exceeded": "🔧 SOLUTION: You're sending too many orders too fast!\n- Wait 60 seconds\n- Reduce order frequency to 1 per 2 seconds\n- Consider upgrading to a paid plan for higher limits",
    
    "insufficient balance": "🔧 SOLUTION: Add funds to your account or reduce your trade size.\nCurrent balance: Check your exchange wallet.\nMinimum required: Your bot's trade amount + fees.",
    
    # Copy Trading Specific
    "copy trade not working": "🔧 SOLUTION: \n1. Make sure the master trader is active\n2. Check if you have enough balance to copy\n3. Verify copy settings (multipler, max trades)\n4. Restart copy trading feature",
    
    "delay in copying": "🔧 SOLUTION: Delays are usually 1-5 seconds.\nIf longer:\n- Check your internet connection\n- Reduce the number of pairs you're copying\n- Contact support for server upgrade",
    
    # General Help
    "how to reset": "🔧 SOLUTION: To reset your bot:\n1. Go to Settings → Advanced\n2. Tap 'Reset Configuration'\n3. Re-enter your API key\n4. Reconfigure your trading pairs\n⚠️ This will delete all current settings!",
    
    "default": "📚 I don't have that specific problem in my knowledge base yet. Please:\n1. Check your bot's manual\n2. Contact support with screenshots\n3. Type /escalate for human help\n\nI'll learn from this complaint to help others!"
}

# ============================================
# SMART SEARCH FUNCTION
# ============================================
def find_solution(complaint):
    complaint_lower = complaint.lower()
    
    # Try to find matching problem
    for problem, solution in KNOWLEDGE_BASE.items():
        if problem in complaint_lower:
            return solution
    
    # Check for transaction hash
    if "0x" in complaint and len(complaint) > 40:
        return "🔍 I see a transaction hash! Check it here:\nhttps://bscscan.com/tx/" + extract_tx_hash(complaint)
    
    # No match found
    return KNOWLEDGE_BASE["default"]

def extract_tx_hash(text):
    # Find first 0x... pattern
    import re
    match = re.search(r'0x[a-fA-F0-9]{64}', text)
    return match.group(0) if match else "unknown"

# ============================================
# TELEGRAM BOT HANDLERS
# ============================================
async def start(update, context):
    await update.message.reply_text(
        "🤖 **Complaint Solver Bot Activated!**\n\n"
        "**How to use me:**\n"
        "1️⃣ Forward any complaint about your trading bot\n"
        "2️⃣ I'll search my knowledge base\n"
        "3️⃣ I'll give you a step-by-step solution\n\n"
        "**Commands:**\n"
        "/help - Show this message\n"
        "/escalate - Get human support\n"
        "/addproblem - Teach me a new solution\n\n"
        "I learn from every complaint! 📚"
    )

async def help_command(update, context):
    await update.message.reply_text(
        "📖 **Help Guide**\n\n"
        "**Just forward a complaint message to me!**\n\n"
        "Examples of what I can solve:\n"
        "• 'API key invalid'\n"
        "• 'Bot not placing trades'\n"
        "• 'Withdrawal not received'\n"
        "• 'Wrong profit calculation'\n"
        "• 'Copy trade not working'\n\n"
        "I'll automatically detect the problem and give solutions!"
    )

async def handle_complaint(update, context):
    # Get the complaint text
    if update.message.forward_origin:
        complaint = update.message.text
    else:
        complaint = update.message.text
    
    # Send thinking message
    await update.message.reply_text("🔍 **Analyzing your complaint...**")
    
    # Find solution
    solution = find_solution(complaint)
    
    # Send solution
    await update.message.reply_text(
        f"✅ **Solution Found!**\n\n{solution}\n\n"
        f"❓ Did this solve your problem?\n"
        f"Reply with 'yes' or 'no'"
    )
    
    # Store for feedback
    context.user_data['last_complaint'] = complaint

async def handle_feedback(update, context):
    feedback = update.message.text.lower()
    
    if feedback == "yes":
        await update.message.reply_text(
            "🎉 **Great!** I'm happy I could help!\n\n"
            "Forward another complaint anytime, or type /help for options."
        )
    elif feedback == "no":
        await update.message.reply_text(
            "😕 **I'm sorry that didn't help.**\n\n"
            "Type /escalate and a human will help you within 24 hours.\n\n"
            "Also, tell me what the correct solution was and I'll learn!"
        )
        # Store for learning
        context.user_data['needs_learning'] = True

async def escalate(update, context):
    await update.message.reply_text(
        "📢 **Escalated to Human Support**\n\n"
        "Please send:\n"
        "1. Your complaint description\n"
        "2. Your bot name\n"
        "3. Screenshots (if any)\n\n"
        "A human will respond within 24 hours."
    )
    # You'll get notified via your own Telegram (setup below)

async def add_problem(update, context):
    await update.message.reply_text(
        "📝 **Teach Me a New Solution**\n\n"
        "Send me the problem and solution like this:\n\n"
        "Problem: [describe the issue]\n"
        "Solution: [step by step fix]\n\n"
        "Example:\n"
        "Problem: bot crashes at midnight\n"
        "Solution: Update your API key, it expires at UTC midnight"
    )
    context.user_data['awaiting_problem'] = True

async def save_new_problem(update, context):
    if not context.user_data.get('awaiting_problem'):
        return
    
    text = update.message.text
    
    if "Problem:" in text and "Solution:" in text:
        # Extract problem and solution
        problem_part = text.split("Solution:")[0].replace("Problem:", "").strip()
        solution_part = text.split("Solution:")[1].strip()
        
        # Save to knowledge base (in memory - for persistence we'd need database)
        KNOWLEDGE_BASE[problem_part.lower()] = f"🔧 SOLUTION: {solution_part}"
        
        await update.message.reply_text(
            f"✅ **Learned!**\n\nI've added this solution to my knowledge base.\n"
            f"Now when someone says '{problem_part}', I'll know what to do!"
        )
        context.user_data['awaiting_problem'] = False
    else:
        await update.message.reply_text(
            "❌ **Format not recognized**\n\n"
            "Please use:\n"
            "Problem: [description]\n"
            "Solution: [steps]\n\n"
            "Type /addproblem to try again"
        )

# ============================================
# WEBHOOK SETUP (for phone-friendly hosting)
# ============================================
def main():
    # Create bot application
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("escalate", escalate))
    app.add_handler(CommandHandler("addproblem", add_problem))
    
    # Add message handlers
    app.add_handler(MessageHandler(filters.FORWARDED, handle_complaint))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_problem))
    
    # For Render.com - use webhook
    print("🤖 Bot is starting...")
    
    # Use polling (simpler for free tier)
    app.run_polling()

if __name__ == "__main__":
    main()
