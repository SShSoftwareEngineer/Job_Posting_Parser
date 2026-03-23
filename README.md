# Job Posting Parser

Multi-source job market intelligence system for data-driven career insights.

## Overview

Automated data collection and analysis pipeline that aggregates job postings from Telegram channels and email newsletters, extracts comprehensive vacancy details from source websites, and enables multi-dimensional market analysis.

## Features

### Multi-Source Data Collection

- **Telegram channels**: Asynchronous parsing via Telethon API
- **Email newsletters**: IMAP-based extraction via IMAPClient

### Two-Stage Extraction

1. **Initial parsing**: Extract basic info from Telegram posts and emails
2. **Deep scraping**: Follow links to source websites for full vacancy details
   - BeautifulSoup for HTML parsing
   - AIOHTTP for async HTTP requests
   - AsyncIO Semaphore for rate limiting (prevents blocking)

### Comprehensive Data Extraction

18+ parameters extracted per vacancy:

| Category | Parameters                                                     |
|----------|----------------------------------------------------------------|
| **Position** | position, experience, employment case                          |
| **Location** | location, offices, candidate locations (remote/relocation)     |
| **Technical** | main technology, tech stack, languages                         |
| **Compensation** | salary diapason                                                |
| **Company** | company name, company type, domain                             |
| **Content** | job description preview, job description full text, notes |
| **Metadata** | URL (source link)                                              |

### Data Processing & Storage

- **Validation**: Pydantic schemas ensure data quality and type safety
- **Storage**: SQLAlchemy ORM with SQLite (PostgreSQL-ready schema)
- **Export**: Excel reports via openpyxl + Pandas for stakeholder analysis
- **Filtering**: Query by any parameter combination for targeted insights

### Performance & Reliability

- **Async operations**: Concurrent data collection with AsyncIO
- **Rate limiting**: Semaphore-based request throttling to avoid website blocks
- **Error handling**: Graceful failures with retry mechanisms
- **Data normalization**: Clean and consistent format across sources

## Use Cases

- 📊 **Salary analysis**: Understand market rates by role, experience, location
- 🛠️ **Tech trends**: Identify most demanded technologies and skills
- 🌍 **Location insights**: Remote vs on-site opportunities, relocation offers
- 🏢 **Company research**: Analyze by company type (product/service/startup)
- 📈 **Market dynamics**: Track changes over time, seasonal patterns
- 🎯 **Job search**: Filter by multiple criteria to find ideal positions

## Project Stats

- **3,800+ job postings** analyzed
- **2 data sources**: Telegram + Email
- **18 parameters** extracted per vacancy
- **Multi-dimensional** filtering and analysis

## Tech Stack

- **Data Collection**: 
  - Telegram: Telethon, AsyncIO
  - Email: IMAPClient
  - Web: AIOHTTP, BeautifulSoup
- **Data Processing**: 
  - Validation: Pydantic
  - Export: Pandas, openpyxl
  - Parsing: Regular Expressions
- **Storage**: SQLAlchemy ORM, SQLite (PostgreSQL-ready)
- **Concurrency**: AsyncIO with Semaphore for rate limiting
- **Language**: Python 3.9+


## Installation

### Setup

1. **Clone the repository:**  
   git clone https://github.com/SShSoftwareEngineer/Job_Posting_Parser.git  
   cd Job_Posting_Parser

2. **Install dependencies:**  
   poetry install  
   poetry shell

3. **Configure credentials in a .env file**

4. **Run the parser:**
   python job_posting_parser.py

### Extracted Parameters Explained

- **POSITION**: Job title (e.g., "Python Developer", "Data Engineer")
- **EXPERIENCE**: Required years of experience
- **MAIN_TECH**: Primary technology (Python, Java, etc.)
- **TECH_STACK**: List of all required technologies
- **LINGVO**: Required language skills (English, Ukrainian, etc.)
- **SALARY_FROM / SALARY_TO**: Compensation range
- **JOB_DESC_PREV**: Short description from initial post
- **JOB_DESC**: Complete job description from source website
- **EMPLOYMENT**: Employment type (full-time, part-time, contract)
- **CANDIDATE_LOCATIONS**: Remote work, relocation options
- **COMPANY**: Company name
- **LOCATION**: Primary office location
- **COMPANY_TYPE**: Product company, service/outsource, startup
- **DOMAIN**: Business domain (FinTech, E-commerce, etc.)
- **OFFICES**: List of office locations
- **URL**: Link to full vacancy on website
- **NOTES**: Additional information

## Project Insights

This project demonstrates:

- ✅ **Multi-source ETL**: Unified pipeline for different data sources
- ✅ **Two-stage extraction**: Initial + deep scraping workflow
- ✅ **Async programming**: Concurrent I/O with rate limiting
- ✅ **Web scraping**: Robust HTML parsing with error handling
- ✅ **Database design**: Normalized schema with 18 structured fields
- ✅ **Scalability**: SQLite for development, PostgreSQL-ready for production
- ✅ **Multi-dimensional analysis**: Complex filtering across multiple parameters

## Roadmap

### Planned Features

- [ ] **PostgreSQL migration**: Production deployment with larger datasets
- [ ] **Web dashboard**: Interactive UI with charts (Plotly/Dash)
- [ ] **Advanced analytics**: Salary predictions, trend forecasting
- [ ] **More sources**: LinkedIn, DOU, Indeed APIs
- [ ] **ML-powered**: Automatic tech stack categorization, skill extraction

### Under Consideration

- Docker containerization for easy deployment
- REST API for programmatic access
- Scheduled cloud deployment (AWS Lambda/GCP Functions)
- Integration with job application trackers

## Why SQLite?

**Current choice: SQLite**
- Zero configuration, single file
- Perfect for development and personal use
- Handles 500+ vacancies efficiently

**PostgreSQL ready:**
- Schema designed for easy migration
- Just change DATABASE_URL connection string
- Planned for:
  - Datasets >10K vacancies
  - Multi-user access
  - Production deployment

## License

This project is licensed under the MIT License.

## Contact

**Sergiy Shypulin**

- Email: [s.shypulin@gmail.com](mailto:s.shypulin@gmail.com)
- LinkedIn: [linkedin.com/in/sergiy-shypulin](https://linkedin.com/in/sergiy-shypulin)
- GitHub: [@SShSoftwareEngineer](https://github.com/SShSoftwareEngineer)
