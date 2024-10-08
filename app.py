from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import requests
import logging
import os 
import threading
import time
import json
from collections import deque

# 設置日誌級別
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# 使用原始的環境變量設置
configuration = Configuration(access_token='NWmFHK/y6vv0B9AOfTMiyKNHtnw7cHXwuDnz+CkAqiO44NLXWhPj0PUPZT5UTzVlT1A/X24pvnKCMCYohffQAuABfKYtfMbfe5tcXGy1JYJx8whrvJiw8D5l27v3xAe/dYStjwBSRAn6r4Ick0NKCQdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('d01197870f2bb7c6f403e85bff251537')
perplexity_api_key = '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'

# 任務隊列
task_queue = deque()
stop_event = threading.Event()
task_thread = None
is_first_request = True

def process_tasks():
    app.logger.info("Task processing thread started")
    while not stop_event.is_set():
        if task_queue:
            user_id, query = task_queue.popleft()
            app.logger.info(f"Processing task for user {user_id}: {query}")
            try:
                ai_response = get_perplexity_response(query)
                app.logger.info(f"Received AI response: {ai_response[:100]}...")  # 記錄回應的前100個字符
                send_message(user_id, ai_response)
                app.logger.info(f"Sent response to user {user_id}")
            except Exception as e:
                app.logger.error(f"Error processing task: {e}")
                send_message(user_id, "溫馨提醒：使用【問大神】請直接接續問題:)")
        time.sleep(1)
    app.logger.info("Task processing thread stopped")

@app.before_request
def before_request():
    global is_first_request, task_thread
    if is_first_request:
        app.logger.info("Starting task processing thread")
        task_thread = threading.Thread(target=process_tasks, daemon=True)
        task_thread.start()
        is_first_request = False

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    
    if not signature:
        app.logger.warning("X-Line-Signature is missing")
        return 'OK', 200
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.warning("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK'

def get_perplexity_response(query):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {perplexity_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [
           {"role": "system", "content": "你是一個有幫助的助手。請用繁體中文回答，並從台灣的角度出發。假設用戶位於台灣，除非他們特別說明。對於天氣、當地新聞或活動等問題，預設回答台灣的情況。提供準確、簡潔但信息豐富的回答，盡量控制在3000字以內。"},
           {"role": "user", "content": query}
        ],
         "max_tokens": 800
    }
    try:
        app.logger.info(f"Sending request to Perplexity API: {json.dumps(data, ensure_ascii=False)}")
        response = requests.post(url, json=data, headers=headers, timeout=120)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        app.logger.info(f"Received response from Perplexity API: {content}")
        return content[:3000]
    except requests.RequestException as e:
        app.logger.error(f"Error when calling Perplexity API: {e}")
        app.logger.error(f"Response content: {response.text}")
        raise

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    triggers = ['問大神', '請問大神', '大神']
    
    if any(user_message.startswith(trigger) for trigger in triggers):
        matched_trigger = next(trigger for trigger in triggers if user_message.startswith(trigger))
        query = user_message[len(matched_trigger):].strip()
        
        app.logger.info(f"Adding task to queue for user {event.source.user_id}: {query}")
        task_queue.append((event.source.user_id, query))
    else:
        app.logger.info(f"Received non-AI message: {user_message}")

def send_message(user_id, message):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=message)]
            )
        )

@app.route("/ping", methods=['GET', 'POST'])
def ping():
    app.logger.info("Received ping request")
    return 'pong', 200

@app.errorhandler(500)
def internal_error(error):
    app.logger.error('Server Error: %s', error)
    return "500 Internal Server Error", 500

@app.before_request
def log_request_info():
    app.logger.info('Headers: %s', request.headers)
    app.logger.info('Body: %s', request.get_data())

@app.after_request
def log_response_info(response):
    app.logger.info('Response Status: %s', response.status)
    app.logger.info('Response: %s', response.get_data())
    return response

if __name__ == "__main__":
    app.logger.info("Starting the application")
    port = int(os.environ.get('PORT', 5001))  # 默認使用 5001，但允許環境變量覆蓋
    app.logger.info(f"Application will run on port {port}")
    app.run(host='0.0.0.0', port=port)
