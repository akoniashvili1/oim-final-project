# Insider Trading Intelligence System  
## A Web App for Hedge Fund-Grade Signal Detection

### 1. The Big Idea

This Python project builds an institutional-style market signal detector that tracks insider (C-suite executive) stock transactions to identify potentially high-conviction trades before broader market awareness. It uses public SEC Form 4 filings, filters for high-conviction insider buys, runs NLP on earnings call transcripts to align sentiment with trades, and outputs an interactive dashboard with buy/sell signals.

Minimum Viable Product (MVP):
- Scrape SEC Form 4 data to identify insider transactions
- Filter out routine/passive trades
- Assign a basic conviction score to each trade
- Output results in tabular format

Stretch Goals:
- Integrate NLP sentiment scoring of earnings call transcripts
- Create a stock ranking model
- Display everything in a simple web app built with Streamlit

---

### 2. Learning Objectives

- Deepen proficiency in web scraping using Python (`requests`, `BeautifulSoup`)
- Apply sentiment analysis with NLP (possibly `spaCy`, `NLTK`, or `transformers`)
- Learn basic ML model development for ranking systems
- Build an interactive web dashboard (likely with `Streamlit`)
- Sharpen software design skills, including modular architecture and version control

---

### 3. Implementation Plan

Libraries/Tools:
  - `requests`, `BeautifulSoup`, `pandas` for data extraction and manipulation
  - `spaCy` or `transformers` for NLP sentiment analysis
  - `sklearn` for ranking model (optional)
  - `Streamlit` for building the interactive web-based app interface

Initial Plan:
  1. Scrape and clean Form 4 filings from the SEC EDGAR database.
  2. Filter data to exclude passive/automated sales.
  3. Create a scoring function to assess the strength of insider buying signals.
  4. Add transcript scraping and apply sentiment analysis.
  5. Merge the two datasets and display output on a Streamlit dashboard.

---

### 4. Project Schedule

Week 1 – Define trade filters, scrape SEC Form 4 data, clean data  
Week 2 – Build conviction score model, start basic command-line output  
Week 3 – Add transcript scraping + sentiment scoring (stretch)  
Week 4 – Build Streamlit dashboard, integrate components  
Week 5 – Polish, test, write documentation, finalize submission

---

### 5. Collaboration Plan

This is an individual project. Git will be used for version control and for submitting the markdown proposal and subsequent development milestones. I will organize my code into clear modules and document as I go. I’ll follow a light version of agile—prioritizing iterative builds and testing small pieces before scaling. I will test weekly. I’ll track progress using GitHub issues and commits, and push updates regularly. I will make sure to work in sprints, to identify, test, and debug errors early. 

---

### 6. Risks and Limitations

- Data availability & formatting: SEC filings may change structure or throttle scraping. I may need a backup API (e.g., OpenInsider).
- Transcript access: Earnings calls may require additional parsing logic or source alternatives.
- NLP accuracy: Sentiment analysis on financial text may need fine-tuning or domain-specific models. 
- Time limits: Stretch goals depend on whether MVP is stable early. Balancing front-end polish with backend analysis depth is a challenge.

---

### 7. Additional Course Content

Would benefit from deeper walkthroughs on:
- Modular code design for large-scale scripts
- Web scraping best practices (handling rate limits, etc.)
- Working with unstructured data (transcripts, text analysis)
- Streamlit-specific deployment guidance
- Data scraping and cleaning

---

### GitHub Repository
https://github.com/akoniashvili1/oim-final-project/blob/main/proposal.md
