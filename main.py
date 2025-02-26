import fitz  # PyMuPDF
import logging
import os
import asyncio
import uuid  # Import this at the top of your script
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes, CallbackQueryHandler
# from keep_alive import keep_alive
# keep_alive()

from dotenv import load_dotenv
load_dotenv()

# Replace with your Telegram bot token
BOT_TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
import os

# Define folders for input and edited PDFs
INPUT_FOLDER = "input_pdfs"
OUTPUT_FOLDER = "edited_pdfs"

# Ensure both folders exist
os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Enable logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Conversation states
WAITING_OLD_TEXT, WAITING_NEW_TEXT = range(2)

# Dictionary to store user text replacements
user_replacements = {}

def edit_pdf(input_pdf, output_pdf, output_pdf_name):
    doc = fitz.open(input_pdf)
    page = doc[0]        # Select the first page

    hide_rect = fitz.Rect(36.0, 304.0, 300, 410)   # Define the rectangle where text should be hidden
    # Draw a white rectangle over the text area
    page.draw_rect(hide_rect, color=(1, 1, 1), fill=(1, 1, 1))  # White fill

    # Insert new text at the specified position
    rect = fitz.Rect(36, 329, 500, 400)  # Define a large area for text
    page.insert_textbox(
        rect,
        "Coding Services",
        fontsize=23,  # Increase font size
        fontname="helvetica-bold",
        color=(0, 0, 0),
        align=0  # Left alignment
    )

    page.insert_text(
        (36, 383),
        output_pdf_name,
        fontsize=17,  # Increased size
        fontname="helvetica-bold",
        color=(0, 0, 0)
    )

    doc.save(output_pdf)
    doc.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id  # Get the user's Telegram ID
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Access Denied! Only the admin can use this bot.")
        return  # Stop execution if user is not admin

    await update.message.reply_text("✅ Welcome, Admin! Send me a PDF to edit.")

async def receive_new_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id  # Get user ID

    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Access Denied! Only the admin can use this bot.")
        return  # Stop execution

    await update.message.reply_text("Now send me a PDF to process.")
    return ConversationHandler.END


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id  # Get user ID

    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Access Denied! Only the admin can use this bot.")
        return  # Stop execution if user is not admin

    file = update.message.document
    if file.mime_type == "application/pdf":
        # Get original file name
        original_filename = file.file_name
        file_base, _ = os.path.splitext(original_filename)  # Extract name without extension

        # ✅ Define paths for input & output files
        input_pdf_path = os.path.join(INPUT_FOLDER, f"{file_base}.pdf")  # Save input PDF in "input_pdfs/"

        # ✅ Set output file name based on prefix
        if file_base.startswith("plag"):
            output_pdf_name = f"Plag_Report{uuid.uuid4().hex[:4]}.pdf"
        elif file_base.startswith("ai"):
            output_pdf_name = f"AI_Report{uuid.uuid4().hex[:4]}.pdf"
        else:
            output_pdf_name = f"{file_base}.pdf"

        output_pdf_path = os.path.join(OUTPUT_FOLDER, output_pdf_name)  # Save edited PDF in "edited_pdfs/"

        # ✅ Download input file
        new_file = await context.bot.get_file(file.file_id)
        await new_file.download_to_drive(input_pdf_path)

        # ✅ Edit the PDF and save it
        edit_pdf(input_pdf_path, output_pdf_path, output_pdf_name)

        # ✅ Delete the input file after processing
        if os.path.exists(input_pdf_path):
            os.remove(input_pdf_path)
            print(f"Deleted input file: {input_pdf_path}")

        # ✅ Send edited PDF to the user
        await update.message.reply_document(document=open(output_pdf_path, "rb"))

        # ✅ Ask admin whether to delete the output file
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"delete:{output_pdf_path}")],
            [InlineKeyboardButton("❌ No, Keep", callback_data="keep")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Do you want to delete the output file `{output_pdf_name}`?",
            reply_markup=reply_markup
        )

    else:
        await update.message.reply_text("Please upload a valid PDF file.")


async def delete_file_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id  # Get user ID

    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Access Denied! Only the admin can use this bot.")
        return  # Stop execution

    query: CallbackQuery = update.callback_query
    await query.answer()

    if query.data.startswith("delete:"):
        output_pdf_path = query.data.split("delete:")[1]

        if os.path.exists(output_pdf_path):
            os.remove(output_pdf_path)
            await query.edit_message_text(text=f"✅ Output file deleted: `{output_pdf_path}`")
            print(f"Deleted output file: {output_pdf_path}")
        else:
            await query.edit_message_text(text="⚠️ File not found or already deleted.")
    elif query.data == "keep":
        await query.edit_message_text(text="✅ Output file kept.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("edit", receive_new_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # ✅ Add callback query handler for deletion decision
    app.add_handler(CallbackQueryHandler(delete_file_callback))


    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
