# 🕵️‍♂️ PennyWise: Forensic Transaction Intelligence

*Autonomous financial anomaly detection and ledger auditing.*

![PennyWise Dashboard Screenshot](https://via.placeholder.com/800x400?text=Insert+Screenshot+of+Your+Dashboard+Here)

## 📌 The Problem
Traditional financial audits rely on manual sampling, leaving massive blind spots in corporate ledgers. PennyWise acts as an autonomous forensic accountant, scanning 100% of transaction data to detect structuring, duplicate invoicing, and statistical anomalies in seconds.

## 🚀 Core Features
* **Relative Size Factor (RSF) Engine:** Isolates massive, out-of-policy transactions by comparing the largest expense in a category to the second largest.
* **Benford's Law Integrity Check:** Mathematically proves if a dataset has been manually manipulated or "stuffed" by analyzing the distribution of leading digits.
* **Structuring Detection:** Uses vectorization to catch split-invoicing (e.g., submitting five $4,999 bills to bypass a $5,000 approval limit).
* **Executive PDF Export:** Automatically generates styled, boardroom-ready reports summarizing critical anomalies and Systemic MAD scores.

## 🛠️ Tech Stack
* **Frontend UI:** Solara (Reactive Component Architecture) / Streamlit
* **Forensic Backend:** Python, Pandas, NumPy
* **Data Visualization:** Plotly (Interactive), xhtml2pdf (Static generation)

## You can try it here:
https://pennywise-forensics.streamlit.app/

## 💻 How to Run Locally

1. Clone this repository:
```bash
git clone [https://github.com/YOUR_USERNAME/pennywise-forensics.git](https://github.com/YOUR_USERNAME/pennywise-forensics.git)

