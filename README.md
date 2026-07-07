# 💝 Donation Manager System

A desktop-based **Donation Management System** developed using **Python**, **CustomTkinter**, and **MySQL**. The application allows organizations to manage donors, events, donations, and view donation statistics through an interactive graphical user interface.

---

## 📌 Features

- 🧑 Manage donor information
- 🎯 Manage fundraising events
- 💰 Record and track donations
- 📊 Visualize donation statistics using charts
- 🔄 Automatic donation simulator
- 📂 Export data
- 🖥️ Modern CustomTkinter GUI
- 🗄️ MySQL database integration

---

## 🛠️ Technologies Used

- Python 3.x
- Tkinter
- CustomTkinter
- MySQL
- mysql-connector-python
- Matplotlib

---

## 📁 Project Structure

```
online_voting_sys_py-main/
│
├── README.md
│
└── online voting sys/
    └── Donation Manager/
        ├── donation manager.py
        └── donation manager db.sql
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/online_voting_sys_py.git
```

### 2. Move into the project directory

```bash
cd online_voting_sys_py
```

### 3. Install required packages

```bash
pip install customtkinter
pip install matplotlib
pip install mysql-connector-python
```

Or install all together:

```bash
pip install customtkinter matplotlib mysql-connector-python
```

---

## 🗄️ Database Setup

1. Open MySQL.

2. Create a database.

```sql
CREATE DATABASE donation_manager;
```

3. Import the provided SQL file:

```
donation manager db.sql
```

4. Update the database credentials inside the Python file.

```python
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "YOUR_PASSWORD",
    "database": "donation_manager"
}
```

---

## ▶️ Running the Project

```bash
python "donation manager.py"
```

---

## 📊 Modules

- Donor Management
- Event Management
- Donation Management
- Donation Simulator
- Charts & Reports
- Database Operations

---

## 📦 Dependencies

- customtkinter
- matplotlib
- mysql-connector-python
- tkinter (built into Python)

---

## 🚀 Future Improvements

- User Authentication
- PDF Receipt Generation
- Email Notifications
- Backup & Restore Database
- Cloud Database Support
- Search & Filter Enhancements
- Multi-user Support

---

## 👨‍💻 Author

**Rahul Kulkarni**



---

## 📄 License

This project is developed for educational and learning purposes.

Feel free to modify and enhance it according to your requirements.

---

## ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub.
