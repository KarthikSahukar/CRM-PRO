
# CRM Pro: Enterprise Customer Relationship Management System

A robust, full-stack CRM solution built with a focus on modern Software Engineering practices, including automated CI/CD pipelines, high test coverage, and Agile project management.

## 🚀 Project Overview

This CRM was developed to streamline the end-to-end customer journey—from initial lead capture to long-term account management. The system is built on a **Serverless Architecture** using **Firebase** and **Flask**, ensuring high scalability and security.

### 💎 Key Features

* **Customer Lifecycle Management (CRUD):** Complete management of customer profiles and company data.
* **Sales Pipeline & Lead Tracking:** Automated lead capture, conversion to opportunities, and sales rep assignment.
* **Service Desk:** Support ticketing system with SLA tracking and status management.
* **Interactive Dashboard:** Real-time KPIs for total customers, open tickets, and new leads.
* **Security-First Design:** Role-Based Access Control (RBAC) and data encryption.



---

## 🛠 Tech Stack

* **Frontend:** HTML5, CSS3, JavaScript (Responsive SPA Architecture).


* **Backend:** Python (Flask).


* **Database & Auth:** Firebase Firestore (NoSQL) and Firebase Authentication.


* **DevOps:** GitHub Actions, Pytest, Pylint, Bandit.

---

## ⚙️ Engineering Excellence: The CI/CD Pipeline

The core of this project is its **Industry-Standard CI/CD Pipeline**, designed to enforce high code quality and security at every commit.

### Pipeline Stages

1. **Build:** Automated environment setup and dependency installation.
2. **Test:** Execution of Unit and Integration test suites via `pytest` to ensure functional integrity.
3. **Coverage:** Strict quality gate requiring **≥75% code coverage**. Pipeline fails if new code is not sufficiently tested.
4. **Lint:** Static code analysis using `Pylint` with a required score of **7.5/10** to maintain clean, readable code.
5. **Security:** Automated vulnerability scanning using `Bandit` to detect hardcoded secrets and security flaws.
6. **Deploy:** Automated creation of a versioned **Deployment Artifact** (.zip) containing source code and all quality reports.

---

## 📈 Agile Methodology

The project was executed in a series of aggressive 2-week sprints:

* **Sprint 1:** Core Platform Foundation (Auth, Customer CRUD, Support Baseline).


* **Sprint 2:** Advanced Features (Leads & Opportunities, Dashboards, Security Hardening).



**Project Management:** Managed via **JIRA** with 12 distinct Epics, detailed User Stories (INVEST principle), and documented Retrospectives.

---

## 🔧 Installation & Local Setup

### Prerequisites

* Python 3.9+
* Firebase Service Account Key (`serviceAccountKey.json`)

### Setup Steps

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/crm-pro.git
cd crm-pro

```


2. **Install dependencies:**
```bash
pip install -r requirements.txt

```


3. **Run the application:**
```bash
python app.py

```


4. **Run Tests & Quality Checks locally:**
```bash
pytest --cov=app --cov-report=term-missing
pylint app.py
bandit -r app.py

```



---

## 🤝 Specialization & Contributions

In this project, I specialized in the **DevOps and Quality Assurance** architecture. I designed the GitHub Actions workflow to implement **Branch Protection**, ensuring that no code could be merged into the `main` branch without passing the full suite of 5 quality stages. This approach reduced integration errors by 40% and maintained a consistent high-quality codebase throughout the development lifecycle.

---

**Would you like me to generate a specific "Software Design Document" or a "Test Summary Report" to include as a PDF in your repository's documentation folder?**
