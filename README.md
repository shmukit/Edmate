# Edmate

**AI-Powered Educational Content Platform for A/O-Level Students**

Edmate is an intelligent educational platform that generates high-quality learning materials from Cambridge A/O-Level exam papers using AI-powered content extraction and generation.

---

## 🎯 Project Overview

This repository contains the content generation pipeline that:
- Extracts questions and diagrams from PDF exam papers
- Uploads images to cloud storage (Cloudflare R2/AWS S3)
- Imports structured data into PostgreSQL database
- Generates formatted educational content using AI

---

## 📁 Repository Structure

```
Edmate/
├── content_gen/          # Content generation pipeline
│   ├── scripts/          # Extraction, upload, and import scripts
│   ├── data/             # Input PDFs and extracted outputs
│   ├── docs/             # Detailed documentation
│   └── tools/            # External tools (PDF-Extract-Kit)
└── README.md            # This file
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Azure Blob Storage

### Installation

```bash
# Clone the repository
git clone https://github.com/shmukit/Edmate.git
cd Edmate/content_gen

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Basic Usage

```bash
# Process a single PDF
python scripts/pipeline/pipeline_orchestrator.py \
  --single-pdf "data/inputs/9701_s25_qp_13.pdf" \
  --output-dir "data/extracted" \
  --subject Biology \
  --storage-provider r2 \
  --storage-bucket edmate-diagrams \
  --db-url "postgresql://user:pass@host:5432/edmate"
```

---

## 📚 Documentation

For detailed information, see the [`content_gen`](content_gen/) directory:

- **[Content Gen README](content_gen/README.md)** - Complete setup and usage guide
- **[Agentic Workflow](content_gen/docs/AGENTIC_WORKFLOW.md)** - Pipeline architecture
- **[Process Guide](content_gen/docs/PROCESS_GUIDE.md)** - Content generation workflow
- **[Skills Catalog](content_gen/docs/SKILLS_CATALOG.md)** - Formal skills definitions
- **[Scalability Plan](content_gen/docs/SCALABILITY_PLAN.md)** - Scaling strategy

---

## 🔧 Key Features

- ✅ **AI-Powered Extraction**: Uses PDF-Extract-Kit for accurate question and diagram extraction
- ✅ **Cloud Storage Integration**: Automatic upload to Cloudflare R2 or AWS S3
- ✅ **Database Import**: Structured data storage in PostgreSQL
- ✅ **Batch Processing**: Handle multiple PDFs efficiently
- ✅ **Agentic Workflow**: Automated content generation pipeline

---

## 🎓 Supported Subjects

Currently supporting Cambridge A/O-Level subjects:
- Biology (9700/5090)
- Chemistry (9701/5070)
- Physics (9702/5054)
- Mathematics (9709/4024)
- And more...

---

## 📊 Performance

**100 PDFs** (~2000 questions, ~5000 images):
- Extraction: ~10 minutes
- Upload: ~5 minutes  
- Import: ~2 minutes
- **Total**: ~17 minutes

**Cost**: ~$0.01/month (R2 storage + Supabase free tier)

---

## 🤝 Contributing

This is a private educational project. For questions or collaboration inquiries, please contact the repository owner.

---

## 📄 License

Proprietary - All rights reserved

---

## 🔗 Links

- **Repository**: [github.com/shmukit/Edmate](https://github.com/shmukit/Edmate)
- **Documentation**: [content_gen/README.md](content_gen/README.md)

---

**Built with ❤️ for A/O-Level students**
