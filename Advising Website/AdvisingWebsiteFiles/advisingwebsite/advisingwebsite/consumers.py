from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
import json
from advisingwebsiteapp.models import Message, Chat

User = get_user_model()

class ChatConsumer(WebsocketConsumer):

    def fetch_messages(self, data):
        chat = Chat.objects.filter(id=data['chat_id']).first()
        messages = chat.last_10_messages()
        messages = messages[::-1] #Flips message order so they are in the correct order to be displayed
        content = {
            'command': 'messages',
            'messages': self.messages_to_json(messages)
        }
        self.send_message(content)

    def new_message(self, data):
        author = data['from']
        user = User.objects.filter(email=author).first()
        chat_member = user.joined_chats.filter(chat__id=data['chat_id']).first()
        message = Message.objects.create(
            sent_by_member=chat_member,
            chat=Chat.objects.filter(id=data['chat_id']).first(),
            message_content=data['message'])
        content = {
            'command': 'new_message',
            'message': self.message_to_json(message)
        }
        return self.send_chat_message(content)

    def messages_to_json(self, messages):
        result = []
        for message in messages:
            result.append(self.message_to_json(message))
        return result

    def message_to_json(self, message):
        return {
            'author': message.sent_by_member.user.email.strip('"'),
            'content': message.message_content,
            'date_sent': str(message.date_sent)
        }

    commands = {
        'fetch_messages': fetch_messages,
        'new_message': new_message
    }

    def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.room_id = 'chat_%s' % self.chat_id
        async_to_sync(self.channel_layer.group_add)(
            self.room_id,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_id,
            self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)
        self.commands[data['command']](self, data)
        

    def send_chat_message(self, message):    
        async_to_sync(self.channel_layer.group_send)(
            self.room_id,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    def send_message(self, message):
        self.send(text_data=json.dumps(message))

    def chat_message(self, event):
        message = event['message']
        self.send(text_data=json.dumps(message))