# 🌐 PUBLIC CODE PLAYBOOK - Agent Core Utils

## ✅ THIS REPOSITORY IS PUBLIC & OPEN SOURCE

**All code in this repository is public and will be visible to everyone on GitHub.**

### 🎯 Purpose
This repository contains generic, reusable utilities that:
- **Have no business logic**
- **Contain no competitive advantages**
- **Are completely generic**
- **Could benefit other projects**
- **Work in GitHub Actions CI/CD**

### ✅ What SHOULD Go Here
- **Generic web scraping utilities**
- **Standard HTTP/API helpers**
- **Common data validation functions**
- **Basic date/time utilities**
- **Generic database connection helpers**
- **Standard file I/O operations**
- **Common string/text processing**
- **Generic browser automation tools**
- **Standard error handling patterns**

### ❌ What Should NOT Go Here
- **Business logic** (keep in roswell-shared)
- **Proprietary algorithms** (keep private)
- **Domain-specific logic** (keep private)
- **Revenue/profit calculations** (keep private)
- **Internal workflows** (keep private)
- **Competitive advantages** (keep private)
- **API keys or secrets** (never commit anywhere)

### ✅ GitHub Actions Compatible
Code here can be used as dependencies in GitHub Actions because this repository is public.

### 🔄 Decision Process
**DEFAULT CHOICE: Put new code in roswell-shared (private)**

Only put code HERE if:
1. ✅ **You explicitly decide it should be public**
2. ✅ It's completely generic with no business value
3. ✅ It has no competitive implications
4. ✅ It could help other developers
5. ✅ It contains zero proprietary information

### 🧹 Code Quality Requirements
**🚨 CRITICAL: Ruff must be kept clean at ALL TIMES**

- **Zero ruff violations allowed** - CI will break if any exist
- **Run `ruff check . --fix` before every commit**
- **Never commit code with ruff warnings or errors**
- **All team members must maintain ruff cleanliness**

```bash
# REQUIRED before any commit
cd /path/to/agent-core-utils
ruff check . --fix
```

### 🔍 Review Checklist
Before adding code here, ask:
- [ ] Could a competitor use this against us?
- [ ] Does this reveal our business processes?
- [ ] Is this specific to our business domain?
- [ ] Does this contain any proprietary logic?

**If ANY answer is "yes" → Keep it in roswell-shared (private)**

### 📝 Examples of Public Code
```python
# ✅ BELONGS HERE - Generic Utilities
def clean_phone_number(phone: str) -> str:
    """Remove formatting from phone number."""
    return re.sub(r'[^\d]', '', phone)

def validate_email(email: str) -> bool:
    """Check if email format is valid."""
    return '@' in email and '.' in email.split('@')[1]

# ✅ BELONGS HERE - Generic Web Tools
class GenericWebScraper:
    def get_page_text(self, url: str) -> str:
        """Extract text from any webpage."""
        pass

# ❌ DOES NOT BELONG - Business Logic
def calculate_profit_margin():  # → roswell-shared
    pass

def analyze_market_position():   # → roswell-shared  
    pass
```

### 🚨 Security Reminders
- **Never commit API keys, passwords, or secrets**
- **Assume anyone can read this code**
- **Keep all business logic in roswell-shared**
- **When in doubt, keep it private**

---
**Remember: Default to private (roswell-shared). Only make public when explicitly beneficial and safe.**
