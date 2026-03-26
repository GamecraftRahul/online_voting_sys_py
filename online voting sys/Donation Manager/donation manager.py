

import csv
import queue
import random
import threading
import time
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk, messagebox, filedialog

import customtkinter as ctk
import mysql.connector
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# matplotlib for embedded charts
from matplotlib.figure import Figure

# ----------------- CONFIG -----------------
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "RAHUL123",         # <<-- set your MySQL password
    "database": "donation_manager"
}

SIM_MIN_INTERVAL = 10
SIM_MAX_INTERVAL = 15
SIM_MIN_AMOUNT = 1
SIM_MAX_AMOUNT = 1000

POLL_MS = 1000  # GUI poll interval for new donations queue

# ----------------- DB HELPERS -----------------
def get_connection():
    """Return a new DB connection. Caller MUST close."""
    return mysql.connector.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"],
        autocommit=False
    )

def fetch_all(query, params=None):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, params or ())
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception as e:
        print("DB fetch error:", e)
        return []
    finally:
        if conn:
            conn.close()

def execute(query, params=None):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, params or ())
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print("DB execute error:", e)
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# ----------------- SIMULATOR THREAD -----------------
class DonationSimulator(threading.Thread):
    def __init__(self, out_queue, stop_event):
        super().__init__(daemon=True)
        self.out_queue = out_queue
        self.stop_event = stop_event

    def run(self):
        while not self.stop_event.is_set():
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT id FROM events")
                event_rows = cur.fetchall()
                cur.execute("SELECT id FROM donors")
                donor_rows = cur.fetchall()
                cur.close()
                conn.close()

                event_ids = [r[0] for r in event_rows]
                donor_ids = [r[0] for r in donor_rows]

                if not event_ids or not donor_ids:
                    # Wait a bit and retry
                    for _ in range(3):
                        if self.stop_event.is_set(): break
                        time.sleep(1)
                    continue

                event_id = random.choice(event_ids)
                donor_id = random.choice(donor_ids)
                amount = random.randint(SIM_MIN_AMOUNT, SIM_MAX_AMOUNT)
                message = random.choice(["", "Keep it up!", "Happy to help", "Best wishes", "Thank you!"])
                created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

                conn = get_connection()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO donations (event_id, donor_id, amount, currency, message, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
                    (event_id, donor_id, amount, "INR", message, created_at)
                )
                donation_id = cur.lastrowid
                conn.commit()
                cur.close()
                conn.close()

                # notify GUI
                self.out_queue.put(donation_id)
            except Exception as e:
                print("Simulator error:", e)

            # sleep 10-15 seconds, but check stop_event frequently
            interval = random.uniform(SIM_MIN_INTERVAL, SIM_MAX_INTERVAL)
            elapsed = 0.0
            while elapsed < interval:
                if self.stop_event.is_set():
                    break
                time.sleep(0.5)
                elapsed += 0.5

# ----------------- GUI APP -----------------
class DonationManagerApp:
    def __init__(self, master):
        self.master = master
        master.title("Donation Manager")
        master.geometry("1200x750")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # queue for new donation IDs inserted by simulator
        self.new_q = queue.Queue()
        self.stop_event = threading.Event()

        # start simulator thread
        self.simulator = DonationSimulator(self.new_q, self.stop_event)
        self.simulator.start()

        # build UI
        self.build_ui()

        # start polling queue
        self.master.after(POLL_MS, self.poll_queue)

    def build_ui(self):
        # top header
        header = ctk.CTkFrame(self.master, height=70, corner_radius=0)
        header.pack(fill="x", side="top")
        ctk.CTkLabel(header, text="Donation Manager", font=("Helvetica", 22, "bold")).pack(side="left", padx=16, pady=10)
        self.status_label = ctk.CTkLabel(header, text="Ready", font=("Helvetica", 11))
        self.status_label.pack(side="right", padx=14)

        # main frame with left sidebar and right content
        main = ctk.CTkFrame(self.master)
        main.pack(fill="both", expand=True, padx=12, pady=12)

        # left column (controls)
        left = ctk.CTkFrame(main, width=320)
        left.pack(side="left", fill="y", padx=(0,12))
        left.pack_propagate(False)

        # Create Event card
        ev_card = ctk.CTkFrame(left, corner_radius=8)
        ev_card.pack(fill="x", pady=(8,12))
        ctk.CTkLabel(ev_card, text="Create Event", font=("Helvetica", 14, "bold")).pack(anchor="w", padx=10, pady=(8,4))
        self.ev_name = ctk.CTkEntry(ev_card, placeholder_text="Event name")
        self.ev_name.pack(fill="x", padx=10, pady=4)
        self.ev_target = ctk.CTkEntry(ev_card, placeholder_text="Target amount (optional)")
        self.ev_target.pack(fill="x", padx=10, pady=4)
        self.ev_desc = ctk.CTkTextbox(ev_card, height=90)
        self.ev_desc.pack(fill="x", padx=10, pady=4)
        ctk.CTkButton(ev_card, text="Create Event", command=self.create_event).pack(padx=10, pady=8)

        # Filters & actions
        filt_card = ctk.CTkFrame(left, corner_radius=8)
        filt_card.pack(fill="x", pady=(0,12))
        ctk.CTkLabel(filt_card, text="Filters & Actions", font=("Helvetica", 14, "bold")).pack(anchor="w", padx=10, pady=(8,4))
        ctk.CTkLabel(filt_card, text="Filter by event:").pack(anchor="w", padx=10, pady=(4,2))
        self.event_filter = ctk.CTkComboBox(filt_card, values=["All events"], command=self.on_filter_changed)
        self.event_filter.set("All events")
        self.event_filter.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(filt_card, text="Search donor / message:", anchor="w").pack(anchor="w", padx=10, pady=(6,2))
        self.search_entry = ctk.CTkEntry(filt_card, placeholder_text="Type and press Enter")
        self.search_entry.pack(fill="x", padx=10, pady=4)
        self.search_entry.bind("<Return>", lambda e: self.load_donations())

        btns = ctk.CTkFrame(filt_card)
        btns.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(btns, text="Refresh", command=self.full_refresh).pack(side="left", expand=True, padx=4)
        ctk.CTkButton(btns, text="Export CSV", command=self.export_csv).pack(side="right", expand=True, padx=4)

        # Donors quick view
        donors_card = ctk.CTkFrame(left, corner_radius=8)
        donors_card.pack(fill="both", expand=True, pady=(0,12))
        ctk.CTkLabel(donors_card, text="Recent Donors", font=("Helvetica", 14, "bold")).pack(anchor="w", padx=10, pady=(8,4))
        self.donors_list = tk.Listbox(donors_card, height=10)
        self.donors_list.pack(fill="both", padx=10, pady=(4,10), expand=True)

        # right content: dashboard + table + chart
        right = ctk.CTkFrame(main)
        right.pack(side="right", fill="both", expand=True)

        # stats cards
        stats = ctk.CTkFrame(right)
        stats.pack(fill="x", padx=6, pady=(0,10))
        self.card_total = ctk.CTkFrame(stats, corner_radius=8)
        self.card_total.pack(side="left", padx=6, pady=6, ipadx=8, ipady=8)
        self.lbl_total = ctk.CTkLabel(self.card_total, text="Total Donations\n0", font=("Helvetica", 14, "bold"), justify="center")
        self.lbl_total.pack(padx=12, pady=12)
        self.card_amount = ctk.CTkFrame(stats, corner_radius=8)
        self.card_amount.pack(side="left", padx=6, pady=6, ipadx=8, ipady=8)
        self.lbl_amount = ctk.CTkLabel(self.card_amount, text="Total Amount\n₹0", font=("Helvetica", 14, "bold"), justify="center")
        self.lbl_amount.pack(padx=12, pady=12)
        self.card_events = ctk.CTkFrame(stats, corner_radius=8)
        self.card_events.pack(side="left", padx=6, pady=6, ipadx=8, ipady=8)
        self.lbl_events = ctk.CTkLabel(self.card_events, text="Events\n0", font=("Helvetica", 14, "bold"), justify="center")
        self.lbl_events.pack(padx=12, pady=12)

        # table frame
        table_frame = ctk.CTkFrame(right)
        table_frame.pack(fill="both", expand=True, padx=6, pady=(0,6))

        columns = ("id", "created_at", "event", "donor", "country", "amount", "message")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
        # set column widths
        self.tree.column("id", width=70, anchor="center")
        self.tree.column("created_at", width=150, anchor="w")
        self.tree.column("event", width=180, anchor="w")
        self.tree.column("donor", width=160, anchor="w")
        self.tree.column("country", width=100, anchor="w")
        self.tree.column("amount", width=90, anchor="e")
        self.tree.column("message", width=320, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        # double-click to view details
        self.tree.bind("<Double-1>", self.on_row_double_click)

        # chart frame
        chart_frame = ctk.CTkFrame(right, height=220)
        chart_frame.pack(fill="x", padx=6, pady=(6,0))
        chart_frame.pack_propagate(False)
        self.fig = Figure(figsize=(7,2.4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Donations (last 30 days)")
        self.ax.set_ylabel("Amount (INR)")
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # initial load
        self.full_refresh()

    # ----------------- UI ACTIONS -----------------
    def set_status(self, text):
        self.status_label.configure(text=text)

    def create_event(self):
        name = self.ev_name.get().strip()
        desc = self.ev_desc.get("1.0", "end").strip()
        target = self.ev_target.get().strip() or "0"
        if not name:
            messagebox.showwarning("Validation", "Please enter an event name.")
            return
        try:
            target_val = int(target)
        except:
            messagebox.showwarning("Validation", "Target must be a number.")
            return
        ok = execute("INSERT INTO events (name, description, target_amount) VALUES (%s,%s,%s)", (name, desc, target_val))
        if ok:
            self.set_status(f"Event '{name}' created.")
            self.ev_name.delete(0, "end")
            self.ev_desc.delete("1.0", "end")
            self.ev_target.delete(0, "end")
            self.load_event_filter()
            self.load_stats()
        else:
            messagebox.showerror("Error", "Failed to create event.")

    def load_event_filter(self):
        rows = fetch_all("SELECT id, name FROM events ORDER BY id DESC")
        names = ["All events"] + [f"{r[1]} (#{r[0]})" for r in rows]
        self.event_map = {f"{r[1]} (#{r[0]})": r[0] for r in rows}
        self.event_filter.configure(values=names)
        # keep current if available
        curr = self.event_filter.get()
        if curr not in names:
            self.event_filter.set("All events")

    def on_filter_changed(self, val):
        self.load_donations()

    def build_donation_query(self):
        base = """SELECT donations.id, donations.created_at, events.name, donors.name, donors.country, donations.amount, donations.message
                  FROM donations
                  LEFT JOIN events ON donations.event_id = events.id
                  LEFT JOIN donors ON donations.donor_id = donors.id"""
        where = []
        params = []
        evsel = self.event_filter.get()
        if evsel and evsel != "All events":
            ev_id = self.event_map.get(evsel)
            if ev_id:
                where.append("donations.event_id = %s")
                params.append(ev_id)
        term = self.search_entry.get().strip()
        if term:
            where.append("(donors.name LIKE %s OR donations.message LIKE %s OR events.name LIKE %s)")
            like = f"%{term}%"
            params.extend([like, like, like])
        if where:
            base += " WHERE " + " AND ".join(where)
        base += " ORDER BY donations.id DESC LIMIT 500"
        return base, params

    def load_donations(self):
        q, params = self.build_donation_query()
        rows = fetch_all(q, params)
        # clear tree
        for it in self.tree.get_children():
            self.tree.delete(it)
        for r in rows:
            created = r[1].strftime("%Y-%m-%d %H:%M:%S") if hasattr(r[1], "strftime") else str(r[1])
            amt_text = f"₹{r[5]}"
            self.tree.insert("", "end", values=(r[0], created, r[2] or "Unknown", r[3] or "Anonymous", r[4] or "Unknown", amt_text, r[6] or ""))
        self.set_status(f"Loaded {len(rows)} donations.")
        self.load_recent_donors()

    def load_recent_donors(self):
        rows = fetch_all("SELECT name, country FROM donors ORDER BY id DESC LIMIT 25")
        self.donors_list.delete(0, "end")
        for r in rows:
            self.donors_list.insert("end", f"{r[0]} — {r[1]}")

    def load_stats(self):
        tot = fetch_all("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM donations")
        evs = fetch_all("SELECT COUNT(*) FROM events")
        if tot:
            c, s = tot[0]
            self.lbl_total.configure(text=f"Total Donations\n{c}")
            self.lbl_amount.configure(text=f"Total Amount\n₹{s}")
        if evs:
            self.lbl_events.configure(text=f"Events\n{evs[0][0]}")

    def load_chart(self):
        # simple aggregation: sum per day for last 30 days
        end = datetime.utcnow().date()
        start = end - timedelta(days=29)
        q = """
            SELECT DATE(created_at) as d, COALESCE(SUM(amount),0) FROM donations
            WHERE created_at >= %s AND created_at <= %s
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at)
        """
        rows = fetch_all(q, (start.strftime("%Y-%m-%d 00:00:00"), (end.strftime("%Y-%m-%d 23:59:59"))))
        # prepare x,y for 30 days
        days = [(start + timedelta(days=i)) for i in range(30)]
        day_str = [d.strftime("%Y-%m-%d") for d in days]
        sums = {r[0].strftime("%Y-%m-%d"): r[1] for r in rows}
        y = [sums.get(d, 0) for d in day_str]

        self.ax.clear()
        self.ax.plot(day_str, y)
        self.ax.set_title("Donations (last 30 days)")
        self.ax.set_xticks(day_str[::6])
        self.ax.tick_params(axis='x', rotation=25)
        self.ax.set_ylabel("INR")
        self.fig.tight_layout()
        self.canvas.draw()

    def full_refresh(self):
        self.set_status("Refreshing data...")
        self.load_event_filter()
        self.load_donations()
        self.load_stats()
        self.load_chart()
        self.set_status("Refreshed.")

    def export_csv(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showinfo("Export", "No data to export.")
            return
        fname = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv")])
        if not fname:
            return
        with open(fname, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id","created_at","event","donor","country","amount","message"])
            for it in items:
                vals = self.tree.item(it, "values")
                writer.writerow(vals)
        messagebox.showinfo("Export", f"Exported {len(items)} rows to {fname}")

    def on_row_double_click(self, event):
        item = self.tree.focus()
        if not item:
            return
        vals = self.tree.item(item, "values")
        txt = f"Donation ID: {vals[0]}\nTime: {vals[1]}\nEvent: {vals[2]}\nDonor: {vals[3]}\nCountry: {vals[4]}\nAmount: {vals[5]}\nMessage: {vals[6]}"
        messagebox.showinfo("Donation details", txt)

    # ----------------- Queue polling -----------------
    def poll_queue(self):
        updated = False
        while not self.new_q.empty():
            donation_id = self.new_q.get()
            try:
                row = fetch_all(
                    """SELECT donations.id, donations.created_at, events.name, donors.name, donors.country, donations.amount, donations.message
                       FROM donations
                       LEFT JOIN events ON donations.event_id = events.id
                       LEFT JOIN donors ON donations.donor_id = donors.id
                       WHERE donations.id = %s""", (donation_id,)
                )
                if row:
                    r = row[0]
                    created = r[1].strftime("%Y-%m-%d %H:%M:%S") if hasattr(r[1], "strftime") else str(r[1])
                    self.tree.insert("", 0, values=(r[0], created, r[2] or "Unknown", r[3] or "Anonymous", r[4] or "Unknown", f"₹{r[5]}", r[6] or ""))
                    updated = True
            except Exception as e:
                print("Poll error:", e)

        if updated:
            # keep table length manageable
            children = self.tree.get_children()
            if len(children) > 600:
                for c in children[600:]:
                    self.tree.delete(c)
            self.set_status("New donations arrived.")
            self.load_stats()
            self.load_chart()

        # schedule next poll
        self.master.after(POLL_MS, self.poll_queue)

    def on_close(self):
        if messagebox.askyesno("Quit", "Quit Donation Manager?"):
            self.set_status("Shutting down...")
            self.stop_event.set()
            # wait shortly for simulator to stop
            time.sleep(0.6)
            self.master.destroy()

# ----------------- Run -----------------
if __name__ == "__main__":
    root = ctk.CTk()
    app = DonationManagerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
