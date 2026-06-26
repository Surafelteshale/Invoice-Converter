import re
import os
import pandas as pd
from flask import Flask, render_template, request, send_file

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

VAT_RATE = 0.15

SKIP_KEYWORDS = [
    "SUBTOTAL", "TOTAL", "TAX", "TXBL", "CASH",
    "ITEM#", "SIGNATURE", "TIN", "TEL"
]

SKIP_INVOICE_KEYWORDS = [
    "SESSION Z REPORT",
    "PLU Z REPORT",
]


def process_invoice(input_path, output_path):

    rows = []

    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    invoices = re.split(r"FS No\.", text)[1:]

    for inv in invoices:

        inv_upper = inv.upper()

        if any(k in inv_upper for k in SKIP_INVOICE_KEYWORDS):
            continue

        if "TOTAL" not in inv_upper:
            continue

        fs_match = re.search(r"(\d+)", inv)
        fs_no = f"FS {fs_match.group(1)}" if fs_match else ""

        date_match = re.search(r"(\d{2}/\d{2}/\d{4})", inv)
        sale_date = date_match.group(1) if date_match else ""

        lines = inv.splitlines()

        pending_qty = None
        pending_unit_price = None

        for line in lines:

            line_clean = line.strip()
            line_upper = line_clean.upper()

            if any(k in line_upper for k in SKIP_KEYWORDS):
                continue

            qty_match = re.search(r"(\d+)\s*x\s*(\d+\.\d+)", line_clean)
            if qty_match:
                pending_qty = int(qty_match.group(1))
                pending_unit_price = float(qty_match.group(2))
                continue

            item_match = re.search(r"(.+?)\s+\*(\d+\.\d+)", line_clean)

            if item_match:
                name = item_match.group(1).strip()
                price_in_invoice = float(item_match.group(2))

                if any(k in name.upper() for k in SKIP_KEYWORDS):
                    continue

                if pending_qty is not None:
                    qty = pending_qty
                    unit_price = pending_unit_price
                else:
                    qty = 1
                    unit_price = price_in_invoice

                pending_qty = None
                pending_unit_price = None

                total_value = qty * unit_price
                vat = total_value * VAT_RATE
                value_after_vat = total_value + vat

                rows.append([
                    "S",
                    "G",
                    1,
                    "",
                    "No Name",
                    sale_date,
                    "BIA025663",
                    fs_no,
                    name,
                    7,
                    qty,
                    round(unit_price, 3),
                    round(total_value, 3),
                    round(vat, 3),
                    round(value_after_vat, 3)
                ])

    columns = [
        "VAT CATEGORY",
        "CALENDAR TYPE",
        "TYPE OF SALE",
        "Buyer TIN",
        "Buyer Name",
        "Date of Sale",
        "MRC Number",
        "Description",
        "Item Name",
        "Unit of Measure",
        "Quantity",
        "Unit Price",
        "Total Value",
        "VAT",
        "Value After VAT"
    ]

    df = pd.DataFrame(rows, columns=columns)
    df.to_excel(output_path, index=False)


@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":

        file = request.files["invoice"]
        input_path = os.path.join(UPLOAD_FOLDER, "invoices.txt")
        output_path = os.path.join(OUTPUT_FOLDER, "result.xlsx")

        file.save(input_path)
        process_invoice(input_path, output_path)

        return send_file(output_path, as_attachment=True)

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)