# EmpatheticAI


Setting up environment 

Step 1 : Download The Virutal Package In Your Computer
pip install virtualenv

Step 2 : Change To The Project Folder Directory
cd /Users/nithiyapriyaramesh/Desktop/codes/RAG_sourcecode

Step 3 : Create Virtual Environment
python3 -m venv env

Step 4 : Activate Virutal Environment
source env/bin/activate

Step 5 : Install Required Packages From Requirements.txt
pip install -r requirements.txt

Step 6 : Create .env file & include API KEY
touch .env
OPENAI_API_KEY=<addkey>

Step 7 : Create .env file & include API KEY

Step 8 :  change file path for static files in line 216 (directory = '/Users/nithiyapriyaramesh/Desktop/LLM_RAG/RAG_sourcecode/static/www.burpple.com')

Step 9 : To Run The Flask Project
python main.py

Step 10 : Copy The Local Host Link And Paste It To The Browser For Example:
http://127.0.0.1:5000

it might take a while to load
