#!/usr/bin/env python3
"""
Smart Expense Tracker with Monthly Summary
Save as: main.py
"""

import json
import os
import time
from datetime import datetime, date
import calendar
import csv

# File names
EXPENSES_FILE = "expenses.json"
LOG_FILE = "app_log.txt"

# ---------------------------
# Decorator: logging & timing
# ---------------------------
def log_and_time(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_dt = datetime.now()
        print(f"[{start_dt.strftime('%Y-%m-%d %H:%M:%S')}] Starting '{func.__name__}'")
        t0 = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            t1 = time.perf_counter()
            duration = t1 - t0
            log_line = f"[{start_dt.strftime('%Y-%m-%d %H:%M:%S')}] Function '{func.__name__}' executed in {duration:.4f}s\n"
            # Append to log file
            try:
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(log_line)
            except Exception as e:
                # If logging fails, print to console but don't crash program
                print("Failed to write log:", e)
            # Print a brief summary
            print(f"Function '{func.__name__}' finished in {duration:.4f}s\n")
    return wrapper

# ---------------------------
# JSON storage helpers
# ---------------------------
def ensure_expenses_file():
    """Ensure expenses.json exists and contains a list; create if missing or corrupted."""
    if not os.path.exists(EXPENSES_FILE):
        with open(EXPENSES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)
        return

    # If exists, try to read and validate it's a list
    try:
        with open(EXPENSES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("expenses.json does not contain a list")
    except Exception:
        # Backup corrupted file and create a fresh one
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"expenses_corrupted_backup_{ts}.json"
            os.rename(EXPENSES_FILE, backup_name)
            print(f"Corrupted expenses.json moved to {backup_name}. Created new expenses.json.")
        except Exception:
            print("Could not move corrupted expenses.json; attempting to overwrite.")
        with open(EXPENSES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)

def load_expenses():
    ensure_expenses_file()
    with open(EXPENSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_expenses(expenses):
    with open(EXPENSES_FILE, "w", encoding="utf-8") as f:
        json.dump(expenses, f, indent=2, ensure_ascii=False)

# ---------------------------
# Core functions
# ---------------------------
@log_and_time
def add_expense(date_str=None, category=None, amount=None, description=None):
    """
    Adds an expense to expenses.json. If called from console interaction,
    missing values are prompted for.
    """
    # Date
    if not date_str:
        user_input = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
        date_str = user_input or date.today().isoformat()
    else:
        date_str = date_str.strip()

    # Validate date format
    try:
        # This will raise ValueError for invalid formats
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print("Invalid date format. Expected YYYY-MM-DD. Expense not added.")
        return False

    # Category
    if not category:
        category = input("Enter category (e.g., Food, Travel, Shopping, Bills): ").strip()
    if not category:
        category = "Misc"

    # Amount
    if amount is None:
        amount_str = input("Enter amount: ").strip()
    else:
        amount_str = str(amount)

    try:
        amt = float(amount_str)
        if amt < 0:
            raise ValueError("Amount cannot be negative.")
    except ValueError:
        print("Invalid amount. Please enter a numeric non-negative value. Expense not added.")
        return False

    # Description
    if description is None:
        description = input("Enter description (optional): ").strip()

    # Build entry
    entry = {
        "date": parsed_date.isoformat(),
        "category": category,
        "amount": round(amt, 2),
        "description": description or ""
    }

    # Append to JSON file
    try:
        expenses = load_expenses()
        expenses.append(entry)
        save_expenses(expenses)
        print("✅ Expense added successfully!")
        return True
    except Exception as e:
        print("Failed to save expense:", e)
        return False

@log_and_time
def view_expenses():
    """
    Reads all expenses and prints them sorted by date (ascending).
    Also prints total expenditure at the end.
    """
    try:
        expenses = load_expenses()
    except Exception as e:
        print("Could not read expenses:", e)
        return

    # Parse dates for sorting; skip malformed entries gracefully
    def parse_safe(d):
        try:
            return datetime.strptime(d["date"], "%Y-%m-%d").date()
        except Exception:
            return date.min

    expenses_sorted = sorted(expenses, key=parse_safe)

    # Display as a formatted table
    if not expenses_sorted:
        print("No expenses recorded yet.")
        return

    header = f"{'Date':10} | {'Category':12} | {'Amount':10} | Description"
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    total = 0.0
    for e in expenses_sorted:
        d = e.get("date", "")
        c = e.get("category", "")
        a = e.get("amount", 0.0)
        desc = e.get("description", "")
        try:
            amt = float(a)
        except Exception:
            amt = 0.0
        total += amt
        print(f"{d:10} | {c:12} | {amt:10.2f} | {desc}")

    print("-" * len(header))
    print(f"{'Total':25} | {total:10.2f}")
    print()

@log_and_time
def generate_monthly_summary(month=None, year=None, export_json=True, export_csv=False):
    """
    Generate summary grouped by category for the given month and year.
    If month/year not provided, prompt the user (format: MM YYYY).
    Optionally exports to summary_Month_Year.json and/or CSV.
    """
    if month is None or year is None:
        user = input("Enter month and year (MM YYYY): ").strip()
        if not user:
            print("No month/year provided.")
            return
        try:
            parts = user.split()
            if len(parts) != 2:
                raise ValueError
            month = int(parts[0])
            year = int(parts[1])
        except Exception:
            print("Invalid input. Expected: MM YYYY (e.g., 11 2025).")
            return

    try:
        month = int(month)
        year = int(year)
        if not (1 <= month <= 12):
            raise ValueError
    except Exception:
        print("Invalid month/year provided.")
        return

    # Load expenses
    try:
        expenses = load_expenses()
    except Exception as e:
        print("Could not read expenses:", e)
        return

    # Aggregate by category for the given month/year
    summary = {}
    total = 0.0
    for e in expenses:
        d_str = e.get("date", "")
        try:
            d = datetime.strptime(d_str, "%Y-%m-%d").date()
        except Exception:
            continue
        if d.year == year and d.month == month:
            category = e.get("category", "Misc")
            try:
                amt = float(e.get("amount", 0.0))
            except Exception:
                amt = 0.0
            summary[category] = summary.get(category, 0.0) + amt
            total += amt

    month_name = calendar.month_name[month]
    title = f"===== Monthly Summary: {month_name} {year} ====="
    print("\n" + title)
    if not summary:
        print("No expenses found for this month.")
    else:
        # Print categories sorted by amount descending
        for cat, amt in sorted(summary.items(), key=lambda x: x[0].lower()):
            print(f"{cat}: ₹{amt:.2f}")
        print("-" * len(title))
        print(f"Total: ₹{total:.2f}")

    # Export options
    if export_json and summary:
        out = {
            "month": month,
            "month_name": month_name,
            "year": year,
            "categories": {k: round(v, 2) for k, v in summary.items()},
            "total": round(total, 2),
            "generated_at": datetime.now().isoformat()
        }
        filename = f"summary_{month_name}_{year}.json"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2, ensure_ascii=False)
            print(f"Summary exported to '{filename}'")
        except Exception as e:
            print("Failed to export JSON summary:", e)

    if export_csv and summary:
        csv_filename = f"summary_{month_name}_{year}.csv"
        try:
            with open(csv_filename, "w", newline='', encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Category", "Amount"])
                for k, v in summary.items():
                    writer.writerow([k, round(v, 2)])
                writer.writerow([])
                writer.writerow(["Total", round(total, 2)])
            print(f"CSV summary exported to '{csv_filename}'")
        except Exception as e:
            print("Failed to export CSV summary:", e)

# ---------------------------
# CLI Main Loop
# ---------------------------
def main():
    ensure_expenses_file()
    while True:
        print("===== Smart Expense Tracker =====")
        print("1. Add Expense")
        print("2. View All Expenses")
        print("3. Generate Monthly Summary")
        print("4. Exit")
        print("--------------------------------")
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            add_expense()
        elif choice == "2":
            view_expenses()
        elif choice == "3":
            # Ask whether to export CSV as well
            export_csv_input = input("Export summary as JSON? (Y/n) [default Y]: ").strip().lower()
            export_json_flag = (export_csv_input != "n")
            export_csv_flag = False
            if export_json_flag:
                csv_input = input("Also export CSV? (y/N) [default N]: ").strip().lower()
                export_csv_flag = (csv_input == "y")
            else:
                # If they chose not to export JSON, still allow CSV
                csv_input = input("Export CSV summary? (y/N) [default N]: ").strip().lower()
                export_csv_flag = (csv_input == "y")
            generate_monthly_summary(export_json=export_json_flag, export_csv=export_csv_flag)
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1-4.")

if __name__ == "__main__":
    main()
