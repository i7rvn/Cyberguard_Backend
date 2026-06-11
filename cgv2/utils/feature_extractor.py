"""Feature Extractor — يحول المدخل لـ vector عددي"""
import re

class FeatureExtractor:
    def extract(self, tool: str, data: str) -> list:
        if tool in ["malicious_links"]:
            return self._url(data)
        elif tool in ["phishing","spam"]:
            return self._text(data)
        elif tool in ["sql_injection","xss","python_vuln","js_vuln"]:
            return self._code(data)
        elif tool in ["password_strength"]:
            return self._password(data)
        else:
            return self._generic(data)

    def _url(self, url: str) -> list:
        u = url.lower()
        return [
            min(len(url)/200, 1.0),
            url.count(".")/10,
            url.count("/")/10,
            url.count("-")/10,
            url.count("?")/5,
            1.0 if "https" in u else 0.0,
            1.0 if any(t in u for t in [".tk",".ml",".ga",".cf",".gq"]) else 0.0,
            1.0 if "login" in u else 0.0,
            1.0 if "verify" in u else 0.0,
            1.0 if "account" in u else 0.0,
            1.0 if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}', url) else 0.0,
            url.count("@")/2,
        ]

    def _text(self, text: str) -> list:
        t = text.lower()
        words = t.split()
        ph = ["urgent","verify","suspended","password","click","account","bank"]
        return [
            min(len(text)/1000, 1.0),
            sum(1 for w in words if w in ph)/10,
            text.count("!")/10,
            text.count("$")/5,
            1.0 if "http" in t else 0.0,
            sum(1 for c in text if c.isupper())/max(len(text),1),
            min(len(set(words))/100, 1.0),
            1.0 if re.search(r'\d{16}', text) else 0.0,
        ]

    def _code(self, code: str) -> list:
        c = code.lower()
        sql = ["select","insert","drop","union","or 1=1","--","'"]
        xss = ["<script","javascript:","onerror","alert(","document.cookie"]
        return [
            min(len(code)/500, 1.0),
            sum(1 for k in sql if k in c)/len(sql),
            sum(1 for k in xss if k in c)/len(xss),
            code.count("'")/20,
            code.count(";")/10,
            code.count("(")/20,
            code.count("<")/10,
            1.0 if "exec" in c or "eval" in c else 0.0,
        ]

    def _password(self, pwd: str) -> list:
        common = ["password","123456","qwerty","letmein","admin","welcome"]
        return [
            min(len(pwd)/20, 1.0),
            1.0 if any(c.isupper() for c in pwd) else 0.0,
            1.0 if any(c.islower() for c in pwd) else 0.0,
            1.0 if any(c.isdigit() for c in pwd) else 0.0,
            1.0 if any(c in "!@#$%^&*()_+" for c in pwd) else 0.0,
            0.0 if any(c in pwd.lower() for c in common) else 1.0,
            min(len(set(pwd))/20, 1.0),
        ]

    def _generic(self, data: str) -> list:
        return [
            min(len(data)/500, 1.0),
            data.count("\n")/50,
            sum(1 for c in data if c.isdigit())/max(len(data),1),
            1.0 if "http" in data.lower() else 0.0,
            min(len(set(data))/50, 1.0),
            data.count(".")/20,
            data.count("@")/5,
            min(len(data.split())/100, 1.0),
        ]
