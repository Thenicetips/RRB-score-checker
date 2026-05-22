from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

# Custom filter to process cell content
@app.template_filter('classify')
def classify_cell(cell):
    # Remove digits and split into words
    words = re.sub(r'\d+', '', cell).split()
    # Take the first two words and join them with a dash (or leave empty if none)
    return '-'.join(words[:2]).lower() if words else 'no-class'

app.jinja_env.filters['classify'] = classify_cell

# Function to scrape a webpage
def scrape_webpage(url):
    response = requests.get(url)
    response.raise_for_status()  # Check for HTTP request errors
    return BeautifulSoup(response.content, 'html.parser')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get URL from form
        url = request.form.get('url')
        try:
            # Scrape the webpage
            soup = scrape_webpage(url)

            # Main info extraction
            main_info_panels = []
            main_info_divs = soup.find_all('div', class_='main-info-pnl')
            for main_info_div in main_info_divs:
                panel = {"strong_text": None, "table_rows": []}
                
                # Extract strong tag text
                strong_tag = main_info_div.find('strong')
                #panel["strong_text"] = strong_tag.text.strip() if strong_tag else "No strong tag found!"

                # Extract table rows
                table = main_info_div.find('table')
                if table:
                    rows = table.find_all('tr')
                    for row in rows:
                        tds = row.find_all('td')
                        panel["table_rows"].append([td.text.strip() for td in tds])

                main_info_panels.append(panel)

            # Section data extraction
            bold_spans = soup.find_all('span', class_='bold')
            sections = []

            overall_correct = 0
            overall_wrong = 0
            overall_not_answered = 0

            for span in bold_spans:
                section_name = span.text.strip()
                section_data = {"name": section_name, "correct": 0, "wrong": 0, "not_answered": 0}

                # Find questions
                section_div = span.find_parent('div', class_='section-cntnr')
                if section_div:
                    question_divs = section_div.find_all('div', class_='question-pnl')
                    for question_div in question_divs:
                        question_td = question_div.find_all('td', class_='bold')
                        if question_td and len(question_td) > 1:
                            question_text = question_td[1].text.strip()
                        else:
                            section_data["not_answered"] += 1
                            continue

                        # Right answer and user response comparison
                        right_ans_td = question_div.find('td', class_='rightAns')
                        right_ans = right_ans_td.text.strip() if right_ans_td else "---"

                        last_td_table = question_div.find('table', class_='menu-tbl')
                        last_td = last_td_table.find_all('td')[-1].text.strip() if last_td_table else "---"

                        right_ans_digit = re.search(r'\d', right_ans)
                        last_td_digit = re.search(r'\d', last_td)

                        if not right_ans_digit or not last_td_digit:
                            section_data["not_answered"] += 1
                        elif right_ans_digit.group() == last_td_digit.group():
                            section_data["correct"] += 1
                        else:
                            section_data["wrong"] += 1

                # Update overall counters
                overall_correct += section_data["correct"]
                overall_wrong += section_data["wrong"]
                overall_not_answered += section_data["not_answered"]

                sections.append(section_data)

            # Render template
            return render_template(
                'results.html',
                main_info_panels=main_info_panels,
                sections=sections,
                overall={"correct": overall_correct, "wrong": overall_wrong, "not_answered": overall_not_answered},
            )

        except Exception as e:
            return f"An error occurred: {e}"

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
