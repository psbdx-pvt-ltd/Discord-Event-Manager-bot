# 📅 Discord Event Manager Bot

![Version](https://img.shields.io/badge/Version-1.3-blue?style=for-the-badge)
![Language](https://img.shields.io/badge/Language-Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-Open%20Source-orange?style=for-the-badge)

[![Support](https://img.shields.io/badge/Get_Support-PSBDx-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://psbdx.xo.je/support/)
[![Bug Report](https://img.shields.io/badge/Report_Bug-PSBDx-red?style=for-the-badge)](https://psbdx.xo.je/bug-report/)
[![Documentation](https://img.shields.io/badge/Documentation-v1.3-2ea44f?style=for-the-badge&logo=bookstack&logoColor=white)](https://documentations.psbdx.rf.gd/discord-event-manager/v1-3)

## 📖 About
A robust, open-source Discord bot designed to make hosting events seamless. Whether you are running an art contest, a gaming tournament, or a recruitment drive, this bot handles the heavy lifting.

It features a **dynamic storage system** (perfect for free hosting like Render) and uses **Private Threads** to collect user submissions, keeping your main channels clean and organized.

**Developed by:** [PSBDx](https://github.com/psbdx-pvt-ltd)

## ✨ Key Features
- **💾 Dynamic Storage (Unique!):** Solves the data loss problem on free hosting (like Render/Heroku) by using a Discord channel as a database. Your event settings survive restarts!
- **📝 Custom Forms:** Admins can create events with up to 10 questions.
- **📂 Media Support:** Users can submit Images, Videos, and PDFs securely.
- **🔒 Private Threads:** Submissions happen in private threads—no more "Closed DMs" errors!
- **⏱️ Cronjob Ready:** Built-in web server to keep the bot alive 24/7 using uptime monitors.
- **📢 Auto-Publish:** Automatically posts formatted submissions to your public event channel.

## 🛠️ Quick Setup

1. **Clone the Repo:**
   ```bash
   git clone https://github.com/psbdx-pvt-ltd/Discord-Event-Manager-bot.git
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables (.env):**
   * `DISCORD_TOKEN`: Your Bot Token.
   * `ADM_ID`: Your Discord User ID (Admin).
   * `SRCE_CHNL`: ID of a private channel for database storage.
   * `EVNT_CHNL`: ID of the public channel for event posts.
   * `USE_DISCORD_STORAGE`: Set to `True`.

4. **Run the Bot:**
   ```bash
   python bot.py
   ```

## 🤖 Commands
| Command | Description |
| :--- | :--- |
| `/new_event` | (Admin Only) Open the GUI to create a new event. |
| `/join` | (User) Check the latest event and start a submission thread. |
| `/about` | View bot version and developer info. |

---
*Made with 💖 and Python by PSBDx.*
