from flask import Flask, request, abort
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import requests
import logging
import os
# 設置日誌級別
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

import logging

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# 使用環境變量

configuration = Configuration(access_token='NWmFHK/y6vv0B9AOfTMiyKNHtnw7cHXwuDnz+CkAqiO44NLXWhPj0PUPZT5UTzVlT1A/X24pvnKCMCYohffQAuABfKYtfMbfe5tcXGy1JYJx8whrvJiw8D5l27v3xAe/dYStjwBSRAn6r4Ick0NKCQdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('d01197870f2bb7c6f403e85bff251537')
perplexity_api_key = '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'

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.warning("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK'


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    triggers = ['問大神', '請問大神', '大神']
    
    if any(user_message.startswith(trigger) for trigger in triggers):
        # 找到匹配的觸發詞
        matched_trigger = next(trigger for trigger in triggers if user_message.startswith(trigger))
        query = user_message[len(matched_trigger):].strip()  # 移除觸發詞並去除空白
        app.logger.info(f"Querying Perplexity AI with: {query}")
        ai_response = get_perplexity_response(query)
        
        app.logger.info(f"Sending response to LINE: {ai_response}")
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=ai_response)]
                )
            )
    else:
        app.logger.info(f"Received non-AI message: {user_message}")

import json

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
         "max_tokens": 800  # 調整為較小的值，大約對應3000字符
    }
    try:
        app.logger.info(f"Sending request to Perplexity API: {json.dumps(data, ensure_ascii=False)}")
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        app.logger.info(f"Received response from Perplexity API: {content}")
        return content[:3000]  # 確保回應不超過3000字符
    except requests.RequestException as e:
        app.logger.error(f"Error when calling Perplexity API: {e}")
        app.logger.error(f"Response content: {response.text}")
        return "抱歉，大神現在有點忙。請稍後再問問看吧！"
    
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    triggers = ['問大神', '請問大神', '大神']
    
    if any(user_message.startswith(trigger) for trigger in triggers):
        # 找到匹配的觸發詞
        matched_trigger = next(trigger for trigger in triggers if user_message.startswith(trigger))
        query = user_message[len(matched_trigger):].strip()  # 移除觸發詞並去除空白
        app.logger.info(f"Querying Perplexity AI with: {query}")
        ai_response = get_perplexity_response(query)
        
        app.logger.info(f"Sending response to LINE: {ai_response}")
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=ai_response)]
                )
            )
    else:
        app.logger.info(f"Received non-AI message: {user_message}")
    

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5001))  # 默認使用 5001，但允許環境變量覆蓋
    app.run(host='0.0.0.0', port=port)
