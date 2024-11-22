import os
import re
import openai
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from selenium.webdriver.common.by import By
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import threading

app = Flask(__name__)
CORS(app, supports_credentials=True)


# Serve the React app's static files
# @app.route('/', defaults={'path': ''})
# @app.route('/<path:path>')
# def serve_react(path):
#     if path != "" and os.path.exists(app.static_folder + '/' + path):
#         return send_from_directory(app.static_folder, path)
#     else:
#         return send_from_directory(app.static_folder, 'index.html')


openai.api_key = ('sk-proj-hmQSzOkvXzzpDqm6A0Zy-A9bWYGArHXUq2TBBBuod4B'
                  '-74YZ696OoGohZ6USEwv4EBJ3djlh2vT3BlbkFJQ_4L_xEERm_HjdKlvrr1'
                  '-rW8MI96aCX9g8rHFe94cOZtweDozGpqGyw2cNV1cTJ13DSRf4TYcA')
# Replace with your actual API key  # Replace with your actual API key
# Oxylabs Proxy credentials
USERNAME = 'linkedinai927_mfjQF'
PASSWORD = 'Linkedinai927='
ENDPOINT = "pr.oxylabs.io:7777"

scraped_data = {}
user_responses = {}


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
    # proxies = chrome_proxy(USERNAME, PASSWORD, ENDPOINT)

    # Initialize the Chrome driver with the proxy settings
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        # seleniumwire_options=proxies,
        options=options
    )
    return driver


# Function to validate LinkedIn URL
def validate_linkedin_url(url):
    linkedin_regex = r'^https?:\/\/(www\.)?linkedin\.com\/in\/[a-zA-Z0-9\-]+\/?$'
    return re.match(linkedin_regex, url) is not None


# Scrape the profile data
def scrape_linkedin_profile(linkedin_url):
    global scraped_data

    # List of accounts and passwords to rotate through
    accounts = [
        {"email": "dabc43038@gmail.com", "password": "abcd@1234"},
        {"email": "zxyz89122@gmail.com", "password": "xyz@1234"},
        {"email": "zxz05793@gmail.com", "password": "xz@12345"},
        {"email": "wwx95346@gmail.com", "password": "wwx@1234"}
    ]

    driver = None
    account_used = None

    for account in accounts:
        driver = setup_driver_with_proxy()

        try:
            # Login process using account details
            driver.get('https://www.linkedin.com/checkpoint/lg/login')
            time.sleep(3)

            username = driver.find_element(By.ID, 'username')
            username.send_keys(account["email"])

            password = driver.find_element(By.ID, 'password')
            password.send_keys(account["password"])

            time.sleep(5)
            send_btn = driver.find_element(By.XPATH, '//*[@id="organic-div"]/form/div[3]/button')
            send_btn.click()

            time.sleep(5)
            if "feed" in driver.current_url or "profile" in driver.current_url:
                print(f"Successfully logged in with {account['email']}")
                account_used = account
                break  # Exit loop after successful login

            print(f"Failed login attempt for {account['email']}")

        except Exception as e:
            print(f"Error with account {account['email']}: {e}")
        finally:
            if account_used is None:
                driver.quit()

    # If no account was able to login, stop further processing
    if account_used is None:
        print("All accounts failed to login.")
        return {"error": "All accounts failed to login."}

    # Continue with scraping after successful login
    try:
        driver.get(linkedin_url)
        time.sleep(5)

        name = None
        headline = None
        summary = None

        # Scrape name, headline, and summary
        try:
            name = driver.find_element(By.CLASS_NAME, 'v-align-middle').text.strip()
        except:
            print("Could not scrape name")

        try:
            headline = driver.find_element(By.CSS_SELECTOR, "div.text-body-medium").text.strip()
        except:
            print("Could not scrape headline")

        try:
            summary = driver.find_element(By.XPATH,
                                          '//*[@id="profile-content"]/div/div[2]/div/div/main/section[2]/div[3]/div/div/div/span[1]').text.strip()
        except:
            print("Could not scrape summary")

        # Store the data, using defaults if necessary
        scraped_data = {
            'name': name or "Name not found",
            'headline': headline or "Headline not found",
            'summary': summary or "Summary not found",
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



# Function to generate suggestions using OpenAI API
def generate_suggestions(profile_data):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user",
                   "content": f"Analyze the following LinkedIn profile data and provide suggestions for optimization "
                              f"and only rewrite it section by section :\n\n{profile_data}"}]
    )
    suggestions = response['choices'][0]['message']['content']
    return suggestions


# Function to dynamically scrape LinkedIn sections
def scrape_linkedin_section(driver, linkedin_url, section):
    global scraped_data

    section_url = f"{linkedin_url}/details/{section}/"
    driver.get(section_url)
    time.sleep(10)

    if section == "experience":
        try:
            # Locate the experiences using a more precise selector and filter duplicates
            experience_elements = driver.find_elements(By.CLASS_NAME, 'pvs-list__item--line-separated')

            # Initialize a list to store the formatted experiences
            unique_experiences = []

            # Loop through each experience element and extract relevant details
            for exp_element in experience_elements:
                e_text = exp_element.text.strip()

                # Replace 'to' with '-' to standardize date formats
                e_text = e_text.replace(" to ", " - ")

                # Split the text based on new lines (this helps with removing duplicated lines)
                lines = e_text.split("\n")

                # Use a set to filter out any repeated lines within the same experience block
                unique_lines = list(dict.fromkeys(lines))  # dict.fromkeys() preserves order and removes duplicates

                # Rejoin the filtered lines back into a single string for that experience (without newlines)
                formatted_experience = " ".join(unique_lines)  # Joins with a space instead of a newline

                # Check if the experience has already been added (to avoid duplicates across all experiences)
                if formatted_experience not in unique_experiences:
                    unique_experiences.append(formatted_experience)

            # Store the formatted unique experiences in the scraped_data object
            scraped_data['experience'] = unique_experiences

        except:
            print(f"Error scraping experience section")
            pass

    elif section == "education":
        try:
            # Find all education elements
            educations = driver.find_elements(By.XPATH,
                                              '//*[@id="profile-content"]/div/div[2]/div/div/main/section/div[2]/div/div[1]/ul/li')
            num_positions = len(educations)
            print(f"Found {num_positions} education entries.")

            # Extract institute names/details
            education_Details = driver.find_elements(By.CSS_SELECTOR, '.display-flex a span[aria-hidden="true"]')
            education_details = []

            # Adjust the range if num_positions == 1
            if num_positions == 1:
                loop_range = num_positions + 2
            else:
                loop_range = num_positions * num_positions

            # Ensure the loop runs according to the number of education entries found
            for i in range(loop_range):
                if i < len(education_Details):  # Prevent index error
                    education_text = education_Details[i].text.strip()
                    print(f"Institute Details: {education_text}")
                    education_details.append(education_text)
                else:
                    print(f"Institute Details: Not found for education at index {i}")
                    education_details.append("Details not found")

            scraped_data['education'] = education_details  # Save the education details
        except:
            print(f"Error scraping education section")
            pass

    elif section == "skills":
        try:
            skills = driver.find_elements(By.CSS_SELECTOR,
                                          '[data-field="skill_page_skill_topic"] div div div div span[aria-hidden="true"]')

            skill_details = []

            for s in skills:
                skill_text = s.text.strip().replace(",", '')

                # Only append non-empty skills
                if skill_text:
                    skill_details.append(skill_text)
                    print(f"Skill : {skill_text}")

            # Save the skills details only if there are skills
            if skill_details:
                scraped_data['skills'] = skill_details

        except:
            print(f"Error scraping skills section")
            pass


# API to submit LinkedIn URL for scraping
@app.route('/submit', methods=['POST'])
def submit_linkedin_url():
    data = request.get_json()
    linkedin_url = data.get('linkedin_url')

    # Validate LinkedIn URL
    if not linkedin_url:
        return jsonify({'error': 'No LinkedIn URL provided'}), 400
    if not isinstance(linkedin_url, str) or ',' in linkedin_url:
        return jsonify({'error': 'Please provide a single LinkedIn URL without commas.'}), 400
    if not validate_linkedin_url(linkedin_url):
        return jsonify(
            {'error': 'Invalid LinkedIn URL format. Please use the format: https://www.linkedin.com/in/username/'}), 400

    # Perform scraping directly and keep the POST request active until scraping is done
    scrape_linkedin_profile(linkedin_url)

    return jsonify({'message': 'Scraping complete for ' + linkedin_url, 'data': scraped_data}), 200


# API to get scraped data
@app.route('/data', methods=['GET'])
def get_scraped_data():
    if not scraped_data:
        return jsonify({"error": "No data was found."}), 404  # Return 404 if no data found

    return jsonify(scraped_data), 200  # Return 200 if scraped data is available



@app.route('/gpt-suggestion', methods=['POST'])
def generate_gpt_suggestions():
    global scraped_data
    if not scraped_data:
        return jsonify({'error': 'No scraped data available. Please scrape a LinkedIn profile first.'}), 400

    # Log the request to ensure data is received
    data = request.get_json()
    app.logger.info(f"Received data for GPT suggestion: {data}")

    # Get the responses from the frontend
    looking_for_job = data.get('looking_for_job', '').lower()  # "yes" or "no"
    job_type = data.get('job_type', '')  # "remote", "hybrid", "onsite"
    job_preference = data.get('job_preference', '')  # User input for job preference

    # Construct profile data string from scraped data
    profile_data = f"""
       Headline: {scraped_data.get('headline')}
       Summary: {scraped_data.get('summary')}
       Experience: {scraped_data.get('experience')}
       Education: {scraped_data.get('education')}
       Skills: {scraped_data.get('skills')}
       """

    if looking_for_job == 'yes':
        # If user is looking for a job, tailor the prompt to the job type and preference
        app.logger.info(f"User is looking for a {job_type} job with preference: {job_preference}")

        # Define prompt based on job type and preference
        prompt = f"""
        The user is looking for a {job_type} job. Their job preference is: "{job_preference}". Based on the following LinkedIn profile data, provide detailed suggestions for improvement for each section 
        (Headline, Summary, Experience, Education, Skills) to make the profile more attractive for {job_type} jobs. Also, consider the user's job preference.\n\n{profile_data}
        """
    else:
        # If user is not looking for a job, provide general suggestions for LinkedIn profile improvement
        app.logger.info(f"User is not looking for a job. Generating general profile improvement suggestions.")

        # Define a general prompt for improving the LinkedIn profile
        prompt = f"""
        The user is not actively looking for a job. Based on the following LinkedIn profile data, provide general suggestions for improvement for each section (Headline, Summary, Experience, Education, Skills) to enhance the profile for overall professional growth and networking opportunities.\n\n{profile_data}
        """

    app.logger.info(f"Generated prompt: {prompt}")

    try:
        # Generate suggestions using OpenAI GPT
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        gpt_suggestions = response['choices'][0]['message']['content']

        # Log the suggestions for debugging
        app.logger.info(f"Generated GPT suggestions: {gpt_suggestions}")

        # Structure the GPT suggestions in the same format as the scraped data
        structured_suggestions = {
            'headline': f"Headline Suggestion: {gpt_suggestions.split('Headline:')[1].split('Summary:')[0].strip() if 'Headline:' in gpt_suggestions else scraped_data.get('headline')}",
            'summary': f"Summary Suggestion: {gpt_suggestions.split('Summary:')[1].split('Experience:')[0].strip() if 'Summary:' in gpt_suggestions else scraped_data.get('summary')}",
            'experience': f"Experience Suggestion: {gpt_suggestions.split('Experience:')[1].split('Education:')[0].strip() if 'Experience:' in gpt_suggestions else scraped_data.get('experience')}",
            'education': f"Education Suggestion: {gpt_suggestions.split('Education:')[1].split('Skills:')[0].strip() if 'Education:' in gpt_suggestions else scraped_data.get('education')}",
            'skills': f"Skills Suggestion: {gpt_suggestions.split('Skills:')[1].strip() if 'Skills:' in gpt_suggestions else scraped_data.get('skills')}"
        }

        # Store the structured suggestions in scraped_data for further reference or retrieval
        scraped_data['gpt_suggestions'] = structured_suggestions

        return jsonify({
            'message': 'GPT suggestions generated successfully',
            'suggestions': structured_suggestions
        }), 200

    except Exception as e:
        # Log the error if something goes wrong
        app.logger.error(f"Error generating GPT suggestions: {e}")
        return jsonify({'error': 'Failed to generate suggestions from GPT'}), 500


@app.route('/get-gpt-suggestions', methods=['GET'])
# Endpoint for submitting user responses to GPT suggestions
def get_gpt_suggestions():
    global scraped_data
    # Check if GPT suggestions are available
    if 'gpt_suggestions' not in scraped_data:
        return jsonify({'error': 'No GPT suggestions available. Please generate suggestions first.'}), 400

    # Return only the GPT suggestions without the wrapper
    return jsonify(scraped_data['gpt_suggestions']), 200


def update_linkedin_profile(linkedin_url, linkedin_email, linkedin_password):
    driver = setup_driver_with_proxy()  # Use the driver setup with proxy if required
    try:
        # Login to LinkedIn using user-provided credentials
        driver.get('https://www.linkedin.com/checkpoint/lg/login')
        time.sleep(3)

        username = driver.find_element(By.ID, 'username')
        username.send_keys(linkedin_email)  # Use the email provided by the user
        password = driver.find_element(By.ID, 'password')
        password.send_keys(linkedin_password)  # Use the password provided by the user
        time.sleep(3)
        login_button = driver.find_element(By.XPATH, '//*[@id="organic-div"]/form/div[3]/button')
        login_button.click()
        time.sleep(5)

        # Navigate to the LinkedIn profile
        driver.get(linkedin_url)
        time.sleep(5)

        # Check for approved sections and update the profile accordingly

        # Update headline if approved
        if 'headline' in user_responses[linkedin_url]['responses'] and user_responses[linkedin_url]['responses']['headline'] == 'yes':
            headline_element = driver.find_element(By.CLASS_NAME, 'pv-top-card__headline')
            headline_element.clear()
            headline_element.send_keys(scraped_data.get('headline', 'New GPT-generated headline'))
            time.sleep(3)

        # Update summary if approved
        if 'summary' in user_responses[linkedin_url]['responses'] and user_responses[linkedin_url]['responses']['summary'] == 'yes':
            summary_element = driver.find_element(By.CLASS_NAME, 'pv-about-section')
            summary_element.clear()
            summary_element.send_keys(scraped_data.get('summary', 'New GPT-generated summary'))
            time.sleep(3)

        # Update experience if approved
        if 'experience' in user_responses[linkedin_url]['responses'] and user_responses[linkedin_url]['responses']['experience'] == 'yes':
            # Navigate to the experience section
            driver.get(f'{linkedin_url}/details/experience/')
            time.sleep(5)
            experience_element = driver.find_element(By.CLASS_NAME, 'pvs-list__item--line-separated')
            experience_element.clear()
            experience_element.send_keys(scraped_data.get('experience', ['New GPT-generated experience'])[0])  # Use the first experience for example
            time.sleep(3)

        # Submit the changes
        save_button = driver.find_element(By.XPATH, '//*[@id="save-button-id"]')  # Adjust the selector to match the Save button
        save_button.click()
        time.sleep(3)

    except Exception as e:
        print(f"Error updating LinkedIn profile: {e}")
    finally:
        driver.quit()



@app.route('/submit_response', methods=['POST'])
def submit_response():
    data = request.get_json()
    linkedin_url = data.get('linkedin_url')
    suggestion_type = data.get('suggestion_type')
    response = data.get('response')

    # Additional: Request user credentials for profile update
    linkedin_email = data.get('email')  # User email
    linkedin_password = data.get('password')  # User password

    if not linkedin_url or not suggestion_type or not response:
        return jsonify({'error': 'LinkedIn URL, suggestion type, or response not provided'}), 400

    if response.lower() not in ['yes', 'no']:
        return jsonify({'error': 'Response must be "yes" or "no"'}), 400

    if not linkedin_email or not linkedin_password:
        return jsonify({'error': 'LinkedIn credentials not provided'}), 400

    if linkedin_url in user_responses:
        user_responses[linkedin_url]['responses'][suggestion_type] = response.lower()
    else:
        user_responses[linkedin_url] = {'suggestions': {}, 'responses': {suggestion_type: response.lower()}}

    # If all sections are approved, trigger LinkedIn update
    if all(val == 'yes' for val in user_responses[linkedin_url]['responses'].values()):
        # Pass the credentials to the update function
        update_linkedin_profile(linkedin_url, linkedin_email, linkedin_password)

    return jsonify({'message': 'Response and credentials recorded successfully'}), 200


# Endpoint to fetch suggestions and user responses for a profile
@app.route('/get_user_responses', methods=['GET'])
def get_user_responses():
    linkedin_url = request.args.get('linkedin_url')
    if not linkedin_url or linkedin_url not in user_responses:
        return jsonify({'error': 'No data found for the given LinkedIn URL'}), 404

    return jsonify(user_responses[linkedin_url]), 200


@app.route('/submit', methods=['OPTIONS'])
@app.route('/data', methods=['OPTIONS'])
def options():
    response = jsonify({'message': 'CORS preflight allowed'})
    response.headers.add('Access-Control-Allow-Origin', '*')  # or specify a domain like 'http://localhost:3000'
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')  # This is for allowing credentials
    return response



# Start the Flask app
if __name__ == '__main__':
    app.run(port=5000, debug=True)
