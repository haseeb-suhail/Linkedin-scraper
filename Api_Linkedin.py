from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium.webdriver.common.by import By
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import threading

app = Flask(__name__)
CORS(app)

# Oxylabs Proxy credentials
USERNAME = 'linkedinai927_mfjQF'
PASSWORD = 'Linkedinai927='
ENDPOINT = "pr.oxylabs.io:7777"

scraped_data = {}


# Proxy configuration function
def chrome_proxy(user: str, password: str, endpoint: str) -> dict:
    wire_options = {
        "proxy": {
            "http": f"http://{user}:{password}@{endpoint}",
            "https": f"https://{user}:{password}@{endpoint}",
        }
    }
    return wire_options


# Set up Selenium with proxy
def setup_driver_with_proxy():
    options = Options()
    options.add_argument('--start-maximized')

    # Set up the proxy using selenium-wire's proxy option
    proxies = chrome_proxy(USERNAME, PASSWORD, ENDPOINT)

    # Initialize the Chrome driver with the proxy settings
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        seleniumwire_options=proxies,
        options=options
    )
    return driver


# Scrape the profile data
def scrape_linkedin_profile(linkedin_url):
    global scraped_data
    driver = setup_driver_with_proxy()

    # Login process
    driver.get('https://www.linkedin.com/checkpoint/lg/login')
    time.sleep(3)
    username = driver.find_element(By.ID, 'username')
    username.send_keys("ayeshaasmat.techionik@gmail.com")
    password = driver.find_element(By.ID, 'password')
    password.send_keys("mh11gaming")
    send_btn = driver.find_element(By.XPATH, '//*[@id="organic-div"]/form/div[3]/button')
    send_btn.click()
    time.sleep(5)

    # Navigate to the LinkedIn profile
    driver.get(linkedin_url)
    time.sleep(5)

    try:
        # Scrape name, headline, and summary
        name = driver.find_element(By.CLASS_NAME, 'v-align-middle').text.strip()
        headline = driver.find_element(By.CSS_SELECTOR, "div.text-body-medium").text.strip()
        summary = driver.find_element(By.XPATH,
                                      '//*[@id="profile-content"]/div/div[2]/div/div/main/section[2]/div[3]/div/div/div/span[1]').text.strip()

        # Store the data
        scraped_data = {
            'name': name,
            'headline': headline,
            'summary': summary,
            'experience': [],
            'education': [],
            'skills': []
        }

        # Scrape experience, education, and skills sections
        sections = ['experience', 'education', 'skills']
        for section in sections:
            scrape_linkedin_section(driver, linkedin_url, section)

    except Exception as e:
        print(f"Error scraping profile: {e}")
    finally:
        driver.quit()


# Function to dynamically scrape LinkedIn sections
def scrape_linkedin_section(driver, linkedin_url, section):
    global scraped_data

    section_url = f"{linkedin_url}details/{section}/"
    driver.get(section_url)
    time.sleep(3)

    if section == "experience":
        try:
            experience = driver.find_elements(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section/div[2]/div/div[1]/ul/li')
            num_positions = len(experience)
            print(f"Found {num_positions} experiences.")
            for i in range(0, num_positions):
                try:
                    # Scrape experience
                    try:
                        company_name = driver.find_element(By.XPATH, f'//*[@id="profilePagedListComponent-EXPERIENCE-VIEW-DETAILS-{i}"]/div/div/div[2]/div[1]/a/div/div/div/div/span[1]').text.strip()
                    except:
                        company_name = driver.find_element(By.XPATH, f'//*[@id="profilePagedListComponent-EXPERIENCE-VIEW-DETAILS-{i}"]/div/div/div[2]/div[1]/div/span[1]/span[1]').text.strip()

                    print(f"Company Name: {company_name}")

                    try:
                        time_duration_at_company = driver.find_element(By.XPATH, f'//*[@id="profilePagedListComponent-EXPERIENCE-VIEW-DETAILS-{i}"]/div/div/div[2]/div[1]/a/span/span[1]').text.strip()
                    except:
                        time_duration_at_company = driver.find_element(By.XPATH, f'//*[@id="profilePagedListComponent-EXPERIENCE-VIEW-DETAILS-{i}"]/div/div/div[2]/div[1]/div/span[2]/span[1]').text.strip()

                    print(f"Time Duration at Company: {time_duration_at_company}")

                    try:
                        work_location = driver.find_element(By.XPATH, f'//*[@id="profilePagedListComponent-EXPERIENCE-VIEW-DETAILS-{i}"]/div/div/div[2]/div[1]/a/span[2]/span[1]').text.strip()
                    except:
                        work_location = driver.find_element(By.XPATH, f'//*[@id="profilePagedListComponent-EXPERIENCE-VIEW-DETAILS-{i}"]/div/div/div[2]/div[1]/div/span[3]/span[1]').text.strip()

                    print(f"Work Location: {work_location}")
                except Exception as e:
                    print(f"Error scraping experience at index {i}: {e}")
        except Exception as e:
            print(f"Error scraping experience section: {e}")

    elif section == "education":
        try:
            educations = driver.find_elements(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section/div[2]/div/div[1]/ul/li')
            num_positions = len(educations)
            print(f"Found {num_positions} educations.")
            for i in range(0, num_positions):
                try:
                    institute_name = driver.find_element(By.XPATH, f'//*[@id="profilePagedListComponent-EDUCATION-VIEW-DETAILS-{i}"]/div/div/div[2]/div[1]/a/div/div/div/div/span[1]').text.strip()
                    print(f"Institute Name: {institute_name}")
                except:
                    pass
                try:
                    degree = driver.find_element(By.XPATH, f'//*[@id="profilePagedListComponent-EDUCATION-VIEW-DETAILS-{i}"]/div/div/div[2]/div[1]/a/span[1]/span[1]').text.strip()
                    print(f"Degree: {degree}")
                except:
                    pass
                try:
                    duration = driver.find_element(By.XPATH, f'//*[@id="profilePagedListComponent-EDUCATION-VIEW-DETAILS-{i}"]/div/div/div[2]/div[1]/a/span[2]/span[1]').text.strip()
                    print(f"Duration: {duration}")
                except:
                    pass
        except Exception as e:
            print(f"Error scraping education section: {e}")

    elif section == "skills":
        try:
            skills = driver.find_elements(By.XPATH, '//*[@id="profilePagedListComponent-SKILLS-VIEW-DETAILS-profileTabSection-ALL-SKILLS-NONE-en-US"]/div/div/div[1]/ul/li')
            num_positions = len(skills)
            print(f"Found {num_positions} skills.")
            for i in range(0, num_positions):
                try:
                    skill_name = driver.find_element(By.XPATH, f'//*[@id="profilePagedListComponent-SKILLS-VIEW-DETAILS-{i}"]/div/div/div[2]/div[1]/a/div/div/div/div/span[1]').text.strip()
                    print(f"Skill: {skill_name}")
                except:
                    pass
        except Exception as e:
            print(f"Error scraping skills section: {e}")



# API to submit LinkedIn URL for scraping
@app.route('/submit', methods=['POST'])
def submit_linkedin_url():
    data = request.get_json()
    app.logger.info(f"Received data: {data}")  # Add this line
    linkedin_url = data.get('linkedin_url')
    if not linkedin_url:
        return jsonify({'error': 'No LinkedIn URL provided'}), 400

    scraping_thread = threading.Thread(target=scrape_linkedin_profile, args=(linkedin_url,))
    scraping_thread.start()

    return jsonify({'message': 'Scraping started for ' + linkedin_url}), 200



# API to get scraped data
@app.route('/data', methods=['GET'])
def get_scraped_data():
    return jsonify(scraped_data)


# Start the Flask app
if __name__ == '__main__':
    app.run(port=5000, debug=True)
