Created by Lilian-Moon11. Contact/Issues: https://github.com/Lilian-Moon11/local-patient-advocate/issues

# Local Patient Advocate 🛡️

**A secure, accessible, and local-first tool for managing medical records and generating Release of Information (ROI) forms.**

> **Status:** MVP (In Development)
> **License:** GNU AGPLv3

## The Privacy Promise
This application is designed with a "Zero-Trust" architecture to meet strict security needs:
* **Local Execution:** The app runs entirely on your machine as a native desktop application.
* **Encryption at Rest:** All patient data is stored in a local SQLite database encrypted with **SQLCipher (256-bit AES)**. The file is unreadable without your password.
* **No Cloud Sync:** Patient data never leaves your device.
* **Accessible:** Built with **Flet** to ensure compatibility with screen readers (NVDA, JAWS) and keyboard navigation.

## Installation & Setup

### Prerequisites
* Python 3.10 or higher

### Installation
1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/Lilian-Moon11/local-patient-advocate.git](https://github.com/Lilian-Moon11/local-patient-advocate.git)
    cd local-patient-advocate
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # Mac/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## How to Run
This runs as a **desktop application**.

```bash
python main.py

First-Time Setup & Security Warning
A window will open asking for a Database Password.

If this is your first time, the password you enter will become the encryption key for your new database.

Important: Do not lose this password. There is no "reset" button because the data is encrypted mathematically using your password. If you lose it, your data is gone forever.

Technology Stack

GUI: Flet (Flutter for Python) for accessibility and native performance.


Database: SQLite with SQLCipher for transparent encryption.


Security: PBKDF2 Key Derivation + AES-256 Encryption.


License
This project is licensed under the GNU AGPLv3. See the LICENSE file for details.