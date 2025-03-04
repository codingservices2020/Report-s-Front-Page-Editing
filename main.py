import fitz  # PyMuPDF
import logging
import os
import uuid  # Import this at the top of your script
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
from telegram.ext import CallbackQueryHandler
from PyPDF2 import PdfReader, PdfWriter
from keep_alive import keep_alive
keep_alive()

# from dotenv import load_dotenv
# load_dotenv()

# Replace with your Telegram bot token
BOT_TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PDF_PASSWORD = os.getenv("PDF_PASSWORD")
SIGN_TEXT_1 = os.getenv("SIGN_TEXT_1")
SIGN_TEXT_2 = os.getenv("SIGN_TEXT_2")
SIGN_TEXT_3 = os.getenv("SIGN_TEXT_3")

# Define folders for input and edited PDFs
INPUT_FOLDER = "input_pdfs"
OUTPUT_FOLDER = "edited_pdfs"

# Ensure both folders exist
os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Enable logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Function to edit the PDF and add the signature text to the first page
def edit_pdf(input_pdf, output_pdf, output_pdf_name, selected_text):
    doc = fitz.open(input_pdf)
    page = doc[0]        # Select the first page

    # Hide text or area (e.g., if needed)
    hide_rect = fitz.Rect(30.0, 304.0, 600, 410)   # Define the rectangle where text should be hidden
    page.draw_rect(hide_rect, color=(1, 1, 1), fill=(1, 1, 1))  # White fill

    # Insert new text at the specified position
    rect = fitz.Rect(36, 329, 600, 400)  # Define a large area for text
    page.insert_textbox(
        rect,
        selected_text,
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

    # Add the digital signature text on the first page directly
    if selected_text != SIGN_TEXT_1:
        page.insert_text(
            (402, 560),  # Position for "Digitally signed by"
            f"Digitally signed by {selected_text}",
            fontsize=8,  # Adjust font size as needed
            fontname="times-italic",
            color=(1, 0, 0)  # Black color
        )
    else:
        # Insert new text at the specified position
        rect = fitz.Rect(382, 680, 580, 740)  # Define a large area for text
        page.draw_rect(rect, color=(1, 0, 0))
        page.insert_textbox(
            rect,
            f"\n  \t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tDigitally signed by {selected_text}\n\n"
            f" Contact to Coding Services for Plagiarism and AI checking report on telegram @coding_services.",
            fontsize=8,  # Increase font size
            fontname="times-italic",
            color=(0, 0, 0),
            align=0  # Left alignment
        )




    doc.save(output_pdf)
    doc.close()

def sign_pdf(pdf_file_path):
    # Read the existing PDF with PdfReader
    with open(pdf_file_path, "rb") as f:
        reader = PdfReader(f)  # Use PdfReader instead of PdfFileReader
        writer = PdfWriter()    # Use PdfWriter instead of PdfFileWriter

        # Copy all pages from the original PDF to the writer
        for page_num in range(len(reader.pages)):
            writer.add_page(reader.pages[page_num])

        # Define signed file path in OUTPUT_FOLDER
        signed_pdf_path = os.path.join(OUTPUT_FOLDER, "" + os.path.basename(pdf_file_path))

        # Apply encryption with restrictions (no editing, but allow reading and copying)
        user_password = ""  # No password for the user
        owner_password = PDF_PASSWORD  # Owner password
        writer.encrypt(user_password=user_password, owner_pwd=owner_password, permissions_flag=3)

        # Save the signed PDF in the OUTPUT_FOLDER
        with open(signed_pdf_path, "wb") as f_out:
            writer.write(f_out)

    return signed_pdf_path


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id  # Get the user's Telegram ID
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Access Denied! Only the admin can use this bot.")
        return  # Stop execution if user is not admin

    await update.message.reply_text("✅ Welcome, Admin! Send me a PDF to edit.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # sent_message = await update.message.reply_text(f"Processing. Please wait...")
    user_id = update.message.from_user.id  # Get user ID

    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Access Denied! Only the admin can use this bot.")
        return  # Stop execution if user is not admin

    file = update.message.document
    if file.mime_type == "application/pdf":
        # Get original file name
        original_filename = file.file_name
        file_base, _ = os.path.splitext(original_filename)  # Extract name without extension

        # Define paths for input & output files
        input_pdf_path = os.path.join(INPUT_FOLDER, f"{file_base}.pdf")  # Save input PDF in "input_pdfs/"

        # Set output file name based on prefix
        if file_base.startswith("plag"):
            output_pdf_name = f"Plag_Report{uuid.uuid4().hex[:4]}.pdf"
        elif file_base.startswith("ai"):
            output_pdf_name = f"AI_Report{uuid.uuid4().hex[:4]}.pdf"
        else:
            output_pdf_name = f"{file_base}.pdf"

        output_pdf_path = os.path.join(OUTPUT_FOLDER, output_pdf_name)  # Save edited PDF in "edited_pdfs/"

        # Download input file
        new_file = await context.bot.get_file(file.file_id)
        await new_file.download_to_drive(input_pdf_path)

        # Show buttons to select signature text
        keyboard = [
            [InlineKeyboardButton(SIGN_TEXT_1, callback_data=f"sign_text:{SIGN_TEXT_1}")],
            [InlineKeyboardButton(SIGN_TEXT_2, callback_data=f"sign_text:{SIGN_TEXT_2}")],
            [InlineKeyboardButton(SIGN_TEXT_3, callback_data=f"sign_text:{SIGN_TEXT_3}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Choose a text for the signature:", reply_markup=reply_markup)

        # Store file paths in context for later use
        context.user_data["input_pdf_path"] = input_pdf_path
        context.user_data["output_pdf_path"] = output_pdf_path
        context.user_data["output_pdf_name"] = output_pdf_name


async def select_sign_text_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query: CallbackQuery = update.callback_query
    user_id = query.from_user.id  # ✅ Correct way to get user ID in callback queries

    if user_id != ADMIN_ID:
        await query.answer("🚫 Access Denied! Only the admin can use this bot.", show_alert=True)
        return  # Stop execution if user is not admin

    await query.answer()  # ✅ Acknowledge button press

    selected_text = query.data.split("sign_text:")[1]  # Extract chosen text
    print(f"selected_text: {selected_text}")
    sent_message = await query.edit_message_text(text=f"Processing. Please wait...")
    # sent_message = await update.message.reply_text(f"Processing. Please wait...")

    # Retrieve stored file paths
    input_pdf_path = context.user_data["input_pdf_path"]
    output_pdf_path = context.user_data["output_pdf_path"]
    output_pdf_name = context.user_data["output_pdf_name"]

    # Edit the PDF with the selected sign text
    edit_pdf(input_pdf_path, output_pdf_path, output_pdf_name, selected_text)

    # ✅ Delete the input file after processing
    if os.path.exists(input_pdf_path):
        os.remove(input_pdf_path)
        print(f"Deleted input file: {input_pdf_path}")

    # Now proceed to signing the PDF
    signed_pdf_path = sign_pdf(output_pdf_path)

    # Send the signed PDF
    with open(signed_pdf_path, "rb") as f:
        await context.bot.send_document(chat_id=ADMIN_ID, document=f)

    if os.path.exists(output_pdf_path):
        os.remove(output_pdf_path)
        print(f"Deleted output file: {output_pdf_path}")
    context.job_queue.run_once(delete_message, 1,
                                       data=(sent_message.chat.id, sent_message.message_id))

# ------------------ Delete Message Function ------------------ #
async def delete_message(context: CallbackContext):
    chat_id, message_id = context.job.data
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # ✅ Add callback query handler for deletion decision
    app.add_handler(CallbackQueryHandler(select_sign_text_callback, pattern=r"sign_text:.*"))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
