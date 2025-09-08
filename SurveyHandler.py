from abc import ABC, abstractmethod
from openai import OpenAI
import os
from dotenv import load_dotenv
import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from datetime import date, datetime
from selenium.webdriver.common.keys import Keys

load_dotenv(dotenv_path="api.env")  # או תשנה את שם הקובץ ל־.env ואז לא צריך פרמטר
api_key = os.getenv("api")
client = OpenAI(api_key=api_key)

class Survey(ABC):
    def __init__(self, link_texts, driver):
        self.link_texts = link_texts
        self.driver = driver

        self.question_container = ""
        self.query_location = ""
        self.continue_location = ""
        self.send_location = ""
        self.radio_container = ""
        self.radio_value_location = ""
        self.table_question_title = ""
        self.table_options_containers = ""

        self.question_text = ""
        self.pageQuestion = None

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
                continueBtn = self.get_continue_btn()
                if not continueBtn: return True
                pageQuestions = self.get_page_questions()
                for i in range(len(pageQuestions)):
                    time.sleep(1)
                    self.pageQuestion = pageQuestions[i]
                    self.question_text = self.get_question(self.pageQuestion,self.query_location)
                    if(self.handle_radio_matrix()): pass
                    elif(self.handle_radio()): pass
                    if(self.handle_checkbox_matrix()): pass
                    if(self.handle_select()): pass
                    if(self.handle_text()): pass
                    try: continueBtn.click()
                    except Exception: pass
                    pageQuestionsNEW = self.get_page_questions()
                    if len(pageQuestionsNEW) != len(pageQuestions): break                                        #  אם בעמוד הנוכחי אין אותו מספר שאלות - דף חדש
                    if self.get_question(pageQuestionsNEW[i],self.query_location) != self.question_text: break   #  אם השאלה בעמוד הקודם והנוכחי שונה - דף חדש
                    else:                                                                                        #  אם השאלה בעמוד הקודם והנוכחי דומה - רענון
                        pageQuestions = pageQuestionsNEW                                                         #  נעדכן את השאלות הנוכחות
                        continueBtn = self.get_continue_btn()                                                    #
                if not pageQuestions: continueBtn.click()
                time.sleep(0.5)
        except Exception as e:
            print(f"❌ שגיאה במילוי הסקר: {e}")
            self.handle_exception()
            return False

    def get_page_questions(self):
        try:
            questions = self.driver.find_elements(By.CLASS_NAME, self.question_container)
            return questions
        except Exception as e:
            print(f"❌ שגיאה כללית בשליפת תשובות: {e}")
            return None
    def get_question(self,container, query_location=""):
        try:
            outer = container.find_element(By.CLASS_NAME, query_location) if query_location else container
            inner_elements = outer.find_elements(By.XPATH, ".//*")
            for elem in inner_elements:
                text = elem.text.strip()
                if text: return text
            return outer.text.strip()
        except Exception as e:
            print(f"❌ שגיאה באחזור טקסט: {e}")
        return ""
    def get_continue_btn(self):
        for by in [By.NAME, By.CLASS_NAME]:
            for val in [self.continue_location, self.send_location]:
                try:
                    button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by, val))
                    )
                    return button
                except:
                    continue
        print("❌ לא נמצא כפתור כניסה/המשך (לא לפי NAME ולא לפי CLASS_NAME)")
        return None

    def handle_radio_matrix(self):
        try:
            rows = self.pageQuestion.find_elements(By.CSS_SELECTOR, "tbody > tr")
            # table_options_containers = rows[0].find_elements(By.CLASS_NAME, self.table_options_containers)
            table_options_containers = self.pageQuestion.find_elements(By.CSS_SELECTOR, "thead th")[1:]
            options_text = [self.get_question(o) for o in table_options_containers]
            for i,row in enumerate(rows):
                try:
                    row_question = self.get_question(row, self.table_question_title)
                    if not row_question: continue
                    radio_inputs = row.find_elements(By.CSS_SELECTOR, 'input[type="radio"], ins')
                    visible = []
                    for el in radio_inputs:
                        try:
                            style = (el.get_attribute("style") or "").lower()
                            hidden_attr = (el.get_attribute("hidden") or "").lower()
                            display_none = "display: none" in style
                            if not display_none and hidden_attr != "true":
                                visible.append(el)
                        except Exception:
                            continue
                    answer_indexes = self.ask_chatgpt_for_index(options_text,row_question)
                    for answer_index in answer_indexes:
                        if answer_index is not None and 0 <= answer_index < len(radio_inputs):
                            self.set_checked(radio_inputs[answer_index])
                        else:
                            print(f"⚠️ לא נמצאה תשובה מתאימה ל: {row_question}")
                except Exception as row_e:
                    print(f"שגיאה בשורת טבלה: {row_e}")
                    return False
            return len(rows) > 0
        except Exception as e:
            print(f"❌ שגיאה בטבלת מטריצה: {e}")
        return False
    def handle_checkbox_matrix(self):
        try:
            rows = self.pageQuestion.find_elements(By.CSS_SELECTOR, "tbody > tr")
            headers = self.pageQuestion.find_elements(By.CSS_SELECTOR, "thead th")[1:]  # הכותרות של הטבלה (למעט העמודה הראשונה)
            option_texts = []
            for header in headers:
                text = header.text.strip()
                if text:
                    option_texts.append(text)
            for row in rows:
                try:
                    cells = row.find_elements(By.CSS_SELECTOR, "td")
                    if not cells:
                        continue
                    question_text = cells[0].text.strip()
                    inputs = []
                    for i, cell in enumerate(cells[1:]):
                        try:
                            checkbox = cell.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                            inputs.append((option_texts[i], checkbox))
                        except:
                            continue
                    if not inputs:
                        continue
                    options = [text for text, _ in inputs]
                    answer_indexes = self.ask_chatgpt_for_index(options,question_text)
                    for answer_index in answer_indexes:
                        if answer_index is not None and 0 <= answer_index < len(inputs):
                            try:
                                self.set_checked(inputs[answer_index][1])
                            except ElementClickInterceptedException:
                                label = self.pageQuestion.find_element(By.CSS_SELECTOR,f"label[for='{inputs[answer_index][1].get_attribute('id')}']")
                                self.set_checked(label)
                        else:
                            print(f"⚠️ לא נבחרה תשובה ל: {question_text}")
                except Exception as row_e:
                    print(f"⚠️ שגיאה בשורת טבלה: {row_e}")
                    continue
            return len(rows) > 0
        except Exception as e:
            print(f"❌ שגיאה בטבלת צ'קבוקסים כללית: {e}")
            return False

    def get_radio(self):
        try:
            labels = self.pageQuestion.find_elements(By.CLASS_NAME, self.radio_container)
            options = []
            for label in labels:
                try:
                    spans = label.find_elements(By.TAG_NAME, self.radio_value_location)
                    if not spans:
                        spans = label.find_elements(By.CLASS_NAME, self.radio_value_location)
                    text_span = next((span for span in spans if span.text.strip()), None)
                    if label and text_span:
                        answer_text = text_span.text.strip()
                        options.append((answer_text, label))
                except Exception as inner_e:
                    print(f"שגיאה ב-label בודד: {inner_e}")
                    continue
            return options if options else None
        except Exception as e:
            print(f"❌ שגיאה כללית בשליפת תשובות: {e}")
            return None
    def handle_radio(self):
        radios = self.get_radio()
        if radios:
            answers = [ans for (ans, _) in radios]
            answer_indexes = self.ask_chatgpt_for_index(answers)
            for answer_index in answer_indexes:
                if answer_index is not None and 0 <= answer_index < len(radios):
                    chosen_answer = radios[answer_index][1]
                    self.set_checked(chosen_answer)
            return True
    def get_select(self):
        try:
            select_elem = self.pageQuestion.find_element(By.TAG_NAME, "select")
            select = Select(select_elem)
            options = [option.text.strip() for option in select.options if option.get_attribute("value") != "null"]
            return options, select
        except Exception as e:
            print(f"❌ שגיאה כללית בשליפת תשובות בחירה: {e}")
            return None, None
    def handle_select(self):
        options, select_element = self.get_select()
        if options:
            answer_indexes = self.ask_chatgpt_for_index(options)
            for answer_index in answer_indexes:
                if answer_index is not None and 0 <= answer_index < len(options):
                    select_element.select_by_index(answer_index+1)  # מדלגים על "בחר תשובה"
            return True

    def set_checked(self, element, checked=True):
        element.click()
        try: self.driver.execute_script("arguments[0].checked = arguments[1];", element, checked)
        except Exception: pass

    def get_text_inputs(self):
        try:
            inputs = self.pageQuestion.find_elements(By.CSS_SELECTOR, 'input:not([type]), input[type="text"], textarea')
            visible_inputs = []
            for inp in inputs:
                input_type = (inp.get_attribute("type") or "").lower()
                style = (inp.get_attribute("style") or "").lower()
                if input_type == "hidden": continue
                if "display: none" in style: continue
                if not inp.is_displayed(): continue
                visible_inputs.append(inp)
            if not visible_inputs:
                inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input:not([type]), input[type="text"], textarea')
                for inp in inputs:
                    input_type = (inp.get_attribute("type") or "").lower()
                    style = (inp.get_attribute("style") or "").lower()
                    if input_type == "hidden": continue
                    if "display: none" in style: continue
                    if not inp.is_displayed(): continue
                    visible_inputs.append(inp)
            return visible_inputs if visible_inputs else None

        except Exception as e:
            print(f"❌ שגיאה בשליפת input טקסט: {e}")
            return None
    def handle_text(self):
        text_inputs = self.get_text_inputs()
        if text_inputs:
            if not self.question_text:
                for ti in text_inputs:
                    question_con = ti.find_element(By.XPATH, "..")
                    self.question_text += self.get_question(question_con) + ", "
            responses = self.ask_chatgpt_for_texts(len(text_inputs))
            for input_elem, text in zip(text_inputs, responses):
                input_elem.clear()
                input_elem.send_keys(text)
                time.sleep(0.2)
                try: input_elem.send_keys(Keys.ENTER)
                except Exception: pass
            return True

    def ask_chatgpt_for_index(self, answers, addon=""):
        options_block = "\n".join(f"{i}. {a}" for i, a in enumerate(answers))
        prompt = (
f"""שמי אדם סין, רווק, בלי ילדים, נולדתי ב02/02/2004, סטודנט למדעי המחשב שנה ג' מפתח תקווה. התאריך הוא {date.today()}
אני רוצה למלא סקר עם תשובות רנדומליות אך הגיוניות לנתוניי. השאלה:
{self.question_text} - {addon}
תשובות אפשריות:
{options_block}
החזר רק את מספר התשובה המתאימה (למשל: 2)""")
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            reply = response.choices[0].message.content.strip()
            matches = re.findall(r"\d+", reply)
            return [int(m) for m in matches] if matches else []
        except Exception as e:
            print(f"ChatGPT error: {e}")
            return None
    def ask_chatgpt_for_texts(self, num_fields):
        prompt = (
f"""שמי אדם סין, רווק, בלי ילדים, נולדתי ב02/02/2004, סטודנט למדעי המחשב שנה ג' מפתח תקווה. התאריך הוא {date.today()}
השאלה הבאה היא שאלה פתוחה עם{num_fields} שדות קלט.
אנא החזר בדיוק{num_fields} תשובות, כל אחת מתאימה לשדה לפי הסדר וקצרה אם לא נאמר אחרת.
תשובות יכתבו כך:
1. תשובה ראשונה
2. תשובה שנייה
...
שאלה:{self.question_text}""")
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            reply = response.choices[0].message.content.strip()
            matches = re.findall(r"^\d+\.\s*(.+)$", reply, re.MULTILINE)
            if len(matches) == num_fields:
                return matches
            else:
                print(f"⚠️ כמות התשובות שחזרה לא תואמת את מספר השדות ({len(matches)} מתוך {num_fields})")
                return [""] * num_fields
        except Exception as e:
            print(f"ChatGPT error: {e}")
            return ["" for _ in range(num_fields)]
