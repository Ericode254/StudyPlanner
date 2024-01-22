from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import openai
import os
from dotenv import load_dotenv
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.utils import secure_filename
from datetime import datetime
from kybra import query

load_dotenv()

openai.api_key = os.getenv("openai-api-key")

app = Flask(__name__)
CORS(app)

# Setup logger
handler = RotatingFileHandler('info.log', maxBytes=100000, backupCount=3)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)


@app.route('/', methods=['GET'])
def frontend():
    return render_template('index.html')


@app.route('/study_plan_creator_frontend', methods=['POST', 'GET'])
def study_plan_creator_frontend():
    return render_template('study_plan_creator_frontend.html')


@app.route('/study_plan_creator', methods=['POST', 'GET'])
def study_plan_creator():
    # print(request.form)
    goal = request.form.get('goal')
    timeframe = request.form.get('timeframe')
    project_type = request.form.get('project_type')
    reference_preference = request.form.get('reference_preference')
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f'Stated Time on study plan creator: {time}')
    logger.info(f'Goal: {goal}')
    logger.info(f'Timeframe: {timeframe}')
    logger.info(f'Project Type: {project_type}')
    logger.info(f'Reference Preference: {reference_preference}')

    # Define the dictionary
    experts = {
        'coding': 'Senior Engineer',
        'art': 'Artist',
        'art & craft': 'Craftsman',
        'music': 'Musician',
        'dance': 'Dancer',
        'cooking': 'Chef',
        'photography': 'Photographer',
        'writing': 'Author',
        'design': 'Designer',
        'marketing': 'Marketing Specialist',
        'finance': 'Financial Analyst',
        'science': 'Scientist',
        'mathematics': 'Mathematician',
        'history': 'Historian',
        'philosophy': 'Philosopher'
    }

    # print(experts)
    # Get the expert for the given project type
    expert = experts.get(project_type, 'General Coding Expert')
    # expert = experts[project_type]
    # print(expert)
    system_prompt = f'''
    Suppose you are {expert}. You also works as a tutor of {project_type} and creates study plans to help people to learn different topics.
    You will be provided with the goal of the student, their time commitment, and resource preferences.
    You will create a study plan with timelines and links to resources. 
    Only include relevant resources because time is limited.
    '''

    query = f'''
    {goal}. I can study on this topic for {timeframe}. I only want {reference_preference} as references.
    Make a {timeframe.split()[-1].replace('s', '')}-by-{timeframe.split()[-1].replace('s', '')} plan with detailed steps and references.
    '''

    print(system_prompt, query)

    try:
        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=[{
                'role': 'system', 'content': system_prompt,
                'role': 'user', 'content': query

            }],
            max_tokens=2000,
            temperature=0.1
        )
    except Exception as e:
        print(e)
        logger.error(f'Error: {e}')
        return jsonify({"error": e})

    # print(response.choices[0].message.content)
    logger.info(f'Response: {response.choices[0].message.content}')
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f'End Time on study plan creator: {time}')

    return jsonify({"response": response.choices[0].message.content})



    @query
    def display_info() -> str:
        return "Hello"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
