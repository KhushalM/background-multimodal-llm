# 📦 Dependencies Management

## 🎯 **All Python dependencies are in the `backend/` directory**

### **📁 Clean Structure:**
```
background-multimodal-llm/
├── backend/
│   ├── requirements.txt      ← 🎯 Main Python dependencies  
│   ├── pyproject.toml        ← 🎯 Modern Python project config
│   └── INSTALL.md           ← 📖 Installation guide
└── frontend/
    └── package.json         ← Frontend dependencies (npm)
```

### **Files Location:**
- **Main dependencies:** `backend/requirements.txt` 
- **Modern config:** `backend/pyproject.toml`
- **Installation guide:** `backend/INSTALL.md`

### **Quick Setup:**
```bash
cd backend
uv venv venv
source venv/bin/activate
uv pip install -r requirements.txt
```

### **For detailed instructions, see:** 
👉 **[backend/INSTALL.md](backend/INSTALL.md)**

---

**Note:** Frontend dependencies are managed separately in `frontend/package.json` 