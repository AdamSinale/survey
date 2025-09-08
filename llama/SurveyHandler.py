from abc import ABC, abstractmethod
import time
import re, json

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from llama_cpp import Llama

_llm = None
def get_llm():
    global _llm
    if _llm is not None:
        return _llm
    _llm = Llama(model_path="AI/Nous-Hermes-2-Mistral-7B-DPO.Q5_K_M.gguf", n_ctx=2048)
    return _llm

selectors = [By.ID, By.CLASS_NAME]

class Survey(ABC):
    def __init__(self, link_texts, driver):
        self.link_texts = link_texts
        self.driver = driver

        self.continue_location = ""
        self.send_location = ""
        self.page_container = ""

    @abstractmethod
    def handle_exception(self):
        pass
    def get_link(self):
        for text in self.link_texts:
            try:
                link = self.driver.find_element(By.XPATH, f"//a[contains(text(),'{text}')]")
                return link
            except:
                continue
        self.handle_exception()
        return None

    def fill_survey(self):
        print("📝 ממלא סקר")
        try:
            while True:
                if not self.get_continue_btn(): return True
                wait = WebDriverWait(self.driver, 20)
                containers = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME,self.page_container)))
                for container in containers:
                    html = container.get_attribute("outerHTML")
                    answers_plan = extract_answers_llama(html)
                    answer_objects = []
                    for v in answers_plan.values():
                        if isinstance(v, list):
                            answer_objects.extend(v)
                        elif isinstance(v, dict):
                            answer_objects.append(v)
                    for ans in answer_objects:
                        aid = ans.get("answerId")
                        acls = ans.get("answerClass")
                        atext = ans.get("answerText")
                        acted = False
                        if aid and aid != "NaN":                # 1) לפי ID (כולל label[for] ו-select/textarea)
                            try:
                                lbl = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{aid}']")
                                lbl.click()
                                acted = True
                            except: pass
                            if not acted:
                                try:
                                    el = self.driver.find_element(By.ID, aid)
                                    tag = el.tag_name.lower()
                                    if tag == "select" and atext and atext != "NaN":
                                        Select(el).select_by_visible_text(atext);
                                        acted = True
                                    elif tag in ("input", "button", "label", "span", "div"):
                                        el.click()
                                        acted = True
                                    elif tag == "textarea" and atext and atext != "NaN":
                                        try: el.clear()
                                        except: pass
                                        el.send_keys(atext)
                                        acted = True
                                except: pass
                            if acted:
                                time.sleep(0.3)
                                continue
                        if acls and acls != "NaN":                     # 2) לפי CLASS (רק אם ייחודי)
                            try:
                                els = self.driver.find_elements(By.CLASS_NAME, acls)
                                if len(els) == 1:
                                    el = els[0]
                                    if el.tag_name.lower() == "select" and atext and atext != "NaN":
                                        Select(el).select_by_visible_text(atext)
                                        acted = True
                                    else:
                                        el.click()
                                        acted = True
                            except: pass
                            if acted:
                                time.sleep(0.3)
                                continue

                        if atext and atext != "NaN":                       # 3) לפי טקסט נראה (label/button/span/div) או option בתוך select
                            try:
                                el = self.driver.find_element(
                                    By.XPATH,
                                    f".//*[self::label or self::button or self::span or self::div]"
                                    f"[contains(normalize-space(.), {json.dumps(atext)})]"
                                )
                                el.click()
                                acted = True
                            except:
                                try:
                                    opt = self.driver.find_element(
                                        By.XPATH,
                                        f".//option[contains(normalize-space(.), {json.dumps(atext)})]"
                                    )
                                    sel = opt.find_element(By.XPATH, "./ancestor::select[1]")
                                    Select(sel).select_by_visible_text(atext)
                                    acted = True
                                except: pass
                        if not acted:
                            print(f"❌ - Couldn't act on: {ans}")
                continueBtn = self.get_continue_btn()
                if not continueBtn: return True
                continueBtn.click()
                time.sleep(0.5)

        except Exception as e:
            print(f"❌ שגיאה במילוי הסקר: {e}")
            self.handle_exception()
            return False

    def get_continue_btn(self):
        for by in [By.NAME, By.CLASS_NAME]:
            for val in [self.continue_location, self.send_location]:
                try:
                    button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((by, val))
                    )
                    return button
                except:
                    continue
        print("❌ לא נמצא כפתור כניסה/המשך (לא לפי NAME ולא לפי CLASS_NAME)")
        return None

def extract_answers_llama(file_content: str):
    llm = get_llm()

    system = (
        "You are a strict DOM survey planner. "
        "Return ONLY valid JSON for ONE question. "
        "For radio/single-select: one object. For checkboxes: array. "
        "Use answerId if exists, else answerClass, else answerText. "
        "For text/numeric: put value in answerText. Missing -> 'NaN'. "
        "No prose."
    )
    user = (
        "Profile: Adam Sin, single, no kids, born 2004-02-02, CS grad, Petah Tikva. "
        "If the question asks for AGE, compute it from the birthdate (today).\n"
        'Schema: {"question1":{"question":"...","answerId":"...","answerClass":"NaN","answerText":"..."}}\n'
        "HTML:\n" + file_content
    )

    # ✅ מצב CHAT—מחזיר message.content ולא text
    resp = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        max_tokens=384,          # קצת מרווח
        temperature=0,
    )

    raw = resp["choices"][0]["message"]["content"] or ""
    plan = parse_plan(raw)
    if not isinstance(plan, dict):
        raise ValueError("Model did not return a JSON object")
    return plan

def _extract_first_json(s: str):
    if not isinstance(s, str) or not s.strip(): return None
    s = s.strip()
    s = re.sub(r'^\s*(answer|output|result)\s*:\s*', '', s, flags=re.I)
    m = re.search(r'[\{\[]', s)
    if not m: return None
    i = m.start()
    s = s[i:]
    open_ch = s[0]
    close_ch = '}' if open_ch == '{' else ']'
    depth = 0
    for j, ch in enumerate(s):
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                payload = s[:j+1]
                return payload
    return None

def parse_plan(raw):
    try: return json.loads(raw)
    except Exception: pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, flags=re.I)
    if m:
        try: return json.loads(m.group(1).strip())
        except Exception: pass
    m = re.search(r"\[OUT\]\s*([\s\S]+?)\s*\[/OUT\]", raw, flags=re.I)
    if m:
        try: return json.loads(m.group(1).strip())
        except Exception: pass
    payload = _extract_first_json(raw)
    if payload:
        try: return json.loads(payload)
        except Exception: pass
    return {}