# 🚀 Installation & Usage

## 📦 Install Dependencies

Install the required Python packages:

```powershell
pip install requests colorama
```

---

## 🔎 Enable Your Own SearXNG Instance

Set your SearXNG instance URL using an environment variable:

```powershell
$env:SEARXNG_URL="http://localhost:8080"
```

Then run the scraper:

```powershell
python anna-crawler.py
```

---

## 🧩 Processing Pipeline

The scraper follows this workflow:

```text
                    Keywords
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
       SearXNG    Common Crawl   Optional API
          │             │             │
          └─────────────┼─────────────┘
                        ▼
                URL Deduplication
                        │
                        ▼
            Discovered-URLs[TOTAL].txt
                        │
                        ▼
              Downloaded-Files/
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
       file.pdf      file.csv      file.txt
          │
          ├──────────► file.log
          │
          └──────────► file.xlsx
```

---

## 📁 Output Structure

After execution, discovered URLs and downloaded files are organized automatically:

```text
.
├── Discovered-URLs[TOTAL].txt
│
└── Downloaded-Files/
    ├── file.pdf
    ├── file.csv
    ├── file.txt
    ├── file.log
    └── file.xlsx
```

### 📄 Supported File Types

| Extension | Format          |
| --------- | --------------- |
| `.pdf`    | PDF documents   |
| `.csv`    | CSV data        |
| `.txt`    | Text files      |
| `.log`    | Log files       |
| `.xlsx`   | Excel workbooks |

> 💡 **Tip:** Keep your SearXNG instance running before starting the scraper. Computers, remarkably, still refuse to search servers that aren't there.
