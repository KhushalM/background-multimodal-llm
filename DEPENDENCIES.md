# 📦 Dependencies Management

## 🎯 **Python Dependencies Structure**

### **📁 Clean Structure:**
```
background-multimodal-llm/
├── requirements.txt          ← 🎯 Complete dependencies (all components)
├── backend/
│   ├── requirements.txt      ← 🎯 Backend-specific dependencies  
│   ├── pyproject.toml        ← 🎯 Modern Python project config
│   └── INSTALL.md           ← 📖 Installation guide
└── frontend/
    └── package.json         ← Frontend dependencies (npm)
```

### **Dependencies Files:**
- **🌟 Root `requirements.txt`:** Complete set of all Python dependencies
- **🔧 `backend/requirements.txt`:** Backend-specific dependencies (compatibility)
- **⚙️ `backend/pyproject.toml`:** Modern Python project configuration with optional dependencies
- **🌐 `frontend/package.json`:** React frontend dependencies (npm)

### **Quick Setup:**
```bash
# Option 1: Install all dependencies from root
pip install -r requirements.txt

# Option 2: Use modern backend setup with uv
cd backend
uv venv venv
source venv/bin/activate
uv pip install -e .

# Option 3: Frontend setup (Vite + React + TypeScript)
cd frontend
npm install
npm run dev  # Start development server
```

### **For detailed instructions, see:** 
👉 **[backend/INSTALL.md](backend/INSTALL.md)**

---

**Note:** 
- **Root `requirements.txt`:** Use for simple, complete setup
- **Backend `pyproject.toml`:** Use for development with optional dependencies
- **Frontend:** Vite + React + TypeScript setup - always run commands from `frontend/` directory

**Important:** Frontend commands must be run from the `frontend/` directory:
```bash
cd frontend
npm run dev    # Start development server
npm run build  # Production build
npm run lint   # Run linting
``` 